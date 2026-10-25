"""Servicio de Seguimiento de Evolución Jurisprudencial (Fase 2.3).

Identifica relaciones y dinámicas de precedentes entre providencias de la Corte Constitucional:
- Cita de providencia
- Reiteración de criterio
- Distinción de precedente (distinguishing)
- Modificación o cambio de regla (overruling)
- Sentencia de unificación relacionada (SU)

REGLA JURÍDICA FUNDAMENTAL:
Utiliza exclusivamente evidencia documental verificable (citas textuales y extractos auténticos).
JAMÁS declara que un precedente ha sido superado o modificado únicamente porque otra sentencia lo mencione.
Toda relación descubierta automáticamente recibe el estado:
'Posible evolución jurisprudencial — pendiente de verificación'
Solo un profesional jurídico acreditado puede certificarla como 'verificado_humano'.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from app.config import get_settings
from app.services import despacho_store as store

log = logging.getLogger("memorialista.despacho.evolucion_jurisprudencial")

_CITATION_PATTERN = re.compile(
    r"\b(?:sentencias?\s+|auto\s+)?(T|C|SU|A)[-\s]?(\d{1,5})\s*(?:(?:de|\/|-)\s*(\d{2,4}))\b",
    re.IGNORECASE,
)

_UNIFICATION_MARKERS = re.compile(
    r"(sentencia\s+de\s+unificaci[oó]n|unificaci[oó]n\s+jurisprudencial|unifica\s+(?:el\s+criterio|la\s+postura|la\s+regla))",
    re.IGNORECASE,
)
_REITERATION_MARKERS = re.compile(
    r"(reitera(?:ci[oó]n)?(?:\s+de)?\s+jurisprudencia|en\s+reiterada\s+jurisprudencia|l[ií]nea\s+jurisprudencial\s+(?:pac[ií]fica|uniforme|constante)|ha\s+sostenido\s+de\s+manera\s+invariable)",
    re.IGNORECASE,
)
_DISTINCTION_MARKERS = re.compile(
    r"(a\s+diferencia\s+de|se\s+distingue\s+de|no\s+resulta\s+aplicable\s+el\s+precedente|supuesto\s+(?:f[aá]ctico|de\s+hecho)\s+diferente|difiere\s+sustancialmente)",
    re.IGNORECASE,
)
_MODIFICATION_MARKERS = re.compile(
    r"(cambio\s+de\s+jurisprudencia|abandono\s+de\s+(?:la\s+postura|del\s+criterio)|se\s+aparta\s+del\s+precedente|rectifica\s+la\s+interpretaci[oó]n|nueva\s+regla\s+jurisprudencial)",
    re.IGNORECASE,
)


def normalize_ruling_tag(tipo: str, num: str, anio: str) -> str:
    """Normaliza identificador al estándar oficial ej. 'T-760/08'."""
    tipo = tipo.upper().strip()
    num = str(int(num))
    if len(anio) == 4:
        anio = anio[-2:]
    return f"{tipo}-{num}/{anio}"


def classify_relation_context(context_window: str, target_ruling: str) -> str:
    """Clasifica el tipo de relación jurisprudencial a partir del contexto textual que rodea la cita."""
    if _MODIFICATION_MARKERS.search(context_window):
        return "modificacion_regla"
    if _DISTINCTION_MARKERS.search(context_window):
        return "distincion"
    if _UNIFICATION_MARKERS.search(context_window) or target_ruling.startswith("SU-"):
        return "unificacion"
    if _REITERATION_MARKERS.search(context_window):
        return "reiteracion"
    return "cita"


async def extract_jurisprudential_relations(
    source_sentencia: str,
    text: str,
    document_id: Optional[str] = None,
    service_key: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Extrae citas y relaciones jurisprudenciales detectadas en el texto de una providencia."""
    settings = get_settings()
    key = service_key or settings.SUPABASE_SERVICE_ROLE_KEY

    source_norm = source_sentencia.strip().upper()
    discovered_relations = []
    seen_targets: Set[Tuple[str, str]] = set()

    # Dividir texto en párrafos para análisis contextual
    paragraphs = [p.strip() for p in text.split("\n") if len(p.strip()) > 30]

    for p in paragraphs:
        for match in _CITATION_PATTERN.finditer(p):
            tipo = match.group(1)
            num = match.group(2)
            anio = match.group(3)
            target_norm = normalize_ruling_tag(tipo, num, anio)

            # Evitar auto-citas
            if target_norm == source_norm:
                continue

            # Extraer ventana de cita
            start = max(0, match.start() - 120)
            end = min(len(p), match.end() + 150)
            quote = p[start:end].strip()

            rel_type = classify_relation_context(p, target_norm)
            key_pair = (target_norm, rel_type)
            if key_pair in seen_targets:
                continue
            seen_targets.add(key_pair)

            rel_record = {
                "source_sentencia": source_norm,
                "target_sentencia": target_norm,
                "relation_type": rel_type,
                "evidence_quote": quote,
                "evidence_section": "consideraciones",
                "source_document_id": document_id,
                "status": "posible_evolucion_pendiente",
                "ui_disclaimer": "Posible evolución jurisprudencial — pendiente de verificación.",
            }
            discovered_relations.append(rel_record)

            # Persistir en Supabase si se dispone de credenciales
            if key:
                try:
                    # Determinar si existe documento destino en despacho_corpus_documentos
                    target_doc = await store.db_request(
                        "GET",
                        f"despacho_corpus_documentos?title=ilike.*{target_norm}*&select=id&limit=1",
                        key,
                        service=True,
                    )
                    target_id = target_doc[0]["id"] if target_doc else None

                    insert_payload = {
                        "source_sentencia": source_norm,
                        "target_sentencia": target_norm,
                        "relation_type": rel_type,
                        "evidence_quote": quote,
                        "evidence_section": "consideraciones",
                        "source_document_id": document_id,
                        "target_document_id": target_id,
                        "status": "posible_evolucion_pendiente",
                    }
                    await store.db_request(
                        "POST",
                        "despacho_corpus_evolucion_jurisprudencial",
                        key,
                        json=insert_payload,
                        service=True,
                    )
                except Exception as exc:
                    # Silenciar violaciones de unicidad ya indexadas
                    log.debug("Relación %s -> %s ya existía o error: %s", source_norm, target_norm, exc)

    return discovered_relations


