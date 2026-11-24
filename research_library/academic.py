"""Read public scholarly metadata from Crossref and arXiv."""

import json
import re
import time
from collections import OrderedDict
from dataclasses import dataclass
from datetime import date, datetime, timezone
from email.utils import parsedate_to_datetime
from http.client import HTTPException
from threading import Lock
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

from .ingest import normalize_doi

PROVIDERS = {"crossref": "Crossref", "arxiv": "arXiv"}
FIELDS = {
    "cs.AI": ("人工智能", "artificial intelligence"),
    "cs.CL": ("自然语言处理", "natural language processing"),
    "cs.CV": ("计算机视觉", "computer vision"),
    "cs.LG": ("机器学习", "machine learning"),
    "stat.AP": ("应用统计", "applied statistics"),
    "math.OC": ("优化与控制", "optimization and control"),
    "eess.SP": ("信号处理", "signal processing"),
    "quant-ph": ("量子物理", "quantum physics"),
    "econ.EM": ("计量经济", "econometrics"),
    "q-bio.QM": ("定量生物学方法", "quantitative biology"),
}
ROWS = 10
MAX_PAGE = 50
MAX_BODY = 1024 * 1024
ATOM = "{http://www.w3.org/2005/Atom}"
ARXIV = "{http://arxiv.org/schemas/atom}"
OPENSEARCH = "{http://a9.com/-/spec/opensearch/1.1/}"


class SearchError(ValueError):
    """A public error message that does not include remote content."""


@dataclass(frozen=True)
class SearchQuery:
    provider: str
    keyword: str
    author: str
    year: str
    field: str
    page: int


def parse_query(args):
    provider = args.get("source", "crossref")
    keyword, author, year, field = (args.get(name, "").strip() for name in ("q", "author", "year", "field"))
    page = args.get("page", "1").strip()
    if provider not in PROVIDERS or field and field not in FIELDS:
        raise SearchError("请选择有效的检索服务和研究领域。")
    if len(keyword) > 150 or len(author) > 100:
        raise SearchError("关键词最多 150 个字符，作者最多 100 个字符。")
    if year and (not re.fullmatch(r"[0-9]{4}", year) or not 1000 <= int(year) <= date.today().year + 1):
        raise SearchError("请输入有效的四位年份。")
    if not re.fullmatch(r"[0-9]{1,2}", page) or not 1 <= int(page) <= MAX_PAGE:
        raise SearchError(f"可查看第 1 至 {MAX_PAGE} 页，请缩小检索范围。")
    if not (keyword or author or year or field):
        raise SearchError("请输入关键词、作者、年份或选择研究领域。")
    return SearchQuery(provider, keyword, author, year, field, int(page))


def _url(query):
    offset = (query.page - 1) * ROWS
    if query.provider == "crossref":
        params = {"rows": ROWS, "offset": offset, "select": "DOI,title,author,published,type,container-title"}
        terms = [query.keyword]
        if query.field:
            terms.append(FIELDS[query.field][1])
        if any(terms):
            params["query.bibliographic"] = " ".join(filter(None, terms))
        if query.author:
            params["query.author"] = query.author
        if query.year:
            params["filter"] = f"from-pub-date:{query.year}-01-01,until-pub-date:{query.year}-12-31"
        return "https://api.crossref.org/works?" + urlencode(params)

    def phrase(value):
        return ' '.join(re.sub(r'["\\\x00-\x1f]', ' ', value).split())

    clauses = [f'{key}:"{phrase(value)}"' for key, value in (("all", query.keyword), ("au", query.author))
               if phrase(value)]
    if query.field:
        clauses.append(f"cat:{query.field}")
    if query.year:
        clauses.append(f"submittedDate:[{query.year}01010000 TO {query.year}12312359]")
    if not clauses:
        raise SearchError("请输入可检索的关键词或作者。")
    params = {"search_query": " AND ".join(clauses), "start": offset, "max_results": ROWS}
    return "https://export.arxiv.org/api/query?" + urlencode(params)


def clean(value, limit):
    return " ".join(value.split())[:limit] if isinstance(value, str) else ""


def _first(value, limit):
    return clean(value[0], limit) if isinstance(value, list) and value else ""


def _year(value):
    value = clean(str(value), 4) if value is not None else ""
    return value if re.fullmatch(r"[1-9][0-9]{3}", value) else ""


def _count(value):
    try:
        return max(0, int(value))
    except (ValueError, TypeError):
        return 0


