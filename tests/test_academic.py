import io
import json
import re
import unittest
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlencode, urlsplit
from unittest.mock import Mock

from research_library.academic import AcademicSearch, SearchError, parse_query

CROSSREF = {
    "status": "ok", "message-type": "work-list", "message": {
        "total-results": 21, "items": [{
            "DOI": "10.12345/sample.EN", "title": ["可信科研检索"],
            "author": [{"given": "A.", "family": "Rivera"}], "published": {"date-parts": [[2024]]},
            "container-title": ["Fixture journal"], "type": "journal-article",
        }],
    },
}
ATOM_FEED = b"""<feed xmlns="http://www.w3.org/2005/Atom" xmlns:os="http://a9.com/-/spec/opensearch/1.1/">
<os:totalResults>1</os:totalResults><entry><id>http://arxiv.org/abs/1801.12345v3</id>
<title>Evidence locating</title><published>2018-07-06T00:00:00Z</published>
<author><name>A. Rivera</name></author><category term="cs.CL"/></entry></feed>"""


class AcademicProtocolTest(unittest.TestCase):
    def test_crossref_query_and_cache_use_the_documented_fields(self):
        opener = Mock(return_value=io.BytesIO(json.dumps(CROSSREF).encode()))
        service = AcademicSearch(opener)
        query = parse_query({"q": "可信", "author": "Rivera", "year": "2024", "field": "cs.CL", "page": "2"})
        rows, total = service.fetch(query)
        self.assertEqual((rows[0]["title"], rows[0]["year"], total), ("可信科研检索", "2024", 21))
        self.assertEqual(rows[0]["url"], "https://doi.org/10.12345/sample.EN")
        url = urlsplit(opener.call_args.args[0].full_url)
        params = parse_qs(url.query)
        self.assertEqual(url.netloc, "api.crossref.org")
        self.assertEqual(params["query.bibliographic"], ["可信 natural language processing"])
        self.assertEqual(params["query.author"], ["Rivera"])
        self.assertEqual(params["offset"], ["10"])
        self.assertEqual(params["filter"], ["from-pub-date:2024-01-01,until-pub-date:2024-12-31"])
        self.assertEqual(service.fetch(query), (rows, total))
        opener.assert_called_once()

    def test_arxiv_category_and_version_are_separate_from_doi(self):
        opener = Mock(return_value=io.BytesIO(ATOM_FEED))
        rows, total = AcademicSearch(opener).fetch(parse_query(
            {"source": "arxiv", "q": "evidence", "field": "cs.CL", "year": "2018", "author": "Rivera"}
        ))
        self.assertEqual(total, 1)
        self.assertEqual(rows[0]["provider_id"], "1801.12345v3")
        self.assertEqual(rows[0]["url"], "https://arxiv.org/abs/1801.12345v3")
        self.assertEqual(rows[0]["doi"], "")
        params = parse_qs(urlsplit(opener.call_args.args[0].full_url).query)
        self.assertIn('au:"Rivera" AND cat:cs.CL AND submittedDate:[201801010000 TO 201812312359]',
                      params["search_query"][0])

    def test_rate_limits_do_not_retry_and_invalid_input_does_not_fetch(self):
        error = HTTPError("https://api.crossref.org", 429, "remote", {"Retry-After": "11"}, io.BytesIO(b""))
        opener = Mock(side_effect=error)
        service = AcademicSearch(opener)
        with self.assertRaisesRegex(SearchError, "11 秒"):
            service.fetch(parse_query({"q": "test"}))
        with self.assertRaisesRegex(SearchError, "暂缓"):
            service.fetch(parse_query({"q": "another"}))
        for invalid in ({"year": "abcd"}, {"page": "500", "q": "x"}, {"source": "unknown", "q": "x"}):
            with self.assertRaises(SearchError):
                parse_query(invalid)
        self.assertEqual(opener.call_count, 1)


if __name__ == "__main__":
    unittest.main()