async def verify_jurisprudential_relation(
    relation_id: str,
    verified: bool,
    actor: Dict[str, Any],
    notes: Optional[str] = None,
    service_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Certifica o descarta formalmente una relación jurisprudencial mediante revisión jurídica humana."""
    settings = get_settings()
    key = service_key or settings.SUPABASE_SERVICE_ROLE_KEY
    if not key:
        raise ValueError("Se requiere SUPABASE_SERVICE_ROLE_KEY.")

    new_status = "verificado_humano" if verified else "descartado"
    now_iso = datetime.now(timezone.utc).isoformat()
    verified_by = f"{actor.get('name', 'Revisor Jurídico')} ({actor.get('role', 'abogado')})"

    patch_payload = {
        "status": new_status,
        "verified_by": verified_by,
        "verified_at": now_iso,
        "verification_notes": notes or ("Confirmada por profesional jurídico." if verified else "Descartada tras revisión jurídica."),
    }

    res = await store.db_request(
        "PATCH",
        f"despacho_corpus_evolucion_jurisprudencial?id=eq.{relation_id}",
        key,
        json=patch_payload,
        service=True,
    )

    return {
        "relation_id": relation_id,
        "status": new_status,
        "verified_by": verified_by,
        "verified_at": now_iso,
        "verification_notes": patch_payload["verification_notes"],
    }


async def scan_corpus_for_jurisprudential_evolution(
    batch_limit: int = 10,
    service_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Escanea incrementalmente documentos existentes del corpus para construir el mapa evolutivo."""
    settings = get_settings()
    key = service_key or settings.SUPABASE_SERVICE_ROLE_KEY
    if not key:
        return {"processed": 0, "relations_found": 0}

    docs = await store.db_request(
        "GET",
        f"despacho_corpus_documentos?select=id,title,metadata&limit={batch_limit}",
        key,
        service=True,
    ) or []

    total_relations = 0
    for d in docs:
        meta = d.get("metadata") or {}
        if isinstance(meta, str):
            try: meta = json.loads(meta)
            except Exception: meta = {}
        sentencia = str(meta.get("sentencia") or d.get("title", "").replace("Sentencia ", "").split(" - ")[0]).strip().upper()

        # Recuperar fragmentos
        frags = await store.db_request(
            "GET",
            f"despacho_corpus_fragmentos?document_id=eq.{d['id']}&select=content&order=ordinal.asc&limit=40",
            key,
            service=True,
        ) or []
        doc_text = "\n\n".join(f.get("content", "") for f in frags)
        if doc_text:
            rels = await extract_jurisprudential_relations(sentencia, doc_text, document_id=d["id"], service_key=key)
            total_relations += len(rels)

    return {
        "documents_scanned": len(docs),
        "relations_found": total_relations,
    }
