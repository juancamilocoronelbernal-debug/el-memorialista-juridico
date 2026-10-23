"""OCR real local e invariantes de recuperación/monitor; proveedores IA controlados."""
import copy
import hashlib
import io
import json
import math
import time
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest
from fastapi import HTTPException

from app.config import get_settings
from app.services import despacho_ai as ai, despacho_knowledge as knowledge
from app.services import despacho_ocr as ocr, despacho_monitors as monitors, despacho_store as store

OWNER, OTHER, DOC, MATTER = [str(uuid4()) for _ in range(4)]


def document(text="Existe una cláusula arbitral.", **kwargs):
    return {"id": DOC, "owner_id": OWNER, "kind": "document", "version": 1, "title": "Contrato",
            "matter_id": None, "data": {"text": text, "pages": [{"page": 2, "text": text}], "pagination": "pages"}, **kwargs}


@pytest.fixture
def configured(monkeypatch):
    s = get_settings()
    for key, value in {"SUPABASE_URL": "https://unit.supabase.test", "SUPABASE_ANON_KEY": "public-test",
                       "GEMINI_API_KEY": "key-test", "DESPACHO_EMBEDDINGS_ENABLED": True,
                       "DESPACHO_MONITOR_AI_ENABLED": True, "DESPACHO_OCR_ENABLED": True}.items():
        monkeypatch.setattr(s, key, value)
    return s


def test_chunks_keep_physical_pages_and_bounded_overlap():
    value = document("a" * 7000)
    chunks = knowledge.document_chunks(value)
    assert len(chunks) == 4
    assert all(c["page"] == 2 and c["segment"] is None for c in chunks)
    assert all(0 < len(c["content"]) <= 2400 for c in chunks)
    value["data"]["pagination"] = "segments"
    assert all(c["page"] is None and c["segment"] == 2 for c in knowledge.document_chunks(value))


@pytest.mark.parametrize("bad", [[0] * 768, [float("inf")] * 768, [float("nan")] * 768, [True] * 768, [1] * 767])
def test_embeddings_reject_invalid_vectors(bad):
    with pytest.raises(HTTPException):
        knowledge._vector(bad)


def test_embeddings_are_normalized():
    vector = knowledge._vector([3, 4] + [0] * 766)
    assert math.isclose(sum(x*x for x in vector), 1)
    assert vector[:2] == [0.6, 0.8]


@pytest.mark.asyncio
async def test_embedding_request_uses_api_contract_and_hides_secret(configured, monkeypatch):
    original = httpx.AsyncClient
    def handler(request):
        assert request.url.path.endswith(":batchEmbedContents")
        assert request.headers["x-goog-api-key"] == "key-test"
        assert "key-test" not in str(request.url)
        data = json.loads(request.content)["requests"][0]
        assert data["taskType"] == "RETRIEVAL_QUERY" and data["outputDimensionality"] == 768
        return httpx.Response(200, json={"embeddings": [{"values": [1] + [0] * 767}]})
    monkeypatch.setattr(knowledge.httpx, "AsyncClient", lambda **kw: original(transport=httpx.MockTransport(handler)))
    result = await knowledge.embed_texts(["cláusulas arbitrales"], query=True)
    assert len(result[0]) == 768


@pytest.mark.asyncio
async def test_partial_embedding_failure_replaces_only_text_index(configured, monkeypatch):
    monkeypatch.setattr(store, "fetch_item", AsyncMock(return_value=document("A" * 60000)))
    vector = [1] + [0] * 767
    monkeypatch.setattr(knowledge, "embed_texts", AsyncMock(side_effect=[[vector] * 24, HTTPException(429, "Cuota")]))
    db = AsyncMock(return_value={"chunks": 28})
    monkeypatch.setattr(store, "db_request", db)
    result = await knowledge.index_document(OWNER, "jwt", DOC)
    assert result["semantic"] is False and result["method"] == "text"
    chunks = db.call_args.kwargs["json"]["p_chunks"]
    assert all(c["embedding"] is None and c["embedding_model"] is None for c in chunks)
    assert db.call_args.kwargs["json"]["p_version"] == 1
    assert any("únicamente" in warning for warning in result["warnings"])


