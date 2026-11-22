import csv
import io
import json
import sqlite3
import unittest
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlencode, urlsplit
from unittest.mock import Mock, patch

from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfgen.canvas import Canvas

from research_library import create_app
from research_library.agentarts import AgentArtsError
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


    def test_batch_upload_retains_valid_pdfs_and_skips_duplicates(self):
        chinese = sample_pdf("zh")
        english = sample_pdf("en")
        response = self.client.post(self.topic_path + "/documents", data={
            "csrf_token": self.csrf(),
            "pdf": [(io.BytesIO(chinese), "first.pdf"), (io.BytesIO(b"broken"), "broken.pdf"),
                    (io.BytesIO(english), "second.pdf"), (io.BytesIO(chinese), "copy.pdf")],
        }, content_type="multipart/form-data")
        self.assertEqual(response.location, self.topic_path)
        body = self.client.get(response.location).get_data(as_text=True)
        self.assertIn("新增 2 篇，重复跳过 1 份，导入失败 1 份", body)
        self.assertIn("broken.pdf", body)
        self.assertIn("multiple required", body)
        topic_id = self.topic_path.rsplit("/", 1)[1]
        documents = self.app.extensions["research_library"].list_documents(topic_id, "", "")
        self.assertEqual({row["filename"] for row in documents}, {"first.pdf", "second.pdf"})
        for row in documents:
            self.assertEqual(self.client.get(f'/api/v1/documents/{row["id"]}/pages/2').status_code, 200)

    def test_batch_upload_enforces_caps_and_individual_size(self):
        self.app.config["MAX_CONTENT_LENGTH"] = 512
        def send(parts):
            return self.client.post(self.topic_path + "/documents", data={
                "csrf_token": self.csrf(),
                "pdf": [(io.BytesIO(content), name) for name, content in parts],
            }, content_type="multipart/form-data")

        pdf = sample_pdf("en")
        overflow = send([(f"{number}.pdf", pdf) for number in range(11)])
        self.assertIn("每批最多上传 10 份", self.client.get(overflow.location).get_data(as_text=True))
        with patch("research_library.MAX_BATCH_BYTES", len(pdf) + 20):
            self.assertEqual(send([("first.pdf", pdf), ("second.pdf", pdf)]).status_code, 413)
        topic_id = self.topic_path.rsplit("/", 1)[1]
        library = self.app.extensions["research_library"]
        self.assertEqual(library.list_documents(topic_id, "", ""), [])
        with patch("research_library.MAX_UPLOAD_BYTES", len(pdf)):
            response = send([("oversized.pdf", pdf + b"x"), ("allowed.pdf", pdf)])
        self.assertIn("新增 1 篇，重复跳过 0 份，导入失败 1 份",
                      self.client.get(response.location).get_data(as_text=True))
        self.assertEqual([row["filename"] for row in library.list_documents(topic_id, "", "")], ["allowed.pdf"])

    def test_rename_topic_updates_title_without_changing_existing_source_urls(self):
        path, document = self.document_row(self.upload(sample_pdf("en"), "owned.pdf"))
        self.create_topic("Other Topic")
        form = self.client.get(self.topic_path).get_data(as_text=True)
        self.assertIn("编辑名称", form)
        self.assertIn(f'action="{self.topic_path}/name"', form)
        self.assertEqual(self.client.post(self.topic_path + "/name", data={"name": "Blocked"}).status_code, 400)
        for invalid, message in (("  other topic ", "已有同名课题"), ("  ", "1 至 100"),
                                 ("a" * 101, "1 至 100")):
            response = self.client.post(self.topic_path + "/name", data={
                "csrf_token": self.csrf(), "name": invalid,
            }, follow_redirects=True)
            html = response.get_data(as_text=True)
            self.assertIn(message, html)
            self.assertIn("data-rename-topic open", html)
            self.assertIn("<h1>可信科研检索</h1>", html)
        response = self.client.post(self.topic_path + "/name", data={
            "csrf_token": self.csrf(), "name": "  已重命名的课题  ",
        })
        self.assertEqual(response.location, self.topic_path)
        listing = create_app(self.config).test_client().get(self.topic_path).get_data(as_text=True)
        self.assertIn("<h1>已重命名的课题</h1>", listing)
        self.assertIn("<span>已重命名的课题</span>", listing)
        self.assertIn(path + "?page=1", listing)
        page = self.client.get("/api/v1" + path + "/pages/2").json
        self.assertEqual(page["source_url"], path + "?page=2")
        self.assertEqual(page["document_id"], document["id"])
        self.assertIn("已重命名的课题", self.client.get(page["source_url"]).get_data(as_text=True))

    def test_matrix_generates_and_links_bilingual_pdf_candidates(self):
        _, zh = self.document_row(self.upload(sample_pdf("zh"), "chinese.pdf"))
        fixture = io.BytesIO()
        canvas = Canvas(fixture, pagesize=A4)
        canvas.setTitle("Matrix sample")
        for index, raw in enumerate((
            "Research question: How can citations be tracked reliably?",
            "Introduction: Prior work lacks page-level comparisons.",
            "We propose a method to preserve citation provenance.",
            "Our contributions are a matrix and an auditing procedure.",
            "We use three datasets with publicly available papers.",
            "Experimental setup: Each document is processed independently.",
            "Evaluation metrics: precision and recall.",
            "Main results: The page links matched the original source.",
            "Limitations: The dataset covers only two languages.",
            "Future work: Extend the method to scanned sources.",
        )):
            canvas.drawString(60, 745 - 30 * index, raw)
        canvas.save()
        _, en = self.document_row(self.upload(fixture.getvalue(), "english.pdf"))
        route = self.topic_path + "/matrix"
        self.assertIn(f'href="{route}"', self.client.get(self.topic_path).get_data(as_text=True))
        before = self.client.get(route).get_data(as_text=True)
        self.assertIn("待补充", before)
        query = urlencode({"document": [zh["id"], en["id"]]}, doseq=True)
        generated = self.client.post(f"{route}?{query}", data={"csrf_token": self.csrf()}, follow_redirects=True)
        self.assertEqual(generated.status_code, 200)
        self.assertIn("已添加", generated.get_data(as_text=True))
        library = self.app.extensions["research_library"]
        cells = library.matrix_cells([en["id"]])
        self.assertEqual(len(cells), 10)
        for key, cell in cells.items():
            self.assertEqual(cell["source"], "excerpt")
            page = library.page(en["id"], cell["page"])
            self.assertIn(cell["quote"], page["text"], key)
            self.assertEqual(cell["text"], cell["quote"])
        result = self.client.get(f"{route}?{query}&field=metrics&linked=1").get_data(as_text=True)
        self.assertIn("Evaluation metrics", result)
        self.assertNotIn('<th scope="row">研究局限</th>', result)
        empty = self.client.get(route + "?selected=1").get_data(as_text=True)
        self.assertNotIn("待补充", empty)

    def test_matrix_editor_checks_evidence_preserves_manual_cells_and_exports(self):
        path, paper = self.document_row(self.upload(sample_pdf("en"), "one.pdf"))
        route = self.topic_path + "/matrix"
        editor = path + "/matrix/results"
        quote = "The evidence belongs on the second PDF page."
        url = editor + "?" + urlencode({"document": paper["id"], "view_field": "results"})
        self.assertIn("主要实验结果", self.client.get(url).get_data(as_text=True))
        payload = {"csrf_token": self.csrf(), "text": "=1+1", "page": 1, "quote": quote}
        self.assertEqual(self.client.post(url, data=payload).status_code, 400)
        self.assertEqual(self.client.post(url, data={**payload, "page": 2, "quote": "nonexistent citation"}).status_code, 400)
        saved = self.client.post(url, data={**payload, "page": 2})
        self.assertEqual(saved.status_code, 302)
        self.assertIn("field=results", saved.location)
        self.client.post(route + "?document=" + paper["id"], data={"csrf_token": self.csrf()})
        fresh = create_app(self.config)
        library = fresh.extensions["research_library"]
        cell = library.matrix_cells([paper["id"]])[(paper["id"], "results")]
        self.assertEqual((cell["text"], cell["source"], cell["page"], cell["quote"]), ("=1+1", "manual", 2, quote))
        export = fresh.test_client().get(route + ".csv?field=results&linked=1")
        self.assertEqual(export.status_code, 200)
        self.assertIn("attachment", export.headers["Content-Disposition"])
        self.assertTrue(export.data.startswith(b"\xef\xbb\xbf"))
        rows = list(csv.reader(io.StringIO(export.data.decode("utf-8-sig"))))
        self.assertEqual(rows[1], [paper["title"], "主要实验结果", "'=1+1", "手动填写", "2", quote])
        self.client.post(path + "/delete", data={"csrf_token": self.csrf()})
        self.assertEqual(library.matrix_cells([paper["id"]]), {})

    def test_matrix_rejects_cross_topic_selection(self):
        _, own = self.document_row(self.upload(sample_pdf("en"), "own.pdf"))
        other_topic = self.create_topic("另一个课题")
        _, other = self.document_row(self.upload(sample_pdf("zh"), "other.pdf", other_topic))
        route = self.topic_path + "/matrix"
        query = urlencode({"document": [own["id"], other["id"]]}, doseq=True)
        self.assertEqual(self.client.get(f"{route}?{query}").status_code, 400)
        self.assertEqual(self.client.get(f"{route}.csv?{query}").status_code, 400)
        self.client.post(f"{route}?{query}", data={"csrf_token": self.csrf()})
        library = self.app.extensions["research_library"]
        self.assertEqual(library.matrix_cells([own["id"], other["id"]]), {})

    def qa_request(self, document_ids, question, action="find"):
        return self.client.post(self.topic_path + "/qa", data={
            "csrf_token": self.csrf(), "document": document_ids, "question": question, "action": action,
        })

    def test_qa_local_multi_pdf_evidence_and_single_preselection(self):
        zh_path, zh = self.document_row(self.upload(sample_pdf("zh"), "question-zh.pdf"))
        en_path, en = self.document_row(self.upload(sample_pdf("en"), "question-en.pdf"))
        listing = self.client.get(self.topic_path).get_data(as_text=True)
        self.assertIn(f'href="{self.topic_path}/qa"', listing)
        self.assertIn(f'{self.topic_path}/qa?document={zh["id"]}', self.client.get(zh_path).get_data(as_text=True))
        form = self.client.get(f'{self.topic_path}/qa?document={zh["id"]}').get_data(as_text=True)
        self.assertIn(f'value="{zh["id"]}" checked', form)
        self.assertNotIn(f'value="{en["id"]}" checked', form)
        response = self.qa_request([zh["id"], en["id"]], "证据定位标记 second PDF page")
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        for path, quote in ((zh_path, "第二页中的证据定位标记"),
                            (en_path, "The evidence belongs on the second PDF page.")):
            self.assertIn(f'href="{path}?page=2"', body)
            self.assertIn(quote, body)
            self.assertIn(quote, self.client.get(f"/api/v1{path}/pages/2").json["text"])
        self.assertNotIn('id="qa-answer"', body)

    def test_qa_prioritizes_the_page_that_explains_a_technical_phrase(self):
        raw = io.BytesIO()
        canvas = Canvas(raw, pagesize=A4)
        canvas.drawString(72, 720, "The author proposed scaled dot-product attention.")
        canvas.showPage()
        canvas.drawString(72, 720, "Scaled Dot-Product Attention.")
        canvas.drawString(72, 700, "Scaled dot-product attention computes weighted values.")
        canvas.save()
        path, paper = self.document_row(self.upload(raw.getvalue(), "phrase-ranking.pdf"))
        body = self.qa_request([paper["id"]], "What is scaled dot product attention?").get_data(as_text=True)
        self.assertLess(body.index(f'href="{path}?page=2"'), body.index(f'href="{path}?page=1"'))

    def test_qa_scope_limits_and_empty_evidence_do_not_call_cloud(self):
        _, paper = self.document_row(self.upload(sample_pdf("en"), "question-en.pdf"))
        other_topic = self.create_topic("其他研究课题")
        _, other = self.document_row(self.upload(sample_pdf("zh"), "other-topic.pdf", other_topic))
        _, scanned = self.document_row(self.upload(scanned_page(), "scan.pdf"))
        client = Mock()
        self.app.config["AGENTARTS_CLIENT"] = client
        for ids, question in (([paper["id"], other["id"]], "second PDF page"),
                              ([paper["id"]], "a" * 501), ([], "second PDF page")):
            self.assertEqual(self.qa_request(ids, question, "answer").status_code, 400)
        no_match = self.qa_request([paper["id"]], "xyzyzxx", "answer").get_data(as_text=True)
        self.assertIn("找不到与问题匹配", no_match)
        no_text = self.qa_request([scanned["id"]], "扫描文本", "answer").get_data(as_text=True)
        self.assertIn("找不到与问题匹配", no_text)
        client.ask.assert_not_called()

    def test_qa_verifies_quotes_and_uses_stored_page_links(self):
        path, paper = self.document_row(self.upload(sample_pdf("en"), "question-en.pdf"))
        quote = "The evidence belongs on the second PDF page."
        client = Mock()
        # Serialized model-shaped fixture. No live provider call in this test.
        client.ask.return_value = json.dumps({"claims": [
            {"kind": "direct", "text": quote, "citations": [{"source": "E1", "quote": quote, "page": 99}]},
            {"kind": "direct", "text": "A translation.", "citations": [{"source": "E1", "quote": quote}]},
            {"kind": "inference", "text": "Merely fabricated.", "citations": [{"source": "E99", "quote": quote}]},
            {"kind": "direct", "text": "Made up excerpt.", "citations": [{"source": "E1", "quote": "Made up excerpt."}]},
            {"kind": "inference", "text": "10.12345/fabricated", "citations": [{"source": "E1", "quote": quote}]},
        ]})
        self.app.config["AGENTARTS_CLIENT"] = client
        body = self.qa_request([paper["id"]], "second PDF page", "answer").get_data(as_text=True)
        self.assertIn("原文摘录 · 已核对", body)
        self.assertIn("模型推断", body)
        self.assertIn("A translation.", body)
        self.assertEqual(body.count('<h3 class="qa-class unsupported">'), 3)
        self.assertIn(f'href="{path}?page=2"', body)
        for rejected in ("PDF 第 99 页", "Merely fabricated.", "Made up excerpt.", "10.12345/fabricated"):
            self.assertNotIn(rejected, body)
        prompt_data = json.loads(client.ask.call_args.args[0].split("\n", 1)[1])
        self.assertEqual(prompt_data["question"], "second PDF page")
        self.assertIn(quote, prompt_data["excerpts"][0]["text"])
        self.assertTrue(all(set(item) == {"id", "text"} for item in prompt_data["excerpts"]))

    def test_qa_keeps_local_evidence_without_a_usable_cloud_reply(self):
        path, paper = self.document_row(self.upload(sample_pdf("en"), "question-en.pdf"))
        client = Mock()
        for candidate, message in ((None, "尚未启用"), (client, "等待 AgentArts 回答超时"),
                                   (client, "未返回可核验的结构化回答")):
            self.app.config["AGENTARTS_CLIENT"] = candidate
            client.ask.side_effect = AgentArtsError("等待 AgentArts 回答超时") if "超时" in message else None
            client.ask.return_value = "unexpected text"
            body = self.qa_request([paper["id"]], "second PDF page", "answer").get_data(as_text=True)
            self.assertIn(message, body)
            self.assertIn(f'href="{path}?page=2"', body)
            self.assertNotIn('id="qa-answer"', body)


if __name__ == "__main__":
    unittest.main()
