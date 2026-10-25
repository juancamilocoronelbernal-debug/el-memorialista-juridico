"""Consulta autenticada de fuentes oficiales, separada del DMS privado."""
from __future__ import annotations

from typing import Literal, Optional
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from app.routers.despacho_data import identity
from app.services.despacho_corpus_fuentes import (
    catalog, constitutional_metadata, search_corpus, corpus_status, get_document_fragments
)
from app.services.limites import limitador, verificar_acceso

router = APIRouter(prefix='/api/despacho/official', tags=['Corpus oficial'])


class MetadataQuery(BaseModel):
    model_config = ConfigDict(extra='forbid')
    query: str = Field(min_length=2, max_length=120)
    year: int | None = Field(None, ge=1992, le=2100)
    limit: int = Field(10, ge=1, le=25)
    offset: int = Field(0, ge=0, le=10000)


class CorpusQuery(BaseModel):
    model_config = ConfigDict(extra='forbid')
    query: str = Field(min_length=2, max_length=800)
    limit: int = Field(12, ge=1, le=50)
    semantic: bool = True
    depth: Literal['auto', 'quick', 'balanced', 'deep'] = 'auto'


@router.get('/sources')
async def sources(request: Request):
    await identity(request)
    data = catalog()
    return {'sources': data, 'listed': len(data), 'metadata_connectors': sum(x['access'] == 'metadata_api' for x in data),
            'notice': 'Directorio de colecciones. Ninguna está indexada por el solo hecho de aparecer aquí.'}


@router.post('/constitutional-metadata')
async def metadata(payload: MetadataQuery, request: Request):
    uid, _ = await identity(request)
    limitador.verificar(request, 'citas', user_id=uid)
    return await constitutional_metadata(**payload.model_dump())


@router.post('/search')
async def search(payload: CorpusQuery, request: Request):
    uid, token = await identity(request)
    limitador.verificar(request, 'citas', user_id=uid)
    return await search_corpus(token, **payload.model_dump())


@router.get('/status')
async def status(request: Request):
    _, token = await identity(request)
    return await corpus_status(token)


@router.get('/document/fragments')
async def document_fragments(
    request: Request,
    doc_id: Optional[str] = None,
    source_url: Optional[str] = None,
    source_id: Optional[str] = None,
    kind: Literal['official', 'document'] = 'official',
    offset: int = 0,
    limit: int = 50,
    q: Optional[str] = None,
    version: Optional[int] = None,
):
    """Consulta paginada bajo demanda de todos los fragmentos indexados de un documento (activo o versión histórica)."""
    uid, token = await identity(request)
    limitador.verificar(request, 'citas', user_id=uid)
    return await get_document_fragments(
        token,
        doc_id=doc_id,
        source_url=source_url,
        source_id=source_id,
        kind=kind,
        user_id=uid,
        offset=offset,
        limit=limit,
        q=q,
        version=version,
    )


class ConnectorPilotRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    max_rulings: int = Field(20, ge=1, le=20)
    semantic: bool = True


class ConnectorScheduleRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    enabled: bool
    interval_minutes: int = Field(360, ge=15, le=1440)
    run_now: bool = False


class ConnectorDiscoverRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    limit: int = Field(20, ge=1, le=50)
    offset: Optional[int] = Field(None, ge=0, le=100000)


class ConnectorSyncRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    limit: int = Field(20, ge=1, le=50)
    auto_publish: bool = False
    semantic: bool = True


class ConnectorTriageReviewRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    document_id: str = Field(min_length=4, max_length=80)
    decision: Literal['approve', 'reject', 'withdraw']
    reason: Optional[str] = Field(None, max_length=500)
    review_type: Literal['revision_juridica_humana', 'aprobacion_administrativa'] = 'revision_juridica_humana'


class ConnectorPauseRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    reason: Optional[str] = Field(None, max_length=500)


class ConnectorRetriesTriggerRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    limit: int = Field(5, ge=1, le=20)
    force: bool = False


