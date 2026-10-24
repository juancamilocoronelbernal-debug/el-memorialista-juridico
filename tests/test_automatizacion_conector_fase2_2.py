"""Tests para la Fase 2.2: Automatización Real del Conector, Validación Documental Obligatoria y Triage."""
import pytest
import hashlib
from unittest.mock import patch, AsyncMock

from app.services.validador_documental_corpus import (
    validate_ruling_candidate,
    DocumentValidationResult,
)
from app.services import conector_corte_constitucional as conector
from app.services import conector_corte_worker as worker


def _create_mock_ruling_text(sentencia="T-100/24", magistrado="Vladimir Fernández Andrade"):
    return f"""REPÚBLICA DE COLOMBIA
CORTE CONSTITUCIONAL
SALA DE REVISIÓN
SENTENCIA {sentencia}

Magistrado Ponente: {magistrado}
Expediente: T-9.876.543
Referencia: Acción de tutela instaurada por el ciudadano contra la entidad pública.

I. ANTECEDENTES
El accionante interpuso demanda de tutela manifestando que la entidad demandada vulneró su derecho a la salud.
Los hechos se fundamentan en la falta de entrega oportuna de insumos médicos necesarios.

II. CONSIDERACIONES DE LA CORTE
1. Competencia. Esta Sala de Revisión es competente para revisar el fallo de tutela.
2. Problema jurídico: ¿Vulneró la entidad accionada los derechos fundamentales a la salud y vida digna?
3. Fundamentos jurídicos: La jurisprudencia constitucional ha reiterado que el derecho a la salud es fundamental y autónomo.
La ratio decidendi de esta Corporación establece que el acceso oportuno es imperativo.

III. DECISIÓN
En mérito de lo expuesto, la Sala de Revisión de la Corte Constitucional, administrando justicia en nombre del pueblo y por mandato de la Constitución,

RESUELVE:
PRIMERO. Conceder el amparo de los derechos fundamentales invocados.
SEGUNDO. Ordenar a la demandada suministrar los insumos requeridos dentro de las 48 horas siguientes.
Comuníquese, notifíquese y cúmplase.

{magistrado}
Magistrado
"""


def test_validador_10_points_all_pass():
    """Comprueba que una providencia canónica y completa supera las 10 validaciones técnicas."""
    text = _create_mock_ruling_text("T-100/24", "Vladimir Fernández Andrade")
    sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()
    chunks = conector.prepare_ruling_chunks(text, max_chunks=None)
    
    meta = {
        "sentencia": "T-100/24",
        "tipo": "T",
        "anio": 2024,
        "magistrado": "Vladimir Fernández Andrade",
    }
    url = "https://www.corteconstitucional.gov.co/relatoria/2024/T-100-24.htm"
    
    res = validate_ruling_candidate(meta, text, chunks, url, sha256)
    assert res.is_technically_sound is True
    assert res.validation_status == "technically_validated"
    assert len(res.rejection_reasons) == 0
    assert len(res.checks) == 10
    assert all(chk["passed"] for chk in res.checks.values())


def test_validador_rejects_missing_operative_decision():
    """Comprueba que la ausencia de parte resolutiva/RESUELVE bloquea la publicación."""
    text = """REPÚBLICA DE COLOMBIA
CORTE CONSTITUCIONAL
SALA DE REVISIÓN
SENTENCIA T-999/24

Magistrado Ponente: Carlos Camargo Assis
Expediente: T-9.999.999

I. ANTECEDENTES
El accionante interpuso demanda de tutela señalando presuntas vulneraciones a derechos fundamentales.
Se relatan aquí detalladamente los antecedentes fácticos que dieron origen al trámite procesal de instancia.

II. CONSIDERACIONES DE LA CORTE CONSTITUCIONAL
La jurisprudencia constitucional ha sostenido reiteradamente que la tutela procede como mecanismo subsidiario.
Se analizan los requisitos generales de procedibilidad formal de la acción constitucional de amparo.
Sin embargo, el documento se encuentra totalmente inconcluso en su transmisión oficial y carece por completo
de una sección resolutiva, orden o fallo formal que resuelva el caso concreto sometido a revisión judicial."""
    sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()
    chunks = conector.prepare_ruling_chunks(text, max_chunks=None)
    meta = {"sentencia": "T-999/24", "tipo": "T", "anio": 2024, "magistrado": "Carlos Camargo Assis"}
    url = "https://www.corteconstitucional.gov.co/relatoria/2024/T-999-24.htm"

    res = validate_ruling_candidate(meta, text, chunks, url, sha256)
    assert res.is_technically_sound is False
    assert res.validation_status == "validation_failed"
    assert any("operative_decision" in r for r in res.rejection_reasons)