@pytest.mark.asyncio
async def test_index_never_reads_foreign_document_before_embedding(configured, monkeypatch):
    monkeypatch.setattr(store, "fetch_item", AsyncMock(side_effect=HTTPException(404, "No existe")))
    embed = AsyncMock()
    monkeypatch.setattr(knowledge, "embed_texts", embed)
    with pytest.raises(HTTPException):
        await knowledge.index_document(OWNER, "jwt", DOC)
    embed.assert_not_awaited()


@pytest.mark.asyncio
async def test_search_drops_stale_rows_and_limits_selected_documents(configured, monkeypatch):
    monkeypatch.setattr(knowledge, "embed_texts", AsyncMock(side_effect=HTTPException(503, "Sin embeddings")))
    monkeypatch.setattr(store, "fetch_item", AsyncMock(return_value=document(version=2)))
    row = {"document_id": DOC, "document_version": 1, "excerpt": "texto antiguo", "method": "text"}
    db = AsyncMock(side_effect=[[row], {"indexed_documents": 0}])
    monkeypatch.setattr(store, "db_request", db)
    result = await knowledge.search(OWNER, "jwt", {"query": "arbitraje", "scope": "documents", "document_ids": [DOC]})
    assert not result["results"] and result["method"] == "text"
    assert db.call_args_list[0].kwargs["json"]["p_filters"]["document_ids"] == [DOC]
    assert any("cambió" in warning for warning in result["warnings"])


@pytest.mark.asyncio
async def test_search_cannot_return_a_foreign_document(configured, monkeypatch):
    monkeypatch.setattr(store, "db_request", AsyncMock(return_value=[{"document_id": DOC, "document_version": 1}]))
    monkeypatch.setattr(store, "fetch_item", AsyncMock(side_effect=HTTPException(404, "Cuenta distinta")))
    with pytest.raises(HTTPException):
        await knowledge.search(OWNER, "jwt", {"query": "contrato", "semantic": False})


@pytest.mark.asyncio
async def test_chat_uses_index_passages_with_scope_and_citations(configured, monkeypatch):
    row = {"document_id": DOC, "title": "Sentencia incorporada", "excerpt": "Hallazgo localizado en una página posterior.",
           "page": 36, "segment": None, "document_version": 4, "source_url": "https://corteconstitucional.gov.co/test"}
    search = AsyncMock(return_value={"results": [row], "method": "hybrid", "warnings": [], "coverage": {"legal_documents": 1}})
    monkeypatch.setattr(knowledge, "search", search)
    context = await ai.augment_indexed_context(OWNER, "jwt", {"message": "Encuentra precedente", "mode": "research"}, ai.build_context([], "consulta"))
    assert search.call_args.args[2]["scope"] == "legal"
    assert context["payload"][0]["text"] == row["excerpt"]
    assert context["sources"][0]["page"] == 36 and context["sources"][0]["document_version"] == 4
    assert context["sources"][0]["id"] == context["payload"][0]["id"]
    assert context["coverage"]["truncated"] is True


@pytest.mark.asyncio
async def test_chat_selected_files_never_expand_into_unrequested_accounts(configured, monkeypatch):
    search = AsyncMock(return_value={"results": [], "method": "text", "warnings": [], "coverage": {}})
    monkeypatch.setattr(knowledge, "search", search)
    context = ai.build_context([document()], "consulta")
    result = await ai.augment_indexed_context(OWNER, "jwt", {"message": "cláusula", "document_ids": [DOC], "matter_id": MATTER}, context)
    assert search.await_count == 2
    for call in search.call_args_list:
        assert call.args[:2] == (OWNER, "jwt")
        assert call.args[2]["document_ids"] == [DOC]
    assert result["payload"][0]["document_id"] == DOC
    search.reset_mock()
    await ai.augment_indexed_context(OWNER, "jwt", {"message": "q", "knowledge_scope": "off"}, context)
    search.assert_not_awaited()


