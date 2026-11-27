"""Extract text and conservative bibliographic hints from an uploaded PDF."""

import io
import re
from dataclasses import dataclass
from itertools import islice
from pathlib import PurePath

from pypdf import PdfReader
from pypdf.errors import PyPdfError

MAX_UPLOAD_BYTES = 24 * 1024 * 1024
MAX_PAGES = 300
MAX_PAGE_CHARACTERS = 100_000
FIELD_LIMITS = {"title": 400, "authors": 1000, "abstract": 8_000, "keywords": 800,
                "year": 4, "doi": 300, "category": 120}
DOI_PATTERN = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.IGNORECASE)
DOI_LABEL = re.compile(
    r"^[ \t]*(?:DOI[ \t]*[:：]?[ \t]*(?:https?://(?:dx\.)?doi\.org/)?|"
    r"(?:(?:在线阅读(?:[ \t]+View online)?|View online)[ \t]*[:：][ \t]*)?https?://(?:dx\.)?doi\.org/)"
    r"(10\.\d{4,9}/[-._;()/:A-Z0-9]+)", re.IGNORECASE | re.MULTILINE,
)
ABSTRACT_HEADING = re.compile(r"^\s*(?:abstract\b|摘\s*要)\s*[:：.—–-]?\s*(.*)$", re.IGNORECASE)
SECTION_HEADING = re.compile(
    r"^\s*(?:(?:keywords?|index terms)\b|关\s*键\s*[词字]|引言|绪论|正\s*文|"
    r"(?:[1一][.、\s]+\s*)?introduction\b|references\b|参考文献|"
    r"(?:DOI|Authors?|By|Published|Publication\s+date)\s*[:：]|作者\s*[:：]|[∗†‡*])",
    re.IGNORECASE,
)
BYLINE = re.compile(r"^\s*(?:authors?\s*[:：]|by\s+|作者\s*[:：])\s*(.+)$", re.IGNORECASE | re.MULTILINE)
KEYWORDS = re.compile(r"^\s*(?:keywords?|index terms|关\s*键\s*[词字])\s*[:：.—–-]\s*(.+)$",
                      re.IGNORECASE | re.MULTILINE)
PUBLICATION_YEAR = re.compile(
    r"^\s*(?:published(?:\s+(?:online|on))?|(?:date of publication|publication date)|"
    r"发表(?:日期|时间|年)?|出版(?:日期|时间|年)?|发布日期)"
    r"\s*[:：]?\s*[^\r\n]{0,50}?\b((?:18|19|20)\d{2})(?=\D|$)",
    re.IGNORECASE | re.MULTILINE,
)
_JOURNAL_IMPRINT = re.compile(
    r"\[J\][.。]?[ \t]*[^\r\n,，]{1,110}[,，][ \t]*((?:18|19|20)\d{2})[,，][ \t]*\d+\s*\(",
    re.IGNORECASE,
)
_CONFERENCE_PAGES = re.compile(r"\bpages[ \t]+\d+\s*[-–—]\s*\d+", re.IGNORECASE)
_CONFERENCE_MONTH = r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|" \
                    r"Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
_CONFERENCE_DATE = re.compile(
    rf"\b{_CONFERENCE_MONTH}\.?[ \t]+(?:\d{{1,2}}(?:[ \t]*[-–—][ \t]*(?:{_CONFERENCE_MONTH}\.?[ \t]+)?"
    r"\d{1,2})?,?[ \t]+)?((?:18|19|20)\d{2})(?!\d)", re.IGNORECASE,
)
_CHINESE_NAME = r"[\u3400-\u9fff]{2,4}"
_AFFILIATION_NUMBERS = r"(?:[ \t]*\d{1,2}(?:[ \t]*,[ \t]*\d{1,2})*)?"
_CHINESE_BYLINE = re.compile(
    rf"{_CHINESE_NAME}{_AFFILIATION_NUMBERS}(?:\s*[,，、;；]\s*{_CHINESE_NAME}{_AFFILIATION_NUMBERS})+"
)
_FRONT_MATTER_END = re.compile(
    r"^[ \t]*(?:(?:\d+(?:\.\d+)*\.?[ \t]+)?(?:introduction|references|bibliography)\b|"
    r"(?:[一1][、. \t]+)?(?:引言|绪论|参考文献)|您可能感兴趣|推荐阅读|related articles\b)", re.IGNORECASE,
)
NOISE_TITLE = re.compile(r"^(?:abstract\b|摘\s*要|doi\b|https?://|issn\b|isbn\b|arxiv\b|"
                         r"authors?\s*[:：]|作者\s*[:：]|keywords?\b|关键词|"
                         r"research article$|original article$|published\b|"
                         r"publication date\b|发表|出版|copyright\b|©|page\s+\d+|license\b|"
                         r"provided proper attribution\b|permission\b|all rights reserved\b)",
                         re.IGNORECASE)
