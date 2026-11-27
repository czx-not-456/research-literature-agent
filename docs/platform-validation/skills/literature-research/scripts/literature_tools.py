"""Independent, read-only Crossref operations for the literature-research Skill."""

import argparse
import json
import re
import sys
from http.client import HTTPException
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

BASE = "https://api.crossref.org/works"
PREFIX = "LIT_RESEARCH "
MAX_BYTES = 512 * 1024


class CitationServiceError(Exception):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def valid_doi(value):
    return isinstance(value, str) and len(value) <= 210 and bool(re.fullmatch(r"10\.[0-9]{4,9}/[!-~]+", value))


def _request(url, expected):
    req = Request(url, headers={"Accept": "application/json", "User-Agent": "ResearchLiteratureAgentSkill/1.0"})
    try:
        with build_opener(NoRedirect()).open(req, timeout=10) as response:
            payload = response.read(MAX_BYTES + 1)
        if len(payload) > MAX_BYTES:
            raise CitationServiceError("response_too_large")
        result = json.loads(payload)
    except HTTPError as error:
        status = error.code
        error.close()
        raise CitationServiceError(f"http_{status}") from None
    except (URLError, HTTPException, OSError):
        raise CitationServiceError("network_unavailable") from None
    except (ValueError, UnicodeError, RecursionError):
        raise CitationServiceError("malformed_api_response") from None
    if (not isinstance(result, dict) or result.get("status") != "ok"
            or result.get("message-type") != expected or not isinstance(result.get("message"), dict)):
        raise CitationServiceError("unexpected_api_response")
    return result["message"]


def _clean(value, length):
    return " ".join(value.split())[:length] if isinstance(value, str) else ""


def _metadata(item):
    doi = item.get("DOI")
    titles = item.get("title")
    title = _clean(titles[0], 300) if isinstance(titles, list) and titles else ""
    if not valid_doi(doi) or not title:
        return None
    parts = (item.get("published") or {}).get("date-parts") if isinstance(item.get("published"), dict) else None
    year = str(parts[0][0]) if isinstance(parts, list) and parts and isinstance(parts[0], list) and parts[0] else ""
    return {"doi": doi, "title": title, "year": year if re.fullmatch(r"[0-9]{4}", year) else "",
            "kind": _clean(item.get("type"), 48), "url": "https://doi.org/" + quote(doi, safe="/")}


def search(query):
    if not isinstance(query, str) or not 1 <= len(query.strip()) <= 120:
        raise CitationServiceError("invalid_query")
    params = {"query.bibliographic": query.strip(), "rows": 3, "filter": "type:journal-article",
              "select": "DOI,title,published,type"}
    items = _request(BASE + "?" + urlencode(params), "work-list").get("items")
    if not isinstance(items, list):
        raise CitationServiceError("missing_results")
    records = [_metadata(item) for item in items[:3] if isinstance(item, dict)]
    return [item for item in records if item and item["kind"] == "journal-article"]


def verify(doi):
    if not valid_doi(doi):
        raise CitationServiceError("invalid_doi")
    item = _metadata(_request(BASE + "/" + quote(doi, safe="/"), "work"))
    if not item or item["doi"].casefold() != doi.casefold():
        raise CitationServiceError("doi_mismatch_or_missing_metadata")
    return [item]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="operation", required=True)
    commands.add_parser("search").add_argument("--query", required=True)
    commands.add_parser("verify").add_argument("--doi", required=True)
    args = parser.parse_args()
    payload = {"operation": args.operation, "provider": "Crossref"}
    try:
        records = search(args.query) if args.operation == "search" else verify(args.doi)
        payload.update(status="ok" if records else "empty", items=records)
    except CitationServiceError as error:
        payload.update(status="failed", code=str(error), items=[])
    print(PREFIX + json.dumps(payload, ensure_ascii=True, separators=(",", ":")))
    return 0 if payload["status"] != "failed" else 1


if __name__ == "__main__":
    sys.exit(main())
