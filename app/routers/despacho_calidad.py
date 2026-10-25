"""Router API para el Centro de Calidad Jurídica Continua de El Memorialista (Fase 2.3).

Rutas bajo el prefijo /api/despacho/calidad:
- GET  /metricas: Métricas ejecutivas y discriminadas de calidad (técnicas vs jurídicas).
- GET  /corpus/documentos: Catálogo documental con estado de calidad y auditoría.
- POST /corpus/auditar: Auditoría de providencia individual o muestra incremental.
- POST /corpus/retirar: Retiro preventivo reversible de providencia con fallo grave.
- POST /corpus/restaurar: Restauración de providencia con subsanación auditada.
- GET  /incidencias: Bandeja unificada de incidencias (corpus, agente, jurisprudencia).
- GET  /incidencias/{id}: Detalle completo con historial inmutable de acciones.
- PATCH /incidencias/{id}: Transición de estado, asignación y registro de actuaciones.
- POST /reportes-error: Envío de reporte de error desde respuestas del Agente o Jurisprudencia.
- POST /verificacion-inteligente: Auditoría sustantiva selectiva on-demand con Gemini 3.6 Flash.
- GET  /evolucion: Mapa y lista de evolución jurisprudencial (citas, reiteraciones, SU).
- POST /evolucion/{id}/verificar: Certificación jurídica humana vinculante de precedentes.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
import logging
import re
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.config import get_settings
from app.services import despacho_store as store
from app.services.control_calidad_agente import (
    verify_agent_response_quality,
    verify_substantive_agent_response_intelligent,
)
from app.services.control_calidad_corpus import (
    audit_corpus_sample,
    audit_document_quality,
    restore_document_reversible,
    withdraw_document_reversible,
)
from app.services.control_calidad_permisos import (
    extract_user_identity,
    require_document_auditor,
    require_legal_professional,
    require_technical_admin,
)
from app.services.limites import verificar_acceso
from app.services.seguimiento_jurisprudencial import (
    extract_jurisprudential_relations,
    scan_corpus_for_jurisprudential_evolution,
    verify_jurisprudential_relation,
)

log = logging.getLogger("memorialista.despacho.router_calidad")

router = APIRouter(prefix="/api/despacho/calidad", tags=["calidad_juridica"])


# Esquemas Pydantic
class AuditRequest(BaseModel):
    document_id: Optional[str] = None
    sample_size: int = Field(5, ge=1, le=20)


class DocumentWithdrawRequest(BaseModel):
    document_id: str
    reason: str = Field(..., min_length=5)


class DocumentRestoreRequest(BaseModel):
    document_id: str
    resolution_note: str = Field(..., min_length=5)


class IncidentUpdateRequest(BaseModel):
    status: Optional[str] = Field(None, pattern=r"^(detectado|pendiente_revision|en_investigacion|corregido|descartado|cerrado)$")
    assigned_to: Optional[str] = None
    note: Optional[str] = None
    resolution_note: Optional[str] = None


class UserErrorReportRequest(BaseModel):
    target_type: str = Field(..., pattern=r"^(agente_respuesta|jurisprudencia_tarjeta|documento_corpus)$")
    document_id: Optional[str] = None
    document_version: Optional[int] = 1
    fragment_ordinal: Optional[int] = None
    fragment_segment: Optional[int] = None
    response_id: Optional[str] = None
    sentencia: Optional[str] = None
    error_category: str = Field(
        ...,
        pattern=r"^(sentencia_incorrecta|referencia_equivocada|interpretacion_incorrecta|informacion_desactualizada|fragmento_incompleto|otro)$"
    )
    description: Optional[str] = ""
    temporal_citation: Optional[str] = None
    source_fragment_id: Optional[str] = None
    query_summary: Optional[str] = None


class IntelligentVerificationRequest(BaseModel):
    query: str
    answer: str
    sources: List[Dict[str, Any]] = []


class RelationVerificationRequest(BaseModel):
    verified: bool
    notes: Optional[str] = None


# Helpers de protección de datos personales (PII) en incidencias (EM-03)

def _mask_email(email: Optional[str]) -> Optional[str]:
    """Enmascara direcciones de correo electrónico para evitar divulgación transversal de PII."""
    if not email or not isinstance(email, str) or "@" not in email:
        return None
    local, domain = email.strip().split("@", 1)
    if not local or not domain:
        return None
    prefix = local[:2] if len(local) >= 2 else local[:1]
    return f"{prefix}***@{domain}"


def _sanitize_incidencia_item(inc: Dict[str, Any]) -> Dict[str, Any]:
    """Elimina o enmascara datos personales de terceros (`reported_by_email`) en respuestas de incidencias."""
    if not isinstance(inc, dict):
        return inc
    sanitized = dict(inc)
    ev = sanitized.get("evidence")
    if isinstance(ev, dict):
        ev_copy = dict(ev)
        if "reported_by_email" in ev_copy:
            raw_email = ev_copy.get("reported_by_email")
            if raw_email and "***" not in str(raw_email):
                ev_copy["reported_by_email"] = _mask_email(str(raw_email))
        sanitized["evidence"] = ev_copy
    return sanitized


# Endpoints

@router.get("/metricas")
async def get_calidad_metricas(request: Request):
    """Métricas ejecutivas de supervisión continua, distinguiendo comprobaciones técnicas y evaluaciones jurídicas."""
    user = await verificar_acceso(request)
    require_document_auditor(user, "consultar métricas ejecutivas del Centro de Calidad")
    settings = get_settings()
    key = settings.SUPABASE_SERVICE_ROLE_KEY

    # 1. Documentos publicados vs retirados vs con incidencias
    docs = await store.db_request(
        "GET",
        "despacho_corpus_documentos?select=id,published,is_withdrawn,quality_status,last_quality_audit_at",
        key,
        service=True,
    ) or []

    docs_publicados = sum(1 for d in docs if d.get("published"))
    docs_retirados = sum(1 for d in docs if d.get("is_withdrawn"))
    docs_auditados = sum(1 for d in docs if d.get("last_quality_audit_at"))
    docs_con_incidencias = sum(1 for d in docs if d.get("quality_status") in ("con_incidencias", "critico_retirado"))

    # 2. Incidencias
    incidencias = await store.db_request(
        "GET",
        "despacho_corpus_incidencias?select=id,severity,status,issue_type,scope",
        key,
        service=True,
    ) or []

    errores_criticos = sum(1 for i in incidencias if i.get("severity") == "critica" and i.get("status") not in ("corregido", "cerrado", "descartado"))
    docs_pendientes_revision = sum(1 for i in incidencias if i.get("status") in ("detectado", "pendiente_revision"))
    incidencias_solucionadas = sum(1 for i in incidencias if i.get("status") in ("corregido", "cerrado"))
    referencias_invalidas = sum(1 for i in incidencias if i.get("issue_type") in ("referencia_invalida", "cita_inexistente"))
    respuestas_reportadas = sum(1 for i in incidencias if i.get("issue_type") == "reporte_usuario")

    # 3. Evolución jurisprudencial
    relaciones = await store.db_request(
        "GET",
        "despacho_corpus_evolucion_jurisprudencial?select=id,status",
        key,
        service=True,
    ) or []
    evoluciones_pendientes = sum(1 for r in relaciones if r.get("status") == "posible_evolucion_pendiente")
    evoluciones_verificadas = sum(1 for r in relaciones if r.get("status") == "verificado_humano")

    # 4. Estado del conector y fechas de auditoría
    conector_estado = await store.db_request(
        "GET",
        "despacho_conector_corte_estado?id=eq.corte_constitucional&select=last_quality_audit_at,next_run_at,schedule_interval_minutes",
        key,
        service=True,
    )
    last_audit = conector_estado[0].get("last_quality_audit_at") if conector_estado else None
    next_audit = conector_estado[0].get("next_run_at") if conector_estado else None

    return {
        "metricas_tecnicas": {
            "documentos_totales": len(docs),
            "documentos_publicados": docs_publicados,
            "documentos_auditados": docs_auditados,
            "documentos_retirados": docs_retirados,
            "documentos_con_incidencias": docs_con_incidencias,
            "errores_criticos": errores_criticos,
            "referencias_invalidas_detectadas": referencias_invalidas,
            "ultima_auditoria": last_audit,
            "proxima_auditoria": next_audit,
            "costes_supervision_estimados_usd": 0.00,
        },
        "evaluaciones_juridicas": {
            "documentos_pendientes_revision": docs_pendientes_revision,
            "respuestas_reportadas": respuestas_reportadas,
            "incidencias_solucionadas": incidencias_solucionadas,
            "evoluciones_pendientes_verificacion": evoluciones_pendientes,
            "evoluciones_verificadas_humanas": evoluciones_verificadas,
        },
    }


@router.get("/corpus/documentos")
async def get_corpus_documents(
    request: Request,
    quality_status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Lista providencias del Corpus Oficial distinguiendo puntaje técnico de certificación jurídica humana."""
    user = await verificar_acceso(request)
    require_document_auditor(user, "consultar el catálogo administrativo de calidad del corpus")
    settings = get_settings()
    key = settings.SUPABASE_SERVICE_ROLE_KEY

    query_parts = ["select=id,title,published,workflow_status,quality_status,quality_score,is_withdrawn,last_quality_audit_at,metadata,created_at,first_seen_at"]
    if quality_status:
        query_parts.append(f"quality_status=eq.{quality_status}")
    query_parts.append(f"order=first_seen_at.desc.nullslast&limit={limit}&offset={offset}")

    endpoint = f"despacho_corpus_documentos?{'&'.join(query_parts)}"
    docs = await store.db_request("GET", endpoint, key, service=True) or []

    # Consultar revisiones jurídicas aprobadas por abogados para mapear la certificación
    approved_revs = await store.db_request(
        "GET",
        "despacho_corpus_auditoria_revisiones?decision=eq.approve&responsible_role=in.(profesional_juridico,profesional_juridico_autorizado)&select=document_id,responsible_name",
        key,
        service=True,
    ) or []
    approved_map = {r["document_id"]: r.get("responsible_name") for r in approved_revs if r.get("document_id")}

    disclaimer = (
        "El puntaje técnico representa exclusivamente comprobaciones automatizadas de integridad de archivos "
        "(hashes SHA-256, ausencia de duplicados, continuidad de fragmentos y formato de embeddings). Una puntuación "
        "técnica del 100 % NO constituye garantía ni certificación de exactitud jurídica, la cual requiere revisión humana."
    )

    enriched_docs = []
    for d in docs:
        doc_id = d.get("id")
        has_legal_cert = doc_id in approved_map
        enriched_docs.append({
            **d,
            "technical_score": d.get("quality_score", 100.0),
            "legal_certification_status": "certificada_humana" if has_legal_cert else "pendiente_certificacion_humana",
            "legal_certified": has_legal_cert,
            "legal_certified_by": approved_map.get(doc_id),
            "disclaimer": disclaimer,
        })

    return {"documentos": enriched_docs, "limit": limit, "offset": offset, "disclaimer": disclaimer}


