"""Local SQLite persistence. Page numbers are physical PDF pages, starting at 1."""

import hashlib
import json
import sqlite3
from contextlib import closing
from pathlib import Path
from uuid import uuid4

SCHEMA = """
CREATE TABLE IF NOT EXISTS topics (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL COLLATE NOCASE UNIQUE,
    description TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    topic_id TEXT NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    title TEXT NOT NULL,
    authors TEXT NOT NULL DEFAULT '',
    abstract TEXT NOT NULL DEFAULT '',
    keywords TEXT NOT NULL DEFAULT '',
    year TEXT NOT NULL DEFAULT '',
    doi TEXT NOT NULL DEFAULT '',
    category TEXT NOT NULL DEFAULT '',
    sources TEXT NOT NULL,
    page_count INTEGER NOT NULL CHECK (page_count > 0),
    text_page_count INTEGER NOT NULL CHECK (text_page_count BETWEEN 0 AND page_count),
    sha256 TEXT NOT NULL,
    pdf BLOB NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (topic_id, sha256)
);
CREATE INDEX IF NOT EXISTS documents_by_topic ON documents(topic_id, created_at DESC);
CREATE TABLE IF NOT EXISTS pages (
    document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    number INTEGER NOT NULL CHECK (number >= 1),
    text TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('available','truncated','no_text','extraction_failed')),
    PRIMARY KEY (document_id, number)
);
CREATE TABLE IF NOT EXISTS matrix_cells (
    document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    field TEXT NOT NULL,
    text TEXT NOT NULL,
    source TEXT NOT NULL CHECK (source IN ('excerpt', 'manual')),
    page INTEGER,
    quote TEXT NOT NULL,
    PRIMARY KEY (document_id, field),
    FOREIGN KEY (document_id, page) REFERENCES pages(document_id, number) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS reports (
    id TEXT PRIMARY KEY,
    topic_id TEXT NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    sources TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS reports_by_topic ON reports(topic_id, created_at DESC);
CREATE TABLE IF NOT EXISTS report_sections (
    report_id TEXT NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    section TEXT NOT NULL,
    body TEXT NOT NULL,
    evidence TEXT NOT NULL,
    PRIMARY KEY (report_id, section)
);

"""
TITLE_COLUMNS = "id, topic_id, filename, title, authors, abstract, keywords, year, doi, category, sources, page_count, text_page_count, created_at, updated_at"
EDIT_COLUMNS = ("title", "authors", "abstract", "keywords", "year", "doi", "category")
SEARCH_COLUMNS = ("title", "authors", "abstract", "keywords", "year", "doi", "category", "filename")


def _like_pattern(query):
    return "%" + query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