def test_validador_rejects_spa_error():
    """Comprueba que una plantilla SPA vacía (<app-root>) es rechazada con authentic_source = False."""
    text = "<html><body><app-root></app-root><script>app.js</script></body></html>" + " " * 500
    sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()
    chunks = [{"ordinal": 0, "segment": 1, "content": text, "section": "encabezado"}]
    meta = {"sentencia": "T-999/24", "tipo": "T", "anio": 2024, "magistrado": "Carlos Camargo Assis"}
    url = "https://www.corteconstitucional.gov.co/relatoria/2024/T-999-24.htm"
    
    res = validate_ruling_candidate(meta, text, chunks, url, sha256)
    assert res.is_technically_sound is False
    assert any("authentic_source" in r for r in res.rejection_reasons)


def test_validador_rejects_magistrado_inconsistency():
    """Comprueba que si el magistrado indicado no concuerda con el texto se envía a triage."""
    text = _create_mock_ruling_text("T-100/24", "Vladimir Fernández Andrade")
    sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()
    chunks = conector.prepare_ruling_chunks(text, max_chunks=None)
    # Metadato indica magistrado completamente ajeno
    meta = {"sentencia": "T-100/24", "tipo": "T", "anio": 2024, "magistrado": "Alejandro Linares Cantillo"}
    url = "https://www.corteconstitucional.gov.co/relatoria/2024/T-100-24.htm"
    
    res = validate_ruling_candidate(meta, text, chunks, url, sha256)
    assert res.is_technically_sound is False
    assert any("magistrado_consistency" in r for r in res.rejection_reasons)


def test_validador_rejects_truncated_text():
    """Comprueba que si se omiten fragmentos se activa la alarma de truncamiento (no_truncation = False)."""
    text = _create_mock_ruling_text("T-100/24", "Vladimir Fernández Andrade")
    sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()
    # Chunks incompletos que solo cubren una fracción mínima
    chunks = [{"ordinal": 0, "segment": 1, "content": text[:100], "section": "encabezado"}]
    meta = {"sentencia": "T-100/24", "tipo": "T", "anio": 2024, "magistrado": "Vladimir Fernández Andrade"}
    url = "https://www.corteconstitucional.gov.co/relatoria/2024/T-100-24.htm"
    
    res = validate_ruling_candidate(meta, text, chunks, url, sha256)
    assert res.is_technically_sound is False
    assert any("no_truncation" in r for r in res.rejection_reasons)


@pytest.mark.asyncio
async def test_scheduler_configuration():
    """Verifica que la configuración del programador actualice estado y retorne metadatos."""
    with patch("app.services.conector_corte_constitucional.update_schedule_metadata", new_callable=AsyncMock) as mock_up:
        mock_up.return_value = {
            "schedule_enabled": True,
            "schedule_interval_minutes": 180,
            "next_run_at": "2026-10-25T00:00:00Z",
        }
        res = await worker.configure_schedule(enabled=True, interval_minutes=180, run_now=False)
        assert res["schedule"]["schedule_enabled"] is True
        assert res["schedule"]["schedule_interval_minutes"] == 180


@pytest.mark.asyncio
async def test_distributed_locking_logic():
    """Verifica que el bloqueo concurrente distribuido impida ejecuciones simultáneas."""
    with patch("app.services.conector_corte_constitucional.acquire_sync_lock", new_callable=AsyncMock) as mock_lock:
        mock_lock.return_value = False  # Simula que otro worker ya tiene el lock
        res = await conector.run_incremental_sync(limit=10, owner="worker_2")
        assert res["status"] == "busy"
        assert "bloqueo distribuido" in res["message"]