@router.post("/corpus/auditar")
async def trigger_corpus_audit(payload: AuditRequest, request: Request):
    """Ejecuta una auditoría de calidad inmediata sobre un documento o sobre una muestra representativa."""
    user = await verificar_acceso(request)
    identity = require_document_auditor(user, "iniciar auditorías documentales del corpus")

    if payload.document_id:
        result = await audit_document_quality(payload.document_id)
        return {"mode": "single_document", "result": result}
    else:
        sample_res = await audit_corpus_sample(sample_size=payload.sample_size)
        return {"mode": "sample_batch", "result": sample_res}


@router.post("/corpus/retirar")
async def withdraw_corpus_document(payload: DocumentWithdrawRequest, request: Request):
    """Retiro preventivo reversible de una providencia que presenta inconsistencias graves."""
    user = await verificar_acceso(request)
    identity = require_technical_admin(user, "retirar providencias de las búsquedas del corpus")
    res = await withdraw_document_reversible(payload.document_id, payload.reason, identity)
    return res


@router.post("/corpus/restaurar")
async def restore_corpus_document(payload: DocumentRestoreRequest, request: Request):
    """Restaura una providencia previamente retirada tras subsanar sus inconsistencias."""
    user = await verificar_acceso(request)
    identity = require_legal_professional(user, "restaurar providencias al corpus oficial de búsquedas")
    res = await restore_document_reversible(payload.document_id, payload.resolution_note, identity)
    return res


