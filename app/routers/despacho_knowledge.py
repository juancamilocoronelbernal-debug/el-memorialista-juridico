from __future__ import annotations
"""Biblioteca y búsqueda privada; todas las operaciones validan la sesión."""
from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal

from app.routers.despacho_data import identity
from app.services import despacho_knowledge as knowledge
from app.services import despacho_store as store
from app.services.limites import limitador

router = APIRouter(prefix="/api/despacho/knowledge", tags=["Biblioteca y búsqueda"])


class Search(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=1, max_length=4000)
    scope: Literal["documents", "legal"] = "documents"
    matter_id: str | None = None
    semantic: bool = True
    limit: int = Field(20, ge=1, le=50)
    filters: dict[str, str | int | None] = Field(default_factory=dict, max_length=3)


class ImportSource(BaseModel):
    model_config = ConfigDict(extra="forbid")
    url: str = Field(max_length=2048)
    title: str | None = Field(None, max_length=240)
    court: str | None = Field(None, max_length=160)
    year: int | None = Field(None, ge=1800, le=2200)
    document_type: str | None = Field(None, max_length=160)


class Reindex(BaseModel):
    offset: int = Field(0, ge=0, le=100000)
    limit: int = Field(5, ge=1, le=10)


class Crawl(BaseModel):
    url: str = Field(max_length=2048)
    max_documents: int = Field(5, ge=1, le=10)


@router.get("/status")
async def status(request: Request):
    uid, token = await identity(request)
    from app.services.despacho_ocr import ocr_status
    coverage = await store.db_request("POST", "rpc/despacho_cobertura_indice", token,
                                      json={"p_model": knowledge.embedding_status()["model"]})
    return {"embeddings": knowledge.embedding_status(), "ocr": ocr_status(), "coverage": coverage,
            "message": "La cobertura corresponde a documentos incorporados e indexados en tu cuenta."}


@router.get("/sources")
async def sources(request: Request):
    await identity(request)
    return {"sources": knowledge.SOURCES, "notice": "Directorio de sitios oficiales; no es un catálogo de sentencias importadas."}


@router.get("/documents")
async def documents(request: Request, offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100),
                    court: str | None = None, year: int | None = None, document_type: str | None = None):
    uid, token = await identity(request)
    return await knowledge.list_legal_documents(uid, token, offset=offset, limit=limit,
                                                filters={"court": court, "year": year, "document_type": document_type})


@router.post("/search")
async def search(payload: Search, request: Request):
    uid, token = await identity(request)
    limitador.verificar(request, "citas", user_id=uid)
    return await knowledge.search(uid, token, payload.model_dump())


@router.post("/index/{document_id}")
async def index(document_id: str, request: Request):
    uid, token = await identity(request)
    limitador.verificar(request, "redactar", user_id=uid)
    return await knowledge.index_document(uid, token, document_id)


@router.post("/reindex")
async def reindex(payload: Reindex, request: Request):
    uid, token = await identity(request)
    limitador.verificar(request, "redactar", user_id=uid)
    return await knowledge.reindex(uid, token, payload.offset, payload.limit)


@router.post("/import", status_code=201)
async def import_source(payload: ImportSource, request: Request):
    uid, token = await identity(request)
    limitador.verificar(request, "redactar", user_id=uid)
    return await knowledge.import_source(uid, token, payload.model_dump())


@router.post("/crawl")
async def crawl(payload: Crawl, request: Request):
    uid, token = await identity(request)
    limitador.verificar(request, "redactar", user_id=uid)
    return await knowledge.crawl_sources(uid, token, payload.model_dump())
