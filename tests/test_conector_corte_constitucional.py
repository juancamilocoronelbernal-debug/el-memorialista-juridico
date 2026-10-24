"""Pruebas unitarias e integrales para el Conector Oficial de la Corte Constitucional (Fase 2)."""
import pytest
from unittest.mock import AsyncMock, patch

from app.services import conector_corte_constitucional as conector


def test_resolve_relatoria_urls_handles_all_jurisdictional_types():
    # Tutelas (T)
    t_urls = conector.resolve_relatoria_urls("T-100/24", "2024-04-05")
    assert "https://www.corteconstitucional.gov.co/relatoria/2024/T-100-24.htm" in t_urls

    # Constitucionalidad (C)
    c_urls = conector.resolve_relatoria_urls("C-055/22", "2022-02-21")
    assert "https://www.corteconstitucional.gov.co/relatoria/2022/C-055-22.htm" in c_urls

    # Sentencias de Unificación (SU) - deben generar SU016-21.htm prioritariamente
    su_urls = conector.resolve_relatoria_urls("SU-016/21", "2021-01-28")
    assert "https://www.corteconstitucional.gov.co/relatoria/2021/SU016-21.htm" in su_urls
    assert "https://www.corteconstitucional.gov.co/relatoria/2021/SU-016-21.htm" in su_urls

    # Sentencias históricas de los 90s
    t92_urls = conector.resolve_relatoria_urls("T-012/92", "1992-02-25")
    assert "https://www.corteconstitucional.gov.co/relatoria/1992/T-012-92.htm" in t92_urls


def test_html_text_extractor_strips_scripts_and_extracts_clean_text():
    raw_html = """
    <html>
      <head><script>alert('bad');</script><style>.css { color: red; }</style></head>
      <body>
        <h1>REPÚBLICA DE COLOMBIA</h1>
        <h2>CORTE CONSTITUCIONAL</h2>
        <p>SENTENCIA T-100 DE 2024</p>
        <div>Magistrado Ponente: Juan Carlos Cortés González</div>
        <p>RESUELVE: Primero.- TUTELAR los derechos fundamentales.</p>
      </body>
    </html>
    """
    extractor = conector.HTMLTextExtractor()
    extractor.feed(raw_html)
    clean = extractor.get_clean_text()

    assert "alert('bad')" not in clean
    assert ".css" not in clean
    assert "CORTE CONSTITUCIONAL" in clean
    assert "RESUELVE: Primero.- TUTELAR" in clean


@pytest.mark.asyncio
async def test_retrieve_and_validate_ruling_rejects_spa_fallback():
    class MockResponse:
        def __init__(self, content):
            self.content = content
            self.status_code = 200

    class MockClient:
        async def get(self, url, headers=None):
            # Simular página SPA Angular devuelta cuando el archivo no existe
            return MockResponse(b"<!DOCTYPE html><html><head></head><body><app-root></app-root></body></html>")

    with pytest.raises(ValueError, match="marco genérico del portal"):
        await conector.retrieve_and_validate_ruling("https://corte.gov.co/fake.htm", client=MockClient())


def test_prepare_ruling_chunks_caps_at_max_and_classifies_sections():
    # Crear un texto largo simulado con encabezado, consideraciones y parte resolutiva
    long_text = (
        "CORTE CONSTITUCIONAL DE COLOMBIA\nSENTENCIA C-055 DE 2022\n\n"
        + ("Consideraciones de la Sala Plena sobre derechos fundamentales y marco constitucional. " * 3000)
        + "\n\nRESUELVE: Declarar EXEQUIBLE el artículo demandado con los condicionamientos expuestos."
    )
    chunks = conector.prepare_ruling_chunks(long_text, max_chunks=180)

    assert len(chunks) <= 180
    assert chunks[0]["ordinal"] == 0
    assert chunks[0]["segment"] == 1
    # El primer chunk debe ser encabezado
    assert chunks[0]["section"] in ("encabezado", "identificacion")
    # El último chunk debe tener la parte resolutiva
    assert chunks[-1]["section"] == "parte_resolutiva"


@pytest.mark.asyncio
async def test_ingest_ruling_idempotency_skips_identical_document(monkeypatch):
    """Si el documento ya está publicado con idéntico SHA-256, no recomputa embeddings ni reindexa."""
    fake_meta = {
        "sentencia": "T-100/24",
        "url": "https://www.corteconstitucional.gov.co/relatoria/2024/T-100-24.htm",
        "fecha": "2024-04-05"
    }

    # Mock de extracción que devuelve texto fijo
    mock_extracted = {
        "url": fake_meta["url"],
        "raw_html_bytes": 1000,
        "text": "CORTE CONSTITUCIONAL DE COLOMBIA. SENTENCIA T-100/24. RESUELVE: TUTELAR.",
        "char_length": 75,
        "sha256": "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        "has_operative_decision": True,
        "retrieved_at": "2026-10-24T00:00:00Z",
        "legal_basis": "Art. 41 Ley 23/1982"
    }
    monkeypatch.setattr(conector, "retrieve_and_validate_ruling", AsyncMock(return_value=mock_extracted))

    # Mock de documento existente con hash idéntico
    mock_existing = {
        "id": "doc-uuid-existing",
        "version": 1,
        "unchanged": True,
        "title": "Sentencia T-100/24 - Corte Constitucional",
        "published": True
    }
    monkeypatch.setattr(conector, "check_existing_document", AsyncMock(return_value=mock_existing))

    # Ejecutar ingesta
    result = await conector.ingest_ruling(fake_meta, semantic=True, ack_reviews=True)

    assert result["unchanged"] is True
    assert result["status"] == "already_indexed"
    assert result["tokens_consumed"] == 0
    assert result["estimated_cost_usd"] == 0.0
