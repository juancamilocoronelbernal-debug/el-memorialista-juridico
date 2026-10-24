"""Consulta autenticada de fuentes oficiales, separada del DMS privado."""
from __future__ import annotations

from typing import Literal, Optional
from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field

from app.routers.despacho_data import identity
from app.services.despacho_corpus_fuentes import (
    catalog, constitutional_metadata, search_corpus, corpus_status, get_document_fragments
)
from app.services.limites import limitador

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
):
    """Consulta paginada bajo demanda de todos los fragmentos indexados de un documento."""
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
    )


class ConnectorPilotRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    max_rulings: int = Field(20, ge=1, le=20)
    semantic: bool = True


@router.get('/connector/status')
async def get_connector_status_endpoint(request: Request):
    """Devuelve métricas y estado operativo del conector de la Corte Constitucional."""
    uid, _ = await identity(request)
    limitador.verificar(request, 'citas', user_id=uid)
    from app.services import conector_corte_constitucional as conector
    return await conector.get_connector_status()


@router.post('/connector/pilot')
async def run_connector_pilot_endpoint(payload: ConnectorPilotRequest, request: Request):
    """Inicia el piloto controlado de incorporación oficial (máximo 20 sentencias)."""
    uid, _ = await identity(request)
    limitador.verificar(request, 'citas', user_id=uid)
    from app.services import conector_corte_constitucional as conector
    return await conector.run_controlled_pilot(max_rulings=payload.max_rulings, semantic=payload.semantic)


@router.post('/connector/sync')
async def sync_connector_endpoint(payload: ConnectorPilotRequest, request: Request):
    """Sincronización incremental de sentencias oficiales no indexadas."""
    uid, _ = await identity(request)
    limitador.verificar(request, 'citas', user_id=uid)
    from app.services import conector_corte_constitucional as conector
    return await conector.run_controlled_pilot(max_rulings=payload.max_rulings, semantic=payload.semantic)

