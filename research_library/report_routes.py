"""Web entry points for saved literature review reports."""

import io

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, send_file, url_for

from .report import (
    MAX_REPORT_DOCUMENTS, MAX_REPORT_TITLE, MAX_SECTION, SECTION_FIELDS, collect_candidates,
    draft_section, reference_text, sources_from,
)
from .report_export import markdown, word

bp = Blueprint("reports", __name__)
EXPORTS = {
    "md": ("text/markdown", markdown),
    "docx": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", word),
}


def _library():
    return current_app.extensions["research_library"]


def _report(report_id):
    report = _library().report(str(report_id))
    if report is None:
        abort(404)
    return report


@bp.route("/topics/<uuid:topic_id>/reports", methods=["GET", "POST"])
def listing(topic_id):
    topic_id = str(topic_id)
    library = _library()
    topic = library.topic(topic_id)
    if topic is None:
        abort(404)
    documents = library.list_documents(topic_id, "", "")
    title = f'{topic["name"]}文献调研报告'
    selected = []
    error = None
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        selected = list(dict.fromkeys(request.form.getlist("document")))
        scope = {item["id"]: item for item in documents}
        if not 1 <= len(title) <= MAX_REPORT_TITLE:
            error = f"请输入 1 至 {MAX_REPORT_TITLE} 个字符的报告标题。"
        elif not 1 <= len(selected) <= MAX_REPORT_DOCUMENTS or any(doc_id not in scope for doc_id in selected):
            error = f"请选择当前课题中的 1 至 {MAX_REPORT_DOCUMENTS} 篇文献。"
        else:
            sources = sources_from([scope[doc_id] for doc_id in selected])
            cells = collect_candidates(library, topic_id, sources)
            drafts = {key: draft_section(key, sources, cells) for key in SECTION_FIELDS}
            report_id = library.add_report(topic_id, title, sources, drafts)
            return redirect(url_for("reports.detail", report_id=report_id))
    return render_template(
        "reports.html", topic=topic, topics=library.list_topics(), documents=documents, selected=selected,
        reports=library.list_reports(topic_id), title=title, error=error,
        max_title=MAX_REPORT_TITLE, max_documents=MAX_REPORT_DOCUMENTS,
    ), 400 if error else 200


@bp.get("/reports/<uuid:report_id>")
def detail(report_id):
    library = _library()
    report = _report(report_id)
    available = {item["id"] for item in library.list_documents(report["topic_id"], "", "")}
    return render_template(
        "report_detail.html", report=report, topic=library.topic(report["topic_id"]), topics=library.list_topics(),
        section_labels=SECTION_FIELDS, sources={item["number"]: item for item in report["sources"]},
        available=available, reference_text=reference_text,
    )


@bp.route("/reports/<uuid:report_id>/sections/<key>", methods=["GET", "POST"])
def section(report_id, key):
    report = _report(report_id)
    if key not in SECTION_FIELDS:
        abort(404)
    library = _library()
    topic = library.topic(report["topic_id"])
    title = SECTION_FIELDS[key][0]
    destination = url_for("reports.detail", report_id=report_id) + f"#{key}"
    text = report["sections"][key]["body"]
    error = None
    if request.method == "POST":
        action = request.form.get("action")
        if action == "rebuild":
            cells = collect_candidates(library, report["topic_id"], report["sources"])
            draft = draft_section(key, report["sources"], cells)
            library.update_report_section(str(report_id), key, draft.text, draft.evidence)
            flash(f"已从本地文献重建「{title}」。", "success")
            return redirect(destination)
        if action != "save":
            abort(400)
        text = request.form.get("body", "").strip()
        if len(text) > MAX_SECTION:
            error = f"正文最多 {MAX_SECTION} 个字符。"
        else:
            library.update_report_section(str(report_id), key, text)
            flash(f"已保存「{title}」。", "success")
            return redirect(destination)
    return render_template("report_edit.html", report=report, topic=topic, topics=library.list_topics(),
                           section_title=title, text=text, destination=destination, error=error,
                           max_section=MAX_SECTION), 400 if error else 200


@bp.get("/reports/<uuid:report_id>/export/<format>")
def export(report_id, format):
    report = _report(report_id)
    if format not in EXPORTS:
        abort(404)
    mime, formatter = EXPORTS[format]
    return send_file(io.BytesIO(formatter(report)), mimetype=mime, download_name=f"literature-report.{format}",
                     as_attachment=True, max_age=0)
