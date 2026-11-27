"""Preview and apply local updates for documents already in a topic."""

import hashlib
import json

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from itsdangerous import BadData, URLSafeTimedSerializer

from .ingest import InvalidPDF, extract_pdf_metadata
from .matrix import FIELDS, MAX_MATRIX_DOCUMENTS, propose_cells
from .store import BACKFILL_COLUMNS, StaleLibraryRefresh

bp = Blueprint("refresh", __name__)
FIELD_LABELS = {"authors": "作者", "year": "发表年份", "doi": "DOI", "keywords": "关键词", "abstract": "摘要"}
PREVIEW_TTL = 15 * 60
STALE_MESSAGE = "文献或候选已有变化，或预览已过期。请重新生成预览。"


def _propose(library, topic_id, documents):
    ids = [row["id"] for row in documents]
    stored = library.matrix_cells(ids)

    plan = []
    for row in documents:
        doc_id = row["id"]
        entry = {"id": doc_id, "title": row["title"], "fields": {}, "matrix": {}, "error": None}
        plan.append(entry)
        sources = json.loads(row["sources"])
        blanks = [key for key in BACKFILL_COLUMNS if not row[key] and sources.get(key) != "manual"]
        if blanks:
            original = library.pdf(doc_id)
            if original is None:
                raise StaleLibraryRefresh()
            try:
                fresh, origins = extract_pdf_metadata(original["pdf"], original["filename"])
            except InvalidPDF:
                entry["error"] = "原件暂时无法重新解析，本轮跳过这篇文献。"
                continue
            entry["fields"] = {key: {"value": fresh[key], "source": origins[key]} for key in blanks if fresh[key]}

        rows = list(library.passage_rows(topic_id, [doc_id]))
        complete_text = len(rows) == row["page_count"] and all(page["status"] == "available" for page in rows)
        candidates = {
            field: {"text": text, "source": "excerpt", "page": number, "quote": quote}
            for _, field, text, number, quote in propose_cells(rows)
        }
        for field in FIELDS:
            existing = stored.get((doc_id, field))
            if existing is not None and existing["source"] == "manual":
                continue
            before = {key: existing[key] for key in ("text", "source", "page", "quote")} if existing else None
            after = candidates.get(field)
            if before != after and (after is not None or complete_text):
                entry["matrix"][field] = {"before": before, "after": after}
    return plan


def _fingerprint(plan):
    encoded = json.dumps(plan, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@bp.route("/topics/<uuid:topic_id>/refresh", methods=["GET", "POST"])
def review(topic_id):
    topic_id = str(topic_id)
    library = current_app.extensions["research_library"]
    topic = library.topic(topic_id)
    if topic is None:
        abort(404)
    documents = library.list_documents(topic_id, "", "")
    available = {row["id"]: row for row in documents}
    ids, plan, token = [], [], None
    error, status = None, 200
    if request.method == "POST":
        serializer = URLSafeTimedSerializer(current_app.secret_key, salt="local-library-refresh-v1")
        action = request.form.get("action")
        try:
            if action == "apply":
                reviewed = serializer.loads(request.form.get("review", ""), max_age=PREVIEW_TTL)
                if reviewed["topic"] != topic_id:
                    raise StaleLibraryRefresh()
                ids = reviewed["documents"]
            elif action == "preview":
                ids = list(dict.fromkeys(request.form.getlist("document")))
            else:
                abort(400)
            if not 1 <= len(ids) <= MAX_MATRIX_DOCUMENTS or any(doc_id not in available for doc_id in ids):
                if action == "apply":
                    raise StaleLibraryRefresh()
                error, status = f"请选择当前课题中的 1 至 {MAX_MATRIX_DOCUMENTS} 篇本地 PDF。", 400
            else:
                plan = _propose(library, topic_id, [available[doc_id] for doc_id in ids])
                changed = [entry for entry in plan if entry["fields"] or entry["matrix"]]
                fingerprint = _fingerprint(plan)
                if action == "apply":
                    if not changed or reviewed["fingerprint"] != fingerprint:
                        raise StaleLibraryRefresh()
                    library.apply_reviewed_refresh(topic_id, changed)
                    field_count = sum(len(entry["fields"]) for entry in changed)
                    matrix_count = sum(len(entry["matrix"]) for entry in changed)
                    flash(f"已更新 {len(changed)} 篇文献，补齐 {field_count} 个元数据字段，调整 {matrix_count} 个矩阵候选。",
                          "success")
                    return redirect(url_for("refresh.review", topic_id=topic_id))
                if changed:
                    token = serializer.dumps({"topic": topic_id, "documents": ids, "fingerprint": fingerprint})
        except (BadData, StaleLibraryRefresh):
            error, status = STALE_MESSAGE, 409
            plan = []

    return render_template(
        "library_refresh.html", topic=topic, topics=library.list_topics(), documents=documents,
        ids=ids, plan=plan, review_token=token, error=error, limit=MAX_MATRIX_DOCUMENTS,
        labels=FIELD_LABELS, matrix_labels=FIELDS,
    ), status
