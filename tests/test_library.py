import io
import sqlite3
import unittest
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlencode, urlsplit

from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfgen.canvas import Canvas

from research_library import create_app
from research_library.ingest import FIELD_LIMITS


def sample_pdf(language):
    stream = io.BytesIO()
    canvas = Canvas(stream, pagesize=A4)
    if language == "zh":
        font = "STSong-Light"
        pdfmetrics.registerFont(UnicodeCIDFont(font))
        title = "检索增强生成方法比较"
        canvas.setTitle(title)
        canvas.setAuthor("王小明")
        lines = (
            title, "作者：王小明", "出版年：2025", "DOI: 10.12345/sample.zh",
            "摘要：本文比较了用于文献检索的方法。", "关键词：文献检索；证据定位", "引言", "这一行不是摘要。",
        )
        evidence_text = "第二页中的证据定位标记"
    else:
        font = "Helvetica"
        title = "Retrieval with Grounded Evidence"
        canvas.setTitle(title)
        canvas.setAuthor("A. Rivera")
        lines = (
            title, "Author: A. Rivera", "Published: 2024", "DOI: 10.12345/sample.en",
            "Abstract: We compare methods for tracing evidence.", "A second sentence.",
            "Keywords: retrieval; evidence", "1. Introduction", "This is outside the abstract.",
        )
        evidence_text = "The evidence belongs on the second PDF page."
    canvas.setFont(font, 16)
    for index, line in enumerate(lines):
        canvas.drawString(70, 760 - index * 31, line)
        if index == 0:
            canvas.setFont(font, 12)
    canvas.showPage()
    canvas.setFont(font, 12)
    canvas.drawString(70, 760, evidence_text)
    canvas.showPage()
    canvas.save()
    return stream.getvalue()


def scanned_page():
    stream = io.BytesIO()
    canvas = Canvas(stream, pagesize=A4)
    canvas.setTitle("untitled")
    canvas.setAuthor("anonymous")
    canvas.rect(72, 600, 80, 45, fill=1)
    canvas.showPage()
    canvas.save()
    return stream.getvalue()


