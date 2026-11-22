"""Build editable, page-linked comparison drafts from local PDF passages."""

import csv
import io
import re

# Each clue retrieves original text. The field assignment remains a candidate for review.
_FIELDS = (
    ("question", "研究问题", r"研究问题|研究目的|旨在|本文探讨|我们研究|research questions?|our objective|we (?:aim|investigate|explore|ask|seek to)"),
    ("background", "研究背景", r"研究背景|背景与动机|引言|绪论|background and motivation|research background|introduction"),
    ("method", "核心方法", r"核心方法|研究方法|本文提出|我们提出|方法概述|our method|we propose|proposed (?:method|approach|framework)|methodology"),
    ("innovation", "创新点", r"创新点|主要贡献|本文贡献|贡献如下|本文首次|our (?:main )?contributions?|novel (?:contribution|model|approach)|we introduce"),
    ("data", "数据集", r"数据集|数据来源|样本来源|datasets?|data sources?|training data"),
    ("setup", "实验设置", r"实验设置|实验配置|实施细节|实现细节|对照实验|训练设置|超参数|experimental (?:setup|settings?)|implementation details|training (?:setup|details|procedure)|hyperparameters?"),
    ("metrics", "评价指标", r"评价指标|评估指标|评价度量|准确率|召回率|evaluation metrics?|precision and recall|F1[- ]score|exact match|accuracy|BLEU|ROUGE"),
    ("results", "主要实验结果", r"实验结果|主要结果|结果表明|experimental results|main results|results (?:show|indicate)|we achieve"),
    ("limitations", "研究局限", r"研究局限|局限性|研究限制|limitations?|drawbacks?|limited to|we do not (?:consider|evaluate|address)|a (?:key|main) shortcoming"),
    ("future", "未来研究方向", r"未来研究|后续工作|未来工作|未来展望|有待进一步|future (?:work|research|directions?)"),
)
FIELDS = {key: label for key, label, _ in _FIELDS}
_PATTERNS = {
    key: re.compile(r"(?<![A-Za-z])(?:" + cue + r")(?![A-Za-z])", re.I)
    for key, _, cue in _FIELDS
}
_REFERENCE = re.compile(r"^[ \t]*(?:\d+\.?[ \t]+)?(?:References|Bibliography|参考文献)[ \t]*$", re.I | re.M)
MAX_MATRIX_DOCUMENTS = 6
CELL_LIMIT = 1400


def _excerpt(text, hit):
    start = text.rfind("\n", max(0, hit.start() - 115), hit.start()) + 1
    start = max(start, hit.start() - 95)
    end = min(len(text), start + 380)
    if end < len(text):
        boundary = max(text.rfind("\n", hit.end() + 65, end), text.rfind("。", hit.end() + 65, end))
        if boundary >= 0:
            end = boundary + 1
    quote = text[start:end].strip()
    return quote if len("".join(quote.split())) >= 8 else ""


def propose_cells(pages):
    candidates = {}
    bibliography = set()
    for row in pages:
        doc_id = row["document_id"]
        if doc_id in bibliography:
            continue
        text = row["text"]
        references = _REFERENCE.search(text)
        if references:
            text = text[:references.start()]
            bibliography.add(doc_id)
        for field, pattern in _PATTERNS.items():
            key = (doc_id, field)
            if key in candidates:
                continue
            hit = pattern.search(text)
            if hit:
                quote = _excerpt(text, hit)
                if quote:
                    candidates[key] = (doc_id, field, quote, row["number"], quote)
    return list(candidates.values())


def _spreadsheet_cell(value):
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@", "＝", "＋", "－", "＠")):
        return "'" + value
    return value


def export_csv(documents, fields, cells, only_linked):
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer)
    writer.writerow(("文献", "字段", "内容", "来源", "PDF 页码", "原文引文"))
    for document in documents:
        for key in fields:
            cell = cells.get((document["id"], key))
            if only_linked and (not cell or not cell["page"]):
                continue
            source = {"excerpt": "原文候选", "manual": "手动填写"}
            writer.writerow(_spreadsheet_cell(value) for value in (
                document["title"], FIELDS[key], cell["text"] if cell else "",
                source[cell["source"]] if cell and cell["text"] else "待补充",
                cell["page"] if cell else None, cell["quote"] if cell else "",
            ))
    return buffer.getvalue().encode("utf-8-sig")