def _crossref(body):
    data = json.loads(body)
    if not isinstance(data, dict) or data.get("status") != "ok" or data.get("message-type") != "work-list":
        raise SearchError("Crossref 返回了非检索结果。")
    message = data.get("message")
    if not isinstance(message, dict) or not isinstance(message.get("items"), list):
        raise SearchError("Crossref 返回缺少文献列表。")
    records = []
    for item in message["items"][:ROWS]:
        if not isinstance(item, dict):
            continue
        title = _first(item.get("title"), 600)
        doi = normalize_doi(clean(item.get("DOI"), 280))
        if not title or not doi:
            continue
        raw_authors = item.get("author")
        authors = []
        for raw in raw_authors[:50] if isinstance(raw_authors, list) else []:
            if isinstance(raw, dict):
                name = clean(raw.get("name"), 120) or " ".join(filter(None, (
                    clean(raw.get("given"), 60), clean(raw.get("family"), 80)
                )))
                if name:
                    authors.append(name)
        published = item.get("published")
        parts = published.get("date-parts") if isinstance(published, dict) else None
        year = _year(parts[0][0]) if isinstance(parts, list) and parts and isinstance(parts[0], list) and parts[0] else ""
        records.append({
            "provider": "crossref", "provider_id": doi.lower(), "title": title, "authors": "; ".join(authors)[:1000],
            "year": year, "doi": doi, "venue": _first(item.get("container-title"), 350),
            "kind": clean(item.get("type"), 60), "url": "https://doi.org/" + quote(doi, safe="/"),
        })
    return records, _count(message.get("total-results"))


def _arxiv(body):
    if b"<!DOCTYPE" in body or b"<!ENTITY" in body:
        raise SearchError("arXiv 返回的 XML 格式异常。")
    feed = ET.fromstring(body)
    if feed.tag != ATOM + "feed":
        raise SearchError("arXiv 返回了非检索结果。")
    records = []
    for item in feed.findall(ATOM + "entry")[:ROWS]:
        raw_id = item.findtext(ATOM + "id", "")
        if raw_id.startswith(("http://arxiv.org/api/errors", "https://arxiv.org/api/errors")):
            raise SearchError("arXiv 拒绝了这组检索条件。")
        match = re.fullmatch(
            r"https?://arxiv\.org/abs/(\d{4}\.\d{4,5}(?:v\d+)?|[a-z-]+(?:\.[A-Z]{2})?/\d{7}(?:v\d+)?)",
            raw_id,
        )
        title = clean(item.findtext(ATOM + "title"), 600)
        if not match or not title:
            continue
        identifier = match.group(1)
        authors = [clean(node.findtext(ATOM + "name"), 140) for node in item.findall(ATOM + "author")[:50]]
        categories = [clean(node.get("term"), 30) for node in item.findall(ATOM + "category")[:12]]
        records.append({
            "provider": "arxiv", "provider_id": identifier, "title": title,
            "authors": "; ".join(filter(None, authors))[:1000], "year": _year(item.findtext(ATOM + "published", "")),
            "doi": normalize_doi(clean(item.findtext(ARXIV + "doi"), 280)) or "",
            "venue": " · ".join(filter(None, categories)), "kind": "预印本", "url": "https://arxiv.org/abs/" + identifier,
        })
    return records, _count(feed.findtext(OPENSEARCH + "totalResults"))


def _retry_delay(headers):
    value = (headers or {}).get("Retry-After", "")
    try:
        if value.isascii() and value.isdigit() and len(value) < 9:
            return max(5, int(value))
        seconds = (parsedate_to_datetime(value) - datetime.now(timezone.utc)).total_seconds()
        return max(5, int(seconds) + 1)
    except (ValueError, TypeError, OverflowError):
        return 30


class AcademicSearch:
    """Enforce one active request per provider and briefly cache repeated requests."""

    def __init__(self, opener=urlopen):
        self.open = opener
        self.locks = {key: Lock() for key in PROVIDERS}
        self.ready = dict.fromkeys(PROVIDERS, 0)
        self.cache = {key: OrderedDict() for key in PROVIDERS}

    def fetch(self, query):
        provider = query.provider
        label = PROVIDERS[provider]
        lock = self.locks[provider]
        if not lock.acquire(blocking=False):
            raise SearchError(f"{label} 正在处理检索，请稍后再试。")
        try:
            cache = self.cache[provider]
            now = time.monotonic()
            if query in cache and now - cache[query][0] < 180:
                return cache[query][1]
            if now < self.ready[provider]:
                raise SearchError(f"{label} 暂缓接受新检索，请稍后再试。")
            req = Request(_url(query), headers={
                "User-Agent": "ResearchLiteratureWorkbench/0.1",
                "Accept": "application/json" if provider == "crossref" else "application/atom+xml",
            })
            self.ready[provider] = now + (1.05 if provider == "crossref" else 3.1)
            try:
                with self.open(req, timeout=12) as response:
                    body = response.read(MAX_BODY + 1)
                if len(body) > MAX_BODY:
                    raise SearchError(f"{label} 的结果超出单次读取上限。")
                result = _crossref(body) if provider == "crossref" else _arxiv(body)
            except HTTPError as error:
                status = error.code
                if status == 429:
                    delay = _retry_delay(error.headers)
                    self.ready[provider] = time.monotonic() + delay
                    message = f"{label} 已限流，请至少在 {delay} 秒后再试。"
                else:
                    message = f"{label} 请求失败（HTTP {status}）。"
                error.close()
                raise SearchError(message) from None
            except (OSError, URLError, HTTPException):
                raise SearchError(f"暂时无法连接 {label}，请稍后再试。") from None
            except (json.JSONDecodeError, ET.ParseError, UnicodeError, RecursionError):
                raise SearchError(f"{label} 返回了无法读取的结果。") from None
            cache[query] = (time.monotonic(), result)
            cache.move_to_end(query)
            if len(cache) > 16:
                cache.popitem(last=False)
            return result
        finally:
            lock.release()
