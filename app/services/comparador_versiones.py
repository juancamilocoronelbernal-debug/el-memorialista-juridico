"""El Memorialista · Módulo de Control de Versiones y Diff Procesal (v1.0).

Implementa:
- Comparación de versiones de escritos judiciales palabra por palabra (word-level diff).
- Estadísticas de cambios (palabras añadidas, eliminadas y conservadas).
- Generación de documentos Microsoft Word (.docx) con Control de Cambios nativo (OpenXML w:ins y w:del).
"""
from __future__ import annotations

import io
import re
import difflib
import zipfile
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field


class EstadisticasDiff(BaseModel):
    palabras_anadidas: int = 0
    palabras_eliminadas: int = 0
    palabras_sin_cambio: int = 0
    total_palabras_base: int = 0
    total_palabras_comparado: int = 0


class CompararVersionesRequest(BaseModel):
    texto_base: str = Field(description="Texto de la versión anterior o base")
    texto_comparado: str = Field(description="Texto de la versión nueva o comparada")
    autor: Optional[str] = Field(default="El Memorialista", description="Nombre del autor para el control de cambios")
    fecha: Optional[str] = Field(default=None, description="Fecha ISO de la revisión")


class CompararVersionesResponse(BaseModel):
    estadisticas: EstadisticasDiff
    html_diff: str
    parrafos_diff: List[List[Dict[str, str]]]


class ExportarWordDiffRequest(BaseModel):
    texto_base: str = Field(description="Texto de la versión anterior o base")
    texto_comparado: str = Field(description="Texto de la versión nueva o comparada")
    autor: Optional[str] = Field(default="El Memorialista", description="Nombre del autor para las revisiones")
    fecha: Optional[str] = Field(default=None, description="Fecha ISO de la revisión")
    titulo: Optional[str] = Field(default="Escrito con Control de Cambios", description="Título del documento")
    perfil: Optional[Dict[str, Any]] = Field(default=None, description="Perfil del abogado para membrete y tipografía")


def tokenizar_texto(texto: str) -> List[str]:
    """
    Tokeniza el texto preservando palabras (incluyendo acentos y caracteres latinos),
    signos de puntuación, espacios y saltos de línea como unidades atómicas.
    """
    if not texto:
        return []
    # Tokeniza palabras completas (\w+), puntuación ([^\w\s]+), espacios horizontales ([ \t]+) y saltos (\r?\n)
    return re.findall(r"\w+|[^\w\s]+|[ \t]+|\r?\n", texto, re.UNICODE)


def contar_palabras(texto: str) -> int:
    """Cuenta el número de palabras en un texto excluyendo espacios y signos de puntuación sueltos."""
    return len(re.findall(r"\b\w+\b", texto, re.UNICODE))


def xesc(valor: Any) -> str:
    """Escapa caracteres especiales para XML seguro en OpenXML."""
    s = str(valor or "")
    # Eliminar caracteres de control no permitidos en XML
    s = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", s)
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def hesc(valor: Any) -> str:
    """Escapa caracteres para HTML seguro."""
    s = str(valor or "")
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def calcular_diff_palabras(texto_base: str, texto_comparado: str) -> List[Tuple[str, str]]:
    """
    Calcula el diff token por token usando SequenceMatcher.
    Retorna una lista de tuplas (tag, texto) donde tag es 'equal', 'insert' o 'delete'.
    """
    toks1 = tokenizar_texto(texto_base)
    toks2 = tokenizar_texto(texto_comparado)

    sm = difflib.SequenceMatcher(None, toks1, toks2)
    diff_tokens: List[Tuple[str, str]] = []

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            diff_tokens.append(("equal", "".join(toks1[i1:i2])))
        elif tag == "delete":
            diff_tokens.append(("delete", "".join(toks1[i1:i2])))
        elif tag == "insert":
            diff_tokens.append(("insert", "".join(toks2[j1:j2])))
        elif tag == "replace":
            diff_tokens.append(("delete", "".join(toks1[i1:i2])))
            diff_tokens.append(("insert", "".join(toks2[j1:j2])))

    return diff_tokens


def dividir_en_parrafos(diff_tokens: List[Tuple[str, str]]) -> List[List[Dict[str, str]]]:
    """
    Divide los tokens del diff en párrafos independientes preservando los saltos de línea.
    """
    parrafos: List[List[Dict[str, str]]] = [[]]

    for tag, txt in diff_tokens:
        partes = txt.split("\n")
        for idx, parte in enumerate(partes):
            if idx > 0:
                parrafos.append([])
            if parte:
                parrafos[-1].append({"tipo": tag, "texto": parte})

    return parrafos


