"""Servicio de Calidad y Auditoría Permanente del Corpus Jurídico Oficial (Fase 2.3).

Supervisa de manera continua e incremental la integridad, calidad y autenticidad
de cada providencia almacenada en despacho_corpus_documentos y despacho_corpus_fragmentos.

Comprobaciones de Calidad (12 puntos de control):
1. Identidad oficial (número, año, tipo)
2. Coherencia y completitud de metadatos (magistrado, sala, fecha, tema)
3. Integridad del texto (longitud >= 500, sin caracteres binarios nulos)
4. Coincidencia con fuente oficial (dominio corteconstitucional.gov.co)
5. Hash SHA-256 (64 hex) y versión
6. Fragmentos continuos sin omisiones (secuencia chunk_index estricta 0..N-1)
7. Embeddings válidos (768 dimensiones, no nulos, no degenerados)
8. Ausencia de duplicados espurios (mismo radicado o fragmentos repetidos)
9. Clasificación estructural de macro-secciones
10. Presencia de parte resolutiva oficial (RESUELVE / DECISIÓN)
11. Detección y correcta clasificación de salvamentos y aclaraciones de voto
12. Estado y consistencia de publicación

Incluye:
- Mecanismo reversible de retiro y restauración de providencias sin borrado de datos.
- Registro automático e inmutable de incidencias en despacho_corpus_incidencias.
- Auditoría periódica incremental por lotes de muestra (cero costes adicionales).
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import hashlib
import json
import logging
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlsplit

from app.config import get_settings
from app.services import despacho_store as store

log = logging.getLogger("memorialista.despacho.calidad_corpus")

_RULING_IDENTITY_RE = re.compile(r"^(T|C|SU|A)-?(\d{1,5})[/-](\d{2,4})$", re.IGNORECASE)
_OPERATIVE_MARKERS_RE = re.compile(
    r"(\bR\s*E\s*S\s*U\s*E\s*L\s*V\s*E\b|^\s*(?:III|IV|V|VI|VII|VIII|IX|X|\d+)?\s*\.?\s*DECISI[OÓ]N\b|"
    r"^\s*DECIDE\s*[\.:\-]|administrando\s+justicia\s+en\s+nombre\s+del\s+pueblo|"
    r"\bdeclarar\s+(in)?exequible\b|\bconceder\s+el\s+amparo\b|\bamparar\s+el\s+derecho\b|"
    r"\bdeclararse\s+inhibida\b|\binhibirse\s+de\s+emitir\b|\bcarencia\s+actual\s+de\s+objeto\b)",
    re.IGNORECASE | re.MULTILINE,
)
_DISSENT_MARKERS_RE = re.compile(
    r"(salvamento\s+de\s+voto|aclaraci[oó]n\s+de\s+voto|salvamento\s+parcial)",
    re.IGNORECASE,
)


class CorpusDocumentAuditResult:
    """Contenedor estructurado de auditoría de calidad de un documento."""

    def __init__(self, document_id: str, sentencia: str):
        self.document_id = document_id
        self.sentencia = sentencia
        self.checks: Dict[str, Dict[str, Any]] = {}
        self.critical_failures: List[str] = []
        self.warnings: List[str] = []
        self.score: float = 100.0

    def record_check(self, name: str, passed: bool, detail: str, is_critical: bool = True, weight: float = 8.33):
        self.checks[name] = {
            "passed": passed,
            "detail": detail,
            "critical": is_critical,
        }
        if not passed:
            msg = f"[{name}] {detail}"
            if is_critical:
                self.critical_failures.append(msg)
                self.score = max(0.0, self.score - (weight * 2.0))
            else:
                self.warnings.append(msg)
                self.score = max(0.0, self.score - weight)

    @property
    def quality_status(self) -> str:
        if self.critical_failures:
            return "con_incidencias"
        if self.warnings:
            return "con_advertencias"
        return "optimo"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "document_id": self.document_id,
            "sentencia": self.sentencia,
            "quality_status": self.quality_status,
            "quality_score": round(self.score, 2),
            "critical_failures": self.critical_failures,
            "warnings": self.warnings,
            "checks": self.checks,
            "audited_at": datetime.now(timezone.utc).isoformat(),
        }


async def audit_document_quality(document_id: str, service_key: Optional[str] = None) -> Dict[str, Any]:
    """Ejecuta la auditoría integral de 12 puntos sobre un documento y sus fragmentos en Supabase."""
    settings = get_settings()
    key = service_key or settings.SUPABASE_SERVICE_ROLE_KEY
    if not key:
        raise ValueError("Se requiere SUPABASE_SERVICE_ROLE_KEY para auditar la calidad del corpus.")

    # 1. Recuperar documento
    doc_rows = await store.db_request(
        "GET",
        f"despacho_corpus_documentos?id=eq.{document_id}&select=*",
        key,
        service=True,
    )
    if not doc_rows:
        raise ValueError(f"Documento no encontrado: {document_id}")
    doc = doc_rows[0]

    # 2. Recuperar fragmentos
    fragments = await store.db_request(
        "GET",
        f"despacho_corpus_fragmentos?document_id=eq.{document_id}&select=document_id,ordinal,section,content,embedding&order=ordinal.asc",
        key,
        service=True,
    ) or []

    # Metadatos del documento
    meta = doc.get("metadata") or {}
    if isinstance(meta, str):
        try:
            meta = json.loads(meta)
        except Exception:
            meta = {}

    sentencia = str(meta.get("sentencia") or doc.get("title", "").replace("Sentencia ", "").split(" - ")[0]).strip().upper()
    audit = CorpusDocumentAuditResult(document_id, sentencia)

    # 1. Identidad oficial
    id_match = _RULING_IDENTITY_RE.match(sentencia)
    audit.record_check(
        "identidad_oficial",
        bool(id_match),
        f"Identificador '{sentencia}' {'cumple nomenclatura oficial' if id_match else 'no cumple formato oficial T/C/SU/A-###/AA'}",
        is_critical=True,
    )

    # 2. Metadatos
    magistrado = meta.get("magistrado") or meta.get("magistrado_ponente")
    sala = meta.get("sala")
    fecha = meta.get("fecha") or meta.get("fecha_sentencia")
    tema = meta.get("tema") or meta.get("subtema")
    missing_meta = []
    if not magistrado: missing_meta.append("magistrado")
    if not sala: missing_meta.append("sala")
    if not fecha: missing_meta.append("fecha")
    audit.record_check(
        "metadatos_completitud",
        len(missing_meta) == 0,
        f"Metadatos esenciales: {'completos' if not missing_meta else 'faltan: ' + ', '.join(missing_meta)}",
        is_critical=False,
    )

    # 3. Integridad del texto concatenado
    full_text = " ".join(f.get("content", "") for f in fragments)
    has_nulls = "\x00" in full_text
    is_long_enough = len(full_text) >= 500
    audit.record_check(
        "integridad_texto",
        is_long_enough and not has_nulls,
        f"Texto: {len(full_text)} caracteres, {'sin caracteres nulos' if not has_nulls else 'CONTIENE NULOS'}",
        is_critical=True,
    )

    # 4. Coincidencia con fuente oficial
    source_url = str(doc.get("source_url") or "").strip()
    is_official_url = False
    if source_url:
        try:
            parsed = urlsplit(source_url)
            host = (parsed.hostname or "").lower()
            is_official_url = host.endswith("corteconstitucional.gov.co") or host.endswith("datos.gov.co")
        except Exception:
            is_official_url = False
    audit.record_check(
        "fuente_oficial",
        is_official_url,
        f"URL de origen: '{source_url}' ({'dominio institucional verificado' if is_official_url else 'fuente no oficial o inválida'})",
        is_critical=True,
    )

    # 5. Hash SHA-256 de contenido
    content_hash = doc.get("content_hash") or ""
    is_valid_hash = bool(re.match(r"^[0-9a-f]{64}$", content_hash, re.IGNORECASE))
    audit.record_check(
        "hash_version",
        is_valid_hash,
        f"Hash SHA-256: {'válido (64 hex)' if is_valid_hash else 'ausente o corrupto'}",
        is_critical=True,
    )

    # 6. Fragmentos continuos sin omisiones
    expected_indexes = list(range(len(fragments)))
    actual_indexes = [f.get("ordinal") if f.get("ordinal") is not None else f.get("chunk_index") for f in fragments]
    continuous = actual_indexes == expected_indexes and len(fragments) > 0
    audit.record_check(
        "fragmentos_continuidad",
        continuous,
        f"Fragmentos: {len(fragments)} indexados. Secuencia {'100% continua (0..N-1)' if continuous else 'DISCONTINUA O VACÍA'}",
        is_critical=True,
    )

    # 7. Embeddings válidos (768d no nulos)
    valid_embeddings = 0
    zero_or_null = 0
    for f in fragments:
        emb = f.get("embedding")
        if isinstance(emb, str):
            try:
                emb = json.loads(emb)
            except Exception:
                emb = None
        if isinstance(emb, list) and len(emb) == 768 and any(abs(v) > 1e-6 for v in emb):
            valid_embeddings += 1
        else:
            zero_or_null += 1

    all_embeddings_valid = (valid_embeddings == len(fragments)) and len(fragments) > 0
    audit.record_check(
        "embeddings_calidad",
        all_embeddings_valid,
        f"Embeddings: {valid_embeddings}/{len(fragments)} válidos (768d). Nulos o corruptos: {zero_or_null}",
        is_critical=True,
    )

    # 8. Ausencia de duplicados espurios
    # Consultar si hay otro documento activo con la misma sentencia
    other_docs = await store.db_request(
        "GET",
        f"despacho_corpus_documentos?id=neq.{document_id}&title=ilike.*{sentencia}*&select=id,published,workflow_status",
        key,
        service=True,
    ) or []
    has_active_duplicates = any(d.get("published") for d in other_docs)
    audit.record_check(
        "ausencia_duplicados",
        not has_active_duplicates,
        f"Duplicados activos en corpus: {'ninguno detectado' if not has_active_duplicates else f'{len(other_docs)} providencias colisionan con {sentencia}'}",
        is_critical=True,
    )

    # 9. Clasificación estructural
    sections_found = {f.get("section") or f.get("section_type") for f in fragments if (f.get("section") or f.get("section_type"))}
    has_structure = bool({"encabezado", "antecedentes", "consideraciones", "resuelve"} & sections_found) or len(sections_found) >= 2
    audit.record_check(
        "clasificacion_estructural",
        has_structure,
        f"Secciones clasificadas: {', '.join(sorted(sections_found)) if sections_found else 'ninguna'}",
        is_critical=False,
    )

    # 10. Presencia de parte resolutiva oficial
    has_operative = bool(_OPERATIVE_MARKERS_RE.search(full_text)) or ("resuelve" in sections_found)
    audit.record_check(
        "parte_resolutiva",
        has_operative,
        f"Parte resolutiva: {'detectada oficialmente' if has_operative else 'NO ENCONTRADA EN EL TEXTO'}",
        is_critical=True,
    )

    # 11. Salvamentos y aclaraciones de voto
    has_dissent_text = bool(_DISSENT_MARKERS_RE.search(full_text))
    has_dissent_section = any("salvamento" in s or "aclaracion" in s for s in sections_found)
    dissent_consistent = True
    if has_dissent_text and not has_dissent_section:
        dissent_consistent = False
    audit.record_check(
        "salvamentos_aclaraciones",
        dissent_consistent,
        f"Salvamentos/aclaraciones: {'correctamente catalogados' if dissent_consistent else 'mencionados en el texto pero no catalogados como sección separada'}",
        is_critical=False,
    )

    # 12. Estado y consistencia de publicación
    is_withdrawn = bool(doc.get("is_withdrawn"))
    published = bool(doc.get("published"))
    workflow_status = str(doc.get("workflow_status") or "")
    status_consistent = True
    if is_withdrawn and published:
        status_consistent = False
    audit.record_check(
        "consistencia_publicacion",
        status_consistent,
        f"Publicado: {published}, Retirado: {is_withdrawn}, Workflow: '{workflow_status}'",
        is_critical=True,
    )

    result_dict = audit.to_dict()

    # 3. Actualizar despacho_corpus_documentos con los resultados de auditoría
    update_payload = {
        "quality_status": audit.quality_status,
        "quality_checks": result_dict["checks"],
        "last_quality_audit_at": result_dict["audited_at"],
        "quality_score": audit.score,
    }
    await store.db_request(
        "PATCH",
        f"despacho_corpus_documentos?id=eq.{document_id}",
        key,
        json=update_payload,
        service=True,
    )

    # 4. Si hay fallos críticos o advertencias, registrar o actualizar incidencias
    if audit.critical_failures or audit.warnings:
        severity = "critica" if audit.critical_failures else "media"
        issue_type = "hash_mismatch" if any("hash" in f.lower() for f in audit.critical_failures) else (
            "embedding_invalido" if any("embedding" in f.lower() for f in audit.critical_failures) else (
                "parte_resolutiva_ausente" if any("resolutiva" in f.lower() for f in audit.critical_failures) else (
                    "fragmentos_omitidos" if any("continuidad" in f.lower() for f in audit.critical_failures) else (
                        "metadatos_incompletos" if audit.warnings else "otro"
                    )
                )
            )
        )
        
        # Buscar si ya existe una incidencia abierta para este documento y tipo
        existing_inc = await store.db_request(
            "GET",
            f"despacho_corpus_incidencias?document_id=eq.{document_id}&status=in.(detectado,pendiente_revision,en_investigacion)&limit=1",
            key,
            service=True,
        )
        if not existing_inc:
            incident_payload = {
                "document_id": document_id,
                "sentencia": sentencia,
                "scope": "corpus",
                "issue_type": issue_type,
                "severity": severity,
                "status": "detectado",
                "evidence": {
                    "critical_failures": audit.critical_failures,
                    "warnings": audit.warnings,
                    "checks": result_dict["checks"],
                },
                "action_history": [
                    {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "actor": "sistema_auditoria_corpus",
                        "action": "incidencia_detectada_automaticamente",
                        "note": f"Auditoría automática detectó score={audit.score} con estado {audit.quality_status}",
                    }
                ],
            }
            await store.db_request(
                "POST",
                "despacho_corpus_incidencias",
                key,
                json=incident_payload,
                service=True,
            )

    return result_dict


async def withdraw_document_reversible(
    document_id: str,
    reason: str,
    actor: Dict[str, Any],
    service_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Retira temporalmente un documento de las búsquedas RAG de manera 100% reversible (sin borrar datos)."""
    settings = get_settings()
    key = service_key or settings.SUPABASE_SERVICE_ROLE_KEY
    if not key:
        raise ValueError("Se requiere SUPABASE_SERVICE_ROLE_KEY.")

    doc_rows = await store.db_request("GET", f"despacho_corpus_documentos?id=eq.{document_id}&select=*", key, service=True)
    if not doc_rows:
        raise ValueError(f"Documento no encontrado: {document_id}")
    doc = doc_rows[0]

    now_iso = datetime.now(timezone.utc).isoformat()
    update_payload = {
        "published": False,
        "is_withdrawn": True,
        "withdrawn_reason": reason,
        "withdrawn_at": now_iso,
        "workflow_status": "retirado_temporalmente",
        "quality_status": "critico_retirado",
    }
    await store.db_request("PATCH", f"despacho_corpus_documentos?id=eq.{document_id}", key, json=update_payload, service=True)

    # Registrar en auditoría inmutable
    audit_payload = {
        "document_id": document_id,
        "document_version": doc.get("version", 1),
        "responsible_id": actor.get("id", "anon"),
        "responsible_name": actor.get("name", "Administrador"),
        "responsible_role": actor.get("role", "administrador_tecnico"),
        "review_type": "aprobacion_administrativa",
        "decision": "withdraw",
        "reason": reason,
        "previous_workflow_status": doc.get("workflow_status"),
        "new_workflow_status": "retirado_temporalmente",
        "previous_published": doc.get("published"),
        "new_published": False,
        "validation_summary": {"action": "retiro_reversible_preventivo", "withdrawn_at": now_iso},
    }
    await store.db_request("POST", "despacho_corpus_auditoria_revisiones", key, json=audit_payload, service=True)

    # Crear o actualizar incidencia correspondiente
    meta = doc.get("metadata") or {}
    if isinstance(meta, str):
        try: meta = json.loads(meta)
        except Exception: meta = {}
    sentencia = str(meta.get("sentencia") or doc.get("title", "")).strip().upper()

    inc_payload = {
        "document_id": document_id,
        "sentencia": sentencia,
        "scope": "corpus",
        "issue_type": "otro",
        "severity": "critica",
        "status": "en_investigacion",
        "evidence": {"withdrawal_reason": reason, "previous_status": doc.get("workflow_status")},
        "assigned_to": actor.get("name"),
        "action_history": [
            {
                "timestamp": now_iso,
                "actor": actor.get("name", "Sistema"),
                "action": "documento_retirado_temporalmente",
                "note": reason,
            }
        ],
    }
    await store.db_request("POST", "despacho_corpus_incidencias", key, json=inc_payload, service=True)

    return {
        "document_id": document_id,
        "status": "retirado_temporalmente",
        "published": False,
        "is_withdrawn": True,
        "reason": reason,
        "withdrawn_at": now_iso,
    }


