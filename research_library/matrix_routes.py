"""HTTP routes for creating, reviewing, and exporting comparison matrices."""

import io

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, send_file, url_for

from .grounding import find_verified_quote
from .matrix import CELL_LIMIT, FIELDS, MAX_MATRIX_DOCUMENTS, export_csv, propose_cells

bp = Blueprint("matrix", __name__)


def _library():
    return current_app.extensions["research_library"]


def _scope(topic_id):
    library = _library()
    topic = library.topic(topic_id)
    if topic is None:
        abort(404)
    documents = library.list_documents(topic_id, "", "")
    available = {item["id"]: item for item in documents}
    ids = list(dict.fromkeys(request.args.getlist("document")))
    if not ids and request.method == "GET" and request.args.get("selected") != "1":
        ids = list(available)[:MAX_MATRIX_DOCUMENTS]
    if len(ids) > MAX_MATRIX_DOCUMENTS or any(doc_id not in available for doc_id in ids):
        return topic, documents, [], f"请选择当前课题中的至多 {MAX_MATRIX_DOCUMENTS} 篇文献。"
    return topic, documents, ids, None


def _view_options():
    field = request.args.get("field", "")
    if field not in FIELDS:
        field = ""
    linked = request.args.get("linked") == "1"
    return {"field": field, "linked": "1" if linked else None, "selected": 1}


@bp.route("/topics/<uuid:topic_id>/matrix", methods=["GET", "POST"])
def table(topic_id):
    topic_id = str(topic_id)
    library = _library()
    topic, documents, ids, error = _scope(topic_id)
    options = _view_options()
    if request.method == "POST":
        count = 0
        if error or not ids:
            flash(error or "请选择至少一篇文献。", "error")
        else:
            count = library.add_matrix_candidates(propose_cells(library.passage_rows(topic_id, ids)))
            if count:
                flash(f"已添加 {count} 个原文候选，请核对后保存。", "success")
            else:
                flash("没有可新增的候选。已填写字段会保留。", "success")
        return redirect(url_for("matrix.table", topic_id=topic_id, document=ids, **options))
    selection = [item for item in documents if item["id"] in ids]
    cells = library.matrix_cells(ids)
    fields = [options["field"]] if options["field"] else list(FIELDS)
    linked = options["linked"] == "1"
    if linked:
        fields = [key for key in fields if any(cells.get((doc_id, key)) and cells[(doc_id, key)]["page"] for doc_id in ids)]
    return render_template(
        "matrix.html", topic=topic, topics=library.list_topics(), documents=documents, selection=selection,
        ids=ids, cells=cells, fields=fields, labels=FIELDS, max_documents=MAX_MATRIX_DOCUMENTS, error=error,
        linked=linked, options=options,
    ), 400 if error else 200


@bp.get("/topics/<uuid:topic_id>/matrix.csv")
def download(topic_id):
    _, documents, ids, error = _scope(str(topic_id))
    if error or not ids:
        abort(400)
    options = _view_options()
    fields = [options["field"]] if options["field"] else list(FIELDS)
    data = export_csv([item for item in documents if item["id"] in ids], fields,
                      _library().matrix_cells(ids), options["linked"] == "1")
    return send_file(io.BytesIO(data), mimetype="text/csv", as_attachment=True, download_name="literature-matrix.csv")


@bp.route("/documents/<uuid:document_id>/matrix/<field>", methods=["GET", "POST"])
def edit(document_id, field):
    document_id = str(document_id)
    library = _library()
    document = library.document(document_id)
    if document is None or field not in FIELDS:
        abort(404)
    topic = library.topic(document["topic_id"])
    available = {row["id"] for row in library.list_documents(topic["id"], "", "")}
    selection = list(dict.fromkeys(value for value in request.args.getlist("document") if value in available))
    options = _view_options()
    previous_field = request.args.get("view_field", "")
    options["field"] = previous_field if previous_field in FIELDS else ""
    destination = url_for("matrix.table", topic_id=topic["id"], document=selection[:MAX_MATRIX_DOCUMENTS] or [document_id],
                          **options)
    current = library.matrix_cells([document_id]).get((document_id, field))
    values = dict(current) if current else {"text": "", "page": "", "quote": ""}
    message = None
    if request.method == "POST":
        values = {key: request.form.get(key, "").strip() for key in ("text", "page", "quote")}
        page = request.form.get("page", type=int)
        verified = ""
        if len(values["text"]) > CELL_LIMIT:
            message = f"字段内容最多 {CELL_LIMIT} 个字符。"
        elif values["page"] or values["quote"]:
            source = library.page(document_id, page) if page and 1 <= page <= document["page_count"] else None
            verified = find_verified_quote(values["quote"], source["text"]) if source else None
            if not values["text"] or not verified:
                message = "请填写字段内容和有效的 PDF 页码，并复制该页的一段连续原文。"
        if message is None:
            library.set_matrix_cell(document_id, field, values["text"], page, verified)
            flash(f"已保存「{FIELDS[field]}」。", "success")
            return redirect(destination)
    return render_template(
        "matrix_edit.html", topic=topic, topics=library.list_topics(), document=document, field_label=FIELDS[field],
        values=values, destination=destination, message=message, max_cell=CELL_LIMIT,
    ), 400 if message else 200
