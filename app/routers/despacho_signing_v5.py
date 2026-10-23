"""Firma multiparte con verificación por correo; compatible con rutas V4."""
from __future__ import annotations

import re
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Request
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.routers.despacho_data import identity
from app.routers.despacho_signatures import _safe_origin, _rate_limit
from app.services import despacho_delivery as delivery
from app.services import despacho_signing_v5 as signing
from app.services.despacho_export import filename
from app.services.limites import ip_cliente

router = APIRouter(prefix="/api/despacho/signing", tags=["Firma con correo verificado"])
public_router = APIRouter(prefix="/api/firmas-v5", tags=["Destinatario de firma verificada"])


class Signer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=2, max_length=160)
    email: str = Field(min_length=3, max_length=254)

    @field_validator("name")
    @classmethod
    def name_valid(cls, value):
        if len(value.strip()) < 2 or re.search(r"[\x00-\x1f\x7f]", value):
            raise ValueError("Escribe un nombre legible.")
        return value.strip()

    @field_validator("email")
    @classmethod
    def email_valid(cls, value):
        # Pydantic validation should return a 422, not leak provider details.
        from fastapi import HTTPException
        try:
            return delivery.valid_email(value)
        except HTTPException:
            raise ValueError("Revisa el correo del destinatario.") from None


class EnvelopeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=240)
    document_ids: list[UUID] = Field(min_length=1, max_length=10)
    signers: list[Signer] = Field(min_length=1, max_length=10)
    signing_order: Literal["parallel", "sequential"] = "parallel"
    expires_days: int = Field(7, ge=1, le=30)

    @field_validator("title")
    @classmethod
    def title_valid(cls, value):
        if not value.strip() or re.search(r"[\x00-\x1f\x7f]", value):
            raise ValueError("Escribe un título legible.")
        return value.strip()

    @model_validator(mode="after")
    def unique_values(self):
        if len(set(self.document_ids)) != len(self.document_ids):
            raise ValueError("No repitas documentos dentro de la solicitud.")
        if len({s.email for s in self.signers}) != len(self.signers):
            raise ValueError("Cada destinatario debe tener un correo diferente.")
        return self


class Invite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    recipient_ids: list[UUID] = Field(min_length=1, max_length=10)


class LinkToken(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str = Field(pattern=r"^[A-Za-z0-9_-]{43}$")


class Acceptance(LinkToken):
    otp: str = Field(pattern=r"^\d{6}$")
    name: str = Field(min_length=2, max_length=160)
    consent: bool
    manifest_hash: str = Field(pattern=r"^[a-f0-9]{64}$")


def pdf_response(title: str, binary: bytes) -> Response:
    return Response(binary, media_type="application/pdf", headers={
        "Content-Disposition": 'attachment; filename="' + filename(title, "pdf") + '"',
        "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})


@router.get("")
async def list_envelopes(request: Request):
    owner, token = await identity(request)
    return await signing.list_envelopes(owner, token)


@router.post("", status_code=201)
async def create(payload: EnvelopeCreate, request: Request):
    owner, token = await identity(request)
    _safe_origin(request)
    return await signing.create(owner, token, payload.title, [str(x) for x in payload.document_ids],
        [x.model_dump() for x in payload.signers], payload.signing_order, payload.expires_days)


@router.get("/{envelope_id}")
async def get(envelope_id: UUID, request: Request):
    owner, token = await identity(request)
    return signing.public_envelope(await signing.owned(owner, token, str(envelope_id)))


@router.post("/{envelope_id}/invite")
async def invite(envelope_id: UUID, payload: Invite, request: Request):
    owner, token = await identity(request)
    return await signing.invite(owner, token, str(envelope_id), [str(x) for x in payload.recipient_ids], _safe_origin(request))


@router.post("/{envelope_id}/recipients/{recipient_id}/link")
async def link(envelope_id: UUID, recipient_id: UUID, request: Request):
    owner, token = await identity(request)
    return await signing.link(owner, token, str(envelope_id), str(recipient_id), _safe_origin(request))


@router.post("/{envelope_id}/cancel")
async def cancel(envelope_id: UUID, request: Request):
    owner, token = await identity(request)
    return await signing.cancel(owner, token, str(envelope_id))


@router.get("/{envelope_id}/document")
async def document(envelope_id: UUID, request: Request):
    owner, token = await identity(request)
    return pdf_response(*(await signing.private_document(owner, token, str(envelope_id))))


@router.get("/{envelope_id}/receipt")
async def receipt(envelope_id: UUID, request: Request):
    owner, token = await identity(request)
    title, binary = await signing.receipt(owner, token, str(envelope_id))
    return pdf_response(title + "-constancia", binary)


@public_router.post("/view")
async def view(payload: LinkToken, request: Request):
    _rate_limit(request)
    return await signing.public_view(payload.token, ip=ip_cliente(request), agent=request.headers.get("user-agent", ""))


@public_router.post("/document")
async def public_document(payload: LinkToken, request: Request):
    _rate_limit(request)
    return pdf_response(*(await signing.public_document(payload.token)))


@public_router.post("/otp")
async def otp(payload: LinkToken, request: Request):
    _rate_limit(request, signing=True)
    return await signing.request_otp(payload.token)


@public_router.post("/accept")
async def accept(payload: Acceptance, request: Request):
    _rate_limit(request, signing=True)
    return await signing.accept(payload.token, payload.otp, payload.name, payload.consent, payload.manifest_hash,
        ip=ip_cliente(request), agent=request.headers.get("user-agent", ""))