@router.get('/connector/status')
async def get_connector_status_endpoint(request: Request):
    """Devuelve métricas y estado operativo del conector de la Corte Constitucional."""
    uid, _ = await identity(request)
    limitador.verificar(request, 'citas', user_id=uid)
    from app.services import conector_corte_constitucional as conector
    return await conector.get_connector_status()


@router.post('/connector/schedule')
async def configure_schedule_endpoint(payload: ConnectorScheduleRequest, request: Request):
    """Configura la frecuencia y activación del trabajador automático en segundo plano."""
    uid, _ = await identity(request)
    limitador.verificar(request, 'citas', user_id=uid)
    from app.services.conector_corte_worker import configure_schedule
    return await configure_schedule(
        enabled=payload.enabled,
        interval_minutes=payload.interval_minutes,
        run_now=payload.run_now,
    )


@router.post('/connector/schedule/pause')
async def pause_schedule_endpoint(request: Request, payload: Optional[ConnectorPauseRequest] = None):
    """Pausa administrativamente la sincronización automática."""
    uid, _ = await identity(request)
    limitador.verificar(request, 'citas', user_id=uid)
    from app.services.conector_corte_worker import pause_schedule
    reason = payload.reason if payload else None
    return await pause_schedule(reason=reason)


@router.post('/connector/schedule/resume')
async def resume_schedule_endpoint(request: Request):
    """Reanuda la sincronización automática."""
    uid, _ = await identity(request)
    limitador.verificar(request, 'citas', user_id=uid)
    from app.services.conector_corte_worker import resume_schedule
    return await resume_schedule()


@router.post('/connector/discover')
async def discover_candidates_endpoint(payload: ConnectorDiscoverRequest, request: Request):
    """Descubre incrementalmente providencias candidatas desde el catálogo SODA oficial sin ingestar."""
    uid, _ = await identity(request)
    limitador.verificar(request, 'citas', user_id=uid)
    from app.services import conector_corte_constitucional as conector
    candidates = await conector.discover_incremental_soda_rulings(
        limit=payload.limit,
        offset=payload.offset,
    )
    return {
        "discovered_count": len(candidates),
        "limit": payload.limit,
        "offset": payload.offset,
        "candidates": candidates,
    }


@router.get('/connector/triage')
async def list_triage_endpoint(
    request: Request,
    limit: int = 50,
    offset: int = 0,
):
    """Consulta la bandeja administrativa de revisión previa (triage) para validar/aprobar sentencias."""
    uid, _ = await identity(request)
    limitador.verificar(request, 'citas', user_id=uid)
    from app.services import conector_corte_constitucional as conector
    return await conector.list_triage_inbox(limit=limit, offset=offset)


@router.post('/connector/triage/review')
async def review_triage_endpoint(payload: ConnectorTriageReviewRequest, request: Request):
    """Resuelve la revisión de un documento en triage con estricta verificación de identidad y roles de revisor."""
    usuario = await verificar_acceso(request)
    limitador.verificar(request, 'citas', user_id=usuario['id'])

    user_id = str(usuario.get('id'))
    user_email = usuario.get('email') or ''
    user_meta = usuario.get('user_metadata') or {}
    app_meta = usuario.get('app_metadata') or {}

    verified_name = (
        user_meta.get('full_name')
        or user_meta.get('nombre')
        or (user_email.split('@')[0] if user_email else f'Usuario_{user_id[:8]}')
    )
    raw_role = (
        user_meta.get('rol')
        or user_meta.get('role')
        or app_meta.get('role')
        or usuario.get('role')
        or 'abogado'
    ).lower().strip()

    # Roles jurídicos autorizados para emitir revisión jurídica humana vinculante
    LEGAL_ROLES = {'abogado', 'relator', 'magistrado', 'auditor_juridico', 'admin', 'superadmin'}

    if payload.review_type == 'revision_juridica_humana':
        if raw_role not in LEGAL_ROLES:
            raise HTTPException(
                status_code=403,
                detail=f"Acceso denegado: el rol '{raw_role}' no cuenta con atribuciones jurídicas acreditadas para emitir revisiones jurídicas humanas vinculantes."
            )
        responsible_name = f"{verified_name} ({user_email})" if user_email else verified_name
        responsible_role = f"profesional_juridico_{raw_role}"
    else:
        responsible_name = f"{verified_name} [Admin] ({user_email})" if user_email else f"{verified_name} [Admin]"
        responsible_role = "administrador_sistema"

    from app.services import conector_corte_constitucional as conector
    return await conector.review_triage_document(
        document_id=payload.document_id,
        decision=payload.decision,
        reason=payload.reason,
        review_type=payload.review_type,
        responsible_id=user_id,
        responsible_name=responsible_name,
        responsible_role=responsible_role,
    )