@pytest.mark.asyncio
async def test_missing_index_keeps_selected_context_and_reports_failure(configured, monkeypatch):
    monkeypatch.setattr(knowledge, "search", AsyncMock(side_effect=HTTPException(503, "Falta migración")))
    context = await ai.augment_indexed_context(OWNER, "jwt", {"message": "q", "knowledge_scope": "documents"}, ai.build_context([document()], "q"))
    assert context["payload"] and "Falta migración" in context["warnings"]
    assert context["coverage"]["indexed_retrieval"][0]["method"] == "unavailable"


def scanned_image():
    from PIL import Image, ImageDraw, ImageFont
    image = Image.new("RGB", (1800, 360), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype("DejaVuSans.ttf", 70)
    draw.text((70, 90), "CONTRATO PRUEBA 12345", fill="black", font=font)
    output = io.BytesIO()
    image.save(output, "PNG")
    return output.getvalue()


def test_real_tesseract_recognizes_uploaded_image(configured):
    if not ocr.ocr_status()["available"]:
        pytest.skip("Tesseract y los idiomas configurados no están instalados")
    result = ai.extract_document(scanned_image(), "escaneo.png")
    assert "CONTRATO" in result["text"] and "12345" in result["text"]
    assert result["pagination"] == "pages" and result["mime"] == "image/png"
    assert any("OCR" in warning for warning in result["warnings"])


def test_real_pdf_ocr_keeps_native_page_and_reads_only_scanned_page(configured):
    if not ocr.ocr_status()["pdf_available"]:
        pytest.skip("Tesseract/Poppler no están instalados")
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
    output = io.BytesIO()
    pdf = canvas.Canvas(output)
    pdf.drawString(40, 700, "PAGINA NATIVA 6789")
    pdf.showPage()
    pdf.drawImage(ImageReader(io.BytesIO(scanned_image())), 20, 450, width=550, height=110)
    pdf.save()
    result = ai.extract_document(output.getvalue(), "mixto.pdf")
    assert "NATIVA 6789" in result["pages"][0]["text"]
    assert "12345" in result["pages"][1]["text"] and result["pages"][1]["page"] == 2


def test_invalid_image_is_rejected_before_ocr(configured):
    with pytest.raises(HTTPException):
        ai.extract_document(b"not-image", "fraude.png")


def test_text_at_limit_can_be_stored_after_extraction():
    parsed = ai.extract_document(b"a" * 500001, "limite.txt")
    assert len(parsed["text"]) <= 500000
    store.validate_payload({"kind": "document", "title": "Límite", "data": parsed}, user_id=OWNER)


@pytest.mark.asyncio
async def test_semantic_monitor_reads_late_fragment_and_locates_evidence(configured, monkeypatch):
    text = "x" * 38000 + "La nueva publicación cambia el criterio de contratación."
    calls = []
    async def provider(messages, **kwargs):
        payload = json.loads(messages[0][1].split("\n", 1)[1])
        calls.append(payload["part"])
        relevant = "contratación" in payload["untrusted_text"]
        return {"answer": json.dumps({"relevant": relevant, "summary": "Cambio" if relevant else "Sin coincidencia", "reason": "Criterio", "evidence": ["cambia el criterio de contratación."] if relevant else []}), "provider": "controlled", "model": "test", "warnings": []}
    monkeypatch.setattr(ai, "_call_provider", provider)
    result = await monitors.analyze_source({"url": "https://corteconstitucional.gov.co/", "text": text}, "Cambios de contratación")
    assert sorted(calls) == [1, 2] and result["relevant"] is True
    assert result["coverage"]["chars_reviewed"] == len(text) and result["coverage"]["complete"]
    assert result["evidence"] == ["cambia el criterio de contratación."]


@pytest.mark.asyncio
async def test_semantic_monitor_failure_is_not_absence_of_news(configured, monkeypatch):
    monkeypatch.setattr(ai, "_call_provider", AsyncMock(side_effect=HTTPException(503, "Proveedor caído")))
    with pytest.raises(HTTPException) as error:
        await monitors.analyze_source({"url": "https://corteconstitucional.gov.co/", "text": "Una publicación"}, "novedades")
    assert "No se declaró" in error.value.detail


@pytest.mark.asyncio
async def test_semantic_monitor_preserves_coverage_and_retries_partial_documents(configured, monkeypatch):
    source = {"url": "https://corteconstitucional.gov.co/", "title": "Fuente", "text": "nuevo", "links": []}
    data = {"condition": "cambios", "last_checked": "2026-10-23T00:00:00Z"}
    analysis = {"relevant": True, "evidence": ["nuevo"], "coverage": {"complete": False}, "status": "partial"}
    operation = AsyncMock(return_value=analysis)
    monkeypatch.setattr(monitors, "analyze_source", operation)
    first = await monitors.evaluate_semantic_monitor({}, copy.deepcopy(data), source)
    assert first["last_status"] == "partial" and first["source_hashes"] == {}
    assert first["coverage"]["attempted_documents"] == 1
    await monitors.evaluate_semantic_monitor({}, first, source)
    assert operation.await_count == 2
    assert len(first["findings"]) == 1


@pytest.mark.asyncio
async def test_semantic_monitor_deadline_preserves_pending_and_does_not_call_ia(configured, monkeypatch):
    operation = AsyncMock()
    monkeypatch.setattr(monitors, "analyze_source", operation)
    source = {"url": "https://corteconstitucional.gov.co/", "title": "Fuente", "text": "nuevo", "links": []}
    result = await monitors.evaluate_semantic_monitor({}, {"condition": "cambios", "last_checked": "2026-10-23"}, source, deadline=time.monotonic()-1)
    assert result["last_status"] == "error" and result["source_hashes"] == {}
    assert result["coverage"]["errors"] and result["coverage"]["complete_within_limit"] is False
    operation.assert_not_awaited()


@pytest.mark.asyncio
async def test_semantic_monitor_does_not_rebill_unchanged_completed_source(configured, monkeypatch):
    condition, text, url = "cambios", "estable", "https://corteconstitucional.gov.co/"
    data = {"condition": condition, "condition_hash": hashlib.sha256(condition.encode()).hexdigest(),
            "source_hashes": {url: hashlib.sha256(text.encode()).hexdigest()}, "last_checked": "2026-10-23"}
    operation = AsyncMock()
    monkeypatch.setattr(monitors, "analyze_source", operation)
    result = await monitors.evaluate_semantic_monitor({}, data, {"url": url, "title": "Fuente", "text": text})
    assert result["last_status"] == "unchanged" and result["coverage"]["unchanged_documents"] == 1
    operation.assert_not_awaited()


@pytest.mark.asyncio
async def test_backup_copy_strips_external_sync_key(configured, monkeypatch):
    original = document()
    original["data"].update(external_key="remote-unique", external_source={"connection_id": OTHER, "provider": "google_drive"})
    existing = copy.deepcopy(original)
    existing["title"] = "Título cambiado"
    monkeypatch.setattr(store, "all_items", AsyncMock(return_value=[existing]))
    db = AsyncMock(return_value={"imported": 1})
    monkeypatch.setattr(store, "db_request", db)
    await store.import_workspace(OWNER, "jwt", {"format": "memorialista-despacho", "version": 1, "owner_id": OWNER, "items": [original]})
    writes = db.call_args.kwargs["json"]["p_items"]
    assert len(writes) == 1 and writes[0]["id"] != DOC
    assert "external_key" not in writes[0]["data"]
    assert "connection_id" not in writes[0]["data"]["external_source"]