@router.get("/incidencias")
async def list_incidencias(
    request: Request,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    scope: Optional[str] = None,
    mine_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Consulta la bandeja unificada de incidencias con control de autorización y aislamiento por usuario."""
    user = await verificar_acceso(request)
    identity = extract_user_identity(user)

    if identity.get("has_role_conflict"):
        require_document_auditor(user, "consultar la bandeja de incidencias")

    if not identity["is_document_auditor"]:
        if not mine_only:
            require_document_auditor(user, "consultar la bandeja global de incidencias")

    settings = get_settings()
    key = settings.SUPABASE_SERVICE_ROLE_KEY

    query_parts = ["select=*"]
    if status:
        query_parts.append(f"status=eq.{status}")
    if severity:
        query_parts.append(f"severity=eq.{severity}")
    if scope:
        query_parts.append(f"scope=eq.{scope}")
    if not identity["is_document_auditor"] or mine_only:
        query_parts.append(f"evidence->>reported_by_id=eq.{identity['id']}")
    query_parts.append(f"order=detected_at.desc&limit={limit}&offset={offset}")

    raw_incidencias = await store.db_request("GET", f"despacho_corpus_incidencias?{'&'.join(query_parts)}", key, service=True) or []
    if not identity["is_document_auditor"] or mine_only:
        raw_incidencias = [
            inc for inc in raw_incidencias
            if str((inc.get("evidence") or {}).get("reported_by_id") or "") == str(identity["id"])
        ]

    incidencias = [_sanitize_incidencia_item(inc) for inc in raw_incidencias]
    return {"incidencias": incidencias, "limit": limit, "offset": offset}


@router.get("/incidencias/{incident_id}")
async def get_incidencia(incident_id: str, request: Request):
    """Obtiene el expediente completo de una incidencia verificando permisos o titularidad del reporte."""
    user = await verificar_acceso(request)
    identity = extract_user_identity(user)

    if identity.get("has_role_conflict"):
        require_document_auditor(user, "consultar detalle de incidencia")

    settings = get_settings()
    key = settings.SUPABASE_SERVICE_ROLE_KEY

    incs = await store.db_request("GET", f"despacho_corpus_incidencias?id=eq.{incident_id}&select=*", key, service=True)
    if not incs:
        if not identity["is_document_auditor"]:
            raise HTTPException(403, "Acceso denegado: no tiene permisos para consultar incidencias de otros usuarios.")
        raise HTTPException(404, "Incidencia no encontrada.")

    inc = incs[0]
    reported_by_id = str((inc.get("evidence") or {}).get("reported_by_id") or "")

    if not identity["is_document_auditor"]:
        if not reported_by_id or reported_by_id != str(identity["id"]):
            raise HTTPException(
                status_code=403,
                detail="Acceso denegado: no tiene permisos para consultar incidencias reportadas por otros usuarios.",
            )

    return _sanitize_incidencia_item(inc)


@router.patch("/incidencias/{incident_id}")
async def update_incidencia(incident_id: str, payload: IncidentUpdateRequest, request: Request):
    """Actualiza el estado de una incidencia, asigna responsable o añade una anotación a la bitácora."""
    user = await verificar_acceso(request)
    # SEGURIDAD (EM-03): Exigir como mínimo rol de auditor documental o administrador técnico para cualquier mutación
    identity = require_document_auditor(user, "modificar el estado, asignación o bitácora de incidencias")
    settings = get_settings()
    key = settings.SUPABASE_SERVICE_ROLE_KEY

    incs = await store.db_request("GET", f"despacho_corpus_incidencias?id=eq.{incident_id}&select=*", key, service=True)
    if not incs:
        raise HTTPException(404, "Incidencia no encontrada.")
    inc = incs[0]

    # Si se intenta resolver o cerrar una incidencia (o descartar una incidencia jurídica de fondo), exigir acreditación jurídica
    if payload.status in ("corregido", "cerrado") or (
        payload.status == "descartado" and inc.get("scope") in ("agente", "jurisprudencia")
    ):
        identity = require_legal_professional(user, "resolver o cerrar formalmente incidencias jurídicas de fondo")

    now_iso = datetime.now(timezone.utc).isoformat()
    history = inc.get("action_history") or []

    action_record = {
        "timestamp": now_iso,
        "actor": f"{identity['name']} ({identity['role']})",
        "action": f"cambio_estado_a_{payload.status}" if payload.status else "anotacion_bitacora",
        "note": payload.note or payload.resolution_note or "Actualización de incidencia.",
    }
    history.append(action_record)

    update_payload: Dict[str, Any] = {"action_history": history}
    if payload.status:
        update_payload["status"] = payload.status
        if payload.status in ("corregido", "cerrado"):
            update_payload["resolved_at"] = now_iso
            update_payload["resolution_note"] = payload.resolution_note or payload.note or "Subsanado satisfactoriamente."
    if payload.assigned_to is not None:
        update_payload["assigned_to"] = payload.assigned_to

    await store.db_request("PATCH", f"despacho_corpus_incidencias?id=eq.{incident_id}", key, json=update_payload, service=True)

    return {"incident_id": incident_id, "status": payload.status or inc.get("status"), "history_count": len(history)}


@router.post("/reportes-error")
async def report_user_error(payload: UserErrorReportRequest, request: Request):
    """Permite al usuario autenticado reportar un error desde una respuesta del Agente o tarjeta de Jurisprudencia vinculándolo a identificadores estables."""
    user = await verificar_acceso(request)
    identity = extract_user_identity(user)
    if not user or not user.get("id") or identity["id"] == "anon":
        raise HTTPException(401, "No autenticado.")
    settings = get_settings()
    key = settings.SUPABASE_SERVICE_ROLE_KEY

    now_iso = datetime.now(timezone.utc).isoformat()
    doc_id = payload.document_id
    doc_version = payload.document_version or 1
    sentencia_title = payload.sentencia or ""
    frag_ordinal = payload.fragment_ordinal
    frag_segment = payload.fragment_segment

    # Resolver referencia temporal si vino en citation ej: [O1-S1] o [O2-S3]
    ref_input = payload.temporal_citation or payload.source_fragment_id
    if ref_input and (frag_ordinal is None or frag_segment is None):
        m_ord = re.search(r"\[?O(\d+)(?:-S(\d+))?\]?", ref_input, re.IGNORECASE)
        if m_ord:
            if frag_ordinal is None:
                frag_ordinal = int(m_ord.group(1))
            if frag_segment is None and m_ord.group(2):
                frag_segment = int(m_ord.group(2))

    # Si doc_id no es UUID válido o viene vacío, buscar documento permanente por sentencia
    if not doc_id and sentencia_title:
        doc_rows = await store.db_request(
            "GET",
            f"despacho_corpus_documentos?title=ilike.*{sentencia_title.strip()}*&select=id,version,title&limit=1",
            key,
            service=True,
        ) or []
        if doc_rows:
            doc_id = doc_rows[0].get("id")
            doc_version = doc_rows[0].get("version", 1)
            sentencia_title = doc_rows[0].get("title", sentencia_title)
    elif doc_id:
        doc_rows = await store.db_request(
            "GET",
            f"despacho_corpus_documentos?id=eq.{doc_id}&select=id,version,title&limit=1",
            key,
            service=True,
        ) or []
        if doc_rows:
            doc_version = doc_rows[0].get("version", 1)
            if not sentencia_title:
                sentencia_title = doc_rows[0].get("title", "")

    # Resguardo riguroso de privacidad (EM-03): enmascarar correo del reportante y no exponer PII
    evidence = {
        "error_category": payload.error_category,
        "description": payload.description,
        "target_type": payload.target_type,
        "document_version": doc_version,
        "fragment_ordinal": frag_ordinal,
        "fragment_segment": frag_segment,
        "response_id": payload.response_id,
        "temporal_citation": ref_input,
        "reported_by_id": identity["id"],
        "reported_by_role": identity["role"],
        "reported_by_email": _mask_email(identity.get("email")),
    }

    inc_payload = {
        "document_id": doc_id,
        "sentencia": sentencia_title or (f"Providencia {doc_id}" if doc_id else "Sin providencia identificada"),
        "scope": "agente" if payload.target_type == "agente_respuesta" else ("jurisprudencia" if payload.target_type == "jurisprudencia_tarjeta" else "corpus"),
        "issue_type": "reporte_usuario",
        "severity": "media" if payload.error_category not in ("sentencia_incorrecta", "interpretacion_incorrecta") else "alta",
        "status": "detectado",
        "evidence": evidence,
        "assigned_to": None,
        "action_history": [
            {
                "timestamp": now_iso,
                "actor": f"{identity['name']} ({identity['role']})",
                "action": "reporte_error_usuario_radicado",
                "note": f"Categoría reportada: {payload.error_category}. Detalle: {payload.description or 'Sin descripción adicional'}",
            }
        ],
    }

    res = await store.db_request("POST", "despacho_corpus_incidencias", key, json=inc_payload, service=True)
    return {
        "success": True,
        "message": "Reporte de error radicado exitosamente. Ha sido incorporado al Centro de Calidad Jurídica para revisión profesional.",
        "incident": _sanitize_incidencia_item(inc_payload),
    }


@router.post("/verificacion-inteligente")
async def perform_intelligent_verification(payload: IntelligentVerificationRequest, request: Request):
    """Verificación Inteligente Selectiva (on-demand / high-risk) con Gemini 3.6 Flash."""
    user = await verificar_acceso(request)
    identity = require_document_auditor(user, "ejecutar verificaciones inteligentes con Gemini")
    
    result = await verify_substantive_agent_response_intelligent(
        query=payload.query,
        answer=payload.answer,
        sources=payload.sources,
        user_id=identity["id"],
    )
    return result


@router.get("/evolucion")
async def get_jurisprudential_evolution(
    request: Request,
    source: Optional[str] = None,
    target: Optional[str] = None,
    relation_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
):
    """Consulta relaciones jurisprudenciales detectadas entre providencias."""
    user = await verificar_acceso(request)
    require_document_auditor(user, "consultar el seguimiento de evolución jurisprudencial")
    settings = get_settings()
    key = settings.SUPABASE_SERVICE_ROLE_KEY

    query_parts = ["select=*"]
    if source:
        query_parts.append(f"source_sentencia=ilike.*{source}*")
    if target:
        query_parts.append(f"target_sentencia=ilike.*{target}*")
    if relation_type:
        query_parts.append(f"relation_type=eq.{relation_type}")
    if status:
        query_parts.append(f"status=eq.{status}")
    query_parts.append(f"order=created_at.desc&limit={limit}")

    relations = await store.db_request("GET", f"despacho_corpus_evolucion_jurisprudencial?{'&'.join(query_parts)}", key, service=True) or []
    return {"relaciones": relations, "disclaimer": "Posible evolución jurisprudencial — pendiente de verificación."}


@router.post("/evolucion/escanear")
async def scan_corpus_evolution(request: Request, limit: int = Query(10, ge=1, le=50)):
    """Ejecuta un escaneo incremental del corpus para descubrir relaciones jurisprudenciales."""
    user = await verificar_acceso(request)
    identity = require_document_auditor(user, "escanear evolución jurisprudencial")
    res = await scan_corpus_for_jurisprudential_evolution(batch_limit=limit)
    return res


@router.post("/evolucion/{relation_id}/verificar")
async def verify_relation(relation_id: str, payload: RelationVerificationRequest, request: Request):
    """Certifica formalmente o descarta una relación jurisprudencial mediante revisión jurídica humana."""
    user = await verificar_acceso(request)
    identity = require_legal_professional(user, "certificar evolución jurisprudencial vinculante")
    res = await verify_jurisprudential_relation(
        relation_id=relation_id,
        verified=payload.verified,
        actor=identity,
        notes=payload.notes,
    )
    return res
