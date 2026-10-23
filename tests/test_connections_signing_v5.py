"""Provider calls are controlled; PDF bytes, crypto and validation are real."""
import hashlib
import io
import json
import logging
import secrets
import types
from email.message import EmailMessage
from unittest.mock import AsyncMock
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

import httpx
import pytest
from cryptography.fernet import Fernet
from fastapi import HTTPException
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DictionaryObject, NameObject, TextStringObject

from app.services import despacho_connections as c
from app.services import despacho_delivery as delivery
from app.services import despacho_signing_v5 as s
from app.services.despacho_export import make_pdf
from app.routers.despacho_signing_v5 import EnvelopeCreate, Acceptance
from app.routers.despacho_connections import OAuthAccessLogFilter


@pytest.fixture
def settings(monkeypatch):
    config = types.SimpleNamespace(DESPACHO_CONNECTIONS_ENABLED=True,
        DESPACHO_TOKEN_ENCRYPTION_KEY=Fernet.generate_key().decode(), GOOGLE_OAUTH_CLIENT_ID="google-id",
        GOOGLE_OAUTH_CLIENT_SECRET="google-secret", MICROSOFT_OAUTH_CLIENT_ID="microsoft-id",
        MICROSOFT_OAUTH_CLIENT_SECRET="microsoft-secret", MICROSOFT_OAUTH_TENANT="common",
        SUPABASE_SERVICE_ROLE_KEY="service-secret", SUPABASE_ANON_KEY="anon-key", SUPABASE_URL="https://db.example.invalid",
        DESPACHO_SIGNING_ENABLED=True, DESPACHO_SIGNING_OTP_SECRET=secrets.token_hex(32),
        SMTP_HOST="smtp.example.invalid", SMTP_FROM_EMAIL="notices@example.invalid", SMTP_PORT=587,
        SMTP_TLS_MODE="starttls", SMTP_USERNAME="smtp-user", SMTP_PASSWORD="smtp-password")
    for module in (c, delivery, s):
        monkeypatch.setattr(module, "get_settings", lambda: config)
    return config


def test_tokens_encrypted_and_wrong_key_fails(settings):
    value = {"access_token": "private-access", "refresh_token": "private-refresh"}
    encrypted = c.encrypt(value)
    assert "private" not in encrypted
    assert c.decrypt(encrypted) == value
    settings.DESPACHO_TOKEN_ENCRYPTION_KEY = Fernet.generate_key().decode()
    with pytest.raises(HTTPException) as error:
        c.decrypt(encrypted)
    assert error.value.status_code == 409


def test_oauth_callback_query_is_removed_from_uvicorn_access_logs():
    record = logging.LogRecord("uvicorn.access", logging.INFO, "", 0, '%s - "%s %s HTTP/%s" %d',
        ("client", "GET", "/oauth/despacho/google_drive?code=private-code&state=private-state", "1.1", 303), None)
    assert OAuthAccessLogFilter().filter(record)
    message = record.getMessage()
    assert "/oauth/despacho/google_drive" in message
    assert "private-code" not in message and "private-state" not in message and "?" not in message


@pytest.mark.asyncio
async def test_account_connection_cleanup_is_owner_scoped_and_never_calls_provider(settings, monkeypatch):
    owner, cid = str(uuid4()), str(uuid4())
    calls = AsyncMock(side_effect=[[{"id": cid, "owner_id": owner, "provider": "google_drive"}], [], [], [], []])
    monkeypatch.setattr(c, "admin", calls)
    network = AsyncMock(); monkeypatch.setattr(c, "_json", network)
    result = await c.cleanup_owner_connections(owner)
    assert result["disconnected"] == 1
    assert result["warnings"]
    for call in calls.call_args_list:
        assert call.kwargs["params"]["owner_id"] == "eq." + owner
    network.assert_not_called()


@pytest.mark.asyncio
async def test_connection_and_signing_exports_use_user_token(settings, monkeypatch):
    owner = str(uuid4())
    request = AsyncMock(return_value=[]); monkeypatch.setattr(c.store, "db_request", request)
    assert (await c.export_owner(owner, "user-jwt"))["connections"] == []
    assert request.call_args.args[2] == "user-jwt"
    assert not request.call_args.kwargs.get("service")
    assert (await s.export_owner(owner, "user-jwt"))["envelopes"] == []
    assert request.call_args.args[2] == "user-jwt"
    assert request.call_args.kwargs["service"] is False