def generar_html_diff(parrafos: List[List[Dict[str, str]]]) -> str:
    """
    Genera el HTML con estilo limpio para visualización del diff en la interfaz web.
    """
    html_partes = []

    for p in parrafos:
        if not p:
            html_partes.append('<p class="diff-parrafo diff-vacio">&nbsp;</p>')
            continue

        runs_html = []
        for token in p:
            tipo = token["tipo"]
            texto = hesc(token["texto"])

            if tipo == "equal":
                runs_html.append(f'<span class="diff-txt">{texto}</span>')
            elif tipo == "insert":
                runs_html.append(
                    f'<ins class="diff-ins" title="Texto añadido">{texto}</ins>'
                )
            elif tipo == "delete":
                runs_html.append(
                    f'<del class="diff-del" title="Texto eliminado">{texto}</del>'
                )

        html_partes.append(f'<p class="diff-parrafo">{"".join(runs_html)}</p>')

    return "\n".join(html_partes)


def comparar_versiones(req: CompararVersionesRequest) -> CompararVersionesResponse:
    """Realiza la comparación completa entre dos versiones de un escrito judicial."""
    diff_tokens = calcular_diff_palabras(req.texto_base, req.texto_comparado)
    parrafos = dividir_en_parrafos(diff_tokens)

    # Calcular estadísticas exactas de palabras
    anadidas = 0
    eliminadas = 0
    iguales = 0

    for tag, txt in diff_tokens:
        palabras_bloque = contar_palabras(txt)
        if tag == "insert":
            anadidas += palabras_bloque
        elif tag == "delete":
            eliminadas += palabras_bloque
        elif tag == "equal":
            iguales += palabras_bloque

    stats = EstadisticasDiff(
        palabras_anadidas=anadidas,
        palabras_eliminadas=eliminadas,
        palabras_sin_cambio=iguales,
        total_palabras_base=contar_palabras(req.texto_base),
        total_palabras_comparado=contar_palabras(req.texto_comparado),
    )

    html_diff = generar_html_diff(parrafos)

    return CompararVersionesResponse(
        estadisticas=stats,
        html_diff=html_diff,
        parrafos_diff=parrafos,
    )


