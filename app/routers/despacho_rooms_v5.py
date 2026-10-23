"""APIs privadas y acceso por enlace para salas de clientes."""
from __future__ import annotations

import re
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.routers.despacho_data import identity
from app.routers.despacho_signatures import _safe_origin, _rate_limit
from app.services import despacho_rooms_v5 as rooms
from app.services.despacho_export import filename
from app.services.limites import ip_cliente

router = APIRouter(prefix="/api/despacho/rooms", tags=["Salas de clientes"])
public_router = APIRouter(prefix="/api/salas-v5", tags=["Acceso a sala compartida"])


class RoomCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=240)
    description: str = Field("", max_length=4000)
    document_ids: list[UUID] = Field(min_length=1, max_length=20)
    matter_id: UUID | None = None
    expires_days: int = Field(30, ge=1, le=90)

    @field_validator("title")
    @classmethod
    def readable(cls, value):
        if not value.strip() or re.search(r"[\x00-\x1f\x7f]", value):
            raise ValueError("Escribe un título legible.")
        return value.strip()

    @field_validator("document_ids")
    @classmethod
    def unique(cls, value):
        if len(value) != len(set(value)):
            raise ValueError("Selecciona cada documento una sola vez.")
        return value


class LinkCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: str = Field(min_length=1, max_length=120)
    can_view: bool = True
    can_download: bool = False
    can_upload: bool = False
    expires_days: int = Field(7, ge=1, le=90)

    @field_validator("label")
    @classmethod
    def readable(cls, value):
        if not value.strip() or re.search(r"[\x00-\x1f\x7f]", value):
            raise ValueError("Escribe un nombre legible para el enlace.")
        return value.strip()

    @model_validator(mode="after")
    def permissions(self):
        if not (self.can_view or self.can_upload) or (self.can_download and not self.can_view):
            raise ValueError("Permite ver o aportar; descargar también requiere ver.")
        return self


class PublicToken(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str = Field(pattern=r"^[A-Za-z0-9_-]{43}$")


class PublicDocument(PublicToken):
    document_id: UUID
    mode: Literal["view", "download"] = "view"


def pdf(title: str, data: bytes, *, inline=False) -> Response:
    return Response(data, media_type="application/pdf", headers={"Cache-Control": "private, no-store",
        "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer",
        "Content-Disposition": ("inline" if inline else "attachment") + '; filename="' + filename(title, "pdf") + '"'})


@router.get("")
async def list_rooms(request: Request, offset: int = Query(0, ge=0, le=100000), limit: int = Query(50, ge=1, le=100)):
    owner, token = await identity(request)
    return await rooms.list_rooms(owner, token, offset=offset, limit=limit)


@router.post("", status_code=201)
async def create(payload: RoomCreate, request: Request):
    owner, token = await identity(request)
    _safe_origin(request)
    return await rooms.create(owner, token, payload.title, payload.description, [str(x) for x in payload.document_ids],
        str(payload.matter_id) if payload.matter_id else None, payload.expires_days)


@router.get("/{room_id}")
async def get(room_id: UUID, request: Request):
    owner, token = await identity(request)
    return rooms.public_room(await rooms.owned(owner, token, str(room_id)))


@router.post("/{room_id}/links", status_code=201)
async def link(room_id: UUID, payload: LinkCreate, request: Request):
    owner, token = await identity(request)
    return await rooms.create_link(owner, token, str(room_id), payload.label, payload.can_view, payload.can_download,
        payload.can_upload, payload.expires_days, _safe_origin(request))


@router.delete("/{room_id}/links/{link_id}")
async def revoke_link(room_id: UUID, link_id: UUID, request: Request):
    owner, token = await identity(request)
    return await rooms.revoke(owner, token, str(room_id), str(link_id))


@router.post("/{room_id}/revoke")
async def revoke_room(room_id: UUID, request: Request):
    owner, token = await identity(request)
    return await rooms.revoke(owner, token, str(room_id))


@router.get("/{room_id}/documents/{document_id}")
async def document(room_id: UUID, document_id: UUID, request: Request):
    owner, token = await identity(request)
    return pdf(*(await rooms.private_document(owner, token, str(room_id), str(document_id))))


@router.get("/{room_id}/uploads/{upload_id}")
async def original(room_id: UUID, upload_id: UUID, request: Request):
    owner, token = await identity(request)
    name, mime, binary = await rooms.private_upload(owner, token, str(room_id), str(upload_id))
    extension = name.rsplit(".", 1)[-1].lower()
    return Response(binary, media_type="application/octet-stream", headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff",
        "Content-Disposition": 'attachment; filename="' + filename(name.rsplit(".", 1)[0], extension) + '"'})


@router.post("/{room_id}/uploads/{upload_id}/import")
async def import_upload(room_id: UUID, upload_id: UUID, request: Request):
    owner, token = await identity(request)
    return await rooms.import_upload(owner, token, str(room_id), str(upload_id))


@router.post("/{room_id}/uploads/{upload_id}/reject")
async def reject_upload(room_id: UUID, upload_id: UUID, request: Request):
    owner, token = await identity(request)
    return await rooms.reject_upload(owner, token, str(room_id), str(upload_id))


@public_router.post("/view")
async def public_view(payload: PublicToken, request: Request):
    _rate_limit(request)
    return await rooms.public_view(payload.token, ip=ip_cliente(request), agent=request.headers.get("user-agent", ""))


@public_router.post("/document")
async def public_document(payload: PublicDocument, request: Request):
    _rate_limit(request)
    return pdf(*(await rooms.public_document(payload.token, str(payload.document_id), payload.mode,
        ip=ip_cliente(request), agent=request.headers.get("user-agent", ""))), inline=payload.mode == "view")


@public_router.post("/upload", status_code=201)
async def public_upload(request: Request, token: str = Form(..., min_length=43, max_length=43),
                        request_id: UUID = Form(...), file: UploadFile = File(...)):
    _rate_limit(request, signing=True)
    # Check the link before reading, validating or storing a potentially large file.
    await rooms.public_record(token, mode="upload", ip=ip_cliente(request))
    try:
        binary = await file.read(rooms.MAX_FILE_BYTES + 1)
        if len(binary) > rooms.MAX_FILE_BYTES:
            raise HTTPException(413, "Cada aporte admite hasta 10 MB.")
        return await rooms.public_upload(token, str(request_id), file.filename or "", binary, ip=ip_cliente(request))
    finally:
        await file.close()
