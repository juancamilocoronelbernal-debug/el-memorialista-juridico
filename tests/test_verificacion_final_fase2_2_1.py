"""Tests para la Verificación Final de la Fase 2.2.1:
1. Detección de providencia nueva con fecha reciente.
2. Detección de providencia antigua incorporada tardíamente (revisión retrospectiva rotativa).
3. Drenado dinámico sin omisiones cuando se publican más de 20 incorporaciones entre sincronizaciones.
4. Detección y auditoría de cambios en los metadatos de una sentencia preexistente.
5. Política progresiva de reintentos, diagnóstico de causas, transición a dormant poll y preservación de retry_history.
6. Seguridad criptográfica de identidad en aprobación de triage (rechazo de spoofing y control de rol jurídico HTTP 403).
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.services import conector_corte_constitucional as conector
from app.services import conector_corte_worker as worker


# ---------------------------------------------------------------------------
# 1. DETECCIÓN DE PROVIDENCIA NUEVA CON FECHA RECIENTE
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_discovery_new_ruling_recent_date():
    """Comprueba que una nueva sentencia con fecha reciente sea descubierta y registrada de inmediato."""
    mock_soda = [{
        "sentencia": "T-325/26",
        "sentencia_tipo": "T",
        "fecha_sentencia": "2026-10-24T00:00:00.000",
        "magistrado_a": "Diana Fajardo Rivera",
        "sala": "Sala Novena de Revisión",
        "expediente_tipo": "T",
        "expediente_numero": "1000001",
        "proceso": "Acción de tutela",
        "tema": "Protección a la salud",
    }]

    mock_client = AsyncMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_soda
    mock_client.get = AsyncMock(return_value=mock_resp)

    with patch("app.services.despacho_store.db_request", new_callable=AsyncMock) as mock_store:
        # La tabla de descubrimientos no la tiene registrada aún
        mock_store.return_value = []

        candidates = await conector.discover_incremental_soda_rulings(limit=10, client=mock_client)
        assert len(candidates) == 1
        c = candidates[0]
        assert c["sentencia"] == "T-325/26"
        assert c["is_already_known"] is False
        assert c["anio"] == 2026

        # Verificar inserción en despacho_conector_descubrimientos
        post_calls = [call for call in mock_store.call_args_list if call[0][0] == "POST"]
        assert len(post_calls) >= 1
        inserted = post_calls[0][1]["json"]
        assert inserted["sentencia"] == "T-325/26"
        assert inserted["source_status"] == "discovered"


# ---------------------------------------------------------------------------
# 2. DETECCIÓN DE PROVIDENCIA ANTIGUA INCORPORADA HOY (RETROSPECTIVA)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_discovery_old_ruling_incorporated_today():
    """Comprueba que una sentencia con fecha antigua (ej. 2018) incorporada tardíamente
    sea detectada mediante la revisión retrospectiva rotativa."""
    mock_soda_retro = [{
        "sentencia": "T-850/18",
        "sentencia_tipo": "T",
        "fecha_sentencia": "2018-06-15T00:00:00.000",
        "magistrado_a": "Alberto Rojas Ríos",
        "sala": "Sala Octava de Revisión",
        "expediente_tipo": "T",
        "expediente_numero": "678910",
        "proceso": "Acción de tutela",
        "tema": "Derecho a la pensión",
    }]

    mock_client = AsyncMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_soda_retro
    mock_client.get = AsyncMock(return_value=mock_resp)

    with patch("app.services.conector_corte_constitucional.get_connector_status", new_callable=AsyncMock) as mock_status, \
         patch("app.services.despacho_store.db_request", new_callable=AsyncMock) as mock_store:

        mock_status.return_value = {"retrospective_cursor": {"year": 2018, "offset": 0}}
        mock_store.return_value = []

        retro_candidates = await conector.discover_retrospective_soda_rulings(batch_size=5, client=mock_client, target_year=2018)
        assert len(retro_candidates) == 1
        rc = retro_candidates[0]
        assert rc["sentencia"] == "T-850/18"
        assert rc["anio"] == 2018
        assert rc["is_retrospective"] is True
        assert rc["is_already_known"] is False


# ---------------------------------------------------------------------------
# 3. DRENADO DINÁMICO DE MÁS DE 20 INCORPORACIONES ENTRE SINCRONIZACIONES
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_discovery_more_than_twenty_items_drained():
    """Comprueba que si ingresan más de 20 sentencias nuevas entre ciclos (ej. 25),
    el conector drene páginas sucesivas mediante keyset seek sin omitir ninguna providencia."""
    # Página 1: 20 providencias nuevas
    page1 = [
        {"sentencia": f"T-{300-i}/26", "fecha_sentencia": "2026-10-20T00:00:00.000", "sentencia_tipo": "T"}
        for i in range(20)
    ]
    # Página 2: 5 providencias nuevas adicionales
    page2 = [
        {"sentencia": f"T-{280-i}/26", "fecha_sentencia": "2026-10-19T00:00:00.000", "sentencia_tipo": "T"}
        for i in range(5)
    ]

    mock_client = AsyncMock()
    resp1 = MagicMock(status_code=200)
    resp1.json.return_value = page1
    resp2 = MagicMock(status_code=200)
    resp2.json.return_value = page2

    mock_client.get = AsyncMock(side_effect=[resp1, resp2])

    with patch("app.services.despacho_store.db_request", new_callable=AsyncMock) as mock_store:
        mock_store.return_value = []  # Ninguna es conocida previamente

        candidates = await conector.discover_incremental_soda_rulings(limit=20, client=mock_client)
        # Se deben haber drenado ambas páginas: 20 + 5 = 25 candidatos
        assert len(candidates) == 25
        assert candidates[0]["sentencia"] == "T-300/26"
        assert candidates[-1]["sentencia"] == "T-276/26"
        assert mock_client.get.call_count == 2


# ---------------------------------------------------------------------------
# 4. CAMBIOS EN LOS METADATOS DE UNA SENTENCIA EXISTENTE
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_metadata_change_detection_and_audit():
    """Comprueba que cuando SODA actualiza los metadatos de una sentencia preexistente
    (ej. corrección de magistrado ponente), se detecte la variación y se registre en auditoría."""
    soda_row_updated = [{
        "sentencia": "T-100/24",
        "sentencia_tipo": "T",
        "fecha_sentencia": "2024-04-10T00:00:00.000",
        "magistrado_a": "Vladimir Fernández Andrade",  # Nombre ampliado/corregido
        "sala": "Sala Novena de Revisión",
        "expediente_tipo": "T",
        "expediente_numero": "9876543",
        "proceso": "Acción de tutela",
        "tema": "Derecho fundamental a la salud",
    }]

    mock_client = AsyncMock()
    mock_resp = MagicMock(status_code=200)
    mock_resp.json.return_value = soda_row_updated
    mock_client.get = AsyncMock(return_value=mock_resp)

    # Simular que en la BD el magistrado estaba incompleto ("Vladimir Fernández")
    existing_record = [{
        "sentencia": "T-100/24",
        "magistrado": "Vladimir Fernández",  # Anterior
        "sala": "Sala Novena de Revisión",
        "expediente": "T-9876543",
        "proceso": "Acción de tutela",
        "tema": "Derecho fundamental a la salud",
        "fecha": "2024-04-10",
        "source_status": "published",
        "document_id": "doc-uuid-t100",
    }]

    with patch("app.services.despacho_store.db_request", new_callable=AsyncMock) as mock_store:
        async def store_side_effect(method, endpoint, key, service=False, json=None):
            if method == "GET" and "despacho_conector_descubrimientos" in endpoint:
                return existing_record
            if method == "GET" and "despacho_corpus_documentos" in endpoint:
                return [{"id": "doc-uuid-t100", "metadata": {"sentencia": "T-100/24", "magistrado": "Vladimir Fernández"}}]
            return {}

        mock_store.side_effect = store_side_effect

        candidates = await conector.discover_incremental_soda_rulings(limit=10, client=mock_client)
        assert len(candidates) == 1
        c = candidates[0]
        assert c["is_already_known"] is True
        assert c.get("metadata_updated") is True
        assert any("magistrado" in chg for chg in c.get("metadata_changes", []))

        # Verificar que se llamó a PATCH en descubrimientos y al registro de auditoría
        patch_calls = [call for call in mock_store.call_args_list if call[0][0] == "PATCH"]
        assert len(patch_calls) >= 1
        audit_calls = [call for call in mock_store.call_args_list if "despacho_registrar_auditoria_revision" in call[0][1]]
        assert len(audit_calls) >= 1
        assert "Actualización de metadatos" in audit_calls[0][1]["json"]["p_reason"]


# ---------------------------------------------------------------------------
# 5. POLÍTICA DEFINITIVA DE REINTENTOS PROGRESIVOS Y FASE DORMANT
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_progressive_retries_and_dormant_transition():
    """Comprueba la progresión de reintentos escalonados, la distinción de causas
    y la transición a fase latente semanal (168h) sin marcar como inexistente."""
    with patch("app.services.despacho_store.db_request", new_callable=AsyncMock) as mock_store, \
         patch("app.services.conector_corte_constitucional.validate_and_stage_ruling", new_callable=AsyncMock) as mock_stage:

        # Caso A: Reintento 3 (debe calcular 16 horas)
        item_att3 = [{
            "sentencia": "C-316/26",
            "retry_count": 2,  # Pasa a 3
            "metadata": {"retry_history": []},
        }]
        mock_store.return_value = item_att3
        mock_stage.return_value = {"status": "pending_source", "reasons": ["HTTP 404 No Found en Relatoría"]}

        res = await conector.retry_pending_source_rulings(limit=1)
        assert res["processed_count"] == 1
        assert res["failed_count"] == 1

        patch_call = [c for c in mock_store.call_args_list if c[0][0] == "PATCH"][0]
        patch_payload = patch_call[1]["json"]
        assert patch_payload["retry_count"] == 3
        assert patch_payload["source_status"] == "pending_source"
        # Comprobar registro en historial
        hist = patch_payload["metadata"]["retry_history"]
        assert len(hist) == 1
        assert hist[0]["attempt"] == 3
        assert hist[0]["backoff_hours"] == 16
        assert hist[0]["phase"] == "frequent_retry"

        # Caso B: Reintento 7 (agotados reintentos frecuentes -> transición a dormant poll de 168h)
        mock_store.reset_mock()
        item_att7 = [{
            "sentencia": "C-316/26",
            "retry_count": 6,  # Pasa a 7
            "metadata": {"retry_history": hist},
        }]
        mock_store.return_value = item_att7
        res2 = await conector.retry_pending_source_rulings(limit=1)
        assert res2["failed_count"] == 1

        patch_call2 = [c for c in mock_store.call_args_list if c[0][0] == "PATCH"][0]
        patch_payload2 = patch_call2[1]["json"]
        assert patch_payload2["retry_count"] == 7
        # ¡IMPORTANTE: No se clasifica como permanently_unavailable!
        assert patch_payload2["source_status"] == "pending_source"
        hist2 = patch_payload2["metadata"]["retry_history"]
        assert len(hist2) == 2
        assert hist2[-1]["attempt"] == 7
        assert hist2[-1]["backoff_hours"] == 168  # 1 semana
        assert hist2[-1]["phase"] == "dormant_poll"
        assert patch_payload2["metadata"]["dormant_phase"] is True


# ---------------------------------------------------------------------------
# 6. SEGURIDAD DE REVISIÓN EN TRIAGE (RECHAZO DE IDENTIDAD FALSIFICADA Y 403)
# ---------------------------------------------------------------------------

def test_triage_review_security_identity_and_role_enforcement():
    """Comprueba que el endpoint de triage extraiga obligatoriamente la identidad
    del token verificado y rechace atribuciones de revisión jurídica humana a roles no habilitados (HTTP 403)."""
    client = TestClient(app)

    # 1. Intento de cliente no profesional (rol 'lector' o 'invitado') intentando 'revision_juridica_humana'
    user_lector = {
        "id": "11111111-2222-3333-4444-555555555555",
        "email": "ciudadano@correo.com",
        "user_metadata": {"full_name": "Ciudadano Lector", "rol": "lector"},
    }
    with patch("app.main.verificar_acceso", new_callable=AsyncMock, return_value=user_lector), \
         patch("app.routers.despacho_corpus_fuentes.verificar_acceso", new_callable=AsyncMock, return_value=user_lector), \
         patch("app.services.limites.limitador.verificar", return_value=None):

        payload = {
            "document_id": "doc-uuid-t315",
            "decision": "approve",
            "review_type": "revision_juridica_humana",  # Intento no autorizado
            "reason": "Intento de aprobación sin ser abogado",
        }
        res = client.post("/api/despacho/official/connector/triage/review", json=payload)
        # Debe ser estrictamente denegado con HTTP 403
        assert res.status_code == 403
        assert "no cuenta con atribuciones jurídicas acreditadas" in res.json()["detail"]

    # 2. Profesional jurídico acreditado (rol 'abogado') -> autoriza y fija identidad verificada del servidor
    user_abogado = {
        "id": "22222222-3333-4444-5555-666666666666",
        "email": "abogada.relatora@despacho.co",
        "user_metadata": {"full_name": "Dra. María Paula González", "rol": "abogado"},
    }
    with patch("app.main.verificar_acceso", new_callable=AsyncMock, return_value=user_abogado), \
         patch("app.routers.despacho_corpus_fuentes.verificar_acceso", new_callable=AsyncMock, return_value=user_abogado), \
         patch("app.services.limites.limitador.verificar", return_value=None), \
         patch("app.services.conector_corte_constitucional.review_triage_document", new_callable=AsyncMock) as mock_rev:

        mock_rev.return_value = {"id": "doc-uuid-t315", "workflow_status": "published"}
        payload_valid = {
            "document_id": "doc-uuid-t315",
            "decision": "approve",
            "review_type": "revision_juridica_humana",
            "reason": "Sentencia revisada y confrontada contra la Gaceta Constitucional",
        }
        res_ok = client.post("/api/despacho/official/connector/triage/review", json=payload_valid)
        assert res_ok.status_code == 200

        # Verificar que review_triage_document recibió los datos autenticados del servidor, NO del cliente
        mock_rev.assert_called_once()
        called_kwargs = mock_rev.call_args[1]
        assert called_kwargs["responsible_id"] == "22222222-3333-4444-5555-666666666666"
        assert "Dra. María Paula González" in called_kwargs["responsible_name"]
        assert "abogada.relatora@despacho.co" in called_kwargs["responsible_name"]
        assert called_kwargs["responsible_role"] == "profesional_juridico_abogado"
