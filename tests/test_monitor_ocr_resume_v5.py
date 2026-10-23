"""Behavioral regressions for resumable monitors and incomplete extraction.

The production monitor/analyzer/extractor are exercised. Only external AI,
fetching and persistence are controlled. PDF parsing and, when installed,
Poppler rendering are real; no provider account or public source is contacted.
"""
import asyncio
import copy
import io
import json
import shutil
from pathlib import Path
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.config import get_settings
from app.services import despacho_ai as ai, despacho_monitors as monitors
from app.services import despacho_ocr as ocr, despacho_store as store


ROOT = Path(__file__).resolve().parents[1]
OWNER, MONITOR = str(uuid4()), str(uuid4())
URL = "https://corteconstitucional.gov.co/publicacion.pdf"


@pytest.fixture
def configured(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "DESPACHO_MONITOR_AI_ENABLED", True)
    monkeypatch.setattr(settings, "DESPACHO_OCR_ENABLED", True)
    monkeypatch.setattr(settings, "DESPACHO_OCR_LANGUAGES", "eng")
    # Successful writes remain outside the manual endpoint's thirty-second
    # cooldown. The test must exercise the next run, not wall-clock waiting.
    monkeypatch.setattr(store, "utcnow", lambda: "2020-01-01T00:00:00+00:00")
    return settings


def publication(text="Una publicación de prueba.", **changes):
    return {"url": URL, "title": "Publicación oficial de prueba", "text": text, "links": [],
            "warnings": [], "extraction_coverage": {"complete": True}, **changes}


def provider_payload(messages):
    return json.loads(messages[0][1].rsplit("\n", 1)[1])


def negative_answer():
    return {"answer": json.dumps({"relevant": False, "summary": "Sin coincidencia en el fragmento leído.",
        "reason": "El criterio solicitado no aparece en este texto.", "evidence": []}),
        "provider": "controlled", "model": "test-model", "warnings": []}


def monitor_storage(monkeypatch, source, *, mode="semantic"):
    state = {"source": source, "writes": [], "item": {"id": MONITOR, "owner_id": OWNER, "kind": "monitor",
        "title": "Monitor de prueba", "version": 1, "data": {"url": URL, "condition": "Cambios en contratación",
        "analysis_mode": mode, "keywords": ["contratación"], "enabled": False, "findings": [], "follow_links": False}}}

    async def fetch_item(owner, token, item_id, *, kind):
        assert (owner, token, item_id, kind) == (OWNER, "user-token", MONITOR, "monitor")
        return copy.deepcopy(state["item"])

    async def update_item(owner, token, item_id, body, version):
        assert (owner, token, item_id) == (OWNER, "user-token", MONITOR)
        assert version == state["item"]["version"]
        state["item"] = {**state["item"], **copy.deepcopy(body), "version": version + 1}
        state["writes"].append(copy.deepcopy(body))
        return copy.deepcopy(state["item"])

    async def fetch_source(url):
        assert url == URL
        return copy.deepcopy(state["source"])

    monkeypatch.setattr(store, "fetch_item", fetch_item)
    monkeypatch.setattr(store, "update_item", update_item)
    monkeypatch.setattr(monitors, "fetch_source", fetch_source)
    return state


@pytest.mark.parametrize("change,expected_second_parts", [(None, [2]), ("condition", [1, 2]), ("publication", [1, 2])])
@pytest.mark.asyncio
async def test_run_monitor_resumes_saved_fragments_and_invalidates_changed_inputs(configured, monkeypatch, change, expected_second_parts):
    state = monitor_storage(monkeypatch, publication("A" * 38_000 + "La parte final de una publicación extensa."))
    calls = []
    failed_once = False

    async def provider(messages, **_):
        nonlocal failed_once
        payload = provider_payload(messages)
        calls.append((payload["condition"], payload["part"]))
        if payload["part"] == 2 and not failed_once:
            failed_once = True
            raise HTTPException(503, "Fallo temporal del proveedor")
        return negative_answer()

    monkeypatch.setattr(ai, "_call_provider", provider)
    first = await monitors.run_monitor(OWNER, "user-token", MONITOR)
    assert first["data"]["last_status"] == "partial"
    assert first["data"]["coverage"]["complete_within_limit"] is False
    assert URL in first["data"]["pending_analysis"]
    assert not first["data"]["findings"]
    assert sorted(part for _, part in calls) == [1, 2]

    if change == "condition":
        state["item"]["data"]["condition"] = "Cambios tributarios"
    elif change == "publication":
        state["source"]["text"] = "B" + state["source"]["text"][1:]
    calls.clear()
    second = await monitors.run_monitor(OWNER, "user-token", MONITOR)
    assert sorted(part for _, part in calls) == expected_second_parts
    assert second["data"]["coverage"]["complete_within_limit"] is True
    assert second["data"]["last_status"] == "reviewed"
    assert URL not in second["data"]["pending_analysis"]
    assert len(state["writes"]) == 2


