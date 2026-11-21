"""Web entry point for the single-user research library."""

import hmac
import io
import os
import re
import secrets
from pathlib import Path

from pypdfium2 import PdfiumError

from flask import (
    Flask, abort, flash, redirect, render_template, request, send_file, session, url_for,
)

from .ingest import FIELD_LIMITS, MAX_PAGES, MAX_UPLOAD_BYTES, InvalidPDF, normalize_doi, parse_pdf
from .preview import render_page_png
from .store import Library

FIELD_SOURCES = {
    "pdf_metadata": "PDF 元数据",
    "opening_text": "首页文本推断",
    "filename": "文件名",
    "manual": "手动填写",
}
PAGE_STATUS = {
    "available": "已提取文本",
    "no_text": "未检测到可提取文本",
    "extraction_failed": "本页文本解析失败",
    "truncated": "文本已截断",
}


def create_app(config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=secrets.token_bytes(32),
        LIBRARY_DB=os.environ.get("LITERATURE_DB", str(Path(app.instance_path) / "literature.sqlite3")),
        MAX_CONTENT_LENGTH=MAX_UPLOAD_BYTES + 128 * 1024,
        MAX_FORM_MEMORY_SIZE=256 * 1024,
        MAX_FORM_PARTS=32,
        SESSION_COOKIE_SAMESITE="Strict",
        TRUSTED_HOSTS=["127.0.0.1", "localhost", "[::1]"],
    )
    app.config.update(config or {})
    library = Library(app.config["LIBRARY_DB"])
    app.extensions["research_library"] = library

    def csrf_token():
        if "csrf_token" not in session:
            session["csrf_token"] = secrets.token_urlsafe(32)
        return session["csrf_token"]

    app.jinja_env.globals.update(csrf_token=csrf_token, field_sources=FIELD_SOURCES, page_status=PAGE_STATUS)

    @app.before_request
    def validate_form():
        if request.method != "POST":
            return
        supplied = request.form.get("csrf_token", "")
        expected = session.get("csrf_token")
        if not expected or not supplied.isascii() or not hmac.compare_digest(expected, supplied):
            abort(400, "表单已过期。请刷新页面后再试。")

    @app.after_request
    def browser_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; "
            "frame-src 'self'; frame-ancestors 'self'; form-action 'self'; base-uri 'none'; object-src 'none'"
        )
        return response

    def find_topic(topic_id):
        topic = library.topic(topic_id)
        if topic is None:
            abort(404)
        return topic

    def find_document(document_id):
        document = library.document(document_id)
        if document is None:
            abort(404)
        return document

    def find_page(document_id, number):
        page = library.page(document_id, number)
        if page is None:
            abort(404, "该页不存在。")
        return page

    @app.get("/")
    def home():
        topics = library.list_topics()
        if topics:
            return redirect(url_for("topic", topic_id=topics[0]["id"]))
        return render_template("library.html", topics=topics, topic=None)

    @app.post("/topics")
    def add_topic():
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        if not 1 <= len(name) <= 100 or len(description) > 600:
            flash("请填写 1 至 100 个字符的课题名称，简介最多 600 字。", "error")
        else:
            topic_id = library.create_topic(name, description)
            if topic_id:
                flash("课题已创建。", "success")
                return redirect(url_for("topic", topic_id=topic_id))
            flash("已有同名课题，请使用其他名称。", "error")
        return redirect(url_for("home"))

    @app.get("/topics/<uuid:topic_id>")
    def topic(topic_id):
        topic_id = str(topic_id)
        current = find_topic(topic_id)
        query = request.args.get("q", "").strip()[:200]
        category = request.args.get("category", "").strip()[:120]
        categories = library.categories(topic_id)
        return render_template(
            "library.html", topic=current, topics=library.list_topics(), query=query, category=category,
            categories=categories, documents=library.list_documents(topic_id, query, category),
            max_mib=MAX_UPLOAD_BYTES // (1024 * 1024), max_pages=MAX_PAGES,
        )

    @app.post("/topics/<uuid:topic_id>/documents")
    def upload(topic_id):
        topic_id = str(topic_id)
        find_topic(topic_id)
        destination = url_for("topic", topic_id=topic_id)
        upload_file = request.files.get("pdf")
        if not upload_file or not upload_file.filename:
            flash("请选择要上传的 PDF 文件。", "error")
            return redirect(destination)
        filename = re.sub(r"[\x00-\x1f\x7f]", "", upload_file.filename.replace("\\", "/").split("/")[-1])
        if not filename.lower().endswith(".pdf"):
            flash("目前只支持 PDF 文件。", "error")
            return redirect(destination)
        filename = filename[:-4][:180] + ".pdf"
        raw = upload_file.stream.read(MAX_UPLOAD_BYTES + 1)
        if len(raw) > MAX_UPLOAD_BYTES:
            flash("文件超过 24 MiB，请选择更小的 PDF。", "error")
            return redirect(destination)
        try:
            extracted = parse_pdf(raw, filename)
        except InvalidPDF as error:
            flash(str(error), "error")
            return redirect(destination)
        document_id, inserted = library.add_document(topic_id, filename, raw, extracted)
        flash("文献已导入。" if inserted else "此课题已有同一份 PDF，已打开现有记录。", "success")
        return redirect(url_for("document", document_id=document_id, page=1))

    @app.get("/documents/<uuid:document_id>")
    def document(document_id):
        document_id = str(document_id)
        entry = find_document(document_id)
        number = request.args.get("page", 1, type=int)
        page = find_page(document_id, number)
        return render_template("document.html", topics=library.list_topics(), topic=find_topic(entry["topic_id"]),
                               entry=entry, page=page, field_limits=FIELD_LIMITS)

    @app.get("/documents/<uuid:document_id>/pdf")
    def pdf(document_id):
        row = library.pdf(str(document_id))
        if row is None:
            abort(404)
        return send_file(io.BytesIO(row["pdf"]), mimetype="application/pdf",
                         download_name=row["filename"], conditional=True, max_age=0, etag=row["sha256"])

    @app.get("/documents/<uuid:document_id>/pages/<int:number>/preview.png")
    def preview(document_id, number):
        document_id = str(document_id)
        find_page(document_id, number)
        row = library.pdf(document_id)
        if row is None:
            abort(404)
        tag = f"{row['sha256']}-{number}"
        if request.if_none_match.contains(tag):
            response = app.response_class(status=304)
            response.set_etag(tag)
            return response
        try:
            preview_png = render_page_png(row["pdf"], number)
        except (PdfiumError, ValueError, OverflowError, IndexError):
            return "", 422
        response = send_file(preview_png, mimetype="image/png", conditional=True, etag=tag, max_age=0)
        response.cache_control.private = True
        return response

    @app.get("/api/v1/documents/<uuid:document_id>/pages/<int:number>")
    def evidence(document_id, number):
        document_id = str(document_id)
        entry = find_document(document_id)
        page = find_page(document_id, number)
        return {"document_id": document_id, "title": entry["title"], "physical_page": number,
                "text": page["text"], "status": page["status"],
                "source_url": url_for("document", document_id=document_id, page=number)}

    @app.post("/documents/<uuid:document_id>/metadata")
    def edit_document(document_id):
        document_id = str(document_id)
        find_document(document_id)
        number = request.form.get("page", 1, type=int)
        find_page(document_id, number)
        destination = url_for("document", document_id=document_id, page=number) + "#metadata"
        fields = {key: request.form.get(key, "").strip() for key in FIELD_LIMITS}
        if not fields["title"] or any(len(value) > FIELD_LIMITS[key] for key, value in fields.items()):
            flash("标题为必填项。请检查字段长度。", "error")
            return redirect(destination)
        if fields["year"] and not re.fullmatch(r"[0-9]{4}", fields["year"]):
            flash("年份请填写四位数字，或留空。", "error")
            return redirect(destination)
        if fields["doi"]:
            doi = normalize_doi(fields["doi"])
            if not doi:
                flash("DOI 格式无效。可填写 DOI 或 doi.org 链接。", "error")
                return redirect(destination)
            fields["doi"] = doi
        if not library.update_document(document_id, fields):
            abort(404)
        flash("文献信息已保存。", "success")
        return redirect(destination)

    @app.post("/documents/<uuid:document_id>/delete")
    def delete_document(document_id):
        document_id = str(document_id)
        entry = find_document(document_id)
        library.delete_document(document_id)
        flash("文献已从该课题删除。", "success")
        return redirect(url_for("topic", topic_id=entry["topic_id"]))

    @app.errorhandler(400)
    @app.errorhandler(404)
    @app.errorhandler(413)
    def error(error):
        messages = {
            400: "表单无效或已过期，请返回刷新后再试。",
            404: "找不到这条记录或对应的 PDF 页面。",
            413: "上传文件超过 24 MiB，请选择更小的 PDF。",
        }
        return render_template("error.html", topics=library.list_topics(), topic=None, code=error.code,
                               message=messages[error.code]), error.code

    return app