PLACEHOLDERS = {"none", "untitled", "unknown", "anonymous", "(anonymous)", "未命名", "无标题"}


class InvalidPDF(ValueError):
    """An upload cannot be imported."""


@dataclass(frozen=True)
class Page:
    text: str
    status: str


@dataclass(frozen=True)
class ExtractedPDF:
    fields: dict[str, str]
    sources: dict[str, str]
    pages: list[Page]


def normalize_doi(value):
    value = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi\s*[:：]\s*)", "",
                   value.strip(), flags=re.IGNORECASE)
    value = value.rstrip(".,;:")
    while value.endswith(")") and value.count(")") > value.count("("):
        value = value[:-1]
    return value if DOI_PATTERN.fullmatch(value) else ""


def _clean(value):
    if not isinstance(value, str):
        return ""
    return re.sub(r"[^\S\n]+", " ", value.replace("\x00", "")).strip()


def _field(metadata, name):
    value = _clean(metadata.get(name))
    return "" if value.casefold() in PLACEHOLDERS else value


def _match(pattern, text):
    matched = pattern.search(text)
    return _clean(matched.group(1)) if matched else ""


def _abstract(lines):
    for index, line in enumerate(lines):
        heading = ABSTRACT_HEADING.match(line)
        if not heading:
            continue
        chunks = [_clean(heading.group(1))]
        for following in lines[index + 1:index + 21]:
            if SECTION_HEADING.match(following) or ABSTRACT_HEADING.match(following):
                break
            if following.strip():
                chunks.append(_clean(following))
            if sum(map(len, chunks)) > FIELD_LIMITS["abstract"]:
                break
        return " ".join(filter(None, chunks))
    return ""


def _title(lines):
    for line in lines[:12]:
        line = _clean(line)
        if ABSTRACT_HEADING.match(line):
            break
        length = len(line)
        minimum = 4 if re.search(r"[\u3400-\u9fff]", line) else 6
        if minimum <= length <= 240 and not NOISE_TITLE.match(line) and not line.isnumeric():
            return line
    return ""


