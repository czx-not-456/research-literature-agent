"""Export the saved report as Markdown or a Word Open XML document."""

import io
import re
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

from .report import SECTION_FIELDS, reference_text

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
REL = "http://schemas.openxmlformats.org/package/2006/relationships"
OFFICE_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
TYPES = "http://schemas.openxmlformats.org/package/2006/content-types"
ET.register_namespace("w", W)


def _paragraphs(report):
    yield "Title", report["title"]
    yield "Normal", "本稿汇编选定文献与矩阵内容。请核对研究结论与原文。"
    for key, (title, _) in SECTION_FIELDS.items():
        section = report["sections"][key]
        yield "Heading1", title
        yield "Normal", section["body"] or "待补充。"
        if section["evidence"]:
            yield "Heading2", "本节原文证据"
            for evidence in section["evidence"]:
                yield "Quote", f'[{evidence["number"]}] PDF 第 {evidence["page"]} 页\n{evidence["quote"]}'
    yield "Heading1", "参考文献"
    for item in report["sources"]:
        yield "Normal", f'[{item["number"]}] {reference_text(item)}'


def markdown(report):
    headings = {"Title": "# ", "Heading1": "## ", "Heading2": "### "}
    blocks = []
    for style, text in _paragraphs(report):
        text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        lines = re.sub(r"([\\\x60*_{}\[\]#|])", r"\\\1", text).splitlines()
        if style == "Quote":
            blocks.append("\n".join("> " + line for line in lines))
        elif style in headings:
            blocks.append(headings[style] + " ".join(lines))
        else:
            lines = [re.sub(r"^(\s*)([-+~!=]|\d+\.)(?=\s|$)", r"\1\\\2", line) for line in lines]
            blocks.append("\n".join(lines))
    return ("\n\n".join(blocks) + "\n").encode("utf-8")


def _w(parent, name, **attributes):
    return ET.SubElement(parent, f"{{{W}}}{name}", {f"{{{W}}}{key}": value for key, value in attributes.items()})


def _xml_text(text):
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]", "", text)


def _document(report):
    root = ET.Element(f"{{{W}}}document")
    body = _w(root, "body")
    for style, text in _paragraphs(report):
        lines = "\n".join(_xml_text(text).splitlines())
        for block in re.split(r"\n[ \t]*\n+", lines):
            if not block.strip():
                continue
            paragraph = _w(body, "p")
            _w(_w(paragraph, "pPr"), "pStyle", val=style)
            run = _w(paragraph, "r")
            for index, line in enumerate(block.splitlines()):
                if index:
                    _w(run, "br")
                span = _w(run, "t")
                span.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
                span.text = line
    page = _w(body, "sectPr")
    _w(page, "pgSz", w="12240", h="15840")
    _w(page, "pgMar", top="1370", bottom="1370", left="1370", right="1370", header="720", footer="720", gutter="0")
    return root


def _styles():
    styles = ET.Element(f"{{{W}}}styles")
    normal = _w(styles, "style", type="paragraph", styleId="Normal", default="1")
    _w(normal, "name", val="Normal")
    _w(_w(normal, "pPr"), "spacing", after="110", line="315", lineRule="auto")
    font = _w(normal, "rPr")
    _w(font, "rFonts", ascii="Calibri", hAnsi="Calibri", eastAsia="Microsoft YaHei")
    _w(font, "color", val="000000")
    _w(font, "sz", val="22")
    _w(font, "szCs", val="22")
    for style, name, size, before, after, level in (
        ("Title", "Title", "40", "0", "250", None),
        ("Heading1", "heading 1", "30", "340", "135", "0"),
        ("Heading2", "heading 2", "24", "175", "100", "1"),
        ("Quote", "Quote", "20", "0", "95", None),
    ):
        node = _w(styles, "style", type="paragraph", styleId=style)
        _w(node, "name", val=name)
        _w(node, "basedOn", val="Normal")
        properties = _w(node, "pPr")
        if style == "Quote":
            _w(properties, "spacing", before=before, after=after)
            _w(properties, "ind", left="260")
        else:
            _w(properties, "keepNext")
            _w(properties, "spacing", before=before, after=after)
        if level is not None:
            _w(properties, "outlineLvl", val=level)
        appearance = _w(node, "rPr")
        if style != "Quote":
            _w(appearance, "b")
        _w(appearance, "sz", val=size)
        _w(appearance, "szCs", val=size)
    return styles


def _relationships(target, kind):
    root = ET.Element("Relationships", xmlns=REL)
    ET.SubElement(root, "Relationship", Id="rId1", Type=f"{OFFICE_REL}/{kind}", Target=target)
    return root


def word(report):
    buffer = io.BytesIO()
    types = ET.Element("Types", xmlns=TYPES)
    ET.SubElement(types, "Default", Extension="rels", ContentType="application/vnd.openxmlformats-package.relationships+xml")
    ET.SubElement(types, "Default", Extension="xml", ContentType="application/xml")
    for path, kind in (("/word/document.xml", "document.main"), ("/word/styles.xml", "styles")):
        ET.SubElement(types, "Override", PartName=path,
                      ContentType=f"application/vnd.openxmlformats-officedocument.wordprocessingml.{kind}+xml")
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        for path, xml in (
            ("[Content_Types].xml", types), ("_rels/.rels", _relationships("word/document.xml", "officeDocument")),
            ("word/document.xml", _document(report)), ("word/styles.xml", _styles()),
            ("word/_rels/document.xml.rels", _relationships("styles.xml", "styles")),
        ):
            archive.writestr(path, ET.tostring(xml, encoding="utf-8", xml_declaration=True))
    return buffer.getvalue()
