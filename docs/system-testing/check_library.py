"""Exercise real papers through the local Flask routes in an isolated database."""

import argparse
import hashlib
import io
import json
import logging
import re
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from research_library import create_app

SAMPLES = (
    {
        "file": "bert.pdf",
        "url": "https://aclanthology.org/N19-1423.pdf",
        "sha256": "987545ffb087f1ece898142c403a516baeabeb70ce19089397fac6f7db12c3d4",
        "pages": 16,
        "question": "next sentence prediction task that jointly",
        "quote": "next sentence prediction",
        "reference": {
            "title": "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding",
            "authors": ("Jacob Devlin", "Ming-Wei Chang", "Kenton Lee", "Kristina Toutanova"),
            "year": "2019",
            "doi": "10.18653/v1/N19-1423",
        },
    },
    {
        "file": "mrc-cn.pdf",
        "url": "https://tis.hrbeu.edu.cn/oa/pdfdow.aspx?Sid=202107024",
        "sha256": "4962dd3d4fef10a731f4ccce71e1c7e4c111ae0a65f1ef7aced4f4eff7c8462f",
        "pages": 11,
        "question": "距离真正的理解语言还有较大差距",
        "quote": "距离真正的理解语言还有较大差距",
        "reference": {
            "title": "基于深度学习的机器阅读理解研究综述",
            "authors": ("杜永萍", "赵以梁", "阎婧雅", "郭文阳"),
            "year": "2022",
            "doi": "10.11992/tis.202107024",
        },
    },
)


def sample_bytes(sample, output):
    file = output / sample["file"]
    if file.is_file():
        raw = file.read_bytes()
    else:
        request = Request(sample["url"], headers={"User-Agent": "Research Literature QA/1.0"})
        with urlopen(request, timeout=20) as response:
            raw = response.read(8 * 1024 * 1024 + 1)
    if hashlib.sha256(raw).hexdigest() != sample["sha256"]:
        raise ValueError(f"Unexpected PDF content for {sample['file']}")
    return raw


def metadata_results(document, reference):
    results = {}
    for field, expected in reference.items():
        actual = document[field]
        if not actual:
            results[field] = "missing"
        else:
            actual = re.sub(r"\\s+", " ", actual).strip().casefold()
            if isinstance(expected, tuple):
                actual_names = tuple(part.strip() for part in re.split(r"[;,，；]", actual))
                correct = actual_names == tuple(name.casefold() for name in expected)
            else:
                correct = actual == expected.casefold()
            results[field] = "match" if correct else "mismatch"
    return results


