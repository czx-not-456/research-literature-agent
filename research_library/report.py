"""Draft research reports from recorded literature, with separately tracked source passages."""

from dataclasses import dataclass

from .matrix import FIELDS, propose_cells

MAX_REPORT_DOCUMENTS = 6
MAX_REPORT_TITLE = 140
MAX_SECTION = 24_000
SECTION_FIELDS = {
    "background": ("研究背景", ("background", "question")),
    "history": ("研究发展历程", ()),
    "directions": ("主要研究方向", ("question", "method")),
    "representative": ("代表性研究工作", ("method", "innovation")),
    "comparison": ("不同方法的比较", ("method", "data", "setup", "metrics", "results")),
    "limitations": ("当前研究存在的问题", ("limitations",)),
    "future": ("未来研究方向", ("future",)),
}


@dataclass(frozen=True)
class Draft:
    text: str
    evidence: list


def reference_text(source):
    parts = [source["title"]]
    if source["authors"]:
        parts.append(source["authors"])
    if source["year"]:
        parts.append(source["year"])
    if source["doi"]:
        parts.append("DOI " + source["doi"])
    return " · ".join(parts)


def sources_from(documents):
    return [
        {"number": index, **{key: row[key] for key in ("id", "title", "authors", "year", "doi")}}
        for index, row in enumerate(documents, 1)
    ]


def collect_candidates(library, topic_id, sources):
    ids = [item["id"] for item in sources]
    cells = library.matrix_cells(ids)
    for doc_id, field, text, page, quote in propose_cells(library.passage_rows(topic_id, ids)):
        cells.setdefault((doc_id, field), {"text": text, "source": "excerpt", "page": page, "quote": quote})
    return cells


def draft_section(key, sources, cells):
    if key == "history":
        dated = [source for source in sources if source["year"]]
        lines = [f'{source["year"]} · {source["title"]} [{source["number"]}]'
                 for source in sorted(dated, key=lambda source: (source["year"], source["number"]))]
        lines.extend(f'年份待核实 · {source["title"]} [{source["number"]}]'
                     for source in sources if not source["year"])
        return Draft("\n".join(lines), [])

    paragraphs, evidence = [], []
    for source in sources:
        lines = []
        for field in SECTION_FIELDS[key][1]:
            cell = cells.get((source["id"], field))
            if not cell or not cell["text"]:
                continue
            if cell["page"] and cell["quote"]:
                origin = f'PDF 第 {cell["page"]} 页'
                citation = {"number": source["number"], "page": cell["page"], "quote": cell["quote"]}
                if citation not in evidence:
                    evidence.append(citation)
            else:
                origin = "无页级引文"
            label = "原文候选" if cell["source"] == "excerpt" else "矩阵填写"
            content = cell["text"]
            preview = content[:600] + "…" if len(content) > 600 else content
            lines.append(f'{FIELDS[field]}（{label}，{origin}）\n{preview}')
        if lines:
            paragraphs.append(f'{source["title"]} [{source["number"]}]\n' + "\n\n".join(lines))
    return Draft("\n\n".join(paragraphs), evidence)