class Library:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self.connect()) as db:
            db.execute("PRAGMA journal_mode = WAL")
            db.executescript(SCHEMA)

    def connect(self):
        db = sqlite3.connect(self.path, timeout=5.0)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        return db

    def list_topics(self):
        with closing(self.connect()) as db:
            return db.execute("""
                SELECT topics.*, COUNT(documents.id) AS document_count
                FROM topics LEFT JOIN documents ON documents.topic_id = topics.id
                GROUP BY topics.id
                ORDER BY topics.created_at DESC, topics.name
            """).fetchall()

    def topic(self, topic_id):
        with closing(self.connect()) as db:
            return db.execute("SELECT * FROM topics WHERE id = ?", (topic_id,)).fetchone()

    def create_topic(self, name, description):
        topic_id = str(uuid4())
        with closing(self.connect()) as db, db:
            result = db.execute(
                "INSERT INTO topics(id, name, description) VALUES (?, ?, ?) ON CONFLICT(name) DO NOTHING",
                (topic_id, name, description),
            )
            return topic_id if result.rowcount else None

    def rename_topic(self, topic_id, name):
        with closing(self.connect()) as db, db:
            result = db.execute("UPDATE OR IGNORE topics SET name = ? WHERE id = ?", (name, topic_id))
            return bool(result.rowcount)

    def categories(self, topic_id):
        with closing(self.connect()) as db:
            return [row["category"] for row in db.execute("""
                SELECT DISTINCT category FROM documents
                WHERE topic_id = ? AND category <> '' ORDER BY category COLLATE NOCASE
            """, (topic_id,))]

    def list_documents(self, topic_id, query, category):
        params = {"topic": topic_id, "category": category}
        clauses = ["topic_id = :topic"]
        match_page = "NULL"
        if category:
            clauses.append("category = :category")
        if query:
            params["pattern"] = _like_pattern(query)
            page_match = "p.text LIKE :pattern ESCAPE '\\'"
            match_page = f"(SELECT MIN(p.number) FROM pages p WHERE p.document_id = documents.id AND {page_match})"
            metadata_match = " OR ".join(f"{column} LIKE :pattern ESCAPE '\\'" for column in SEARCH_COLUMNS)
            clauses.append(f"({metadata_match} OR EXISTS (SELECT 1 FROM pages p WHERE p.document_id = documents.id AND {page_match}))")
        with closing(self.connect()) as db:
            return db.execute(f"""
                SELECT {TITLE_COLUMNS}, {match_page} AS matching_page FROM documents
                WHERE {" AND ".join(clauses)}
                ORDER BY created_at DESC, rowid DESC
            """, params).fetchall()

    def add_document(self, topic_id, filename, raw, extracted):
        document_id = str(uuid4())
        digest = hashlib.sha256(raw).hexdigest()
        fields = extracted.fields
        with closing(self.connect()) as db, db:
            inserted = db.execute("""
                INSERT INTO documents (
                    id, topic_id, filename, title, authors, abstract, keywords, year, doi, category,
                    sources, page_count, text_page_count, sha256, pdf
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(topic_id, sha256) DO NOTHING
            """, (
                document_id, topic_id, filename, *(fields[key] for key in EDIT_COLUMNS),
                json.dumps(extracted.sources, ensure_ascii=False), len(extracted.pages),
                sum(bool(page.text) for page in extracted.pages), digest, raw,
            ))
            if not inserted.rowcount:
                existing = db.execute("SELECT id FROM documents WHERE topic_id = ? AND sha256 = ?",
                                      (topic_id, digest)).fetchone()
                return existing["id"], False
            db.executemany("INSERT INTO pages(document_id, number, text, status) VALUES (?, ?, ?, ?)", (
                (document_id, number, page.text, page.status)
                for number, page in enumerate(extracted.pages, start=1)
            ))
            return document_id, True

    def passage_rows(self, topic_id, document_ids):
        placeholders = ", ".join("?" for _ in document_ids)
        with closing(self.connect()) as db:
            yield from db.execute(f"""
                SELECT d.id AS document_id, d.title, p.number, p.text
                FROM pages p JOIN documents d ON p.document_id = d.id
                WHERE d.topic_id = ? AND d.id IN ({placeholders}) AND p.text <> ''
                ORDER BY d.id, p.number
            """, (topic_id, *document_ids))

    def matrix_cells(self, document_ids):
        if not document_ids:
            return {}
        placeholders = ", ".join("?" for _ in document_ids)
        with closing(self.connect()) as db:
            return {
                (row["document_id"], row["field"]): row for row in db.execute(
                    f"SELECT * FROM matrix_cells WHERE document_id IN ({placeholders})", tuple(document_ids)
                )
            }

    def add_matrix_candidates(self, rows):
        with closing(self.connect()) as db, db:
            result = db.executemany("""
                INSERT INTO matrix_cells(document_id, field, text, source, page, quote)
                SELECT ?, ?, ?, 'excerpt', number, ? FROM pages WHERE document_id = ? AND number = ?
                ON CONFLICT(document_id, field) DO NOTHING
            """, ((doc_id, field, text, quote, doc_id, page) for doc_id, field, text, page, quote in rows))
            return result.rowcount

    def set_matrix_cell(self, document_id, field, text, page, quote):
        with closing(self.connect()) as db, db:
            db.execute("""
                INSERT INTO matrix_cells(document_id, field, text, source, page, quote)
                VALUES (?, ?, ?, 'manual', ?, ?)
                ON CONFLICT(document_id, field) DO UPDATE SET
                    text = excluded.text, source = excluded.source, page = excluded.page, quote = excluded.quote
            """, (document_id, field, text, page, quote))

    def list_reports(self, topic_id):
        with closing(self.connect()) as db:
            return db.execute("""
                SELECT id, title, updated_at FROM reports
                WHERE topic_id = ? ORDER BY created_at DESC, rowid DESC
            """, (topic_id,)).fetchall()

    def add_report(self, topic_id, title, sources, drafts):
        report_id = str(uuid4())
        with closing(self.connect()) as db, db:
            db.execute("INSERT INTO reports(id, topic_id, title, sources) VALUES (?, ?, ?, ?)",
                       (report_id, topic_id, title, json.dumps(sources, ensure_ascii=False)))
            db.executemany("INSERT INTO report_sections(report_id, section, body, evidence) VALUES (?, ?, ?, ?)", (
                (report_id, key, draft.text, json.dumps(draft.evidence, ensure_ascii=False))
                for key, draft in drafts.items()
            ))
        return report_id

    def report(self, report_id):
        with closing(self.connect()) as db:
            db.execute("BEGIN")
            row = db.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
            if row is None:
                return None
            report = dict(row)
            report["sources"] = json.loads(row["sources"])
            report["sections"] = {
                item["section"]: {"body": item["body"], "evidence": json.loads(item["evidence"])}
                for item in db.execute("SELECT * FROM report_sections WHERE report_id = ?", (report_id,))
            }
            return report

    def update_report_section(self, report_id, section, text, evidence=None):
        with closing(self.connect()) as db, db:
            if evidence is None:
                db.execute("UPDATE report_sections SET body = ? WHERE report_id = ? AND section = ?",
                           (text, report_id, section))
            else:
                db.execute("UPDATE report_sections SET body = ?, evidence = ? WHERE report_id = ? AND section = ?",
                           (text, json.dumps(evidence, ensure_ascii=False), report_id, section))
            db.execute("UPDATE reports SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (report_id,))

    def document(self, document_id):
        with closing(self.connect()) as db:
            row = db.execute(f"SELECT {TITLE_COLUMNS} FROM documents WHERE id = ?", (document_id,)).fetchone()
        if row is None:
            return None
        result = dict(row)
        result["sources"] = json.loads(result["sources"])
        return result

    def page(self, document_id, number):
        with closing(self.connect()) as db:
            return db.execute(
                "SELECT number, text, status FROM pages WHERE document_id = ? AND number = ?", (document_id, number)
            ).fetchone()

    def pdf(self, document_id):
        with closing(self.connect()) as db:
            return db.execute("SELECT filename, sha256, pdf FROM documents WHERE id = ?", (document_id,)).fetchone()

    def update_document(self, document_id, fields):
        with closing(self.connect()) as db, db:
            row = db.execute(f"SELECT {', '.join(EDIT_COLUMNS)}, sources FROM documents WHERE id = ?",
                             (document_id,)).fetchone()
            if row is None:
                return False
            sources = json.loads(row["sources"])
            for name in EDIT_COLUMNS:
                if fields[name] != row[name]:
                    sources[name] = "manual"
            db.execute("""
                UPDATE documents SET title=?, authors=?, abstract=?, keywords=?, year=?, doi=?, category=?,
                                     sources=?, updated_at=CURRENT_TIMESTAMP WHERE id=?
            """, (*(fields[key] for key in EDIT_COLUMNS), json.dumps(sources, ensure_ascii=False), document_id))
            return True

    def delete_document(self, document_id):
        with closing(self.connect()) as db, db:
            return bool(db.execute("DELETE FROM documents WHERE id=?", (document_id,)).rowcount)
