"""Academic search and user-confirmed import routes."""

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from itsdangerous import BadData, URLSafeTimedSerializer

from .academic import AcademicSearch, FIELDS, MAX_PAGE, PROVIDERS, ROWS, SearchError, parse_query

bp = Blueprint("catalog", __name__)
TOKEN_TTL = 15 * 60


def init_app(app):
    app.extensions["academic_search"] = app.config.get("ACADEMIC_SEARCH_CLIENT") or AcademicSearch()
    app.register_blueprint(bp)
    app.jinja_env.globals["academic_providers"] = PROVIDERS


def _context(topic_id):
    library = current_app.extensions["research_library"]
    topic = library.topic(topic_id)
    if topic is None:
        abort(404)
    return library, topic


def _tokens():
    return URLSafeTimedSerializer(current_app.secret_key, salt="academic-source-import-v1")


@bp.get("/topics/<uuid:topic_id>/search")
def search(topic_id):
    topic_id = str(topic_id)
    library, topic = _context(topic_id)
    args = {name: request.args.get(name, default) for name, default in (
        ("source", "crossref"), ("q", ""), ("author", ""), ("year", ""), ("field", ""),
    )}
    records, total, error = [], 0, None
    query = None
    requested = request.args.get("search") == "1"
    if requested:
        try:
            query = parse_query(request.args)
            records, total = current_app.extensions["academic_search"].fetch(query)
        except SearchError as exc:
            error = str(exc)
    imported_keys = {(row["provider"], row["provider_id"]) for row in library.list_online_sources(topic_id)}
    results = [{
        **record, "imported": (record["provider"], record["provider_id"]) in imported_keys,
        "token": _tokens().dumps({"topic": topic_id, "record": record}),
    } for record in records]
    page = query.page if query else 1
    return render_template(
        "academic_search.html", topic=topic, topics=library.list_topics(), values=args, fields=FIELDS, results=results,
        total=total, page=page, has_next=page < MAX_PAGE and total > page * ROWS, requested=requested, error=error,
    )


@bp.post("/topics/<uuid:topic_id>/sources")
def import_sources(topic_id):
    topic_id = str(topic_id)
    library, _ = _context(topic_id)
    selected = list(dict.fromkeys(request.form.getlist("record")))
    if not 1 <= len(selected) <= ROWS or any(len(token) > 8500 for token in selected):
        flash("请选择本页中要保存的在线文献。", "error")
        return redirect(url_for("catalog.search", topic_id=topic_id))
    records = []
    serializer = _tokens()
    try:
        for token in selected:
            data = serializer.loads(token, max_age=TOKEN_TTL)
            if data["topic"] != topic_id:
                raise BadData("wrong topic")
            records.append(data["record"])
    except BadData:
        flash("检索结果已失效。请在当前课题重新检索后导入。", "error")
        return redirect(url_for("catalog.search", topic_id=topic_id))
    added = library.add_online_sources(topic_id, records)
    flash(f"已保存 {added} 条在线文献，跳过 {len(records) - added} 条重复记录。", "success")
    return redirect(url_for("topic", topic_id=topic_id, _anchor="online-sources"))


@bp.get("/topics/<uuid:topic_id>/sources/<uuid:source_id>")
def detail(topic_id, source_id):
    library, topic = _context(str(topic_id))
    entry = library.online_source(str(topic_id), str(source_id))
    if entry is None:
        abort(404)
    local_pdf = library.document_matching_doi(str(topic_id), entry["doi"]) if entry["doi"] else None
    return render_template("academic_source.html", entry=entry, topic=topic, topics=library.list_topics(),
                           local_pdf=local_pdf)


@bp.post("/topics/<uuid:topic_id>/sources/<uuid:source_id>/delete")
def delete(topic_id, source_id):
    library, _ = _context(str(topic_id))
    if not library.delete_online_source(str(topic_id), str(source_id)):
        abort(404)
    flash("已移除在线文献记录。", "success")
    return redirect(url_for("topic", topic_id=topic_id))