@pytest.mark.asyncio
async def test_uncertain_external_import_keeps_a_committed_original(settings, monkeypatch):
    owner = str(uuid4())
    monkeypatch.setattr(c, "_existing", AsyncMock(return_value=None))
    monkeypatch.setattr(c.store, "upload_bytes", AsyncMock())
    monkeypatch.setattr(c.store, "create_item", AsyncMock(side_effect=HTTPException(503, "Timeout")))
    recovered = {"id": str(uuid4()), "data": {"external_key": "same-source"}}
    monkeypatch.setattr(c.store, "fetch_item", AsyncMock(return_value=recovered))
    remove = AsyncMock(); monkeypatch.setattr(c.store, "remove_storage_paths", remove)
    result = await c._save_import(owner, "jwt", "archivo.txt", b"text", {"text": "text", "mime": "text/plain"}, {}, None, "same-source")
    assert result == recovered
    remove.assert_not_called()


def test_connections_disabled_do_not_claim_ready(settings):
    settings.DESPACHO_CONNECTIONS_ENABLED = False
    assert all(not p["configured"] for p in c.capabilities())
    settings.DESPACHO_CONNECTIONS_ENABLED = True
    settings.MICROSOFT_OAUTH_TENANT = "evil.invalid/path"
    with pytest.raises(HTTPException):
        c.credentials("microsoft_onedrive")


@pytest.mark.asyncio
async def test_oauth_pkce_state_bound_to_owner_cookie_and_redirect(settings, monkeypatch):
    owner = str(uuid4())
    rpc = AsyncMock(return_value={"created": True}); monkeypatch.setattr(c, "rpc", rpc)
    result, cookie = await c.begin(owner, "google_drive", "https://memorialista.example")
    params = parse_qs(urlsplit(result["authorization_url"]).query)
    data = rpc.call_args.args[1]
    assert data["p_owner"] == owner
    assert data["p_binding_hash"] == hashlib.sha256(cookie.encode()).hexdigest()
    assert data["p_state_hash"] == hashlib.sha256(params["state"][0].encode()).hexdigest()
    secret = c.decrypt(data["p_secret"])
    assert secret["redirect_uri"] == "https://memorialista.example/oauth/despacho/google_drive"
    assert params["code_challenge_method"] == ["S256"]
    assert "google-secret" not in result["authorization_url"]
    assert "refresh_token" not in result["authorization_url"]
    assert "write" not in params["scope"][0]


@pytest.mark.asyncio
async def test_oauth_replay_or_wrong_binding_rejected_before_exchange(settings, monkeypatch):
    rpc = AsyncMock(side_effect=HTTPException(400, "Consumido")); monkeypatch.setattr(c, "rpc", rpc)
    network = AsyncMock(); monkeypatch.setattr(c, "_json", network)
    with pytest.raises(HTTPException):
        await c.complete(str(uuid4()), "google_drive", secrets.token_urlsafe(32), secrets.token_urlsafe(32), "code")
    network.assert_not_called()


@pytest.mark.asyncio
async def test_oauth_complete_never_returns_credentials(settings, monkeypatch):
    owner, connection = str(uuid4()), str(uuid4())
    secret = c.encrypt({"verifier": "a" * 64, "redirect_uri": "https://memorialista.example/oauth/despacho/google_drive"})
    rpc = AsyncMock(side_effect=[{"secret": secret}, {"id": connection, "owner_id": owner, "provider": "google_drive", "label": "persona@example.invalid", "scopes": []}])
    monkeypatch.setattr(c, "rpc", rpc)
    network = AsyncMock(side_effect=[{"access_token": "private-access", "refresh_token": "private-refresh", "expires_in": 3600},
        {"email": "persona@example.invalid", "email_verified": True}]); monkeypatch.setattr(c, "_json", network)
    result = await c.complete(owner, "google_drive", secrets.token_urlsafe(32), secrets.token_urlsafe(32), "opaque-code")
    assert result["id"] == connection
    assert "private" not in json.dumps(result)
    assert "client_secret" not in json.dumps(result)
    stored = c.decrypt(rpc.call_args.args[1]["p_secret"])
    assert stored["refresh_token"] == "private-refresh"
    assert network.call_args_list[0].kwargs["data"]["code_verifier"] == "a" * 64


