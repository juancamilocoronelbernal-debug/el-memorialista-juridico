"""Real PDF/format/crypto work; network and provider boundaries are controlled."""
import io
import json
import secrets
import types
import zipfile
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pypdf import PdfReader, PdfWriter

from app.routers.despacho_rooms_v5 import RoomCreate, LinkCreate, PublicToken
from app.services import despacho_rooms_v5 as r
from app.services import despacho_signing_v5 as signing
from app.services.despacho_export import make_pdf


@pytest.fixture
def config(monkeypatch):
    settings=types.SimpleNamespace(SUPABASE_URL="https://db.example.invalid",SUPABASE_ANON_KEY="anon",SUPABASE_SERVICE_ROLE_KEY="service")
    monkeypatch.setattr(r,"get_settings",lambda:settings)
    return settings


def test_room_permissions_and_duplicate_documents_rejected():
    with pytest.raises(ValueError):
        LinkCreate(label="Cliente",can_view=False,can_download=True,can_upload=False)
    with pytest.raises(ValueError):
        LinkCreate(label="Cliente",can_view=False,can_download=False,can_upload=False)
    doc=str(uuid4())
    with pytest.raises(ValueError):
        RoomCreate(title="Sala",document_ids=[doc,doc])
    with pytest.raises(ValueError):
        RoomCreate(title="Sala\ninyectada",document_ids=[doc])
    assert LinkCreate(label="Aportante",can_view=False,can_upload=True).can_upload


def test_disabled_room_configuration_is_clear(config):
    config.SUPABASE_SERVICE_ROLE_KEY=""
    assert r.available()["configured"] is False
    with pytest.raises(HTTPException) as exc:
        r._ensure()
    assert exc.value.status_code==503


def test_private_object_paths_are_account_bound():
    owner,room,doc=map(str,[uuid4(),uuid4(),uuid4()])
    assert r._path(owner,room,doc)==f"{owner}/{room}/documents/{doc}.pdf"
    assert r._path(owner,room,doc,upload=True)==f"{owner}/{room}/uploads/{doc}.bin"
    with pytest.raises(HTTPException):
        r._path(owner,"../../otro",doc)


def test_pdf_watermark_preserves_pages_and_original_text():
    original=make_pdf("Contrato","Contenido que debe permanecer íntegro.\nSegunda cláusula.")
    marked=r.watermark(original,"Cliente de prueba",str(uuid4()),"2026-10-23 10:00 UTC")
    reader=PdfReader(io.BytesIO(marked))
    assert len(reader.pages)==len(PdfReader(io.BytesIO(original)).pages)
    text="\n".join(p.extract_text() for p in reader.pages)
    assert "Contenido que debe permanecer" in text
    assert "COPIA COMPARTIDA" in text
    assert "Cliente de prueba" in text
    assert marked!=original


def test_upload_validator_checks_real_pdf_txt_and_docx():
    pdf=make_pdf("Prueba","Archivo recibido.")
    assert r.validate_upload("../contrato.pdf",pdf)==("contrato.pdf","application/pdf")
    assert r.validate_upload("aporte.txt","Texto en español.".encode())==("aporte.txt","text/plain")
    buffer=io.BytesIO()
    with zipfile.ZipFile(buffer,"w") as archive:
        archive.writestr("word/document.xml",'<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body/></w:document>')
    assert r.validate_upload("archivo.docx",buffer.getvalue())[1]==r.DOCX


@pytest.mark.parametrize("name,binary",[("fake.pdf",b"not pdf"),("empty.txt",b""),("bad.txt",b"\x00binary"),("program.exe",b"hello"),("fake.docx",b"not zip")])
def test_upload_validator_rejects_mismatched_empty_and_unsupported_files(name,binary):
    with pytest.raises(HTTPException):r.validate_upload(name,binary)


def test_upload_validator_rejects_encrypted_pdf_and_docx_macros():
    writer=PdfWriter();writer.add_blank_page(width=200,height=200);writer.encrypt("secret")
    buffer=io.BytesIO();writer.write(buffer)
    with pytest.raises(HTTPException):r.validate_upload("locked.pdf",buffer.getvalue())
    buffer=io.BytesIO()
    with zipfile.ZipFile(buffer,"w") as archive:
        archive.writestr("word/document.xml","<document/>")
        archive.writestr("word/vbaProject.bin",b"active")
    with pytest.raises(HTTPException):r.validate_upload("macro.docx",buffer.getvalue())


@pytest.mark.asyncio
async def test_foreign_room_response_cannot_be_used(config,monkeypatch):
    monkeypatch.setattr(r,"rpc",AsyncMock(return_value=[{"id":str(uuid4()),"owner_id":str(uuid4())}]))
    with pytest.raises(HTTPException) as exc:await r.owned(str(uuid4()),"jwt",str(uuid4()))
    assert exc.value.status_code==502


@pytest.mark.asyncio
async def test_invalid_bearer_link_is_rejected_before_db(monkeypatch):
    rpc=AsyncMock();monkeypatch.setattr(r,"rpc",rpc)
    with pytest.raises(HTTPException):await r.public_record("bad-token")
    rpc.assert_not_called()


@pytest.mark.asyncio
async def test_view_only_link_cannot_download_pdf(config,monkeypatch):
    monkeypatch.setattr(r,"rpc",AsyncMock(side_effect=HTTPException(403,"Sin permiso")))
    read=AsyncMock();monkeypatch.setattr(r,"_verified",read)
    with pytest.raises(HTTPException) as exc:await r.public_document(secrets.token_urlsafe(32),str(uuid4()),"download",ip="",agent="")
    assert exc.value.status_code==403;read.assert_not_called()


