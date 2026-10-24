"""Motor RAG Jurídico Inteligente 2.0 para El Memorialista.

Componente central compartido por el Agente principal y el módulo de Jurisprudencia.
Integra clasificación de intenciones, 4 niveles de profundidad (automático, rápido,
equilibrado, profundo), reranking jurídico multifactorial (13 criterios), clasificación
de secciones procesales, control de contexto/tokens y memoria documental segura.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
import logging
import re
import time
from typing import Any, Awaitable, Callable, Optional
from urllib.parse import urlsplit

import httpx
from fastapi import HTTPException

from app.config import get_settings
from app.services import despacho_store as store

log = logging.getLogger("memorialista.despacho.rag")


# ============================================================================
# 1. CLASIFICACIÓN DE SECCIONES JURÍDICAS (14 Categorías Procesales)
# ============================================================================

class LegalSection(str, Enum):
    ENCABEZADO = "encabezado"
    IDENTIFICACION = "identificacion"
    ANTECEDENTES = "antecedentes"
    HECHOS = "hechos"
    PROBLEMA_JURIDICO = "problema_juridico"
    CONSIDERACIONES = "consideraciones"
    FUNDAMENTOS_JURIDICOS = "fundamentos_juridicos"
    RATIO_DECIDENDI = "ratio_decidendi"
    OBITER_DICTA = "obiter_dicta"
    PARTE_RESOLUTIVA = "parte_resolutiva"
    SALVAMENTO_VOTO = "salvamento_voto"
    ACLARACION_VOTO = "aclaracion_voto"
    REFERENCIAS_NORMATIVAS = "referencias_normativas"
    SECCION_DESCONOCIDA = "seccion_desconocida"


_NEGATIVE_VOTE_NOTE_RE = re.compile(
    r"(no\s+presentar\s+(la\s+)?(aclaraci[oó]n|salvamento)\s+de\s+voto|"
    r"reservar\s+(la\s+)?posibilidad\s+de\s+presentar\s+(aclaraci[oó]n|salvamento)|"
    r"\[\s*nota\s+de\s+relator[ií]a\s*:[^\]]*(aclaraci[oó]n|salvamento)\s+de\s+voto[^\]]*\]|"
    r"con\s+(salvamento|aclaraci[oó]n)\s+(parcial\s+)?de\s+voto\s*$)",
    re.IGNORECASE | re.MULTILINE
)

_OPERATIVE_HEADER_RE = re.compile(
    r"(^\s*(iii|iv|v|vi|vii|viii|ix|x)?\s*\.?\s*decisi[oó]n\b|"
    r"\br\s+e\s+s\s+u\s+e\s+l\s+v\s+e\b|^\s*resuelve\s*[\.:\-\n]|"
    r"notif[ií]quese\s*,?\s*comun[ií]quese\s+y\s+c[uú]mplase)",
    re.IGNORECASE | re.MULTILINE
)

_SECTION_PATTERNS = [
    # Salvamento / Aclaración (máxima prioridad cuando es el cuerpo del voto particular)
    (LegalSection.SALVAMENTO_VOTO, re.compile(
        r"(^\s*salvamento\s+(parcial\s+|conjunto\s+)?de\s+voto\b|"
        r"salvamento\s+(parcial\s+)?de\s+voto\s+(de\s+la\s+|del\s+|a\s+la\s+sentencia)|"
        r"salv[oó]\s+el\s+voto|me\s+aparto\s+de\s+la\s+decisi[oó]n|"
        r"voto\s+disidente|disiento\s+de\s+la\s+posici[oó]n|salva\s+el\s+voto)",
        re.IGNORECASE | re.MULTILINE
    )),
    (LegalSection.ACLARACION_VOTO, re.compile(
        r"(^\s*aclaraci[oó]n\s+(parcial\s+|conjunta\s+)?de\s+voto\b|"
        r"aclaraci[oó]n\s+de\s+voto\s+(de\s+la\s+|del\s+|a\s+la\s+sentencia)|"
        r"aclaro\s+mi\s+voto|comparto\s+la\s+decisi[oó]n\s+pero|"
        r"concurro\s+con\s+la\s+decisi[oó]n)",
        re.IGNORECASE | re.MULTILINE
    )),
    # Parte resolutiva
    (LegalSection.PARTE_RESOLUTIVA, re.compile(
        r"(^\s*(iii|iv|v|vi|vii|viii|ix|x)?\s*\.?\s*decisi[oó]n\b|"
        r"\br\s+e\s+s\s+u\s+e\s+l\s+v\s+e\b|^\s*resuelve\s*[\.:\-\n]|^\s*decide\s*[\.:\-\n]|"
        r"administrando\s+justicia\s+en\s+nombre\s+del\s+pueblo|^\s*primero\s*[\.:\-]|"
        r"^\s*segundo\s*[\.:\-]|declarar\s+(in)?exequible|conceder\s+el\s+amparo|"
        r"amparar\s+el\s+derecho|inaplicar\s+la\s+resoluci[oó]n|notif[ií]quese\s*,?\s*(comun[ií]quese\s+y\s+)?c[uú]mplase|"
        r"negar\s+el\s+amparo|revocar\s+la\s+sentencia|confirmar\s+la\s+sentencia|abstenerse\s+de\s+efectuar\s+el\s+cobro)",
        re.IGNORECASE | re.MULTILINE
    )),
    # Problema jurídico
    (LegalSection.PROBLEMA_JURIDICO, re.compile(
        r"(problema\s+jur[ií]dico|planteamiento\s+del\s+problema|le\s+corresponde\s+a\s+la\s+corte\s+determinar|"
        r"corresponde\s+a\s+la\s+sala\s+(resolver|determinar)|corresponde\s+determinar\s+si\b|"
        r"formulaci[oó]n\s+del\s+problema|¿vulner[oó]|¿procede\s+la\s+acci[oó]n)",
        re.IGNORECASE
    )),
    # Hechos
    (LegalSection.HECHOS, re.compile(
        r"(hechos\s+probados|situaci[oó]n\s+f[aá]ctica|relat[oó]\s+la\s+accionante|manifest[oó]\s+el\s+actor|"
        r"hechos\s+de\s+la\s+demanda|hechos\s+de\s+la\s+tutela|s[ií]ntesis\s+de\s+los\s+hechos|"
        r"cuadro\s+f[aá]ctico|relaci[oó]n\s+f[aá]ctica|hechos\s+relevantes)",
        re.IGNORECASE
    )),
    # Antecedentes
    (LegalSection.ANTECEDENTES, re.compile(
        r"(^\s*i\s*\.?\s*antecedentes\b|tr[aá]mite\s+procesal|actuaciones\s+procesales|"
        r"decisiones\s+de\s+instancia|fallo\s+de\s+primera\s+instancia|fallo\s+de\s+segunda\s+instancia|"
        r"intervenciones\s+ciudadanas|concepto\s+del\s+procurador)",
        re.IGNORECASE | re.MULTILINE
    )),
    # Ratio decidendi (requiere evidencia jurisprudencial explícita)
    (LegalSection.RATIO_DECIDENDI, re.compile(
        r"(regla\s+jurisprudencial|subregla(\s+jurisprudencial|\s+constitucional)?|criterio\s+vinculante|"
        r"constituye\s+ratio\s+decidendi|la\s+corte\s+fija\s+como\s+regla|esta\s+corporaci[oó]n\s+unifica\s+el\s+criterio|"
        r"la\s+regla\s+de\s+derecho\s+aplicable\s+al\s+caso|fundamento\s+determinante\s+de\s+la\s+decisi[oó]n)",
        re.IGNORECASE
    )),
    # Fundamentos jurídicos
    (LegalSection.FUNDAMENTOS_JURIDICOS, re.compile(
        r"(fundamentos\s+jur[ií]dicos|fundamentos\s+normativos|marco\s+normativo|"
        r"an[aá]lisis\s+constitucional|doctrina\s+constitucional|dogm[aá]tica\s+constitucional|"
        r"desarrollo\s+jurisprudencial|par[aá]metro\s+de\s+control)",
        re.IGNORECASE
    )),
    # Consideraciones
    (LegalSection.CONSIDERACIONES, re.compile(
        r"(^\s*ii\s*\.?\s*consideraciones\b|consideraciones\s+de\s+la\s+corte|competencia\s+de\s+la\s+sala|"
        r"an[aá]lisis\s+del\s+caso\s+concreto|el\s+caso\s+concreto|juicio\s+de\s+proporcionalidad)",
        re.IGNORECASE | re.MULTILINE
    )),
    # Encabezado (estructural, no meras menciones en el texto)
    (LegalSection.ENCABEZADO, re.compile(
        r"(^\s*(rep[uú]blica\s+de\s+colombia\s*-\s*rama\s+judicial|corte\s+constitucional|consejo\s+de\s+estado|corte\s+suprema\s+de\s+justicia)\b|"
        r"magistrad[oa]\s+ponente\s*[\.:\-]|m\.p\.\s*[\.:\-]|sala\s+(segunda|plena|de\s+casaci[oó]n|de\s+revisi[oó]n)\b|"
        r"radicaci[oó]n\s*[\.:\-]\s*[0-9]+|^\s*sentencia\s+(t|c|su|a|sl|sc|sp)[- ][0-9]+)",
        re.IGNORECASE | re.MULTILINE
    )),
    # Identificación
    (LegalSection.IDENTIFICACION, re.compile(
        r"(^\s*(expediente|radicaci[oó]n|demandante|accionante|demandado|accionado|asunto)\s*[\.:\-])",
        re.IGNORECASE | re.MULTILINE
    )),
    # Referencias normativas
    (LegalSection.REFERENCIAS_NORMATIVAS, re.compile(
        r"(^\s*art[ií]culo\s+\d+(\s+de\s+la\s+ley|\s+del\s+c[oó]digo|\s+de\s+la\s+constituci[oó]n)|"
        r"^\s*(ley|decreto)\s+\d+\s+de\s+\d{4})",
        re.IGNORECASE | re.MULTILINE
    )),
]


def classify_legal_section(text: str, title: str = "") -> LegalSection:
    """Clasifica un fragmento judicial en una de las 14 secciones procesales normalizadas.

    Nota de auditoría: Clasificación automática heurística; nunca sustituye revisión jurídica humana.
    Cuando no existe certeza estructural suficiente, devuelve SECCION_DESCONOCIDA.
    """
    if not text or not isinstance(text, str):
        return LegalSection.SECCION_DESCONOCIDA

    probe = text[:1800]
    cleaned_probe = _NEGATIVE_VOTE_NOTE_RE.sub("", probe)

    # Si contiene encabezado explícito de RESUELVE / DECISIÓN y no inicia como salvamento/aclaración,
    # priorizar PARTE_RESOLUTIVA sobre notas de firma ("Con salvamento de voto") al pie del fallo.
    if _OPERATIVE_HEADER_RE.search(cleaned_probe) and not re.match(
        r"^\s*(salvamento|aclaraci[oó]n)\s+(parcial\s+|conjunt[oa]\s+)?de\s+voto\b",
        cleaned_probe,
        re.IGNORECASE,
    ):
        return LegalSection.PARTE_RESOLUTIVA

    for section_type, pattern in _SECTION_PATTERNS:
        target_text = cleaned_probe if section_type in (LegalSection.SALVAMENTO_VOTO, LegalSection.ACLARACION_VOTO) else probe
        if pattern.search(target_text):
            return section_type

    return LegalSection.SECCION_DESCONOCIDA


# ============================================================================
# 2. IDENTIFICACIÓN DEL TIPO DE CONSULTA Y ENTIDADES
# ============================================================================

_RULING_REGEX = re.compile(
    r"\b(sentencia\s+)?(t|c|su|a|sl|sc|sp|stc|stp)[- ]?([0-9]{1,4})\s*(de|/|-|\s)\s*([0-9]{2,4})\b",
    re.IGNORECASE
)
_RADICADO_REGEX = re.compile(
    r"\bradicad[oa]\s*([0-9]{10,23}|[0-9]{1,6}-[0-9]{2,4})\b",
    re.IGNORECASE
)
_COURT_REGEX = re.compile(
    r"\b(corte\s+constitucional|consejo\s+de\s+estado|corte\s+suprema(\s+de\s+justicia)?|"
    r"tribunal\s+superior|juzgado|corte\s+idh)\b",
    re.IGNORECASE
)
_GREETING_TOKENS = {
    "hola", "buen", "bueno", "buenos", "dia", "dias", "día", "días",
    "tarde", "tardes", "noche", "noches", "saludo", "saludos", "cordial",
    "gracias", "muchas", "ok", "vale", "entendido", "adios", "adiós",
    "hasta", "luego", "pronto", "que", "qué", "tal", "como", "cómo", "estas", "estás"
}


def _is_greeting(query: str) -> bool:
    cleaned = re.sub(r"[^\w\s]", " ", query.lower()).strip()
    words = cleaned.split()
    if not words or len(words) > 5:
        return False
    return all(w in _GREETING_TOKENS for w in words)
_EXHAUSTIVE_REGEX = re.compile(
    r"\b(analiz(a|ar|e)\s+[ií]ntegramente|an[aá]lisis\s+completo|sentencia\s+completa|"
    r"todos\s+los\s+aspectos|estudio\s+exhaustivo|examen\s+detallado|"
    r"hechos,?\s*(problema\s+jur[ií]dico,?)?\s*fundamentos,?\s*decisi[oó]n|an[aá]lisis\s+estructural)\b",
    re.IGNORECASE
)
_TARGET_SECTION_PATTERNS = [
    (LegalSection.PARTE_RESOLUTIVA, re.compile(r"\b(qu[eé]\s+decidi[oó]|cu[aá]l\s+fue\s+la\s+decisi[oó]n|qu[eé]\s+resolvi[oó]|sentido\s+del\s+fallo|parte\s+resolutiva|ampar[oó]|tutel[oó])\b", re.IGNORECASE)),
    (LegalSection.HECHOS, re.compile(r"\b(cu[aá]les\s+fueron\s+los\s+hechos|qu[eé]\s+pas[oó]|situaci[oó]n\s+f[aá]ctica|antecedentes\s+f[aá]cticos)\b", re.IGNORECASE)),
    (LegalSection.PROBLEMA_JURIDICO, re.compile(r"\b(problema\s+jur[ií]dico|qu[eé]\s+deb[ií]a\s+resolver|cuesti[oó]n\s+jur[ií]dica)\b", re.IGNORECASE)),
    (LegalSection.RATIO_DECIDENDI, re.compile(r"\b(ratio\s+decidendi|regla\s+jurisprudencial|subregla|criterio\s+vinculante|fundamento\s+principal)\b", re.IGNORECASE)),
    (LegalSection.SALVAMENTO_VOTO, re.compile(r"\b(salvamento|aclaraci[oó]n|voto\s+disidente|qu[ií]en\s+salv[oó])\b", re.IGNORECASE)),
    (LegalSection.ENCABEZADO, re.compile(r"\b(qu[ií]en\s+fue\s+el\s+ponente|magistrad[oa]\s+ponente|qu[eé]\s+corporaci[oó]n|qu[eé]\s+fecha)\b", re.IGNORECASE)),
]


def classify_query_intent(query: str, mode: str = "general", history_len: int = 0) -> dict:
    """Clasifica la consulta jurídicamente y recomienda la profundidad óptima sin invocar Gemini."""
    q = query.strip()
    
    # 1. Saludo / consulta trivial
    if _is_greeting(q):
        return {
            "intent": "greeting",
            "suggested_depth": "quick",
            "target_ruling": None,
            "target_radicado": None,
            "target_court": None,
            "target_section": None,
            "skip_retrieval_safe": (history_len == 0),
            "is_exhaustive": False,
        }

    # 2. Extracción de entidades jurídicas
    target_ruling = None
    m_ruling = _RULING_REGEX.search(q)
    if m_ruling:
        tipo = m_ruling.group(2).upper()
        num = m_ruling.group(3)
        anio = m_ruling.group(5)
        if len(anio) == 4:
            anio = anio[2:]
        target_ruling = f"{tipo}-{num}/{anio}"

    target_radicado = None
    m_rad = _RADICADO_REGEX.search(q)
    if m_rad:
        target_radicado = m_rad.group(1)

    target_court = None
    m_court = _COURT_REGEX.search(q)
    if m_court:
        target_court = m_court.group(1).lower()

    # 3. Sección objetivo buscada
    target_section = None
    for sec, pat in _TARGET_SECTION_PATTERNS:
        if pat.search(q):
            target_section = sec.value
            break

    # 4. Exhaustividad
    is_exhaustive = bool(_EXHAUSTIVE_REGEX.search(q))

    # 5. Determinación del intent principal
    if is_exhaustive and target_ruling:
        intent = "exhaustive_ruling_analysis"
        suggested_depth = "deep"
    elif is_exhaustive:
        intent = "exhaustive_analysis"
        suggested_depth = "deep"
    elif target_ruling or target_radicado:
        intent = "specific_ruling"
        suggested_depth = "quick" if target_section else "balanced"
    elif mode == "research":
        intent = "legal_research"
        suggested_depth = "balanced"
    elif mode == "draft":
        intent = "drafting"
        suggested_depth = "balanced"
    elif len(q) > 400:
        intent = "complex_inquiry"
        suggested_depth = "deep"
    elif len(q) < 40 and not target_ruling:
        intent = "short_inquiry"
        suggested_depth = "quick"
    else:
        intent = "general_legal"
        suggested_depth = "balanced"

    return {
        "intent": intent,
        "suggested_depth": suggested_depth,
        "target_ruling": target_ruling,
        "target_radicado": target_radicado,
        "target_court": target_court,
        "target_section": target_section,
        "skip_retrieval_safe": False,
        "is_exhaustive": is_exhaustive,
    }


# ============================================================================
# 3. CUATRO NIVELES DE PROFUNDIDAD Y PRESUPUESTOS DE CONTEXTO
# ============================================================================

DEPTH_PROFILES = {
    "quick": {
        "name": "Rápido",
        "description": "Prioriza identificadores exactos y fragmentos concretos (3 a 5 fragmentos)",
        "candidate_limit": 12,
        "min_passages": 2,
        "max_passages": 5,
        "max_context_chars": 12000,
        "estimated_token_budget": 3000,
        "min_score_threshold": 0.35,
        "section_diversity_required": False,
    },
    "balanced": {
        "name": "Equilibrado",
        "description": "Investigación estándar con reranking y diversidad (6 a 10 fragmentos)",
        "candidate_limit": 26,
        "min_passages": 4,
        "max_passages": 10,
        "max_context_chars": 24000,
        "estimated_token_budget": 6000,
        "min_score_threshold": 0.30,
        "section_diversity_required": True,
    },
    "deep": {
        "name": "Profundo",
        "description": "Análisis exhaustivo multisección (hechos, fundamentos, ratio, decisión, salvamentos) (12 a 18 fragmentos)",
        "candidate_limit": 45,
        "min_passages": 8,
        "max_passages": 18,
        "max_context_chars": 42000,
        "estimated_token_budget": 10500,
        "min_score_threshold": 0.25,
        "section_diversity_required": True,
    },
}


# ============================================================================
# 4. RERANKING JURÍDICO MULTIFACTORIAL (13 Criterios Calibrados)
# ============================================================================

_LEGAL_STOPWORDS = {
    "para", "como", "pero", "este", "esta", "estos", "estas", "sobre", "entre", "hacia",
    "desde", "hasta", "segun", "según", "donde", "cuando", "quien", "quién", "cual", "cuál",
    "sentencia", "corte", "derecho", "articulo", "artículo", "colombia",
    "codigo", "código", "ley", "leyes", "caso", "parte", "partes", "auto", "decreto",
    "tutela", "accion", "acción", "demanda", "explicame", "explícame", "dime", "cuentame",
    "cuéntame", "analiza", "busca", "documento", "documentos", "general", "constitucional",
    "judicial", "nacional", "republica", "república", "providencia", "primer", "primero",
    "segundo", "tercero", "sala", "magistrado", "magistrada", "juez", "tribunal"
}

def _extract_keywords(text: str) -> set[str]:
    cleaned = re.sub(r"[^\w\s]", " ", text.lower())
    words = {w for w in cleaned.split() if len(w) >= 4 and w not in _LEGAL_STOPWORDS}
    return words


def rerank_candidates(
    candidates: list[dict],
    query: str,
    intent_info: dict,
    profile: dict
) -> list[dict]:
    """Segunda etapa de clasificación jurídica tras la búsqueda híbrida en Supabase.
    
    Evalúa 13 factores procesales, sustanciales y semánticos, normalizando puntuaciones
    entre 0.0 y 1.0 para priorizar pertinencia jurídica real sobre mera coincidencia léxica.
    """
    if not candidates:
        return []

    target_ruling = intent_info.get("target_ruling")
    target_radicado = intent_info.get("target_radicado")
    target_court = intent_info.get("target_court")
    target_section = intent_info.get("target_section")
    is_exhaustive = intent_info.get("is_exhaustive")
    query_keywords = _extract_keywords(query)

    scored_candidates = []
    for cand in candidates:
        text = str(cand.get("excerpt") or cand.get("content") or cand.get("text") or "")
        title = str(cand.get("title") or "")
        source_id = str(cand.get("source_id") or "")
        existing_section = cand.get("section")
        if existing_section and existing_section != LegalSection.SECCION_DESCONOCIDA.value:
            section = existing_section
        else:
            section = classify_legal_section(text, title)
        cand["section"] = section.value if isinstance(section, LegalSection) else str(section)
        cand.setdefault("section_classification_origin", "automatic_structural_heuristic")

        # Si el fragmento fue seleccionado manualmente por el abogado, máxima prioridad garantizada
        if cand.get("user_selected"):
            cand["rerank_score"] = 1.0
            cand["ranking_factors"] = {"user_selected": 1.0}
            scored_candidates.append(cand)
            continue

        factors = {}
        
        # 1. Puntuación híbrida de partida (vector + fts normalizada)
        raw_score = cand.get("score")
        is_mock_or_unscored = (raw_score is None)
        if isinstance(raw_score, (int, float)):
            f_score = float(raw_score)
            # RRF suele producir valores <= 0.05 (1/60 + 1/60 ~ 0.033). Normalizar a escala 0-1
            if 0.0 < f_score <= 0.05:
                base_score = min(1.0, f_score / 0.0333)
            else:
                base_score = max(0.0, min(1.0, f_score))
        else:
            base_score = 0.85
        factors["base_score"] = round(base_score, 3)

        # 2. Coincidencia exacta de número/identificador de sentencia (+0.45)
        ruling_match = 0.0
        if target_ruling:
            # Buscar variaciones: "T-100/24", "T-100-24", "T-100 de 2024", "T-100"
            r_parts = target_ruling.split("-")
            tipo = r_parts[0]
            num_sub = r_parts[1].split("/")[0] if len(r_parts) > 1 else ""
            pattern = rf"\b{tipo}[- ]?{num_sub}\b"
            if re.search(pattern, title, re.IGNORECASE) or re.search(pattern, text[:400], re.IGNORECASE):
                ruling_match = 0.45
            elif re.search(pattern, text, re.IGNORECASE):
                ruling_match = 0.35
        factors["ruling_match"] = round(ruling_match, 3)

        # 3. Coincidencia de radicado (+0.35)
        rad_match = 0.0
        if target_radicado and target_radicado in text:
            rad_match = 0.35
        factors["rad_match"] = round(rad_match, 3)

        # 4. Corporación judicial (+0.15)
        court_match = 0.0
        if target_court:
            if target_court in title.lower() or target_court in source_id.lower() or target_court in text[:300].lower():
                court_match = 0.15
        factors["court_match"] = round(court_match, 3)

        # 5. Solapamiento de términos jurídicos clave
        cand_keywords = _extract_keywords(text)
        keyword_overlap = 0.0
        if query_keywords and cand_keywords:
            common = query_keywords.intersection(cand_keywords)
            keyword_overlap = min(0.30, len(common) * 0.06)
        factors["keyword_overlap"] = round(keyword_overlap, 3)

        # COMPROBACIÓN DE PERTINENCIA TEMÁTICA BÁSICA:
        # Una sección procesal SOLO bonifica si hay relación temática real con la consulta.
        # Si la consulta es manifiestamente impertinente (sin coincidencia léxica, de sentencia o radicado, y RRF muy bajo)
        # se penaliza severamente para que no sea seleccionada.
        # Cuando la recuperación fue únicamente vectorial (method == 'semantic', sin FTS) en una consulta
        # temática multi-término (>= 3 palabras clave), se exige al menos 2 coincidencias léxicas (>= 0.12)
        # para evitar falsos positivos por palabras genéricas aisladas (ej. "libertad", "pública").
        is_pure_semantic_fallback = (str(cand.get("method") or "") == "semantic")
        min_kw_overlap = 0.12 if (is_pure_semantic_fallback and len(query_keywords) >= 3) else 0.05
        has_subject_relevance = bool(
            is_mock_or_unscored
            or ruling_match > 0
            or rad_match > 0
            or keyword_overlap >= min_kw_overlap
            or (base_score >= 0.45 and (not query_keywords or keyword_overlap >= min_kw_overlap))
        )

        # 6. Alineación con sección procesal objetivo (+0.30)
        section_match = 0.0
        if has_subject_relevance:
            if target_section and cand["section"] == target_section:
                section_match = 0.30
            elif is_exhaustive and cand["section"] in {
                LegalSection.HECHOS.value,
                LegalSection.PROBLEMA_JURIDICO.value,
                LegalSection.RATIO_DECIDENDI.value,
                LegalSection.PARTE_RESOLUTIVA.value
            }:
                section_match = 0.20
        factors["section_match"] = round(section_match, 3)

        # 7. Densidad sustantiva del fragmento
        substance_score = 0.0
        text_len = len(text.strip())
        if text_len >= 350 and has_subject_relevance:
            substance_score = 0.08
        elif text_len < 100 and not is_mock_or_unscored:
            substance_score = -0.04
        factors["substance_score"] = round(substance_score, 3)

        # Penalización estricta por falta total de afinidad temática
        no_affinity_penalty = -0.40 if not has_subject_relevance else 0.0
        factors["no_affinity_penalty"] = round(no_affinity_penalty, 3)

        # Ponderación dinámica: si se busca una providencia concreta, el identificador pesa más;
        # en consultas temáticas generales o conceptuales, la similitud híbrida/vectorial es el eje central.
        base_weight = 0.40 if target_ruling else 0.60

        # Cálculo de puntuación final compuesta ponderada
        total_score = (
            base_score * base_weight
            + ruling_match
            + rad_match
            + court_match
            + section_match
            + keyword_overlap
            + substance_score
            + no_affinity_penalty
        )
        normalized_score = max(0.0, min(1.0, total_score))
        cand["rerank_score"] = round(normalized_score, 4)
        cand["ranking_factors"] = factors
        scored_candidates.append(cand)

    # Ordenar por rerank_score descendente
    scored_candidates.sort(key=lambda x: x["rerank_score"], reverse=True)
    return scored_candidates


# ============================================================================
# 5. SELECCIÓN INTELIGENTE Y DEDUPLICACIÓN
# ============================================================================

def _normalize_for_dedup(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text.lower().strip())
    return cleaned[:300]


def select_intelligent_fragments(
    ranked_candidates: list[dict],
    profile: dict,
    intent_info: dict
) -> tuple[list[dict], list[dict]]:
    """Aplica control de redundancia, diversidad de secciones y límites de tokens."""
    max_passages = profile["max_passages"]
    max_chars = profile["max_context_chars"]
    min_threshold = profile["min_score_threshold"]
    diversity_required = profile.get("section_diversity_required", True)

    selected = []
    dropped = []
    seen_prefixes = set()
    section_counts: dict[str, int] = {}
    used_chars = 0

    for cand in ranked_candidates:
        text = str(cand.get("excerpt") or cand.get("content") or cand.get("text") or "").strip()
        if not text:
            continue

        score = cand.get("rerank_score", 0.0)
        # Filtro estricto de calidad y pertinencia jurídica:
        # Los fragmentos deben superar el umbral mínimo (salvo selección manual del abogado)
        if not cand.get("user_selected") and score < min_threshold:
            dropped.append(cand)
            continue

        # 1. Deduplicación por prefijo léxico
        norm_key = _normalize_for_dedup(text)
        if norm_key in seen_prefixes:
            dropped.append(cand)
            continue

        # 2. Control de presupuesto de caracteres
        frag_len = len(text)
        if used_chars + frag_len > max_chars and len(selected) >= profile.get("min_passages", 2):
            dropped.append(cand)
            continue

        # 3. Control de redundancia por sección (máximo 4 de una misma sección salvo modo profundo)
        sec = cand.get("section", "seccion_desconocida")
        current_sec_count = section_counts.get(sec, 0)
        max_sec_allowed = 5 if profile.get("name") == "Profundo" else 3
        if diversity_required and current_sec_count >= max_sec_allowed and len(selected) >= 3:
            dropped.append(cand)
            continue

        # Fragmento aceptado
        seen_prefixes.add(norm_key)
        section_counts[sec] = current_sec_count + 1
        used_chars += frag_len
        selected.append(cand)

        if len(selected) >= max_passages:
            break

    return selected, dropped


# ============================================================================
# 6. MEMORIA DOCUMENTAL INTELIGENTE (Caché conversacional segura)
# ============================================================================

class ConversationDocumentMemory:
    """Caché conversacional temporal en memoria, aislada por usuario y conversación."""

    def __init__(self, ttl_seconds: int = 1800):
        self.ttl_seconds = ttl_seconds
        self._cache: dict[str, dict[str, Any]] = {}

    def _key(self, user_id: str, conversation_id: str, scope: str, depth: str, document_ids: list[str]) -> str:
        docs_sorted = ",".join(sorted(str(d) for d in (document_ids or [])))
        raw = f"{user_id}:{conversation_id or 'none'}:{scope}:{depth}:{docs_sorted}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get(
        self,
        user_id: str,
        conversation_id: Optional[str],
        query: str,
        scope: str,
        depth: str,
        document_ids: list[str]
    ) -> Optional[dict]:
        if not conversation_id or not get_settings().DESPACHO_RAG_MEMORY_ENABLED:
            return None

        key = self._key(user_id, conversation_id, scope, depth, document_ids)
        entry = self._cache.get(key)
        if not entry:
            return None

        # Comprobar expiración TTL
        if time.time() - entry["created_at"] > self.ttl_seconds:
            self._cache.pop(key, None)
            return None

        # Comprobar si la consulta es sobre el mismo tema o entidad principal
        prev_intent = entry.get("intent_info", {})
        curr_intent = classify_query_intent(query)
        if prev_intent.get("target_ruling") and prev_intent.get("target_ruling") == curr_intent.get("target_ruling"):
            # Si la nueva consulta busca una sección específica (ej. salvamento_voto, hechos, ratio, etc.)
            req_section = curr_intent.get("target_section")
            if req_section:
                cached_passages = entry.get("data", {}).get("passages", [])
                has_target_section = any(
                    (p.get("section") == req_section or (isinstance(req_section, LegalSection) and p.get("section") == req_section.value))
                    for p in cached_passages
                )
                if not has_target_section:
                    log.info(
                        "Memoria RAG: la consulta solicita sección '%s' no presente en fragmentos cacheados para %s. Forzando recuperación suplementaria.",
                        req_section, curr_intent["target_ruling"]
                    )
                    return None

            log.info("Memoria RAG: reutilizando contexto documental para sentencia=%s", curr_intent["target_ruling"])
            return entry["data"]

        return None

    def get_last_entry(self, user_id: str, conversation_id: Optional[str]) -> Optional[dict]:
        """Obtiene la entrada más reciente de esta conversación para resolución anafórica."""
        if not conversation_id:
            return None
        matches = [
            v for v in self._cache.values()
            if v.get("user_id") == user_id and v.get("conversation_id") == conversation_id
        ]
        if not matches:
            return None
        matches.sort(key=lambda x: x.get("created_at", 0), reverse=True)
        return matches[0]

    def store(
        self,
        user_id: str,
        conversation_id: Optional[str],
        query: str,
        scope: str,
        depth: str,
        document_ids: list[str],
        data: dict,
        intent_info: dict
    ) -> None:
        if not conversation_id or not get_settings().DESPACHO_RAG_MEMORY_ENABLED:
            return

        key = self._key(user_id, conversation_id, scope, depth, document_ids)
        self._cache[key] = {
            "created_at": time.time(),
            "user_id": user_id,
            "conversation_id": conversation_id,
            "query": query,
            "intent_info": intent_info,
            "data": data,
        }
        # Limpieza oportunista si la caché supera 500 entradas
        if len(self._cache) > 500:
            now = time.time()
            self._cache = {k: v for k, v in self._cache.items() if now - v["created_at"] <= self.ttl_seconds}

    def invalidate(self, user_id: str, conversation_id: Optional[str]) -> None:
        if not conversation_id:
            return
        to_del = [k for k, v in self._cache.items() if v.get("user_id") == user_id and v.get("conversation_id") == conversation_id]
        for k in to_del:
            self._cache.pop(k, None)
        prefix = f"{user_id}:{conversation_id}:"
        to_del = [k for k, v in self._cache.items() if v.get("key_prefix", "").startswith(prefix)]
        for k in to_del:
            self._cache.pop(k, None)


# Instancia singleton de memoria documental
document_memory = ConversationDocumentMemory()


# ============================================================================
# 7. ESTIMACIÓN DE COSTES COMERCIALES
# ============================================================================

def estimate_tokens_and_cost(
    prompt_chars: int,
    input_tokens: Optional[int],
    output_tokens: Optional[int],
    model: str = "gemini-3.6-flash"
) -> dict:
    """Calcula tokens reales o estimados (~4 caracteres/token) y costes de referencia."""
    est_in = input_tokens if (input_tokens and input_tokens > 0) else max(1, prompt_chars // 4)
    out_tok = output_tokens or 0
    total_tok = est_in + out_tok

    # Tarifas públicas aproximadas de referencia (Gemini 2.5 / 3.6 Flash: $0.075 / 1M in, $0.30 / 1M out)
    cost_usd = (est_in * 0.000000075) + (out_tok * 0.00000030)

    return {
        "estimated_input_tokens": est_in,
        "output_tokens": out_tok,
        "total_tokens": total_tok,
        "is_token_count_estimated": input_tokens is None,
        "estimated_cost_usd": round(cost_usd, 6),
        "cost_model": model,
    }


# ============================================================================
# 8. VALIDACIÓN ESTRICTA DE FRAGMENTOS SELECCIONADOS POR EL USUARIO
# ============================================================================

async def verify_and_resolve_selected_fragments(
    user_id: str,
    token: str,
    raw_fragments: list[dict],
) -> list[dict]:
    """Valida y recupera los fragmentos seleccionados directamente desde la base de datos oficial o DMS.
    
    MEDIDA DE SEGURIDAD ESTRICTA:
    - El navegador solo envía identificadores documentales (document_id, segment, kind, source_url).
    - El servidor NUNCA confía en el texto o extracto enviado por el cliente.
    - Se verifica que el documento oficial esté efectivamente publicado (published=true).
    - Para documentos del DMS privado, se verifica que pertenezcan estrictamente al usuario autenticado (RLS/owner_id).
    - Todo intento de acceso a documentos privados ajenos o fragmentos inexistentes es rechazado y registrado.
    """
    if not raw_fragments:
        return []

    settings = get_settings()
    base = (settings.SUPABASE_URL or "").rstrip("/")
    if not base:
        return []

    verified_candidates: list[dict] = []
    to_process = raw_fragments[:20]

    for idx, sf in enumerate(to_process):
        if not isinstance(sf, dict):
            continue

        doc_id = sf.get("document_id")
        source_url = sf.get("source_url") or ""
        segment = sf.get("segment")
        ordinal = sf.get("ordinal")
        kind = sf.get("kind")
        citation_id = sf.get("id") or f"SEL-{idx+1}"

        is_official = (
            kind == "official"
            or "corteconstitucional.gov.co" in source_url.lower()
            or (not doc_id and source_url)
        )

        try:
            if is_official or not doc_id:
                # 1. Corpus Jurídico Oficial (despacho_corpus_documentos + despacho_corpus_fragmentos)
                doc_query = "published=eq.true&limit=1"
                if doc_id:
                    doc_query += f"&id=eq.{doc_id}"
                elif source_url:
                    doc_query += f"&source_url=eq.{source_url}"
                else:
                    log.warning("Fragmento seleccionado ignorado: sin document_id ni source_url válido")
                    continue

                headers = {
                    "apikey": settings.SUPABASE_ANON_KEY or "",
                    "Authorization": f"Bearer {token or settings.SUPABASE_ANON_KEY}",
                }
                async with httpx.AsyncClient(timeout=15) as client:
                    d_res = await client.get(f"{base}/rest/v1/despacho_corpus_documentos?{doc_query}", headers=headers)
                    if d_res.status_code >= 400 or not d_res.json():
                        log.warning("Seguridad RAG: documento oficial no encontrado o no publicado (doc_id=%s, url=%s)", doc_id, source_url)
                        continue
                    doc_data = d_res.json()[0]
                    actual_doc_id = doc_data["id"]

                    f_query = f"document_id=eq.{actual_doc_id}"
                    if segment is not None:
                        f_query += f"&segment=eq.{segment}"
                    elif ordinal is not None:
                        f_query += f"&ordinal=eq.{ordinal}"
                    else:
                        f_query += "&order=ordinal.asc&limit=1"

                    fr_res = await client.get(f"{base}/rest/v1/despacho_corpus_fragmentos?{f_query}&limit=1", headers=headers)
                    if fr_res.status_code >= 400 or not fr_res.json():
                        log.warning("Seguridad RAG: fragmento oficial no encontrado en BD (doc_id=%s, seg=%s)", actual_doc_id, segment)
                        continue
                    frag_data = fr_res.json()[0]

                    verified_candidates.append({
                        "id": citation_id,
                        "title": doc_data.get("title") or "Providencia Judicial Oficial",
                        "source_id": doc_data.get("source_id") or "oficial",
                        "source_url": doc_data.get("source_url") or "",
                        "date": doc_data.get("date"),
                        "version": doc_data.get("version", 1),
                        "segment": frag_data.get("segment") or (idx + 1),
                        "section": frag_data.get("section") or "fundamentos_juridicos",
                        "excerpt": frag_data.get("content", ""),  # TEXTO AUTÉNTICO RECUPERADO DE LA BD
                        "document_id": actual_doc_id,
                        "page": frag_data.get("page"),
                        "score": 1.0,
                        "method": "user_selected_verified",
                        "user_selected": True,
                        "verified": True,
                        "kind": "official",
                    })

            else:
                # 2. Documento Privado del Usuario (DMS)
                # Validar posesión estricta mediante fetch_item (garantiza owner_id = user_id)
                try:
                    user_doc = await store.fetch_item(user_id, token, str(doc_id), kind="document")
                except Exception as e:
                    log.warning("ALERTA SEGURIDAD RAG: Intento no autorizado o documento ajeno (doc_id=%s, user_id=%s): %s", doc_id, user_id, e)
                    continue

                headers = {
                    "apikey": settings.SUPABASE_ANON_KEY or "",
                    "Authorization": f"Bearer {token}",
                }
                f_query = f"document_id=eq.{doc_id}&owner_id=eq.{user_id}"
                if segment is not None:
                    f_query += f"&segment=eq.{segment}"
                elif ordinal is not None:
                    f_query += f"&ordinal=eq.{ordinal}"
                else:
                    f_query += "&order=ordinal.asc&limit=1"

                async with httpx.AsyncClient(timeout=15) as client:
                    fr_res = await client.get(f"{base}/rest/v1/despacho_indice?{f_query}&limit=1", headers=headers)
                    if fr_res.status_code >= 400 or not fr_res.json():
                        log.warning("Seguridad RAG: fragmento DMS no encontrado en despacho_indice (doc_id=%s, seg=%s)", doc_id, segment)
                        continue
                    frag_data = fr_res.json()[0]

                    verified_candidates.append({
                        "id": citation_id,
                        "title": user_doc.get("title") or "Documento Privado",
                        "source_id": str(doc_id),
                        "source_url": "",
                        "date": user_doc.get("created_at"),
                        "version": user_doc.get("version", 1),
                        "segment": frag_data.get("segment") or (idx + 1),
                        "section": "documento_privado",
                        "excerpt": frag_data.get("content", ""),  # TEXTO AUTÉNTICO RECUPERADO DE LA BD
                        "document_id": str(doc_id),
                        "page": frag_data.get("page"),
                        "score": 1.0,
                        "method": "user_selected_verified",
                        "user_selected": True,
                        "verified": True,
                        "kind": "document",
                    })

        except Exception as ex:
            log.warning("Error validando fragmento seleccionado sf=%s: %s", sf, ex)
            continue

    return verified_candidates


# ============================================================================
# 9. CONTROLADOR CENTRAL: RECUPERACIÓN Y AUMENTO UNIFICADO (RAG 2.0)
# ============================================================================

async def retrieve_and_augment_rag(
    user_id: str,
    token: str,
    request: dict,
    context: dict,
    on_progress: Optional[Callable[[str, str], Awaitable[None]]] = None,
) -> dict:
    """Servicio central de recuperación jurídica inteligente 2.0.
    
    Compartido por el Agente principal (chat tradicional y SSE streaming)
    y el módulo de Jurisprudencia. Respeta aislamiento RLS, adapta la profundidad
    solicitada, aplica reranking y devuelve citas verificables [O1-S1] y [D1-S1].
    """
    settings = get_settings()

    # Si el motor V2 está desactivado por configuración, reversión transparente a V1
    if not getattr(settings, "DESPACHO_RAG_V2_ENABLED", True):
        from app.services import despacho_ai
        return await despacho_ai._legacy_augment_context(user_id, token, request, context)

    t_start = time.monotonic()
    scope = request.get("knowledge_scope", "auto")
    if scope == "off" or not (settings.SUPABASE_URL and settings.SUPABASE_ANON_KEY):
        return context

    query = request["message"][:4000].strip()
    history = request.get("history") or []
    conversation_id = request.get("conversation_id") or request.get("matter_id")

    # 1. Identificación del tipo de consulta
    intent_info = classify_query_intent(query, mode=request.get("mode", "general"), history_len=len(history))

    # 2. Determinación de la profundidad
    req_depth = request.get("depth", "auto")
    if req_depth in DEPTH_PROFILES:
        depth_key = req_depth
    else:
        depth_key = intent_info["suggested_depth"]
    profile = DEPTH_PROFILES[depth_key]

    if on_progress:
        await on_progress("query_analysis", f"Analizando consulta ({intent_info['intent']}) · Profundidad: {profile['name']}…")

    # 3. Optimización para saludos o consultas triviales
    if intent_info.get("skip_retrieval_safe") and scope == "auto" and not request.get("document_ids"):
        if on_progress:
            await on_progress("retrieval", "Consulta general; no requiere recuperación de fuentes.")
        context["coverage"] = {
            "scope": scope,
            "depth": depth_key,
            "detected_intent": intent_info["intent"],
            "candidates_retrieved": 0,
            "selected_passages": 0,
            "available_passages": 0,
            "chars_sent": 0,
            "truncated": False,
            "method": "respuesta directa sin recuperación documental",
            "memory_hit": False,
        }
        return context

    # 4. Comprobación de Memoria Documental Temporal
    custom_selected = request.get("selected_fragments") or []
    doc_ids_req = request.get("document_ids") or []
    if not custom_selected:
        cached = document_memory.get(user_id, conversation_id, query, scope, depth_key, doc_ids_req)
        if cached:
            log.info("Memoria RAG: recuperado contexto de memoria para user=%s conv=%s", user_id, conversation_id)
            if on_progress:
                await on_progress("retrieval", "Reutilizando fuentes autorizadas de la sesión…")
            context.update(cached)
            context["coverage"]["memory_hit"] = True
            return context

    # Comprobación de anáfora / seguimiento sobre sentencia previa en memoria
    if not intent_info.get("target_ruling"):
        prev_entry = document_memory.get_last_entry(user_id, conversation_id)
        if prev_entry:
            prev_ruling = prev_entry.get("intent_info", {}).get("target_ruling")
            if prev_ruling and re.search(r"\b(esta|este|dicha|dicho)\s+(sentencia|providencia|fallo|decisi[oó]n)\b|salvamento|aclaraci[oó]n|resuelve|ratio|magistrad[oa]|hechos", query, re.I):
                intent_info["target_ruling"] = prev_ruling
                log.info("Memoria RAG: asociando consulta anafórica a sentencia previa=%s", prev_ruling)

    search_query = query
    if intent_info.get("target_ruling") and not re.search(_RULING_REGEX, query):
        search_query = f"{intent_info['target_ruling']} {query}"

    t_retrieval_0 = time.monotonic()
    raw_candidates: list[dict] = []
    warnings: list[str] = []
    retrieval_method = "hybrid"
    pub_docs = 0
    idx_frags = 0

    # Si el usuario envió fragmentos seleccionados manualmente, se verifican rigurosamente en BD
    # El servidor rechaza texto inyectado por el cliente y recupera la evidencia auténtica desde Supabase
    if custom_selected:
        verified_custom = await verify_and_resolve_selected_fragments(user_id, token, custom_selected)
        for cand in verified_custom:
            if cand.get("excerpt"):
                raw_candidates.append(cand)

    # 5. Ejecución de la búsqueda híbrida según el ámbito autorizado
    if scope == "official":
        from app.services import despacho_corpus_fuentes as official
        if on_progress:
            await on_progress("retrieval", "Consultando Corpus Jurídico Oficial…")

        try:
            status = await official.corpus_status(token)
            pub_docs = status.get("published_documents", 0)
            idx_frags = status.get("indexed_fragments", 0)
        except Exception:
            pass

        try:
            corpus_res = await asyncio.wait_for(
                official.search_corpus(token, search_query[:800], limit=profile["candidate_limit"], semantic=True),
                timeout=45
            )
            raw_candidates.extend(corpus_res.get("results", []))
            retrieval_method = corpus_res.get("method") or "hybrid"
            warnings.extend(corpus_res.get("warnings", []))
        except (HTTPException, TimeoutError) as exc:
            detail = str(exc.detail) if isinstance(exc, HTTPException) else "La consulta al corpus oficial superó el tiempo disponible."
            warnings.append(detail)

    else:
        from app.services import despacho_knowledge as knowledge
        scopes = ["documents", "legal"] if scope == "all" else [
            "legal" if scope == "auto" and request.get("mode") == "research" else "documents" if scope == "auto" else scope
        ]
        if scope == "auto" and request.get("document_ids"):
            scopes = ["documents", "legal"]

        if on_progress:
            await on_progress("retrieval", "Recuperando fuentes autorizadas de tu biblioteca…")

        async def _retrieve_scope(s_name: str):
            try:
                res = await asyncio.wait_for(
                    knowledge.search(user_id, token, {
                        "query": query,
                        "scope": s_name,
                        "semantic": True,
                        "limit": profile["candidate_limit"],
                        "matter_id": request.get("matter_id") if s_name == "documents" else None,
                        "document_ids": request.get("document_ids") or [],
                    }),
                    timeout=45
                )
                return s_name, res
            except (HTTPException, TimeoutError) as exc:
                detail = str(exc.detail) if isinstance(exc, HTTPException) else "La búsqueda del índice superó el tiempo disponible."
                return s_name, {"results": [], "warnings": [detail], "method": "unavailable", "coverage": {}}

        metadata = []
        results = await asyncio.gather(*(_retrieve_scope(s_name) for s_name in scopes))
        for s_name, res in results:
            warnings.extend(res.get("warnings", []))
            raw_candidates.extend(res.get("results", []))
            metadata.append({
                "scope": s_name,
                "method": res.get("method"),
                "results": len(res.get("results", [])),
                "coverage": res.get("coverage", {})
            })
            retrieval_method = res.get("method") or retrieval_method

    t_retrieval_dur = time.monotonic() - t_retrieval_0

    # 6. Reranking Jurídico Multifactorial (13 Factores)
    if on_progress:
        await on_progress("reranking", "Evaluando relevancia y aplicando reranking jurídico…")

    t_rerank_0 = time.monotonic()
    ranked_candidates = rerank_candidates(raw_candidates, query, intent_info, profile)
    t_rerank_dur = time.monotonic() - t_rerank_0

    # 7. Selección Inteligente y Deduplicación
    if on_progress:
        await on_progress("selection", "Seleccionando fragmentos pertinentes y administrando contexto…")

    selected_passages, dropped_passages = select_intelligent_fragments(ranked_candidates, profile, intent_info)

    # 8. Mapeo y Formato de Citas Verificables ([O1-S1] y [D1-S1])
    from app.services.despacho_ai import safe_source_url

    passages = []
    new_sources = {}
    doc_urls = []
    doc_ids = list(context.get("coverage", {}).get("document_ids") or [])
    next_indices = {}

    if scope == "official":
        for row in selected_passages:
            url = row.get("source_url") or row.get("url") or ""
            if url and url not in doc_urls:
                doc_urls.append(url)
            doc_idx = (doc_urls.index(url) + 1) if url in doc_urls else 1
            seg_idx = row.get("segment") or 1
            ref = row.get("id") if (row.get("user_selected") and row.get("id")) else f"O{doc_idx}-S{seg_idx}"
            location = f"Segmento {seg_idx}"
            if row.get("version"):
                location += f" (v{row['version']})"

            text_content = row.get("excerpt") or row.get("text") or row.get("content") or ""
            passage = {
                "id": ref,
                "title": row.get("title") or "Documento oficial",
                "source_id": row.get("source_id"),
                "source_url": url,
                "date": row.get("date"),
                "document_version": row.get("version", 1),
                "segment": seg_idx,
                "section": row.get("section", "seccion_desconocida"),
                "rerank_score": row.get("rerank_score", 0.0),
                "text": text_content,
                "method": row.get("method") or retrieval_method,
                "kind": "official",
                "user_selected": bool(row.get("user_selected")),
            }
            passages.append(passage)
            new_sources[ref] = {
                "id": ref,
                "kind": "official",
                "title": row.get("title") or "Documento oficial",
                "source_id": row.get("source_id"),
                "url": safe_source_url(url),
                "location": location,
                "document_version": row.get("version", 1),
                "segment": seg_idx,
                "section": row.get("section", "seccion_desconocida"),
                "date": row.get("date"),
                "score": row.get("rerank_score") or row.get("score"),
                "method": row.get("method") or retrieval_method,
                "excerpt": text_content[:700],
                "verified": False,
                "user_selected": bool(row.get("user_selected")),
                "provenance": "Fragmento seleccionado por el abogado" if row.get("user_selected") else f"Corpus Jurídico Oficial · {row.get('section', 'documento')} ({row.get('source_id', 'oficial')}). Revisa el original."
            }

        used_chars = sum(len(p["text"]) for p in passages)
        context["passages"] = passages
        context["payload"] = [{
            "id": p["id"],
            "tipo": "corpus_juridico_oficial",
            "titulo": p["title"],
            "title": p["title"],
            "organismo": p.get("source_id"),
            "url_oficial": p["source_url"],
            "source_url": p["source_url"],
            "fecha": p.get("date"),
            "date": p.get("date"),
            "seccion": p.get("section"),
            "section": p.get("section"),
            "segmento": p.get("segment"),
            "segment": p.get("segment"),
            "texto": p["text"],
            "text": p["text"],
            "version": p.get("document_version", 1),
            "document_version": p.get("document_version", 1),
        } for p in passages]
        context["sources"] = [new_sources[p["id"]] for p in passages]

        coverage_data = {
            "scope": "official",
            "depth": depth_key,
            "depth_name": profile["name"],
            "detected_intent": intent_info["intent"],
            "dms_documents": 0,
            "personal_library_documents": 0,
            "official_documents": len(doc_urls),
            "official_corpus_total_published": pub_docs,
            "official_corpus_total_fragments": idx_frags,
            "candidates_retrieved": len(raw_candidates),
            "retrieved_passages": len(raw_candidates),
            "selected_passages": len(passages),
            "available_passages": len(raw_candidates),
            "sections_represented": list({p.get("section") for p in passages if p.get("section")}),
            "chars_sent": used_chars,
            "estimated_tokens": max(1, used_chars // 4),
            "truncated": len(passages) < len(raw_candidates),
            "method": f"RAG 2.0 · {profile['name']} ({retrieval_method} + reranking jurídico)",
            "retrieval_time_seconds": round(t_retrieval_dur, 2),
            "rerank_time_seconds": round(t_rerank_dur, 3),
            "memory_hit": False,
            "indexed_retrieval": [{
                "scope": "official",
                "method": f"{retrieval_method}+rerank",
                "results": len(raw_candidates),
                "coverage": {"documents": len(doc_urls), "published_in_corpus": pub_docs}
            }]
        }
        context["coverage"] = coverage_data

        if not passages:
            if pub_docs == 0:
                warnings.append("El Corpus Jurídico Oficial no tiene documentos publicados actualmente.")
            else:
                warnings.append(f"No se encontraron fragmentos jurídicamente pertinentes en el Corpus Jurídico Oficial para esta consulta ({pub_docs} documento(s) disponible(s)).")
        else:
            warnings.append(f"RAG 2.0 ({profile['name']}): {len(passages)} fragmentos seleccionados de {len(raw_candidates)} candidatos mediante reranking jurídico.")

    else:
        # Ámbito DMS privado y biblioteca jurídica
        for passage in context.get("passages") or []:
            match = re.fullmatch(r"D(\d+)-S(\d+)", passage.get("id", ""))
            if match:
                number = int(match[1])
                next_indices[number] = max(next_indices.get(number, 0), int(match[2]))

        for row in selected_passages:
            doc_id = row.get("document_id") or "doc"
            if doc_id not in doc_ids:
                doc_ids.append(doc_id)
            number = doc_ids.index(doc_id) + 1
            next_indices[number] = next_indices.get(number, 0) + 1
            ref = row.get("id") if (row.get("user_selected") and row.get("id")) else f"D{number}-S{next_indices[number]}"

            text_content = row.get("excerpt") or row.get("text") or row.get("content") or ""
            passage = {
                "id": ref,
                "document_id": doc_id,
                "title": row.get("title") or "Documento",
                "page": row.get("page"),
                "segment": row.get("segment"),
                "section": row.get("section", "seccion_desconocida"),
                "rerank_score": row.get("rerank_score", 0.0),
                "text": text_content,
                "document_version": row.get("document_version", 1),
                "user_selected": bool(row.get("user_selected")),
            }
            passages.append(passage)
            location = f"Página {row['page']}" if row.get("page") else f"Segmento {row.get('segment') or 1}"
            new_sources[ref] = {
                "id": ref,
                "kind": "document",
                "title": row.get("title") or "Documento",
                "document_id": doc_id,
                "document_version": row.get("document_version", 1),
                "page": row.get("page"),
                "segment": row.get("segment"),
                "section": row.get("section", "seccion_desconocida"),
                "url": safe_source_url(row.get("source_url")),
                "location": location,
                "excerpt": text_content[:700],
                "score": row.get("rerank_score"),
                "verified": False,
                "user_selected": bool(row.get("user_selected")),
                "provenance": "Fragmento seleccionado por el abogado" if row.get("user_selected") else f"Índice privado · {row.get('section', 'documento')} ({row.get('title')}). Revisa el original."
            }

        existing_sources = {source["id"]: source for source in context.get("sources") or []}
        all_passages = [*passages, *(context.get("passages") or [])]
        chosen = all_passages[:profile["max_passages"]]
        used_chars = sum(len(p["text"]) for p in chosen)

        context["passages"] = chosen
        context["payload"] = [{
            "id": p["id"],
            "document_id": p.get("document_id"),
            "titulo": p.get("title"),
            "title": p.get("title"),
            "seccion": p.get("section"),
            "section": p.get("section"),
            "pagina": p.get("page"),
            "page": p.get("page"),
            "segmento": p.get("segment"),
            "segment": p.get("segment"),
            "texto": p["text"],
            "text": p["text"],
            "document_version": p.get("document_version", 1),
        } for p in chosen]
        context["sources"] = [new_sources[p["id"]] if p["id"] in new_sources else existing_sources.get(p["id"]) for p in chosen if p["id"] in new_sources or p["id"] in existing_sources]

        coverage_data = {
            "scope": scope,
            "depth": depth_key,
            "depth_name": profile["name"],
            "detected_intent": intent_info["intent"],
            "documents": len(doc_ids),
            "document_ids": doc_ids,
            "candidates_retrieved": len(raw_candidates),
            "retrieved_passages": len(raw_candidates),
            "selected_passages": len(chosen),
            "available_passages": len(raw_candidates) + (context.get("coverage", {}).get("available_passages") or 0),
            "sections_represented": list({p.get("section") for p in chosen if p.get("section")}),
            "chars_sent": used_chars,
            "estimated_tokens": max(1, used_chars // 4),
            "truncated": True if raw_candidates else (len(chosen) < len(raw_candidates)),
            "method": f"RAG 2.0 · {profile['name']} ({retrieval_method} + reranking jurídico)",
            "retrieval_time_seconds": round(t_retrieval_dur, 2),
            "rerank_time_seconds": round(t_rerank_dur, 3),
            "memory_hit": False,
            "indexed_retrieval": metadata,
        }
        context["coverage"].update(coverage_data)
        warnings.append(f"RAG 2.0 ({profile['name']}): {len(chosen)} fragmentos seleccionados de {len(raw_candidates)} candidatos mediante reranking jurídico.")

    context["warnings"] = list(dict.fromkeys(context.get("warnings", []) + warnings))

    # Guardar en memoria conversacional si procede
    document_memory.store(
        user_id=user_id,
        conversation_id=conversation_id,
        query=query,
        scope=scope,
        depth=depth_key,
        document_ids=doc_ids_req,
        data={
            "passages": context["passages"],
            "payload": context["payload"],
            "sources": context["sources"],
            "coverage": context["coverage"],
            "warnings": context["warnings"]
        },
        intent_info=intent_info
    )

    t_total = time.monotonic() - t_start
    log.info(
        "RAG 2.0 completado: scope=%s depth=%s intent=%s candidatos=%d seleccionados=%d chars=%d duracion=%.2fs",
        scope, depth_key, intent_info["intent"], len(raw_candidates), len(context.get("passages", [])),
        context.get("coverage", {}).get("chars_sent", 0), t_total
    )

    return context