def generar_docx_con_control_de_cambios(
    texto_base: str,
    texto_comparado: str,
    autor: str = "El Memorialista",
    fecha: Optional[str] = None,
    titulo: str = "Escrito con Control de Cambios",
    perfil: Optional[Dict[str, Any]] = None,
) -> bytes:
    """
    Construye un documento Microsoft Word (.docx) completo en formato OpenXML
    con revisiones de control de cambios activas (w:ins y w:del).
    """
    diff_tokens = calcular_diff_palabras(texto_base, texto_comparado)
    parrafos = dividir_en_parrafos(diff_tokens)

    fecha_revision = (
        fecha
        or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    )
    autor_seguro = xesc(autor or "El Memorialista")

    # Extraer formato del perfil si está disponible
    formato = (perfil or {}).get("formato", {})
    fuente = formato.get("fuente") or "Arial"
    tam_pt = float(formato.get("tamano") or 12)
    sz = int(tam_pt * 2)  # OpenXML usa medios puntos (half-points)
    interlineado = float(formato.get("interlineado") or 1.5)
    line_rule = int(240 * interlineado)

    # Construir párrafos en OpenXML
    revision_id = 1
    cuerpo_xml_partes = []

    for p in parrafos:
        runs_p = []
        for item in p:
            tipo = item["tipo"]
            txt = xesc(item["texto"])

            if tipo == "equal":
                runs_p.append(
                    f'<w:r>'
                    f'<w:rPr><w:rFonts w:ascii="{fuente}" w:hAnsi="{fuente}"/><w:sz w:val="{sz}"/><w:szCs w:val="{sz}"/></w:rPr>'
                    f'<w:t xml:space="preserve">{txt}</w:t>'
                    f'</w:r>'
                )
            elif tipo == "insert":
                runs_p.append(
                    f'<w:ins w:id="{revision_id}" w:author="{autor_seguro}" w:date="{fecha_revision}">'
                    f'<w:r>'
                    f'<w:rPr>'
                    f'<w:rFonts w:ascii="{fuente}" w:hAnsi="{fuente}"/><w:sz w:val="{sz}"/><w:szCs w:val="{sz}"/>'
                    f'<w:color w:val="15803D"/><w:u w:val="single"/>'
                    f'</w:rPr>'
                    f'<w:t xml:space="preserve">{txt}</w:t>'
                    f'</w:r>'
                    f'</w:ins>'
                )
                revision_id += 1
            elif tipo == "delete":
                runs_p.append(
                    f'<w:del w:id="{revision_id}" w:author="{autor_seguro}" w:date="{fecha_revision}">'
                    f'<w:r>'
                    f'<w:rPr>'
                    f'<w:rFonts w:ascii="{fuente}" w:hAnsi="{fuente}"/><w:sz w:val="{sz}"/><w:szCs w:val="{sz}"/>'
                    f'<w:color w:val="B91C1C"/><w:strike/>'
                    f'</w:rPr>'
                    f'<w:delText xml:space="preserve">{txt}</w:delText>'
                    f'</w:r>'
                    f'</w:del>'
                )
                revision_id += 1

        cuerpo_p = "".join(runs_p)
        cuerpo_xml_partes.append(
            f'<w:p>'
            f'<w:pPr>'
            f'<w:spacing w:before="0" w:after="160" w:line="{line_rule}" w:lineRule="auto"/>'
            f'<w:jc w:val="both"/>'
            f'</w:pPr>'
            f'{cuerpo_p}'
            f'</w:p>'
        )

    # Sección y márgenes (Oficio / A4 colombianos: 3 cm izq, 3 cm sup, 2 cm der, 2 cm inf)
    sect_pr = (
        f'<w:sectPr>'
        f'<w:pgSz w:w="12240" w:h="15840"/>'  # Carta (Letter)
        f'<w:pgMar w:top="1701" w:right="1134" w:bottom="1134" w:left="1701" w:header="709" w:footer="709" w:gutter="0"/>'
        f'<w:cols w:space="708"/>'
        f'</w:sectPr>'
    )

    doc_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">\n'
        '<w:body>\n'
        f'{"".join(cuerpo_xml_partes)}\n'
        f'{sect_pr}\n'
        '</w:body>\n'
        '</w:document>'
    )

    # settings.xml con <w:trackRevisions/> para forzar el modo de revisión activa
    settings_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<w:settings xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">\n'
        '<w:trackRevisions/>\n'
        '<w:zoom w:percent="100"/>\n'
        '<w:defaultTabStop w:val="708"/>\n'
        '<w:characterSpacingControl w:val="doNotCompress"/>\n'
        '<w:compat><w:compatSetting w:name="compatibilityMode" w:uri="http://schemas.microsoft.com/office/word" w:val="15"/></w:compat>\n'
        '</w:settings>'
    )

    styles_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">\n'
        f'<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="{fuente}" w:hAnsi="{fuente}"/><w:sz w:val="{sz}"/><w:szCs w:val="{sz}"/></w:rPr></w:rPrDefault></w:docDefaults>\n'
        '</w:styles>'
    )

    content_types_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">\n'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>\n'
        '<Default Extension="xml" ContentType="application/xml"/>\n'
        '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>\n'
        '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>\n'
        '<Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/>\n'
        '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>\n'
        '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>\n'
        '</Types>'
    )

    root_rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>\n'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>\n'
        '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>\n'
        '</Relationships>'
    )

    word_rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
        '<Relationship Id="rIdStyles" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>\n'
        '<Relationship Id="rIdSettings" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings" Target="settings.xml"/>\n'
        '</Relationships>'
    )

    core_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">\n'
        f'<dc:title>{xesc(titulo)}</dc:title>\n'
        f'<dc:creator>{autor_seguro}</dc:creator>\n'
        f'<cp:lastModifiedBy>{autor_seguro}</cp:lastModifiedBy>\n'
        f'<dcterms:created xsi:type="dcterms:W3CDTF">{fecha_revision}</dcterms:created>\n'
        f'<dcterms:modified xsi:type="dcterms:W3CDTF">{fecha_revision}</dcterms:modified>\n'
        '</cp:coreProperties>'
    )

    app_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">\n'
        '<Application>El Memorialista - Comparador de Versiones</Application>\n'
        '</Properties>'
    )

    # Empaquetar en memoria ZIP (.docx)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types_xml)
        z.writestr("_rels/.rels", root_rels_xml)
        z.writestr("word/document.xml", doc_xml)
        z.writestr("word/settings.xml", settings_xml)
        z.writestr("word/styles.xml", styles_xml)
        z.writestr("word/_rels/document.xml.rels", word_rels_xml)
        z.writestr("docProps/core.xml", core_xml)
        z.writestr("docProps/app.xml", app_xml)

    buffer.seek(0)
    return buffer.getvalue()