@router.get('/connector/retries')
async def list_pending_retries_endpoint(request: Request, limit: int = 50):
    """Lista las sentencias en cola de reintento por falta de texto en Relatoría."""
    uid, _ = await identity(request)
    limitador.verificar(request, 'citas', user_id=uid)
    from app.services import conector_corte_constitucional as conector
    return await conector.list_pending_retries(limit=limit)


@router.post('/connector/retries/trigger')
async def trigger_retries_endpoint(payload: ConnectorRetriesTriggerRequest, request: Request):
    """Dispara manualmente el procesamiento de la cola de reintentos."""
    uid, _ = await identity(request)
    limitador.verificar(request, 'citas', user_id=uid)
    from app.services import conector_corte_constitucional as conector
    return await conector.retry_pending_source_rulings(limit=payload.limit, force=payload.force)


@router.get('/connector/audit')
async def list_audit_trail_endpoint(
    request: Request,
    document_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    """Consulta el registro inmutable de auditoría de revisiones y cambios de estado del corpus."""
    uid, _ = await identity(request)
    limitador.verificar(request, 'citas', user_id=uid)
    from app.services import conector_corte_constitucional as conector
    return await conector.list_audit_trail(document_id=document_id, limit=limit, offset=offset)


@router.post('/connector/pilot')
async def run_connector_pilot_endpoint(payload: ConnectorPilotRequest, request: Request):
    """Inicia el piloto controlado de incorporación oficial (máximo 20 sentencias)."""
    uid, _ = await identity(request)
    limitador.verificar(request, 'citas', user_id=uid)
    from app.services import conector_corte_constitucional as conector
    return await conector.run_controlled_pilot(max_rulings=payload.max_rulings, semantic=payload.semantic)


@router.post('/connector/sync')
async def sync_connector_endpoint(payload: ConnectorSyncRequest, request: Request):
    """Sincronización incremental de sentencias oficiales con bloqueo concurrente y validación previa obligatoria."""
    uid, _ = await identity(request)
    limitador.verificar(request, 'citas', user_id=uid)
    from app.services import conector_corte_constitucional as conector
    owner_id = f"admin_{str(uid)[:8]}"
    return await conector.run_incremental_sync(
        limit=payload.limit,
        auto_publish=payload.auto_publish,
        semantic=payload.semantic,
        owner=owner_id,
    )


class DocumentWorkflowRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    document_id: str = Field(min_length=4, max_length=80)
    workflow_status: Literal[
        'discovered',
        'retrieved',
        'technically_validated',
        'pending_legal_review',
        'approved',
        'published',
        'withdrawn',
    ]
    published: Optional[bool] = None
    reason: Optional[str] = Field(None, max_length=500)


@router.post('/connector/document/status')
async def update_connector_document_status_endpoint(payload: DocumentWorkflowRequest, request: Request):
    """Permite cambiar el estado de ciclo de vida documental o retirar reversiblemente una providencia."""
    uid, _ = await identity(request)
    limitador.verificar(request, 'citas', user_id=uid)
    from app.services import conector_corte_constitucional as conector
    return await conector.change_document_workflow_status(
        payload.document_id,
        payload.workflow_status,
        published=payload.published,
        reason=payload.reason,
    )