@pytest.mark.asyncio
async def test_budget_saves_completed_work_and_cancels_unfinished_provider(configured, monkeypatch):
    source = publication("A" * 38_000 + "Segunda parte pendiente.")
    calls, cancelled, active = [], [], set()
    resume = False

    async def provider(messages, **_):
        part = provider_payload(messages)["part"]
        calls.append(part)
        active.add(part)
        try:
            if part == 2 and not resume:
                await asyncio.Event().wait()
            return negative_answer()
        except asyncio.CancelledError:
            cancelled.append(part)
            raise
        finally:
            active.discard(part)

    monkeypatch.setattr(ai, "_call_provider", provider)
    first = await monitors.analyze_source(source, "condición", budget_seconds=.05)
    assert first["coverage"]["complete"] is False
    assert first["coverage"]["parts_reviewed"] == 1
    assert first["checkpoint"] and not active and cancelled == [2]
    resume = True
    second = await monitors.analyze_source(source, "condición", partials=first["checkpoint"], budget_seconds=.5)
    assert second["coverage"]["complete"] is True and second["coverage"]["cached_parts"] == 1
    assert calls.count(1) == 1 and calls.count(2) == 2
    assert not active


@pytest.mark.parametrize("operation", ["analyze_source", "run_monitor"])
@pytest.mark.asyncio
async def test_cancellation_joins_active_and_queued_reviews_without_writing_success(configured, monkeypatch, operation):
    source = publication("A" * 38_000 + "B" * 38_000 + "Último fragmento en espera.")
    state = monitor_storage(monkeypatch, source)
    started, active, cancelled = set(), set(), set()
    ready = asyncio.Event()

    async def provider(messages, **_):
        part = provider_payload(messages)["part"]
        started.add(part)
        active.add(part)
        if len(started) == 2:
            ready.set()
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            cancelled.add(part)
            raise
        finally:
            active.discard(part)

    monkeypatch.setattr(ai, "_call_provider", provider)
    baseline = asyncio.all_tasks()
    pending = asyncio.create_task(monitors.analyze_source(source, "condición") if operation == "analyze_source" else
                                  monitors.run_monitor(OWNER, "user-token", MONITOR))
    try:
        await asyncio.wait_for(ready.wait(), timeout=2)
        pending.cancel()
        with pytest.raises(asyncio.CancelledError):
            await pending
        assert not active and cancelled == started and len(started) == 2
        assert not state["writes"]
        assert not (asyncio.all_tasks() - baseline)
    finally:
        if not pending.done():
            pending.cancel()
            await asyncio.gather(pending, return_exceptions=True)


def raster_image():
    from PIL import Image, ImageDraw, ImageFont
    image = Image.new("RGB", (1800, 300), "white")
    draw = ImageDraw.Draw(image)
    font_file = ROOT / "app/private/fonts/DejaVuSans.ttf"
    font_src = str(font_file) if font_file.exists() else "DejaVuSans.ttf"
    draw.text((60, 80), "CONTRATO ESCANEADO 12345", fill="black", font=ImageFont.truetype(font_src, 65))
    output = io.BytesIO()
    image.save(output, "PNG")
    return output.getvalue()


def pdf_with_image(*, native_page=False, stamp=False):
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas
    output = io.BytesIO()
    pdf = canvas.Canvas(output)
    if native_page:
        pdf.drawString(40, 750, "Pagina nativa disponible. No contiene la condicion consultada.")
        pdf.showPage()
    if stamp:
        pdf.drawString(40, 760, "SELLO DIGITAL 42")
    pdf.drawImage(ImageReader(io.BytesIO(raster_image())), 20, 450, width=550, height=92)
    pdf.save()
    return output.getvalue()


def ocr_unavailable():
    return {"available": False, "pdf_available": False, "languages": [], "missing_languages": ["eng"],
            "engine": "Tesseract local", "max_pages": 30, "enabled": True}


