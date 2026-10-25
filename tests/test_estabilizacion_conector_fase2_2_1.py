"""Tests para la Fase 2.2.1: Estabilización Definitiva de la Sincronización Automática de Jurisprudencia.

Cubre:
1. Paginación Keyset / Watermark y deduplicación contra saltos de offset.
2. Cola de reintentos con retroceso exponencial para providencias 'pending_source'.
3. Heartbeat de renovación de bloqueo concurrente y protección con Fencing Token.
4. Recuperación tras reinicio y limpieza de bloqueos huérfanos.
5. Pausa y reanudación administrativa del programador asíncrono.
6. Trazabilidad inmutable y diferenciación entre validación técnica, aprobación administrativa y revisión jurídica humana.
7. Endpoints de control administrativo en FastAPI.
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.services import conector_corte_constitucional as conector
from app.services import conector_corte_worker as worker


# ---------------------------------------------------------------------------
# 1. WATERMARK & KEYSET SEEK PAGINATION
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_keyset_seek_pagination_avoids_offset_skipping():
    """Comprueba que el descubrimiento incremental use keyset seek con marca de agua (watermark),
    evitando la omisión de providencias cuando se insertan nuevos registros en el tope del catálogo SODA."""
    mock_soda_response = [
        {
            "sentencia": "T-320/26",
            "sentencia_tipo": "T",
            "fecha_sentencia": "2026-10-15T00:00:00.000",
            "magistrado_a": "Diana Fajardo Rivera",
            "sala": "Sala Novena de Revisión",
            "expediente_tipo": "T",
            "expediente_numero": "999999",
            "proceso": "Acción de tutela",
            "tema": "Derecho a la educación",
        },
        {
            "sentencia": "T-319/26",
            "sentencia_tipo": "T",
            "fecha_sentencia": "2026-10-14T00:00:00.000",
            "magistrado_a": "Antonio José Lizarazo",
            "sala": "Sala Cuarta de Revisión",
            "expediente_tipo": "T",
            "expediente_numero": "999998",
            "proceso": "Acción de tutela",
            "tema": "Seguridad social",
        },
    ]

    mock_client = AsyncMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_soda_response
    mock_client.get = AsyncMock(return_value=mock_resp)

    with patch("app.services.despacho_store.db_request", new_callable=AsyncMock) as mock_store:
        # Simular que no hay sentencias previas registradas en descubrimientos
        mock_store.return_value = []

        candidates = await conector.discover_incremental_soda_rulings(
            limit=10,
            seek_before_fecha="2026-10-10T00:00:00.000",
            seek_before_sentencia="T-315/26",
            client=mock_client,
        )

        assert len(candidates) == 2
        assert candidates[0]["sentencia"] == "T-320/26"
        assert candidates[1]["sentencia"] == "T-319/26"

        # Verificar que la URL de SODA utilizó la condición $where de keyset seek
        mock_client.get.assert_called_once()
        called_url = mock_client.get.call_args[0][0]
        assert "$where=" in called_url
        assert "fecha_sentencia" in called_url


# ---------------------------------------------------------------------------
# 2. RETRY QUEUE WITH EXPONENTIAL BACKOFF (PENDING_SOURCE)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_pending_source_registered_when_html_missing():
    """Comprueba que cuando una providencia existe en SODA pero aún no en Relatoría,
    se catalogue como 'pending_source' con estado reintentable."""
    url = "https://www.corteconstitucional.gov.co/relatoria/2026/C-316-26.htm"
    with patch("app.services.conector_corte_constitucional.check_and_resolve_valid_url", new_callable=AsyncMock) as mock_url, \
         patch("app.services.conector_corte_constitucional.retrieve_and_validate_ruling", new_callable=AsyncMock) as mock_retr, \
         patch("app.services.despacho_store.db_request", new_callable=AsyncMock) as mock_store:
        
        mock_url.return_value = url
        # Simular 404 en Relatoría
        mock_retr.side_effect = ValueError("HTTP 404 Not Found en Relatoría")
        mock_store.return_value = {}

        res = await conector.validate_and_stage_ruling({"sentencia": "C-316/26", "url": url})
        assert res["status"] == "pending_source"
        assert res["source_status"] == "pending_source"
        assert res["retryable"] is True
        assert any("404" in r for r in res["reasons"])


@pytest.mark.asyncio
async def test_retry_queue_exponential_backoff_timing():
    """Comprueba que la cola de reintentos incremente el contador y calcule el backoff exponencial."""
    with patch("app.services.despacho_store.db_request", new_callable=AsyncMock) as mock_store, \
         patch("app.services.conector_corte_constitucional.validate_and_stage_ruling", new_callable=AsyncMock) as mock_stage:

        # 1. Simular elemento en cola de reintentos
        pending_items = [{
            "sentencia": "C-317/26",
            "retry_count": 2,
            "max_retries": 10,
            "tipo": "C",
            "fecha": "2026-09-30",
            "anio": 2026,
            "magistrado": "Carlos Camargo Assis",
        }]

        async def store_side_effect(method, endpoint, key, service=False, json=None):
            if "despacho_listar_pendientes_reintento" in endpoint:
                return pending_items
            return {}

        mock_store.side_effect = store_side_effect
        mock_stage.return_value = {"status": "pending_source", "reasons": ["Aún 404"]}

        res = await conector.retry_pending_source_rulings(limit=5, owner="test_worker")
        assert res["processed_count"] == 1
        assert res["recovered_count"] == 0
        assert res["failed_count"] == 1

        # Verificar que se actualizó el registro con retry_count = 3
        patch_calls = [c for c in mock_store.call_args_list if c[0][0] == "PATCH"]
        assert len(patch_calls) >= 1
        updated_payload = patch_calls[0][1]["json"]
        assert updated_payload["retry_count"] == 3
        assert updated_payload["source_status"] == "pending_source"
        assert "next_retry_at" in updated_payload


# ---------------------------------------------------------------------------
# 3. FENCING TOKEN & DISTRIBUTED LOCK HEARTBEAT
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_lock_heartbeat_renewal_and_fencing_token():
    """Comprueba que el bloqueo concurrente emita un fencing token y lo renueve periódicamente."""
    with patch("app.services.despacho_store.db_request", new_callable=AsyncMock) as mock_store:
        # 1. Adquisición exitosa con fencing token
        mock_store.return_value = {
            "acquired": True,
            "lock_owner": "worker_test_1",
            "fencing_token": 42,
        }
        acquired, token = await conector.acquire_sync_lock_v2(owner="worker_test_1", ttl_seconds=900)
        assert acquired is True
        assert token == 42

        # 2. Renovación de bloqueo exitosa con fencing token coincidente
        mock_store.return_value = True
        renew_ok = await conector.renew_sync_lock(owner="worker_test_1", fencing_token=42, extend_seconds=900)
        assert renew_ok is True

        # 3. Renovación rechazada si el fencing token caducó o fue sobreescrito
        mock_store.return_value = False
        renew_fail = await conector.renew_sync_lock(owner="worker_test_1", fencing_token=41, extend_seconds=900)
        assert renew_fail is False


@pytest.mark.asyncio
async def test_release_sync_lock_requires_matching_fencing_token():
    """Comprueba que la liberación del bloqueo requiera el fencing token activo."""
    with patch("app.services.despacho_store.db_request", new_callable=AsyncMock) as mock_store:
        mock_store.return_value = True
        res = await conector.release_sync_lock_v2(owner="worker_test_1", fencing_token=42)
        assert res is True
        mock_store.assert_called_once()
        assert mock_store.call_args[1]["json"]["p_fencing_token"] == 42


# ---------------------------------------------------------------------------
# 4. RESTART RECOVERY & ORPHAN LOCK CLEARING
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_recover_orphan_locks_on_worker_startup():
    """Comprueba que al reiniciar el contenedor web se detecten y limpien bloqueos huérfanos expirados."""
    with patch("app.services.despacho_store.db_request", new_callable=AsyncMock) as mock_store:
        mock_store.return_value = {
            "cleared": True,
            "cleared_owner": "worker_crashed_99",
            "cleared_fencing_token": 15,
            "message": "Bloqueo huérfano liberado exitosamente tras reinicio",
        }

        orphan_res = await conector.recover_orphan_locks()
        assert orphan_res["cleared"] is True
        assert orphan_res["cleared_owner"] == "worker_crashed_99"


# ---------------------------------------------------------------------------
# 5. ADMINISTRATIVE PAUSE & RESUME
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_administrative_pause_and_resume():
    """Comprueba que la pausa administrativa detenga la ejecución y la reanudación la reactive."""
    with patch("app.services.despacho_store.db_request", new_callable=AsyncMock) as mock_store:
        mock_store.return_value = {}

        # 1. Pausa administrativa
        pause_res = await worker.pause_schedule(reason="Mantenimiento preventivo programado")
        assert pause_res["process_status"] == "paused"
        assert pause_res["schedule_enabled"] is False

        # 2. Reanudación administrativa
        resume_res = await worker.resume_schedule()
        assert resume_res["process_status"] == "idle"
        assert resume_res["schedule_enabled"] is True


# ---------------------------------------------------------------------------
# 6. IMMUTABLE AUDIT TRAIL DIFFERENTIATION
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_audit_trail_distinguishes_human_from_administrative_review():
    """Comprueba que el registro de auditoría distinga taxativamente entre validación técnica automática,
    aprobación administrativa de desarrollo y revisión jurídica humana."""
    with patch("app.services.despacho_store.db_request", new_callable=AsyncMock) as mock_store:
        doc_id = "22222222-3333-4444-5555-666666666666"

        async def store_mock(method, endpoint, key, service=False, json=None):
            if method == "GET" and "despacho_corpus_documentos" in endpoint:
                return [{
                    "id": doc_id,
                    "version": 1,
                    "published": False,
                    "workflow_status": "pending_legal_review",
                    "validation_status": "technically_validated",
                    "metadata": {"sentencia": "T-315/26"},
                }]
            if method == "POST" and "despacho_actualizar_validacion_documento" in endpoint:
                return {
                    "id": doc_id,
                    "validation_status": "approved",
                    "workflow_status": "published",
                    "published": True,
                }
            if method == "POST" and "despacho_registrar_auditoria_revision" in endpoint:
                return {"id": "audit-uuid-1", "registered": True}
            return {}

        mock_store.side_effect = store_mock

        # 1. Registrar revisión jurídica humana formal
        res_human = await conector.review_triage_document(
            document_id=doc_id,
            decision="approve",
            reason="Sentencia revisada y confrontada contra gaceta constitucional",
            review_type="revision_juridica_humana",
            responsible_name="Dra. María Paula González",
            responsible_role="Abogada Relatora Constitucional",
        )
        assert res_human["published"] is True

        # Verificar parámetros pasados a despacho_registrar_auditoria_revision
        audit_calls = [c for c in mock_store.call_args_list if "despacho_registrar_auditoria_revision" in c[0][1]]
        assert len(audit_calls) >= 1
        human_audit = audit_calls[0][1]["json"]
        assert human_audit["p_review_type"] == "revision_juridica_humana"
        assert human_audit["p_responsible_role"] == "Abogada Relatora Constitucional"

        # 2. Registrar aprobación administrativa de prueba
        mock_store.reset_mock()
        res_admin = await conector.review_triage_document(
            document_id=doc_id,
            decision="approve",
            reason="Aprobación técnica de verificación de infraestructura",
            review_type="aprobacion_administrativa",
            responsible_name="Sistema Automatizado / Script",
            responsible_role="Administrador de Sistema",
        )
        assert res_admin["published"] is True
        audit_calls2 = [c for c in mock_store.call_args_list if "despacho_registrar_auditoria_revision" in c[0][1]]
        assert len(audit_calls2) >= 1
        admin_audit = audit_calls2[0][1]["json"]
        assert admin_audit["p_review_type"] == "aprobacion_administrativa"


@pytest.mark.asyncio
async def test_audit_trail_consultation():
    """Comprueba la consulta paginada del historial de auditoría inmutable."""
    with patch("app.services.despacho_store.db_request", new_callable=AsyncMock) as mock_store:
        mock_store.return_value = [{
            "id": "audit-uuid-1",
            "document_id": "doc-uuid-1",
            "review_type": "aprobacion_administrativa",
            "action": "aprobacion_publicacion",
            "responsible_name": "Administrador Técnico",
            "created_at": "2026-10-24T23:00:00Z",
        }]
        audit = await conector.list_audit_trail(limit=10)
        assert isinstance(audit, list)
        assert len(audit) == 1
        assert audit[0]["review_type"] == "aprobacion_administrativa"


# ---------------------------------------------------------------------------
# 7. ROUTER ADMIN ENDPOINTS
# ---------------------------------------------------------------------------

def test_admin_router_endpoints():
    """Verifica la respuesta de los nuevos endpoints administrativos expuestos en FastAPI."""
    client = TestClient(app)

    admin_mock = {
        "id": "00000000-0000-4000-8000-000000000001",
        "email": "admin@example.com",
        "app_metadata": {"role": "admin"},
    }
    with patch("app.main.verificar_acceso", new_callable=AsyncMock, return_value=admin_mock), \
         patch("app.routers.despacho_corpus_fuentes.verificar_acceso", new_callable=AsyncMock, return_value=admin_mock), \
         patch("app.services.limites.limitador.verificar", return_value=None):

        # 1. Pause schedule
        with patch("app.services.conector_corte_worker.pause_schedule", new_callable=AsyncMock) as mock_pause:
            mock_pause.return_value = {"process_status": "paused", "schedule_enabled": False}
            res = client.post("/api/despacho/official/connector/schedule/pause", json={"reason": "Test mantenimiento"})
            assert res.status_code == 200
            assert res.json()["process_status"] == "paused"

        # 2. Resume schedule
        with patch("app.services.conector_corte_worker.resume_schedule", new_callable=AsyncMock) as mock_resume:
            mock_resume.return_value = {"process_status": "idle", "schedule_enabled": True}
            res = client.post("/api/despacho/official/connector/schedule/resume")
            assert res.status_code == 200
            assert res.json()["process_status"] == "idle"

        # 3. List retries
        with patch("app.services.conector_corte_constitucional.list_pending_retries", new_callable=AsyncMock) as mock_retries:
            mock_retries.return_value = [{"sentencia": "C-316/26", "source_status": "pending_source"}]
            res = client.get("/api/despacho/official/connector/retries")
            assert res.status_code == 200
            assert len(res.json()) == 1
            assert res.json()[0]["sentencia"] == "C-316/26"

        # 4. Trigger retries
        with patch("app.services.conector_corte_constitucional.retry_pending_source_rulings", new_callable=AsyncMock) as mock_trig:
            mock_trig.return_value = {"processed_count": 1, "recovered_count": 1, "failed_count": 0}
            res = client.post("/api/despacho/official/connector/retries/trigger", json={"limit": 5, "force": True})
            assert res.status_code == 200
            assert res.json()["recovered_count"] == 1

        # 5. List audit trail
        with patch("app.services.conector_corte_constitucional.list_audit_trail", new_callable=AsyncMock) as mock_audit:
            mock_audit.return_value = [{"review_type": "revision_juridica_humana"}]
            res = client.get("/api/despacho/official/connector/audit")
            assert res.status_code == 200
            assert len(res.json()) == 1