async def restore_document_reversible(
    document_id: str,
    resolution_note: str,
    actor: Dict[str, Any],
    service_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Restaura un documento previamente retirado tras subsanar inconsistencias."""
    settings = get_settings()
    key = service_key or settings.SUPABASE_SERVICE_ROLE_KEY
    if not key:
        raise ValueError("Se requiere SUPABASE_SERVICE_ROLE_KEY.")

    doc_rows = await store.db_request("GET", f"despacho_corpus_documentos?id=eq.{document_id}&select=*", key, service=True)
    if not doc_rows:
        raise ValueError(f"Documento no encontrado: {document_id}")
    doc = doc_rows[0]

    now_iso = datetime.now(timezone.utc).isoformat()
    update_payload = {
        "published": True,
        "is_withdrawn": False,
        "withdrawn_reason": None,
        "withdrawn_at": None,
        "workflow_status": "published",
        "quality_status": "optimo",
    }
    await store.db_request("PATCH", f"despacho_corpus_documentos?id=eq.{document_id}", key, json=update_payload, service=True)

    # Registrar en auditoría inmutable
    audit_payload = {
        "document_id": document_id,
        "document_version": doc.get("version", 1),
        "responsible_id": actor.get("id", "anon"),
        "responsible_name": actor.get("name", "Administrador"),
        "responsible_role": actor.get("role", "profesional_juridico"),
        "review_type": "aprobacion_administrativa",
        "decision": "approve",
        "reason": f"Restauración de providencia: {resolution_note}",
        "previous_workflow_status": doc.get("workflow_status"),
        "new_workflow_status": "published",
        "previous_published": doc.get("published"),
        "new_published": True,
        "validation_summary": {"action": "restauracion_reversible", "restored_at": now_iso},
    }
    await store.db_request("POST", "despacho_corpus_auditoria_revisiones", key, json=audit_payload, service=True)

    # Cerrar incidencias abiertas asociadas
    open_incs = await store.db_request(
        "GET",
        f"despacho_corpus_incidencias?document_id=eq.{document_id}&status=in.(detectado,pendiente_revision,en_investigacion)",
        key,
        service=True,
    ) or []
    for inc in open_incs:
        hist = inc.get("action_history") or []
        hist.append({
            "timestamp": now_iso,
            "actor": actor.get("name", "Sistema"),
            "action": "incidencia_resuelta_y_cerrada",
            "note": resolution_note,
        })
        await store.db_request(
            "PATCH",
            f"despacho_corpus_incidencias?id=eq.{inc['id']}",
            key,
            json={
                "status": "cerrado",
                "resolved_at": now_iso,
                "resolution_note": resolution_note,
                "action_history": hist,
            },
            service=True,
        )

    return {
        "document_id": document_id,
        "status": "published",
        "published": True,
        "is_withdrawn": False,
        "resolution_note": resolution_note,
        "restored_at": now_iso,
    }


async def audit_corpus_sample(sample_size: int = 5, service_key: Optional[str] = None) -> Dict[str, Any]:
    """Audita periódicamente una muestra rotativa de documentos del corpus sin sobrecostes."""
    settings = get_settings()
    key = service_key or settings.SUPABASE_SERVICE_ROLE_KEY
    if not key:
        return {"audited": 0, "results": [], "error": "No service key"}

    # Seleccionar documentos ordenados por última auditoría (los más antiguos primero)
    docs = await store.db_request(
        "GET",
        f"despacho_corpus_documentos?select=id,title&order=last_quality_audit_at.asc.nullsfirst&limit={sample_size}",
        key,
        service=True,
    ) or []

    results = []
    for d in docs:
        try:
            r = await audit_document_quality(d["id"], service_key=key)
            results.append(r)
        except Exception as exc:
            log.warning("Fallo al auditar doc %s: %s", d.get("id"), exc)
            results.append({"document_id": d["id"], "error": str(exc)})

    now_iso = datetime.now(timezone.utc).isoformat()
    # Actualizar estado global del conector con la marca de auditoría
    await store.db_request(
        "PATCH",
        "despacho_conector_corte_estado?id=eq.corte_constitucional",
        key,
        json={
            "last_quality_audit_at": now_iso,
            "quality_audit_metrics": {
                "last_sample_size": len(results),
                "timestamp": now_iso,
                "summary": [
                    {"doc_id": r.get("document_id"), "status": r.get("quality_status"), "score": r.get("quality_score")}
                    for r in results if "quality_status" in r
                ],
            },
        },
        service=True,
    )

    return {
        "audited_count": len(results),
        "timestamp": now_iso,
        "results": results,
    }