def _prominent_title(fragments, cropbox):
    if not fragments:
        return ""
    bottom, height = float(cropbox.bottom), float(cropbox.height)
    if height <= 0:
        return ""
    visible = [
        (y, x, size, text) for y, x, size, text in fragments
        if bottom + 0.48 * height <= y <= bottom + 0.98 * height
        and size >= 9 and not re.match(r"^\s*[\dIVX]+$", text)
    ]
    if not visible:
        return ""
    biggest = max(size for _, _, size, _ in visible)
    typical = sorted(size for _, _, size, _ in visible)[len(visible) // 2]
    if biggest < typical * 1.18:
        return ""
    chosen = sorted(
        (fragment for fragment in visible if fragment[2] >= biggest * 0.90),
        key=lambda fragment: (-fragment[0], fragment[1]),
    )
    title_lines = []
    for y, x, size, text in chosen:
        if title_lines and title_lines[-1][0] - y > biggest * 1.95:
            break
        if title_lines and abs(title_lines[-1][0] - y) <= 2.0:
            title_lines[-1][1].append((x, text))
        else:
            title_lines.append((y, [(x, text)]))
        if len(title_lines) > 3:
            return ""
    candidate = " ".join(
        " ".join(word for _, word in sorted(line)) for _, line in title_lines
    ).strip()
    if 4 <= len(candidate) <= 240 and not NOISE_TITLE.match(candidate):
        return candidate
    return ""


def _first_page_text(page, fragments):
    def record(text, cm, tm, font, size):
        text = " ".join(_clean(text).split())
        if not text:
            return
        horizontal = tm[0] * cm[0] + tm[1] * cm[2]
        vertical = tm[0] * cm[1] + tm[1] * cm[3]
        if horizontal <= 0 or abs(vertical) > abs(horizontal) * 0.15:
            return
        x = tm[4] * cm[0] + tm[5] * cm[2] + cm[4]
        y = tm[4] * cm[1] + tm[5] * cm[3] + cm[5]
        fragments.append((y, x, size * horizontal, text))
    return page.extract_text(visitor_text=record)


def _front_matter(text):
    lines = []
    for line in text.splitlines()[:36]:
        if ABSTRACT_HEADING.match(line) or _FRONT_MATTER_END.match(line):
            break
        if line.strip():
            lines.append(line.strip())
    return lines


def _title_key(line):
    return re.sub(r"\s+", "", line).casefold()


def _chinese_title_byline(headers, title):
    title_key = _title_key(title)
    if not re.search(r"[\u3400-\u9fff]", title_key):
        return ""
    for header in headers:
        for index, line in enumerate(header[:-1]):
            if _title_key(line) != title_key:
                continue
            names = header[index + 1]
            following = header[index + 2:index + 3]
            if not following or not following[0].startswith(("引用本文", "（", "(")):
                continue
            if _CHINESE_BYLINE.fullmatch(names):
                return ", ".join(re.findall(_CHINESE_NAME, names))
    return ""


def _imprint_year(headers, title):
    title_key = _title_key(title)
    for header in headers:
        for line in header:
            imprint = _JOURNAL_IMPRINT.search(line)
            if imprint and title_key and _title_key(line[:imprint.start()]).endswith(title_key):
                return imprint.group(1)
        for index, line in enumerate(header[:6]):
            if line.casefold().startswith("proceedings of "):
                imprint = "\n".join(header[index:index + 4])
                if _CONFERENCE_PAGES.search(imprint):
                    year = _match(_CONFERENCE_DATE, imprint)
                    if year:
                        return year
    return ""


def _extract_metadata(metadata, first_pages, filename, prominent_title):
    first = first_pages[0].text[:14_000]
    opening = "\n".join(page.text[:14_000] for page in first_pages[:2])
    first_lines = first.splitlines()
    headers = [_front_matter(page.text[:14_000]) for page in first_pages[:2]]
    embedded_doi = normalize_doi(_field(metadata, "/DOI")) or normalize_doi(_field(metadata, "/doi"))
    fields = {}
    sources = {}

    def field(name, *candidates):
        for value, source in candidates:
            if value:
                fields[name] = value[:FIELD_LIMITS[name]].strip()
                sources[name] = source
                return
        fields[name] = ""

    title_property = _field(metadata, "/Title")
    filename_title = PurePath(filename).stem or "未命名文献"
    field("title", (title_property, "pdf_metadata"), (prominent_title or _title(first_lines), "opening_text"),
          (filename_title, "filename"))
    title = fields["title"] if sources["title"] != "filename" else ""
    headers = headers[:1] + [
        header for header in headers[1:] if title and any(_title_key(line) == _title_key(title) for line in header)
    ]
    bibliographic_text = "\n".join(line for header in headers for line in header)
    visible_dois = {}
    for match in DOI_LABEL.finditer(bibliographic_text):
        doi = normalize_doi(match.group(1))
        if doi:
            visible_dois.setdefault(doi.casefold(), doi)
    visible_doi = next(iter(visible_dois.values())) if len(visible_dois) == 1 else ""

    field("authors", (_field(metadata, "/Author"), "pdf_metadata"),
          (_match(BYLINE, bibliographic_text) or _chinese_title_byline(headers, title), "opening_text"))
    field("abstract", (_abstract(opening.splitlines()), "opening_text"))
    field("keywords", (_match(KEYWORDS, opening), "opening_text"),
          (_field(metadata, "/Keywords"), "pdf_metadata"))
    field("year", (_imprint_year(headers, title) or _match(PUBLICATION_YEAR, bibliographic_text), "opening_text"))
    field("doi", (embedded_doi, "pdf_metadata"), (visible_doi, "opening_text"))
    fields["category"] = ""
    return fields, sources


def parse_pdf(raw, filename):
    return _parse_pdf(raw, filename, MAX_PAGES)


def extract_pdf_metadata(raw, filename):
    extracted = _parse_pdf(raw, filename, 2)
    return extracted.fields, extracted.sources


def _parse_pdf(raw, filename, extract_limit):
    if not raw or b"%PDF-" not in raw[:1024]:
        raise InvalidPDF("无法识别 PDF 文件。请重新选择原始 PDF。")
    try:
        reader = PdfReader(io.BytesIO(raw))
        if reader.is_encrypted:
            raise InvalidPDF("这份 PDF 已加密。请上传可直接打开的版本。")
        count = len(reader.pages)
        if not 1 <= count <= MAX_PAGES:
            raise InvalidPDF(f"目前支持 1 至 {MAX_PAGES} 页的 PDF。")
        pages = []
        prominent_title = ""
        for number, page in enumerate(islice(reader.pages, extract_limit)):
            try:
                if number == 0:
                    fragments = []
                    text = _clean(_first_page_text(page, fragments))
                    prominent_title = _prominent_title(fragments, page.cropbox)
                else:
                    text = _clean(page.extract_text())
            except (PyPdfError, UnicodeError, ValueError, KeyError, TypeError, OverflowError):
                pages.append(Page("", "extraction_failed"))
                continue
            if len(text) > MAX_PAGE_CHARACTERS:
                pages.append(Page(text[:MAX_PAGE_CHARACTERS], "truncated"))
            else:
                pages.append(Page(text, "available" if text else "no_text"))
        fields, sources = _extract_metadata(reader.metadata or {}, pages, filename, prominent_title)
        return ExtractedPDF(fields, sources, pages)
    except InvalidPDF:
        raise
    except (PyPdfError, UnicodeError, ValueError, KeyError, TypeError, OverflowError, RecursionError) as error:
        raise InvalidPDF("PDF 读取失败。请确认文件完整后再试。") from error