@pytest.mark.parametrize("mode", ["semantic", "keywords"])
@pytest.mark.asyncio
async def test_incomplete_pdf_keeps_warnings_on_initial_and_unchanged_runs_without_findings(configured, monkeypatch, mode):
    monkeypatch.setattr(ocr, "ocr_status", ocr_unavailable)
    extracted = ai.extract_document(pdf_with_image(native_page=True), "parcial.pdf")
    assert extracted["extraction_coverage"]["complete"] is False
    assert extracted["warnings"] and extracted["pages"][1]["text"] == ""
    source = publication(extracted["text"], warnings=extracted["warnings"], extraction_coverage=extracted["extraction_coverage"])
    state = monitor_storage(monkeypatch, source, mode=mode)
    provider = AsyncMock(return_value=negative_answer())
    monkeypatch.setattr(ai, "_call_provider", provider)
    for _ in range(2):
        result = await monitors.run_monitor(OWNER, "user-token", MONITOR)
        data = result["data"]
        assert not data["findings"] and data["last_status"] == "partial"
        assert set(extracted["warnings"]) <= set(data["last_warnings"])
        if mode == "semantic":
            assert data["coverage"]["complete_within_limit"] is False
            assert data["coverage"]["extraction_incomplete_documents"] == 1
        else:
            assert data["extraction_coverage"]["complete"] is False
    assert provider.await_count == (1 if mode == "semantic" else 0)
    assert len(state["writes"]) == 2


@pytest.mark.asyncio
async def test_reading_all_retrieved_text_does_not_claim_complete_original(configured, monkeypatch):
    warning = "La segunda página permanece sin texto extraíble."
    provider = AsyncMock(return_value=negative_answer())
    monkeypatch.setattr(ai, "_call_provider", provider)
    result = await monitors.analyze_source(publication("Texto de la primera página.", warnings=[warning],
        extraction_coverage={"complete": False, "pages_total": 2, "pages_with_text": 1}), "condición")
    assert result["relevant"] is False
    assert result["coverage"]["retrieved_text_complete"] is True
    assert result["coverage"]["source_extraction_complete"] is False
    assert result["coverage"]["complete"] is False and result["status"] == "partial"
    assert warning in result["warnings"]


def test_pdf_with_short_digital_stamp_is_not_declared_read_when_ocr_unavailable(configured, monkeypatch):
    monkeypatch.setattr(ocr, "ocr_status", ocr_unavailable)
    result = ai.extract_document(pdf_with_image(stamp=True), "sello-y-escaneo.pdf")
    assert "SELLO DIGITAL 42" in result["text"]
    assert result["ocr"]["unresolved_pages"] == 1
    assert result["extraction_coverage"]["complete"] is False
    assert any("OCR" in warning for warning in result["warnings"])


def test_stamped_pdf_reaches_ocr_and_replaces_stamp_only_text_with_recovered_body(configured, monkeypatch):
    if not shutil.which("pdftoppm"):
        pytest.skip("Poppler no está instalado para esta comprobación de renderizado real")
    monkeypatch.setattr(ocr, "ocr_status", lambda: {**ocr_unavailable(), "available": True, "pdf_available": True,
                                                   "languages": ["eng"], "missing_languages": []})
    rendered = []
    recovered = "SELLO DIGITAL 42\nCONTRATO ESCANEADO 12345\nTexto recuperado del contenido de la imagen."

    def read_image(path, **_):
        assert Path(path).read_bytes().startswith(b"\x89PNG")
        rendered.append(path)
        return recovered

    monkeypatch.setattr(ocr, "_read_image", read_image)
    result = ai.extract_document(pdf_with_image(stamp=True), "sello-y-escaneo.pdf")
    assert len(rendered) == 1 and recovered in result["text"]
    assert result["ocr"]["processed_pages"] == [1] and result["ocr"]["unresolved_pages"] == 0
    assert result["extraction_coverage"]["complete"] is True


def test_image_ocr_character_budget_is_reported_as_partial_extraction(configured, monkeypatch):
    monkeypatch.setattr(ocr, "ocr_status", lambda: {**ocr_unavailable(), "available": True, "languages": ["eng"], "missing_languages": []})
    monkeypatch.setattr(ocr, "_read_image", lambda *_, **__: "A" * 500_001)
    result = ai.extract_document(raster_image(), "imagen-extensa.png")
    assert len(result["text"]) == 500_000 and result["truncated"] is True
    assert result["extraction_coverage"]["complete"] is False
    assert any("500.000" in warning for warning in result["warnings"])