def test_pagination_cursor_cannot_cross_accounts_or_inject_urls(settings):
    cursor = c._next_cursor("connection-a", "microsoft_onedrive", "https://graph.microsoft.com/v1.0/me/drive/root/children?$skiptoken=123")
    with pytest.raises(HTTPException):
        c._read_cursor(cursor, "connection-b", "microsoft_onedrive")
    hostile = c._next_cursor("a", "microsoft_onedrive", "http://127.0.0.1/internal")
    with pytest.raises(HTTPException):
        c._read_cursor(hostile, "a", "microsoft_onedrive")
    assert "skiptoken" in c._read_cursor(cursor, "connection-a", "microsoft_onedrive")


@pytest.mark.parametrize("value", ["https://attacker.invalid/file", "https://sharepoint.com.attacker.invalid/x", "http://tenant.sharepoint.com/x", "https://user:secret@tenant.sharepoint.com/x", "https://tenant.sharepoint.com:444/x", "https://127.0.0.1/x"])
def test_download_redirects_reject_foreign_private_and_credentials(value):
    with pytest.raises(HTTPException):
        c._download_host(value)


@pytest.mark.asyncio
async def test_microsoft_download_does_not_forward_oauth_token_to_signed_url(monkeypatch):
    calls = []
    class Stream:
        def __init__(self, response): self.response = response
        async def __aenter__(self): return self.response
        async def __aexit__(self, *args): pass
    class Client:
        def __init__(self, *a, **kw): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        def stream(self, method, url, **kwargs):
            calls.append((str(url), kwargs))
            return Stream(httpx.Response(302, headers={"location": "https://tenant.sharepoint.com/download?private=opaque"}) if len(calls) == 1 else httpx.Response(200, content=b"original"))
    monkeypatch.setattr(c.httpx, "AsyncClient", Client)
    monkeypatch.setattr(c, "resolve_public", AsyncMock(return_value="203.0.113.3"))
    result = await c._binary("https://graph.microsoft.com/v1.0/me/drive/items/ID/content", "oauth-secret", microsoft_redirect=True)
    assert result == b"original"
    assert calls[0][1]["headers"]["Authorization"] == "Bearer oauth-secret"
    assert "Authorization" not in calls[1][1]["headers"]
    assert calls[1][1]["extensions"]["sni_hostname"] == "tenant.sharepoint.com"


@pytest.mark.asyncio
async def test_connection_cannot_read_foreign_owner(settings, monkeypatch):
    monkeypatch.setattr(c, "admin", AsyncMock(return_value=[{"id": str(uuid4()), "owner_id": str(uuid4())}]))
    with pytest.raises(HTTPException) as error:
        await c.owned_connection(str(uuid4()), str(uuid4()), secret=True)
    assert error.value.status_code == 502


@pytest.mark.asyncio
async def test_refresh_lease_prevents_duplicate_exchange(settings, monkeypatch):
    owner, cid = str(uuid4()), str(uuid4())
    row = {"id": cid, "owner_id": owner, "provider": "google_drive", "secret": c.encrypt({"access_token": "old", "refresh_token": "refresh", "expires_at": 0})}
    monkeypatch.setattr(c, "owned_connection", AsyncMock(return_value=row))
    monkeypatch.setattr(c, "rpc", AsyncMock(return_value={"acquired": False}))
    network = AsyncMock(); monkeypatch.setattr(c, "_json", network)
    with pytest.raises(HTTPException) as error:
        await c._access(owner, cid)
    assert error.value.status_code == 409
    network.assert_not_called()


def test_eml_extracts_body_and_actual_attachment_without_executing_html():
    message = EmailMessage()
    message["Subject"] = "Contrato de prueba"
    message["From"] = "persona@example.invalid"
    message["To"] = "abogado@example.invalid"
    message.set_content("Contenido del mensaje.")
    message.add_alternative("<p>Contenido</p><script>no ejecutar</script>", subtype="html")
    message.add_attachment(b"Original adjunto", maintype="text", subtype="plain", filename="prueba.txt")
    parsed, attachments = c.parse_email(message.as_bytes())
    assert "Contenido del mensaje" in parsed["text"]
    assert attachments == [("prueba.txt", b"Original adjunto")]
    assert "no ejecutar" not in parsed["text"]