@pytest.mark.asyncio
async def test_idempotency_second_run_zero_tokens():
    """Verifica que una providencia ya indexada no consuma tokens ni genere duplicados."""
    url = "https://www.corteconstitucional.gov.co/relatoria/2024/T-100-24.htm"
    fake_sha = "abcdef0123456789" * 4
    with patch("app.services.conector_corte_constitucional.check_and_resolve_valid_url", new_callable=AsyncMock) as mock_url, \
         patch("app.services.conector_corte_constitucional.retrieve_and_validate_ruling", new_callable=AsyncMock) as mock_retr, \
         patch("app.services.conector_corte_constitucional.check_existing_document", new_callable=AsyncMock) as mock_check:
        
        mock_url.return_value = url
        mock_retr.return_value = {"text": _create_mock_ruling_text(), "sha256": fake_sha, "char_length": 1500, "has_operative_decision": True, "legal_basis": "Art. 41"}
        mock_check.return_value = {"id": "doc-uuid-1", "version": 1, "unchanged": True}

        res = await conector.validate_and_stage_ruling({"sentencia": "T-100/24", "url": url})
        assert res["unchanged"] is True
        assert res["status"] == "already_indexed"
        assert res["tokens_consumed"] == 0
        assert res["estimated_cost_usd"] == 0.0


@pytest.mark.asyncio
async def test_historical_citations_stability():
    """Verifica que las citas históricas [O1-S1] mantengan concordancia documental estricta."""
    # Las citas en el Visor 2.0 y en el Agente RAG 2.0 vinculan el ordinal y la versión documental
    # Verificamos que prepare_ruling_chunks mantenga ordinales 0-indexados estables
    text = _create_mock_ruling_text()
    chunks1 = conector.prepare_ruling_chunks(text, max_chunks=None)
    chunks2 = conector.prepare_ruling_chunks(text, max_chunks=None)

    assert len(chunks1) == len(chunks2)
    for c1, c2 in zip(chunks1, chunks2):
        assert c1["ordinal"] == c2["ordinal"]
        assert c1["segment"] == c2["segment"]
        assert c1["content"] == c2["content"]
        assert c1["section"] == c2["section"]


@pytest.mark.asyncio
async def test_triage_inbox_and_human_review():
    """Verifica la consulta de bandeja de triage y la resolución de decisiones de aprobación/rechazo."""
    with patch("app.services.despacho_store.db_request", new_callable=AsyncMock) as mock_store:
        # 1. Simular consulta de triage
        mock_store.return_value = {
            "total": 1,
            "limit": 50,
            "offset": 0,
            "items": [{
                "id": "11111111-2222-3333-4444-555555555555",
                "title": "Sentencia T-999/24 - Corte Constitucional",
                "validation_status": "validation_failed",
                "workflow_status": "pending_legal_review",
                "published": False,
            }],
        }
        inbox = await conector.list_triage_inbox(limit=50, offset=0)
        assert inbox["total"] == 1
        assert len(inbox["items"]) == 1
        assert inbox["items"][0]["validation_status"] == "validation_failed"

        # 2. Simular aprobación humana
        mock_store.return_value = {
            "id": "11111111-2222-3333-4444-555555555555",
            "validation_status": "approved",
            "workflow_status": "published",
            "published": True,
        }
        res_app = await conector.review_triage_document(
            document_id="11111111-2222-3333-4444-555555555555",
            decision="approve",
            reason="Subsanado manualmente por el magistrado auditor",
        )
        assert res_app["published"] is True
        assert res_app["validation_status"] == "approved"


@pytest.mark.asyncio
async def test_incremental_soda_discovery_parser():
    """Verifica la decodificación de registros SODA oficiales con columnas canónicas."""
    mock_soda_response = [
        {
            "sentencia": "C-316/26",
            "sentencia_tipo": "C",
            "fecha_sentencia": "2026-09-30T00:00:00.000",
            "magistrado_a": "Carlos Camargo Assis",
            "sala": "Sala Plena",
            "expediente_tipo": "D",
            "expediente_numero": "17395",
            "proceso": "Demanda de inconstitucionalidad",
            "tema": "Control de constitucionalidad",
        }
    ]

    from unittest.mock import MagicMock
    mock_client = AsyncMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_soda_response
    mock_client.get = AsyncMock(return_value=mock_resp)

    candidates = await conector.discover_incremental_soda_rulings(limit=1, offset=0, client=mock_client)
    assert len(candidates) == 1
    c = candidates[0]
    assert c["sentencia"] == "C-316/26"
    assert c["tipo"] == "C"
    assert c["fecha"] == "2026-09-30"
    assert c["anio"] == 2026
    assert c["magistrado"] == "Carlos Camargo Assis"
    assert c["expediente"] == "D-17395"
    assert c["sala"] == "Sala Plena"

