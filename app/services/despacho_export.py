"""Exportaciones privadas con texto real; sin conversiones remotas de expedientes."""
from __future__ import annotations

import io
import re
import threading
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

from fastapi import HTTPException

FONT_DIR = Path(__file__).resolve().parents[1] / "private" / "fonts"
_FONT_LOCK = threading.Lock()


def clean_text(value: str) -> str:
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]", "", value).replace("\r\n", "\n").replace("\r", "\n")


def filename(title: str, extension: str) -> str:
    name = re.sub(r"[^a-zA-Z0-9_-]+", "-", title).strip("-")[:70] or "el-memorialista"
    return name + "." + extension


def make_docx(title: str, text: str) -> bytes:
    """OOXML editable, sin macros, vínculos externos ni dependencias ofimáticas."""
    title, text = clean_text(title), clean_text(text)
    paragraphs = []
    for index, line in enumerate([title, "", *text.split("\n")]):
        style = '<w:pPr><w:pStyle w:val="Title"/></w:pPr>' if index == 0 else ""
        pieces = line.split("\t")
        runs = "<w:r>" + "<w:tab/>".join('<w:t xml:space="preserve">' + escape(part) + '</w:t>' for part in pieces) + "</w:r>"
        paragraphs.append("<w:p>" + style + runs + "</w:p>")
    xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    document = xml + '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>' + "".join(paragraphs) + '<w:sectPr><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/></w:sectPr></w:body></w:document>'
    styles = xml + '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/><w:sz w:val="22"/></w:rPr></w:rPrDefault><w:pPrDefault><w:pPr><w:spacing w:after="160" w:line="276" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults><w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:rPr><w:b/><w:sz w:val="34"/></w:rPr></w:style></w:styles>'
    types = xml + '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/></Types>'
    rels = xml + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>'
    doc_rels = xml + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>'
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as z:
        for path, data in {"[Content_Types].xml": types, "_rels/.rels": rels, "word/document.xml": document, "word/styles.xml": styles, "word/_rels/document.xml.rels": doc_rels}.items():
            z.writestr(path, data)
    return output.getvalue()


def make_pdf(title: str, text: str) -> bytes:
    try:
        from reportlab.lib import colors
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.enums import TA_LEFT
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    except ImportError:
        raise HTTPException(503, "La exportación PDF requiere instalar las dependencias del despacho.") from None
    title, text = clean_text(title), clean_text(text)
    with _FONT_LOCK:
        if "MemorialistaSans" not in pdfmetrics.getRegisteredFontNames():
            try:
                pdfmetrics.registerFont(TTFont("MemorialistaSans", str(FONT_DIR / "DejaVuSans.ttf")))
                pdfmetrics.registerFont(TTFont("MemorialistaBold", str(FONT_DIR / "DejaVuSans-Bold.ttf")))
            except Exception:
                raise HTTPException(503, "No se encontraron las fuentes PDF incluidas en el proyecto.") from None
    cmap = pdfmetrics.getFont("MemorialistaSans").face.charToGlyph
    chars = title + text
    # ReportLab no asegura composición bidi/índica. No emitir un PDF incorrecto.
    complex_script = re.search(r"[\u0590-\u0fff\u1780-\u17ff]", chars)
    unsupported = {ch for ch in chars if not ch.isspace() and ord(ch) not in cmap}
    if complex_script or unsupported:
        raise HTTPException(422, "Este texto contiene caracteres que el PDF no puede representar fielmente. Descarga el DOCX editable para conservarlos.")
    output = io.BytesIO()
    doc = SimpleDocTemplate(output, pagesize=A4, rightMargin=54, leftMargin=54,
                            topMargin=54, bottomMargin=54, title=title, author="El Memorialista")
    body = ParagraphStyle("MemBody", fontName="MemorialistaSans", fontSize=10.5,
                          leading=16, spaceAfter=8, alignment=TA_LEFT, splitLongWords=True)
    heading = ParagraphStyle("MemTitle", parent=body, fontName="MemorialistaBold", fontSize=17,
                             leading=22, spaceAfter=18, textColor=colors.HexColor("#172e35"))
    flow = [Paragraph(escape(title), heading)]
    for line in text.split("\n"):
        # Paragraph accepts XML; user text is always escaped, URLs are inert text.
        if line:
            # Bound long paragraphs so layout remains tractable even for pasted OCR.
            for start in range(0, len(line), 8000):
                flow.append(Paragraph(escape(line[start:start + 8000]).replace("\t", "&#160;&#160;&#160;&#160;"), body))
        else:
            flow.append(Spacer(1, 7))

    def footer(canvas, _doc):
        canvas.saveState()
        canvas.setFont("MemorialistaSans", 8)
        canvas.setFillColor(colors.HexColor("#647470"))
        canvas.drawString(54, 30, "El Memorialista")
        canvas.drawRightString(A4[0] - 54, 30, str(_doc.page))
        canvas.restoreState()

    doc.build(flow, onFirstPage=footer, onLaterPages=footer)
    return output.getvalue()