@pytest.mark.asyncio
async def test_import_checks_matter_ownership_before_reading_connection(settings, monkeypatch):
    monkeypatch.setattr(c.store, "fetch_item", AsyncMock(side_effect=HTTPException(404, "Ajeno")))
    access = AsyncMock(); monkeypatch.setattr(c, "_access", access)
    with pytest.raises(HTTPException):
        await c.import_resource(str(uuid4()), "jwt", str(uuid4()), "resource", matter_id=str(uuid4()))
    access.assert_not_called()


def test_smtp_rejects_header_injection_and_unencrypted_transport(settings):
    with pytest.raises(HTTPException):
        delivery.valid_email("persona@example.invalid\r\nBcc:otra@example.invalid")
    settings.SMTP_TLS_MODE = "none"
    with pytest.raises(HTTPException) as error:
        delivery._send("persona@example.invalid", "Prueba", "Cuerpo")
    assert error.value.status_code == 503


def test_smtp_uses_tls_and_reports_only_server_acceptance(settings, monkeypatch):
    events = []
    class SMTP:
        def __init__(self, *args, **kwargs): events.append("connect")
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def ehlo(self): events.append("ehlo")
        def starttls(self, **kwargs): events.append("tls")
        def login(self, *args): events.append("login")
        def send_message(self, message): events.append("send"); return {}
    monkeypatch.setattr(delivery.smtplib, "SMTP", SMTP)
    result = delivery._send("persona@example.invalid", "Prueba", "Cuerpo")
    assert events.index("tls") < events.index("login") < events.index("send")
    assert result["accepted_by_smtp"]
    assert "no confirma" in result["notice"]


def test_signing_validation_rejects_duplicate_docs_and_recipients():
    doc = str(uuid4())
    with pytest.raises(ValueError):
        EnvelopeCreate(title="Contrato", document_ids=[doc, doc], signers=[{"name": "Persona", "email": "a@example.invalid"}])
    with pytest.raises(ValueError):
        EnvelopeCreate(title="Contrato", document_ids=[doc], signers=[{"name": "Persona", "email": "a@example.invalid"}, {"name": "Otra", "email": "A@example.invalid"}])
    with pytest.raises(ValueError):
        Acceptance(token="x" * 43, otp="1", name="Persona", consent=True, manifest_hash="a" * 64)


def test_otp_is_bound_to_link_and_secret(settings):
    first, second = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    assert s._otp_hash(first, "123456") != s._otp_hash(second, "123456")
    assert s._otp_hash(first, "123456") != hashlib.sha256(b"123456").hexdigest()
    assert len(s._otp_hash(first, "123456")) == 64


def test_multidoc_pdf_preserves_order_hashes_and_full_pages():
    originals = []
    for title, body in [("Primero", "Texto uno."), ("Segundo", "Texto dos.")]:
        originals.append(({"id": str(uuid4()), "title": title, "version": 2, "data": {"text": body}}, make_pdf(title, body)))
    binary, docs = s._combine(originals)
    reader = PdfReader(io.BytesIO(binary))
    assert len(reader.pages) == 2
    assert "Texto uno" in reader.pages[0].extract_text()
    assert "Texto dos" in reader.pages[1].extract_text()
    assert docs[1]["first_page"] == docs[1]["last_page"] == 2
    assert docs[0]["sha256"] == hashlib.sha256(originals[0][1]).hexdigest()


def test_pdf_active_scripts_are_rejected_before_signing():
    writer = PdfWriter(); writer.add_blank_page(width=300, height=300)
    writer.add_js("app.alert('unsafe')")
    stream = io.BytesIO(); writer.write(stream)
    with pytest.raises(HTTPException) as error:
        s._combine([({"id": str(uuid4()), "title": "Activo", "data": {"text": ""}}, stream.getvalue())])
    assert error.value.status_code == 422


