"""Consultas privadas, investigación y extracción del despacho."""
from __future__ import annotations

import asyncio
import contextlib
from typing import Literal
from uuid import UUID

import anyio
from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
import json
import logging
from pydantic import BaseModel, Field, field_validator, model_validator

from app.services import despacho_ai
from app.services import despacho_stream
from app.services.limites import limitador, verificar_acceso
from app.services.sesiones import token_bearer

router = APIRouter(prefix="/api/despacho", tags=["Asistente profesional"])


class HistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=despacho_ai.MAX_REPLY_CHARS)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=80_000)
    history: list[HistoryMessage] = Field(default_factory=list, max_length=24)
    mode: Literal["general", "research", "analyze", "draft", "timeline"] = "general"
    document_ids: list[UUID] = Field(default_factory=list, max_length=20)
    matter_id: UUID | None = None
    playbook_id: UUID | None = None
    conversation_id: str | None = None
    knowledge_scope: Literal["auto", "off", "documents", "legal", "all", "official"] = "auto"
    depth: Literal["auto", "quick", "balanced", "deep"] = "auto"
    selected_fragments: list[dict] = Field(default_factory=list, max_length=50)

    @field_validator("message")
    @classmethod
    def clean_message(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Escribe una consulta.")
        return value.strip()

    @model_validator(mode="after")
    def validate_total(self):
        if sum(len(message.content) for message in self.history) > 240_000:
            raise ValueError("El historial es demasiado grande.")
        return self


class TableRequest(BaseModel):
    document_ids: list[UUID] = Field(min_length=1, max_length=10)
    columns: list[str] = Field(min_length=1, max_length=8)
    instruction: str = Field(default="", max_length=6000)

    @field_validator("columns")
    @classmethod
    def validate_columns(cls, columns: list[str]) -> list[str]:
        values = [column.strip() for column in columns]
        if any(not value or len(value) > 160 for value in values):
            raise ValueError("Cada columna requiere entre 1 y 160 caracteres.")
        if len({value.casefold() for value in values}) != len(values):
            raise ValueError("No repitas los nombres de las columnas.")
        return values


async def _identity(request: Request) -> tuple[str, str]:
    user = await verificar_acceso(request)
    return user["id"], token_bearer(request)


async def _while_connected(request: Request, operation):
    """Libera la llamada HTTP al proveedor si el navegador cancela el encargo."""
    task = asyncio.create_task(operation)
    try:
        while not task.done():
            if await request.is_disconnected():
                raise HTTPException(499, "La consulta se canceló antes de recibir la respuesta.")
            await asyncio.wait({task}, timeout=0.3)
        return await task
    finally:
        if not task.done():
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task


@router.post("/chat")
async def chat(req: ChatRequest, request: Request):
    user_id, token = await _identity(request)
    limitador.verificar(request, "redactar", user_id=user_id)
    return await _while_connected(request, despacho_ai.chat(user_id, token, req.model_dump(mode="json")))


@router.post("/chat/stream")
async def chat_stream(req: ChatRequest, request: Request):
    """POST + Bearer, SSE real. Protege sesión y cuota antes de abrir el flujo."""
    user_id, token = await _identity(request)
    limitador.verificar(request, "redactar", user_id=user_id)

    def encode(event: dict) -> str:
        return "event: " + event["event"] + "\ndata: " + json.dumps(
            event["data"], ensure_ascii=False, separators=(",", ":")) + "\n\n"

    async def body():
        queue = asyncio.Queue(maxsize=30)
        async def producer():
            partial = False
            try:
                async for event in despacho_stream.stream_chat(user_id, token, req.model_dump(mode="json")):
                    partial = partial or event["event"] == "delta"
                    await queue.put(event)
            except HTTPException as exc:
                await queue.put({"event": "error", "data": {
                    "message": str(exc.detail), "status": exc.status_code, "partial": partial}})
            except asyncio.CancelledError:
                raise
            except Exception:
                logging.getLogger("memorialista.despacho.stream").exception("Fallo interno del flujo SSE")
                await queue.put({"event": "error", "data": {
                    "message": "No se pudo completar la respuesta; inténtalo de nuevo.",
                    "status": 500, "partial": partial}})
            finally:
                with contextlib.suppress(asyncio.QueueFull):
                    queue.put_nowait(None)

        task = asyncio.create_task(producer())
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=12)
                except asyncio.TimeoutError:
                    if task.done() and queue.empty():
                        break
                    yield ": ping\n\n"
                    continue
                if event is None:
                    break
                yield encode(event)
        finally:
            if not task.done():
                task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

    return StreamingResponse(body(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache, no-transform",
        "X-Accel-Buffering": "no",
        "Pragma": "no-cache",
    })


@router.post("/tables/analyze")
async def analyze_table(req: TableRequest, request: Request):
    user_id, token = await _identity(request)
    # Cada documento representa una llamada: consume la misma cuota de una
    # consulta para que el análisis masivo no evada los límites de gasto.
    for _ in set(req.document_ids):
        limitador.verificar(request, "redactar", user_id=user_id)
    return await _while_connected(request, despacho_ai.analyze_table(user_id, token, req.model_dump(mode="json")))


@router.post("/documents/extract")
async def extract_document(request: Request, file: UploadFile = File(...)):
    user_id, _ = await _identity(request)
    limitador.verificar(request, "citas", user_id=user_id)
    content = await file.read(despacho_ai.MAX_FILE_BYTES + 1)
    await file.close()
    return await anyio.to_thread.run_sync(despacho_ai.extract_document, content, file.filename or "archivo")