class LiteratureLibraryTest(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.database = Path(self.temp.name) / "library.sqlite3"
        self.config = {"TESTING": True, "LIBRARY_DB": self.database}
        self.app = create_app(self.config)
        self.client = self.app.test_client()
        home = self.client.get("/")
        self.assertEqual(home.status_code, 200)
        self.assertIn("为你的研究建一个课题", home.get_data(as_text=True))
        self.topic_path = self.create_topic("可信科研检索")

    def csrf(self):
        with self.client.session_transaction() as session:
            return session["csrf_token"]

    def create_topic(self, name):
        response = self.client.post("/topics", data={"csrf_token": self.csrf(), "name": name})
        self.assertEqual(response.status_code, 302)
        return response.location

    def upload(self, raw, filename, topic=None):
        return self.client.post((topic or self.topic_path) + "/documents", data={
            "csrf_token": self.csrf(), "pdf": (io.BytesIO(raw), filename),
        }, content_type="multipart/form-data")

    def document_row(self, response):
        self.assertEqual(response.status_code, 302)
        path = urlsplit(response.location).path
        self.assertTrue(path.startswith("/documents/"), self.client.get(response.location).get_data(as_text=True))
        document_id = path.rsplit("/", 1)[1]
        return path, self.app.extensions["research_library"].document(document_id)

    def test_bilingual_metadata_original_and_page_evidence(self):
        for language, author, year, phrase in (
            ("zh", "王小明", "2025", "第二页中的证据定位标记"),
            ("en", "A. Rivera", "2024", "The evidence belongs on the second PDF page."),
        ):
            with self.subTest(language=language):
                raw = sample_pdf(language)
                path, entry = self.document_row(self.upload(raw, f"sample-{language}.pdf"))
                self.assertEqual(entry["page_count"], 2)
                self.assertEqual(entry["text_page_count"], 2)
                self.assertEqual(entry["authors"], author)
                self.assertEqual(entry["year"], year)
                self.assertEqual(entry["doi"], f"10.12345/sample.{language}")
                self.assertTrue(entry["abstract"] and entry["keywords"])
                self.assertNotIn("不是摘要", entry["abstract"])
                self.assertNotIn("outside the abstract", entry["abstract"])
                page = self.client.get(f"/api/v1{path}/pages/2").json
                self.assertEqual(page["physical_page"], 2)
                self.assertEqual(page["source_url"], f"{path}?page=2")
                self.assertIn(phrase, page["text"])
                reader = self.client.get(page["source_url"]).get_data(as_text=True)
                self.assertIn(f'{path}/pdf#page=2', reader)
                preview_url = f"{path}/pages/2/preview.png"
                self.assertIn(preview_url, reader)
                self.assertIn(phrase, reader)
                preview = self.client.get(preview_url)
                self.assertEqual(preview.status_code, 200)
                self.assertEqual(preview.mimetype, "image/png")
                self.assertTrue(preview.data.startswith(b"\x89PNG\r\n\x1a\n"))
                self.assertNotEqual(preview.data, self.client.get(f"{path}/pages/1/preview.png").data)
                self.assertEqual(self.client.get(preview_url, headers={"If-None-Match": preview.headers["ETag"]}).status_code, 304)
                pdf = self.client.get(path + "/pdf")
                self.assertEqual(pdf.mimetype, "application/pdf")
                self.assertEqual(pdf.data, raw)
                part = self.client.get(path + "/pdf", headers={"Range": "bytes=0-9"})
                self.assertEqual(part.status_code, 206)
                self.assertEqual(part.data, raw[:10])
                self.assertEqual(self.client.get(f"/api/v1{path}/pages/3").status_code, 404)

    def test_title_uses_page_layout_if_attribution_comes_first(self):
        raw = io.BytesIO()
        canvas = Canvas(raw, pagesize=A4)
        canvas.setTitle("")
        canvas.setAuthor("")
        canvas.setFont("Helvetica", 10)
        canvas.drawString(72, 775, "Provided proper attribution is provided, reprinting is permitted.")
        canvas.drawString(72, 760, "This notice must not be mistaken for the article.")
        canvas.setFont("Helvetica-Bold", 19)
        canvas.drawString(95, 719, "Grounding Literature")
        canvas.drawString(95, 696, "with Reliable Evidence")
        canvas.setFont("Helvetica", 11)
        canvas.drawString(95, 660, "Abstract: Evidence should be locatable.")
        canvas.drawString(95, 640, "* Research support acknowledgement.")
        canvas.save()
        _, entry = self.document_row(self.upload(raw.getvalue(), "paper-with-notice.pdf"))
        self.assertEqual(entry["title"], "Grounding Literature with Reliable Evidence")
        self.assertEqual(entry["abstract"], "Evidence should be locatable.")

    def test_search_scope_edit_duplicate_and_reopen(self):
        raw = sample_pdf("zh")
        path, row = self.document_row(self.upload(raw, "温和样本.pdf"))
        fields = {field: row[field] for field in FIELD_LIMITS}
        fields.update({"title": "人工校订标题", "category": "检索方法", "doi": "https://doi.org/10.12345/revised"})
        self.assertEqual(self.client.post(path + "/metadata", data={
            **fields, "csrf_token": self.csrf(), "page": 2,
        }).status_code, 302)
        self.assertEqual(self.upload(raw, "duplicate.pdf").location, path + "?page=1")
        other_topic = self.create_topic("另一个课题")
        other_path, _ = self.document_row(self.upload(raw, "separate.pdf", other_topic))
        self.assertNotEqual(path, other_path)
        fresh = create_app(self.config).test_client()
        filters = urlencode({"q": "证据定位标记", "category": "检索方法"})
        result = fresh.get(f"{self.topic_path}?{filters}").get_data(as_text=True)
        self.assertIn("人工校订标题", result)
        self.assertIn(f"{path}?page=2", result)
        self.assertNotIn(f"{other_path}?page=", result)
        recent_document = fresh.get(path + "?page=2").get_data(as_text=True)
        self.assertIn("10.12345/revised", recent_document)
        self.assertIn("手动填写", recent_document)
        escaped = fresh.get(self.topic_path + "?q=%25").get_data(as_text=True)
        self.assertIn("未找到匹配文献", escaped)

    def test_rejects_invalid_and_encrypted_and_keeps_textless_pdf(self):
        bogus = self.upload(b"not a PDF", "not-real.pdf")
        self.assertEqual(bogus.location, self.topic_path)
        self.assertIn("无法识别 PDF", self.client.get(bogus.location).get_data(as_text=True))
        writer = PdfWriter()
        writer.add_page(PdfReader(io.BytesIO(scanned_page())).pages[0])
        writer.encrypt("restricted")
        encrypted = io.BytesIO()
        writer.write(encrypted)
        invalid = self.upload(encrypted.getvalue(), "restricted.pdf")
        self.assertIn("已加密", self.client.get(invalid.location).get_data(as_text=True))
        path, entry = self.document_row(self.upload(scanned_page(), "无文本页.pdf"))
        self.assertEqual(entry["title"], "无文本页")
        self.assertEqual(entry["text_page_count"], 0)
        self.assertEqual(entry["year"], "")
        self.assertEqual(entry["doi"], "")
        self.assertEqual(self.client.get(f"/api/v1{path}/pages/1").json["status"], "no_text")
        self.assertIn("扫描页通常需要 OCR", self.client.get(path).get_data(as_text=True))

    def test_delete_cascades_and_post_requires_session(self):
        path, _ = self.document_row(self.upload(sample_pdf("en"), "remove.pdf"))
        self.assertEqual(self.client.post(path + "/delete").status_code, 400)
        self.assertEqual(self.client.get(path).status_code, 200)
        response = self.client.post(path + "/delete", data={"csrf_token": self.csrf()})
        self.assertEqual(response.location, self.topic_path)
        self.assertEqual(self.client.get(path).status_code, 404)
        self.assertEqual(self.client.get(path + "/pdf").status_code, 404)
        with closing(sqlite3.connect(self.database)) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM pages").fetchone()[0], 0)

    def test_separate_topic_names_and_escaped_metadata(self):
        self.assertEqual(self.create_topic("可信科研检索"), "/")
        self.assertIn("已有同名课题", self.client.get("/", follow_redirects=True).get_data(as_text=True))
        path, row = self.document_row(self.upload(sample_pdf("en"), "title.pdf"))
        fields = {field: row[field] for field in FIELD_LIMITS}
        fields.update({"title": "<script>not markup</script>", "year": "20ab"})
        self.client.post(path + "/metadata", data={**fields, "csrf_token": self.csrf()})
        self.assertIn("年份请填写", self.client.get(path).get_data(as_text=True))
        fields["year"] = "2025"
        self.client.post(path + "/metadata", data={**fields, "csrf_token": self.csrf()})
        page = self.client.get(path).get_data(as_text=True)
        self.assertIn("&lt;script&gt;not markup&lt;/script&gt;", page)
        self.assertNotIn("<script>not markup</script>", page)


if __name__ == "__main__":
    unittest.main()
