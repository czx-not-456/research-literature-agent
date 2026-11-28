"""Score local metadata and matrix candidates against annotated public PDFs."""

import argparse
import io
import json
import logging
import re
from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlencode

from check_library import SAMPLES, create_app, metadata_results, sample_bytes
from research_library.matrix import FIELDS


QUALITY_SAMPLES = (*SAMPLES, {
    "file": "chinesebert.pdf",
    "url": "https://aclanthology.org/2021.acl-long.161.pdf",
    "sha256": "c19a13f4168cdb40082a39bd68e2b76844f80ba69182288bf780edf3a8ba8d81",
    "reference": {
        "title": "ChineseBERT: Chinese Pretraining Enhanced by Glyph and Pinyin Information",
        "authors": ("Zijun Sun", "Xiaoya Li", "Xiaofei Sun", "Yuxian Meng", "Xiang Ao", "Qing He", "Fei Wu", "Jiwei Li"),
        "year": "2021",
        "doi": "10.18653/v1/2021.acl-long.161",
    },
}, {
    "file": "srl-cn.pdf",
    "url": "https://tis.hrbeu.edu.cn/oa/pdfdow.aspx?Sid=201910012",
    "sha256": "ebeb8fd352504b2a2e9dacdee802b1c3449bbfc14ddab014a711262b51f54ebd",
    "reference": {
        "title": "融合多层次特征的中文语义角色标注",
        "authors": ("王一成", "万福成", "马宁"),
        "year": "2020",
        "doi": "10.11992/tis.201910012",
    },
})

# Manually checked physical page numbers and required evidence anchors.
MATRIX_REFERENCES = {
    "bert.pdf": {
        "data": (5, "BooksCorpus", "English Wikipedia"),
        "metrics": (1, "MultiNLI accuracy", "SQuAD"),
    },
    "mrc-cn.pdf": {
        "data": (6, "BookTest", "机器阅读理解主要数据集统计"),
        "metrics": (7, "3.2 评价指标", "准确率"),
    },
    "chinesebert.pdf": {
        "data": (4, "CommonCrawl", "pretraining data"),
        "method": (2, "we propose ChineseBERT", "glyph and pinyin information"),
        "metrics": (6, "Accuracy is reported for comparison",),
    },
    "srl-cn.pdf": {
        "data": (5, "清华大学依存句法树库", "原始语料"),
        "metrics": (6, "词准确率", "句子准确率"),
    },
}


def compact(value):
    value = re.sub(r"-\s*\n\s*", "", value.casefold())
    return "".join(value.split())


def check_quality(sample_directory, db, *, extended=False):
    corpus, references = QUALITY_SAMPLES, MATRIX_REFERENCES
    if extended:
        benchmark = json.loads(Path(__file__).with_name("matrix-benchmark.json").read_text(encoding="utf-8"))
        corpus = (*corpus, *benchmark["additional_samples"])
        references = benchmark["labels"]
        assert set(references) == {sample["file"] for sample in corpus}
        assert {field for labels in references.values() for field in labels} == set(FIELDS)
    app = create_app({"TESTING": True, "LIBRARY_DB": db})
    client = app.test_client()
    assert client.get("/").status_code == 200
    with client.session_transaction() as session:
        csrf = session["csrf_token"]

    def post(url, **fields):
        return client.post(url, data={"csrf_token": csrf, **fields})

    topic = post("/topics", name="文献质量标注验证").location
    library = app.extensions["research_library"]
    samples = {}
    metadata_total = Counter()
    matrix_total = Counter()
    by_field = {field: Counter() for field in FIELDS}
    verified_quotes = total_quotes = 0
    for sample in corpus:
        name = sample["file"]
        raw = sample_bytes(sample, sample_directory)
        imported = post(topic + "/documents", pdf=(io.BytesIO(raw), name))
        assert imported.status_code == 302 and imported.location.startswith("/documents/"), name
        doc_id = imported.location.split("?")[0].rsplit("/", 1)[1]
        metadata = metadata_results(library.document(doc_id), sample.get("reference", {}))
        metadata_total.update(metadata.values())
        generated = post(topic + "/matrix?" + urlencode({"document": doc_id}))
        assert generated.status_code == 302, name
        cells = library.matrix_cells([doc_id])
        matrix = {}
        for cell in cells.values():
            total_quotes += 1
            source = library.page(doc_id, cell["page"])
            assert source and cell["quote"] and cell["quote"] in source["text"], (name, cell["field"])
            verified_quotes += 1
        for field, (number, *anchors) in references[name].items():
            reference = library.page(doc_id, number)
            assert reference and anchors and all(compact(anchor) in compact(reference["text"]) for anchor in anchors), (
                "Invalid reference anchor", name, field, number, anchors,
            )
            cell = cells.get((doc_id, field))
            if cell is None:
                matrix[field] = {"status": "missing", "expected_page": number}
                continue
            match = cell["page"] == number and all(compact(anchor) in compact(cell["quote"]) for anchor in anchors)
            matrix[field] = {"status": "match" if match else "different_candidate",
                             "page": cell["page"], "expected_page": number}
        for field, result in matrix.items():
            matrix_total[result["status"]] += 1
            by_field[field][result["status"]] += 1
        samples[name] = {"metadata": metadata, "matrix": matrix}
    result = {"metadata": dict(metadata_total), "matrix": dict(matrix_total), "samples": samples}
    if extended:
        result["matrix_by_field"] = {field: dict(counts) for field, counts in by_field.items()}
        result["quote_location"] = {"verified": verified_quotes, "total": total_quotes}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sample_directory", type=Path, nargs="?", default=Path("."),
                        help="Use PDFs already in this directory when present, or fetch them from the publishers.")
    parser.add_argument("--extended-matrix", action="store_true",
                        help="Evaluate the larger corpus with references across all matrix fields.")
    args = parser.parse_args()
    logging.getLogger("pypdf").setLevel(logging.ERROR)
    with TemporaryDirectory() as temp:
        results = check_quality(args.sample_directory, Path(temp) / "quality.sqlite3", extended=args.extended_matrix)
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
