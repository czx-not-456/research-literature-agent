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

from .agentarts import AgentArtsError
from .catalog_routes import init_app as init_catalog
from .grounding import MAX_DOCUMENTS, MAX_QUESTION, answer_prompt, decode_answer, select_passages, verify_answer
from .ingest import FIELD_LIMITS, MAX_PAGES, MAX_UPLOAD_BYTES, InvalidPDF, normalize_doi, parse_pdf
from .matrix_routes import bp as matrix_blueprint
from .preview import render_page_png
from .refresh_routes import bp as refresh_blueprint
from .report_routes import bp as report_blueprint
from .store import Library

MAX_BATCH_FILES = 10
MAX_BATCH_BYTES = 96 * 1024 * 1024

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
    app.register_blueprint(matrix_blueprint)
    app.register_blueprint(report_blueprint)
    app.register_blueprint(refresh_blueprint)
    init_catalog(app)

    def csrf_token():
        if "csrf_token" not in session:
            session["csrf_token"] = secrets.token_urlsafe(32)
        return session["csrf_token"]

    app.jinja_env.globals.update(csrf_token=csrf_token, field_sources=FIELD_SOURCES, page_status=PAGE_STATUS)

    @app.before_request
    def validate_form():
        if request.method != "POST":
            return
        if request.endpoint == "upload":
            request.max_content_length = MAX_BATCH_BYTES + 128 * 1024
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
            online_sources=library.list_online_sources(topic_id, query) if not category else [],
            max_mib=MAX_UPLOAD_BYTES // (1024 * 1024), max_pages=MAX_PAGES,
            max_batch_files=MAX_BATCH_FILES, max_batch_mib=MAX_BATCH_BYTES // (1024 * 1024),
            rename_open=request.args.get("rename") == "1",
        )

    @app.post("/topics/<uuid:topic_id>/name")
    def rename_topic(topic_id):
        topic_id = str(topic_id)
        find_topic(topic_id)
        name = request.form.get("name", "").strip()
        retry = url_for("topic", topic_id=topic_id, rename=1)
        if not 1 <= len(name) <= 100:
            flash("请填写 1 至 100 个字符的课题名称。", "error")
            return redirect(retry)
        if not library.rename_topic(topic_id, name):
            flash("已有同名课题，请使用其他名称。", "error")
            return redirect(retry)
        flash("课题名称已更新。", "success")
        return redirect(url_for("topic", topic_id=topic_id))

    @app.route("/topics/<uuid:topic_id>/qa", methods=["GET", "POST"])
    def qa(topic_id):
        topic_id = str(topic_id)
        current = find_topic(topic_id)
        documents = library.list_documents(topic_id, "", "")
        available = {row["id"]: row for row in documents}
        client = app.config.get("AGENTARTS_CLIENT")
        requested = request.args.get("document", "")
        selected = [requested] if requested in available else (list(available) if len(available) == 1 else [])
        question = ""
        passages, claims = [], []
        message = None
        status = 200
        if request.method == "POST":
            selected = list(dict.fromkeys(request.form.getlist("document")))
            question = request.form.get("question", "").strip()
            action = request.form.get("action")
            if not 1 <= len(selected) <= MAX_DOCUMENTS or any(doc_id not in available for doc_id in selected):
                message, status = f"请选择当前课题中的 1 至 {MAX_DOCUMENTS} 篇文献。", 400
            elif not 1 <= len(question) <= MAX_QUESTION or action not in ("find", "answer"):
                message, status = f"请输入 1 至 {MAX_QUESTION} 个字符的问题。", 400
            else:
                passages = select_passages(question, library.passage_rows(topic_id, selected))
                if not passages:
                    message = "找不到与问题匹配的可提取原文。可改用论文中的关键词，或检查 PDF 是否为扫描件。"
                elif action == "answer":
                    if client is None:
                        message = "AgentArts 问答尚未启用。下方显示本地匹配的原文。"
                    else:
                        try:
                            answer = decode_answer(client.ask(answer_prompt(question, passages)))
                        except AgentArtsError as error:
                            message = str(error)
                        else:
                            if answer is None:
                                message = "AgentArts 未返回可核验的结构化回答。可以查看下方原文。"
                            else:
                                claims = verify_answer(answer, passages)
        return render_template(
            "qa.html", topic=current, topics=library.list_topics(), documents=documents,
            selected=selected, question=question, passages=passages, claims=claims,
            max_documents=MAX_DOCUMENTS, max_question=MAX_QUESTION, agentarts_enabled=client is not None,
            message=message, submitted=request.method == "POST",
        ), status

    @app.post("/topics/<uuid:topic_id>/documents")
    def upload(topic_id):
        topic_id = str(topic_id)
        find_topic(topic_id)
        destination = url_for("topic", topic_id=topic_id)
        files = [file for file in request.files.getlist("pdf") if file.filename]
        if not files:
            flash("请选择要上传的 PDF 文件。", "error")
            return redirect(destination)
        if len(files) > MAX_BATCH_FILES:
            flash(f"每批最多上传 {MAX_BATCH_FILES} 份 PDF。", "error")
            return redirect(destination)
        total_bytes = 0
        for file in files:
            total_bytes += file.stream.seek(0, io.SEEK_END)
            file.stream.seek(0)
        if total_bytes > MAX_BATCH_BYTES:
            abort(413)

        added = duplicates = 0
        failures = []
        document_id = None
        for file in files:
            filename = re.sub(r"[\x00-\x1f\x7f]", "", file.filename.replace("\\", "/").split("/")[-1])
            try:
                if not filename.lower().endswith(".pdf"):
                    raise InvalidPDF("目前只支持 PDF 文件。")
                filename = filename[:-4][:180] + ".pdf"
                raw = file.stream.read(MAX_UPLOAD_BYTES + 1)
                if len(raw) > MAX_UPLOAD_BYTES:
                    raise InvalidPDF("文件超过 24 MiB，请选择更小的 PDF。")
                extracted = parse_pdf(raw, filename)
                document_id, inserted = library.add_document(topic_id, filename, raw, extracted)
                added += int(inserted)
                duplicates += int(not inserted)
            except InvalidPDF as error:
                failures.append((filename, str(error)))

        if len(files) == 1:
            if document_id is None:
                flash(failures[0][1], "error")
                return redirect(destination)
            flash("文献已导入。" if added else "此课题已有同一份 PDF，已打开现有记录。", "success")
            return redirect(url_for("document", document_id=document_id, page=1))

        flash(f"本批新增 {added} 篇，重复跳过 {duplicates} 份，导入失败 {len(failures)} 份。",
              "error" if failures else "success")
        # Keep flash feedback within the session-cookie size limit.
        for filename, message in failures[:3]:
            label = filename[:60] + ("…" if len(filename) > 60 else "")
            flash(f"「{label or '未命名文件'}」{message}", "error")
        if len(failures) > 3:
            flash("其余失败文件可单独重新导入以查看原因。", "error")
        return redirect(destination)

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
            413: "上传请求过大。每批最多 10 份 PDF，合计不超过 96 MiB。",
        }
        return render_template("error.html", topics=library.list_topics(), topic=None, code=error.code,
                               message=messages[error.code]), error.code

    return app
