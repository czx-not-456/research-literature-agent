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