@pytest.mark.asyncio
async def test_revocation_during_pdf_preparation_stops_response(config,monkeypatch):
    owner,room,doc,link=map(str,[uuid4(),uuid4(),uuid4(),uuid4()])
    record={"owner_id":owner,"id":room,"document":{"id":doc,"title":"Prueba","sha256":"a"*64},"link":{"label":"Cliente","id":link}}
    read=AsyncMock(side_effect=[record,HTTPException(404,"Revocado")]);monkeypatch.setattr(r,"public_record",read)
    monkeypatch.setattr(r,"_verified",AsyncMock(return_value=make_pdf("Prueba","Original")))
    with pytest.raises(HTTPException) as exc:await r.public_document(secrets.token_urlsafe(32),doc,"view",ip="",agent="")
    assert exc.value.status_code==404
    assert read.call_args.kwargs["mode"]=="check"


@pytest.mark.asyncio
async def test_upload_permission_precedes_file_parsing(config,monkeypatch):
    monkeypatch.setattr(r,"public_record",AsyncMock(side_effect=HTTPException(403,"Sin permiso")))
    validate=AsyncMock();monkeypatch.setattr(r,"validate_upload",validate)
    with pytest.raises(HTTPException):await r.public_upload(secrets.token_urlsafe(32),str(uuid4()),"x.txt",b"x",ip="")
    validate.assert_not_called()


@pytest.mark.asyncio
async def test_retried_received_upload_never_writes_another_binary(config,monkeypatch):
    owner,room,upload=map(str,[uuid4(),uuid4(),uuid4()])
    monkeypatch.setattr(r,"public_record",AsyncMock(return_value={"owner_id":owner,"id":room}))
    monkeypatch.setattr(r,"rpc",AsyncMock(return_value={"id":upload,"filename":"x.txt","status":"received"}))
    put=AsyncMock();monkeypatch.setattr(r,"_put",put)
    result=await r.public_upload(secrets.token_urlsafe(32),str(uuid4()),"x.txt",b"text",ip="")
    assert result["received"] and result["idempotent"];put.assert_not_called()


@pytest.mark.asyncio
async def test_uncertain_upload_commit_keeps_original_for_idempotent_retry(config,monkeypatch):
    owner,room,upload=map(str,[uuid4(),uuid4(),uuid4()])
    monkeypatch.setattr(r,"public_record",AsyncMock(return_value={"owner_id":owner,"id":room}))
    monkeypatch.setattr(r,"rpc",AsyncMock(side_effect=[{"id":upload,"filename":"x.txt","status":"pending"},HTTPException(503,"Timeout")]))
    put=AsyncMock();monkeypatch.setattr(r,"_put",put)
    storage=AsyncMock();monkeypatch.setattr(r,"_storage",storage)
    with pytest.raises(HTTPException) as exc:await r.public_upload(secrets.token_urlsafe(32),str(uuid4()),"x.txt",b"text",ip="")
    assert exc.value.status_code==502;assert put.await_count==1;storage.assert_not_called()


@pytest.mark.asyncio
async def test_room_export_uses_user_jwt_and_rejects_foreign_rows(config,monkeypatch):
    owner=str(uuid4());call=AsyncMock(return_value=[]);monkeypatch.setattr(r.store,"db_request",call)
    assert (await r.export_owner(owner,"user-jwt"))["rooms"]==[]
    assert call.call_args.args[2]=="user-jwt";assert call.call_args.kwargs["service"] is False
    call.return_value=[{"owner_id":str(uuid4())}]
    with pytest.raises(HTTPException):await r.export_owner(owner,"user-jwt")


@pytest.mark.asyncio
async def test_imported_upload_is_recovered_without_duplicate_document(config,monkeypatch):
    owner,room,upload,item=map(str,[uuid4(),uuid4(),uuid4(),uuid4()])
    monkeypatch.setattr(r,"owned",AsyncMock(return_value={"id":room,"owner_id":owner}))
    monkeypatch.setattr(r,"rpc",AsyncMock(return_value={"status":"imported","item_id":item}))
    record={"id":item,"data":{"room_upload_id":upload}}
    monkeypatch.setattr(r.store,"fetch_item",AsyncMock(return_value=record))
    put=AsyncMock();monkeypatch.setattr(r.store,"upload_bytes",put)
    create=AsyncMock();monkeypatch.setattr(r.store,"create_item",create)
    assert (await r.import_upload(owner,"jwt",room,upload))["idempotent"]
    put.assert_not_called();create.assert_not_called()


@pytest.mark.asyncio
async def test_pending_upload_is_not_downloadable(config,monkeypatch):
    owner,room,upload=map(str,[uuid4(),uuid4(),uuid4()])
    monkeypatch.setattr(r,"owned",AsyncMock(return_value={"uploads":[{"id":upload,"status":"pending"}]}))
    with pytest.raises(HTTPException) as exc:await r.private_upload(owner,"jwt",room,upload)
    assert exc.value.status_code==409


@pytest.mark.asyncio
async def test_room_storage_purge_targets_only_product_bucket(config,monkeypatch):
    purge=AsyncMock();monkeypatch.setattr(signing,"purge_bucket_owner",purge)
    owner=str(uuid4());await r.purge_owner_storage(owner)
    purge.assert_awaited_once_with(owner,"despacho-salas-v5")