@pytest.mark.asyncio
async def test_otp_missing_mail_never_claims_sent(settings, monkeypatch):
    settings.SMTP_HOST = ""
    database = AsyncMock(); monkeypatch.setattr(s, "rpc", database)
    with pytest.raises(HTTPException) as error:
        await s.request_otp(secrets.token_urlsafe(32))
    assert error.value.status_code == 503
    database.assert_not_called()


@pytest.mark.asyncio
async def test_otp_delivery_failure_invalidates_generation_and_does_not_expose_code(settings, monkeypatch):
    recipient = str(uuid4())
    db = AsyncMock(side_effect=[{"recipient_id": recipient, "email": "persona@example.invalid", "title": "Contrato"}, {"recorded": True}])
    monkeypatch.setattr(s, "rpc", db)
    monkeypatch.setattr(s.delivery, "send_email", AsyncMock(side_effect=HTTPException(502, "Sin confirmación")))
    with pytest.raises(HTTPException):
        await s.request_otp(secrets.token_urlsafe(32))
    assert db.call_args.args[0] == "despacho_signing_otp_delivery"
    assert db.call_args.args[1]["p_sent"] is False
    request = db.call_args_list[0].args[1]
    assert len(request["p_otp_hash"]) == 64
    assert "otp" not in request


@pytest.mark.asyncio
async def test_accept_requires_consent_before_rpc(settings, monkeypatch):
    db = AsyncMock(); monkeypatch.setattr(s, "rpc", db)
    with pytest.raises(HTTPException):
        await s.accept(secrets.token_urlsafe(32), "123456", "Persona", False, "a" * 64, ip="192.0.2.1", agent="QA")
    db.assert_not_called()


@pytest.mark.asyncio
async def test_original_hash_mismatch_blocks_download(monkeypatch):
    monkeypatch.setattr(s, "_storage", AsyncMock(return_value=b"altered"))
    with pytest.raises(HTTPException) as error:
        await s._verified_binary({"storage_path": "path", "bundle_hash": hashlib.sha256(b"original").hexdigest()})
    assert error.value.status_code == 409


@pytest.mark.asyncio
async def test_create_does_not_delete_pdf_if_database_commit_was_uncertain(settings, monkeypatch):
    owner, did = str(uuid4()), str(uuid4())
    item = {"id": did, "title": "Contrato", "version": 1, "data": {"text": "Cláusula completa."}}
    monkeypatch.setattr(s.store, "fetch_item", AsyncMock(return_value=item))
    storage = AsyncMock(); monkeypatch.setattr(s, "_storage", storage)
    monkeypatch.setattr(s, "rpc", AsyncMock(side_effect=HTTPException(502, "Timeout después de guardar")))
    monkeypatch.setattr(s, "owned", AsyncMock(side_effect=HTTPException(503, "Lectura no disponible")))
    with pytest.raises(HTTPException):
        await s.create(owner, "jwt", "Contrato", [did], [{"name": "Persona", "email": "persona@example.invalid"}], "parallel", 7)
    assert [call.args[0] for call in storage.call_args_list] == ["POST"]


def test_evidence_pdf_has_each_signer_and_original_then_receipt():
    original = make_pdf("Contrato", "Texto completo que se aceptó.")
    record = {"id": str(uuid4()), "title": "Contrato", "bundle_hash": s.digest(original), "manifest_hash": "b" * 64,
        "completed_at": "2026-10-23T12:00:00Z", "documents": [{"title": "Contrato", "first_page": 1, "last_page": 1, "sha256": s.digest(original)}],
        "recipients": [{"id": str(uuid4()), "email": "persona@example.invalid", "signed_name": "Nombre Declarado", "signed_at": "2026-10-23T12:00:00Z",
            "signer_ip": "192.0.2.1", "signer_agent": "QA", "consent_text": s.CONSENT}], "audit": [{"at": "2026-10-23T12:00:00Z", "event": "signed"}]}
    binary = s._receipt_pdf(record, original)
    reader = PdfReader(io.BytesIO(binary))
    assert "Texto completo" in reader.pages[0].extract_text()
    text = "\n".join(page.extract_text() for page in reader.pages)
    assert "Nombre Declarado" in text and "persona@example.invalid" in text
    assert "No incluye verificación documental" in text
    assert s.digest(binary) != record["bundle_hash"]