def check_library(output, db):
    app = create_app({"TESTING": True, "LIBRARY_DB": db})
    client = app.test_client()
    assert client.get("/").status_code == 200
    with client.session_transaction() as session:
        csrf = session["csrf_token"]

    def post(path, **data):
        return client.post(path, data={"csrf_token": csrf, **data})

    topic = post("/topics", name="双语真实论文验证").location
    library = app.extensions["research_library"]
    ids = []
    paths = []
    findings = []
    for sample in SAMPLES:
        raw = sample_bytes(sample, output)
        start = perf_counter()
        imported = post(topic + "/documents", pdf=(io.BytesIO(raw), sample["file"]))
        elapsed = round(perf_counter() - start, 3)
        assert imported.status_code == 302
        path = imported.location.split("?")[0]
        assert path.startswith("/documents/")
        doc_id = path.rsplit("/", 1)[1]
        document = library.document(doc_id)
        assert document["page_count"] == document["text_page_count"] == sample["pages"]
        assert client.get(path + "/pdf").data == raw
        page = client.get(f"/api/v1{path}/pages/2").json
        assert page["physical_page"] == 2 and sample["quote"] in page["text"]
        reader = client.get(page["source_url"]).get_data(as_text=True)
        assert f"{path}/pdf#page=2" in reader
        preview = client.get(f"{path}/pages/2/preview.png")
        assert preview.status_code == 200 and preview.mimetype == "image/png"
        (output / (Path(sample["file"]).stem + "-page-2.png")).write_bytes(preview.data)

        response = post(topic + "/qa", document=doc_id, question=sample["question"], action="find")
        assert response.status_code == 200
        body = response.get_data(as_text=True)
        linked_quote = re.search(
            rf'href="{re.escape(path)}\?page=2"[^>]*>[^<]+</a>\s*<blockquote>(.*?)</blockquote>', body, re.S
        )
        assert linked_quote and sample["quote"] in linked_quote.group(1), sample["file"]

        evidence = {"text": f"已对照原件第 2 页（{sample['file']}）。", "quote": sample["quote"]}
        assert post(path + "/matrix/method", page=1, **evidence).status_code == 400
        assert post(path + "/matrix/method", page=2, **evidence).status_code == 302
        findings.append({
            "file": sample["file"], "text_pages": document["text_page_count"],
            "import_seconds": elapsed, "metadata": metadata_results(document, sample["reference"]),
            "evidence_page": 2,
        })
        ids.append(doc_id)
        paths.append(path)

    # Re-import one rendered page as an image-only PDF to exercise the scan fallback.
    scan = io.BytesIO()
    with Image.open(output / "mrc-cn-page-2.png") as image:
        image.convert("RGB").save(scan, "PDF")
    scanned = post(topic + "/documents", pdf=(io.BytesIO(scan.getvalue()), "image-only.pdf"))
    assert scanned.status_code == 302
    scan_path = scanned.location.split("?")[0]
    scan_doc = library.document(scan_path.rsplit("/", 1)[1])
    assert scan_doc["page_count"] == 1 and scan_doc["text_page_count"] == 0
    assert client.get(scan_path + "/pages/1/preview.png").status_code == 200
    scan_qa = post(topic + "/qa", document=scan_doc["id"], question=SAMPLES[1]["question"], action="find")
    assert "找不到与问题匹配的可提取原文" in scan_qa.get_data(as_text=True)

    matrix_csv = client.get(topic + "/matrix.csv?field=method&linked=1")
    assert matrix_csv.status_code == 200
    assert all(sample["quote"] in matrix_csv.data.decode("utf-8-sig") for sample in SAMPLES)
    created = post(topic + "/reports", document=ids, title="双语文献证据检查")
    assert created.status_code == 302
    report = created.location
    html = client.get(report).get_data(as_text=True)
    assert all(f'href="{path}?page=2"' in html for path in paths)
    edit = "人工核对记录。已检查中英文原件的物理页码。"
    assert post(report + "/sections/background", action="save", body=edit).status_code == 302
    assert post(report + "/sections/comparison", action="rebuild").status_code == 302
    md = client.get(report + "/export/md")
    docx = client.get(report + "/export/docx")
    assert md.status_code == docx.status_code == 200
    assert "attachment" in md.headers["Content-Disposition"] and "attachment" in docx.headers["Content-Disposition"]
    markdown = md.data.decode("utf-8")
    with ZipFile(io.BytesIO(docx.data)) as archive:
        assert archive.testzip() is None
        root = ET.fromstring(archive.read("word/document.xml"))
        word_text = "\n".join(node.text or "" for node in root.findall(".//{*}t"))
    for expected in ("参考文献", edit, "PDF 第 2 页", *(sample["quote"] for sample in SAMPLES)):
        assert expected in markdown and expected in word_text, (expected, expected in markdown, expected in word_text)
    (output / "literature-report.md").write_bytes(md.data)
    (output / "literature-report.docx").write_bytes(docx.data)
    return {"samples": findings, "checks": [
        "source_bytes", "page_view", "qa_evidence", "wrong_page_rejected", "matrix_csv",
        "report_links", "report_edit_and_rebuild", "markdown_export", "word_openxml", "image_only_fallback",
    ]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="Directory for temporary render and export files.")
    output = parser.parse_args().output
    output.mkdir(parents=True, exist_ok=True)
    logging.getLogger("pypdf").setLevel(logging.ERROR)
    with TemporaryDirectory() as temporary:
        summary = check_library(output, Path(temporary) / "library.sqlite3")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
