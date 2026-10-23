from typing import Literal

import anyio
from fastapi import APIRouter, Request
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field

from app.services.despacho_export import filename, make_docx, make_pdf
from app.services.limites import verificar_acceso

router = APIRouter(prefix="/api/despacho", tags=["Exportación del despacho"])


class DocumentExport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field("Documento", min_length=1, max_length=240)
    text: str = Field(..., min_length=1, max_length=300_000)
    format: Literal["docx", "pdf"]


@router.post("/export/document")
async def export_document(payload: DocumentExport, request: Request):
    await verificar_acceso(request)
    builder = make_docx if payload.format == "docx" else make_pdf
    data = await anyio.to_thread.run_sync(builder, payload.title, payload.text)
    media = "application/pdf" if payload.format == "pdf" else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    return Response(data, media_type=media, headers={"Content-Disposition": f'attachment; filename="{filename(payload.title, payload.format)}"', "Cache-Control": "private, no-store"})
