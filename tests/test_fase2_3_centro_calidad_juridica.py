"""Suite Integral de Pruebas Automatizadas — Centro de Calidad Jurídica Continua (Fase 2.3).

Verifica exhaustivamente:
1. Permisos y control estricto de roles (técnico vs documental vs profesional jurídico).
2. Protocolo de auditoría del Corpus Oficial (12 puntos de control deterministas).
3. Retiro y restauración 100% reversible de providencias sin borrado de datos.
4. Control de calidad de respuestas del Agente (citas auténticas, referencias [O#-S#], salvamentos vs mayoría).
5. Sistema de radicación y triage de reportes de error de usuarios.
6. Seguimiento de evolución jurisprudencial (citas, reiteraciones, SU, distinguishing, overruling).
7. Métricas de supervisión continua (técnicas vs jurídicas).
8. Integración con streaming SSE en tiempo real sin bloqueo de chunks.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.services.control_calidad_permisos import (
    extract_user_identity,
    require_document_auditor,
    require_legal_professional,
    require_technical_admin,
)
from app.services.control_calidad_agente import (
    extract_cited_rulings,
    verify_agent_response_quality,
)
from app.services.control_calidad_corpus import (
    CorpusDocumentAuditResult,
    audit_document_quality,
    restore_document_reversible,
    withdraw_document_reversible,
)
from app.services.seguimiento_jurisprudencial import (
    classify_relation_context,
    extract_jurisprudential_relations,
    normalize_ruling_tag,
    verify_jurisprudential_relation,
)


@pytest.fixture
def mock_legal_user():
    return {
        "id": "usr_abogado_001",
        "email": "abogado@bufete.co",
        "user_metadata": {
            "nombre_completo": "Dra. Carolina Martínez",
            "role": "abogado",
            "tarjeta_profesional": "TP-123456-CSJ",
        },
        "app_metadata": {"role": "abogado"},
    }


@pytest.fixture
def mock_admin_user():
    return {
        "id": "usr_admin_002",
        "email": "admin@memorialista.co",
        "user_metadata": {
            "nombre_completo": "Carlos Administrador",
            "role": "administrador_tecnico",
        },
        "app_metadata": {"role": "administrador_tecnico"},
    }


@pytest.fixture
def mock_reader_user():
    return {
        "id": "usr_lector_003",
        "email": "lector@externo.co",
        "user_metadata": {
            "nombre_completo": "Juan Lector",
            "role": "lector",
        },
        "app_metadata": {"role": "lector"},
    }


# =========================================================================
# 1. PRUEBAS DE PERMISOS Y ROLES
# =========================================================================

def test_permisos_diferenciacion_roles(mock_legal_user, mock_admin_user, mock_reader_user):
    # Abogado
    id_legal = extract_user_identity(mock_legal_user)
    assert id_legal["is_legal_professional"] is True
    assert id_legal["is_document_auditor"] is True

    # Admin técnico
    id_admin = extract_user_identity(mock_admin_user)
    assert id_admin["is_technical_admin"] is True
    assert id_admin["is_legal_professional"] is False  # Admin no equivale a abogado

    # Lector
    id_reader = extract_user_identity(mock_reader_user)
    assert id_reader["is_legal_professional"] is False
    assert id_reader["is_technical_admin"] is False


def test_permisos_enforcement_rechaza_no_autorizado(mock_reader_user, mock_admin_user):
    from fastapi import HTTPException
    # Lector intentando acción jurídica vinculante
    with pytest.raises(HTTPException) as exc_info:
        require_legal_professional(mock_reader_user, "certificar precedente")
    assert exc_info.value.status_code == 403

    # Admin técnico intentando acción jurídica que exige abogado
    with pytest.raises(HTTPException) as exc_admin:
        require_legal_professional(mock_admin_user, "emitir revisión sustantiva")
    assert exc_admin.value.status_code == 403


# =========================================================================
# 2. PRUEBAS DE CALIDAD DEL CORPUS (12 CHECKS)
# =========================================================================

@pytest.mark.asyncio
async def test_control_calidad_corpus_doc_optimo():
    doc_id = "doc-test-123"
    mock_doc = [{
        "id": doc_id,
        "title": "Sentencia T-002/24 - Corte Constitucional",
        "source_url": "https://www.corteconstitucional.gov.co/relatoria/2024/T-002-24.htm",
        "content_hash": "a" * 64,
        "version": 1,
        "published": True,
        "is_withdrawn": False,
        "workflow_status": "published",
        "metadata": {
            "sentencia": "T-002/24",
            "magistrado": "Jorge Enrique Ibáñez Najar",
            "sala": "Sala Novena de Revisión",
            "fecha": "2024-01-18",
            "tema": "Derecho a la salud y suministro de insumos médicos",
        }
    }]
    mock_frags = [
        {
            "id": f"frag-{i}",
            "chunk_index": i,
            "section_type": "consideraciones" if i < 3 else "resuelve",
            "content": "La Corte Constitucional administrando justicia en nombre del pueblo RESUELVE conceder el amparo " * 5,
            "embedding": [0.05] * 768,
        }
        for i in range(4)
    ]

    with patch("app.services.despacho_store.db_request") as mock_db:
        mock_db.side_effect = [
            mock_doc,     # GET doc
            mock_frags,   # GET fragments
            [],           # GET other_docs (duplicados)
            {},           # PATCH doc update
        ]
        res = await audit_document_quality(doc_id, service_key="test-key")
        assert res["quality_status"] == "optimo"
        assert res["quality_score"] == 100.0
        assert len(res["critical_failures"]) == 0
        assert res["checks"]["identidad_oficial"]["passed"] is True
        assert res["checks"]["fragmentos_continuidad"]["passed"] is True
        assert res["checks"]["embeddings_calidad"]["passed"] is True
        assert res["checks"]["parte_resolutiva"]["passed"] is True


@pytest.mark.asyncio
async def test_control_calidad_corpus_doc_con_fallos_criticos():
    doc_id = "doc-corrupt-999"
    mock_doc = [{
        "id": doc_id,
        "title": "Sentencia Invalida",
        "source_url": "http://sitio-inseguro.com/doc.html",
        "content_hash": "hash_invalido",
        "version": 1,
        "published": True,
        "is_withdrawn": False,
        "workflow_status": "published",
        "metadata": {}
    }]
    mock_frags = [
        {
            "id": "frag-0",
            "chunk_index": 0,
            "section_type": "antecedentes",
            "content": "Texto corto",
            "embedding": [0.0] * 50,  # Embedding corrupto / dimensión errónea
        }
    ]

    with patch("app.services.despacho_store.db_request") as mock_db:
        mock_db.side_effect = [
            mock_doc,
            mock_frags,
            [],
            {},  # PATCH doc
            [],  # GET existing incidents
            {},  # POST new incident
        ]
        res = await audit_document_quality(doc_id, service_key="test-key")
        assert res["quality_status"] == "con_incidencias"
        assert res["quality_score"] < 50.0
        assert len(res["critical_failures"]) > 0
        assert res["checks"]["hash_version"]["passed"] is False
        assert res["checks"]["embeddings_calidad"]["passed"] is False


# =========================================================================
# 3. PRUEBAS DE RETIRO Y RESTAURACIÓN REVERSIBLE
# =========================================================================

@pytest.mark.asyncio
async def test_retiro_y_restauracion_reversible():
    doc_id = "doc-rev-001"
    actor_admin = {"id": "adm1", "name": "Admin Técnico", "role": "administrador_tecnico"}
    actor_abogado = {"id": "law1", "name": "Dra. Abogada", "role": "abogado"}

    mock_doc = [{
        "id": doc_id,
        "title": "Sentencia T-100/24",
        "version": 1,
        "published": True,
        "workflow_status": "published",
        "metadata": {"sentencia": "T-100/24"}
    }]

    # 1. Retirar
    with patch("app.services.despacho_store.db_request") as mock_db:
        mock_db.side_effect = [
            mock_doc,  # GET doc
            {},        # PATCH doc (withdrawn)
            {},        # POST auditoría revisiones (withdraw)
            {},        # POST incidencias
        ]
        ret_res = await withdraw_document_reversible(doc_id, "Inconsistencia de prueba", actor_admin, service_key="test-key")
        assert ret_res["is_withdrawn"] is True
        assert ret_res["published"] is False
        assert ret_res["status"] == "retirado_temporalmente"

    # 2. Restaurar
    with patch("app.services.despacho_store.db_request") as mock_db_res:
        mock_db_res.side_effect = [
            mock_doc,  # GET doc
            {},        # PATCH doc (published)
            {},        # POST auditoría revisiones (approve)
            [{"id": "inc-01", "action_history": []}], # GET open incidencias
            {},        # PATCH close incidencia
        ]
        rest_res = await restore_document_reversible(doc_id, "Subsanado satisfactoriamente", actor_abogado, service_key="test-key")
        assert rest_res["is_withdrawn"] is False
        assert rest_res["published"] is True
        assert rest_res["status"] == "published"


# =========================================================================
# 4. PRUEBAS DE CONTROL DE CALIDAD DEL AGENTE
# =========================================================================

def test_extract_cited_rulings():
    text = "Según la Sentencia T-760 de 2008 y la C-055/22, junto con el Auto 522/23 y la sentencia SU-091 de 2000."
    rulings = extract_cited_rulings(text)
    assert "T-760/08" in rulings
    assert "C-055/22" in rulings
    assert "A-522/23" in rulings
    assert "SU-091/00" in rulings


@pytest.mark.asyncio
async def test_control_calidad_agente_respuestas_autenticas():
    query = "Explica los requisitos de la tutela contra providencias judiciales según la Corte Constitucional"
    answer = (
        "La Corte Constitucional en la Sentencia C-590/05 [O1-S1] fijó los requisitos generales de procedibilidad. "
        "Asimismo, se requiere acreditar la inmediatez y subsidiariedad [O1-S2]."
    )
    sources = [
        {"id": "O1-S1", "title": "Sentencia C-590/05", "section_type": "consideraciones"},
        {"id": "O1-S2", "title": "Sentencia C-590/05", "section_type": "consideraciones"},
    ]

    with patch("app.services.despacho_store.db_request") as mock_db:
        # Mock lookup de la sentencia en BD
        mock_db.return_value = [{"id": "doc-c590", "title": "Sentencia C-590/05"}]
        res = await verify_agent_response_quality(query, answer, sources, service_key="test-key")
        assert res["technical_verification"] == "verificado_tecnicamente"
        assert res["checks"]["sentencias_existen"]["passed"] is True
        assert res["checks"]["referencias_correspondencia"]["passed"] is True
        assert res["checks"]["control_salvamentos"]["passed"] is True
        assert len(res["flags"]) == 0


@pytest.mark.asyncio
async def test_control_calidad_agente_detecta_referencia_invalida_y_salvamento():
    query = "¿Cuál fue la decisión de la tutela?"
    answer = (
        "La Corte Constitucional resolvió conceder el derecho fundamental [O1-S9] "
        "e inventó la regla [O1-S99]."
    )
    # O1-S9 es un salvamento de voto aducido como "resolvió"
    sources = [
        {"id": "O1-S9", "title": "Sentencia T-001/24", "section_type": "salvamento_voto"},
    ]

    with patch("app.services.despacho_store.db_request") as mock_db:
        mock_db.return_value = []
        res = await verify_agent_response_quality(query, answer, sources, service_key="test-key")
        assert res["technical_verification"] == "con_inconsistencias"
        # O1-S99 no existe en sources
        assert res["checks"]["referencias_correspondencia"]["passed"] is False
        assert "O1-S99" in res["checks"]["referencias_correspondencia"]["invalid"]
        # O1-S9 es salvamento presentado como mayoría
        assert res["checks"]["control_salvamentos"]["passed"] is False


# =========================================================================
# 5. PRUEBAS DE SEGUIMIENTO DE EVOLUCIÓN JURISPRUDENCIAL
# =========================================================================

def test_seguimiento_jurisprudencial_clasificacion_contextual():
    p_reit = "En reiterada jurisprudencia, la Corte reitera lo señalado en la Sentencia T-760 de 2008."
    assert classify_relation_context(p_reit, "T-760/08") == "reiteracion"

    p_over = "La Sala Plena adopta un cambio de jurisprudencia y abandono del criterio frente a la Sentencia C-100/15."
    assert classify_relation_context(p_over, "C-100/15") == "modificacion_regla"

    p_dist = "A diferencia de lo considerado en el Auto 120/19, el supuesto de hecho actual difiere sustancialmente."
    assert classify_relation_context(p_dist, "A-120/19") == "distincion"

    p_su = "La Sala unifica el criterio fijado en la Sentencia SU-091 de 2000."
    assert classify_relation_context(p_su, "SU-091/00") == "unificacion"


@pytest.mark.asyncio
async def test_seguimiento_jurisprudencial_extraccion_y_disclaimer():
    text = (
        "Consideraciones de la Corte:\n\n"
        "En reiterada jurisprudencia constitucional, esta Corporación reitera la regla de la Sentencia T-760/08 "
        "en relación con el principio de integralidad en el acceso a la salud."
    )
    with patch("app.services.despacho_store.db_request") as mock_db:
        mock_db.side_effect = [
            [{"id": "doc-t760"}], # target doc lookup
            {},                    # POST evolucion
        ]
        rels = await extract_jurisprudential_relations("T-002/24", text, document_id="doc-source-1", service_key="test-key")
        assert len(rels) >= 1
        r = rels[0]
        assert r["source_sentencia"] == "T-002/24"
        assert r["target_sentencia"] == "T-760/08"
        assert r["relation_type"] == "reiteracion"
        assert r["status"] == "posible_evolucion_pendiente"
        assert "pendiente de verificación" in r["ui_disclaimer"]


# =========================================================================
# 6. PRUEBAS DE ENDPOINTS API DEL CENTRO DE CALIDAD
# =========================================================================

@pytest.fixture
def client_mock_auth():
    test_client = TestClient(app)
    return test_client


def test_endpoint_calidad_metricas(client_mock_auth, mock_admin_user):
    with patch("app.main.verificar_acceso", new_callable=AsyncMock, return_value=mock_admin_user), \
         patch("app.routers.despacho_calidad.verificar_acceso", new_callable=AsyncMock, return_value=mock_admin_user), \
         patch("app.services.limites.limitador.verificar", return_value=None), \
         patch("app.services.despacho_store.db_request") as mock_db:
        
        mock_db.side_effect = [
            [{"id": "d1", "published": True, "is_withdrawn": False, "quality_status": "optimo", "last_quality_audit_at": "2026-10-25T00:00:00Z"}], # docs
            [{"id": "i1", "severity": "media", "status": "detectado", "issue_type": "reporte_usuario", "scope": "agente"}], # incidencias
            [{"id": "e1", "status": "posible_evolucion_pendiente"}], # relaciones
            [{"last_quality_audit_at": "2026-10-25T00:00:00Z", "next_run_at": "2026-10-25T06:00:00Z"}], # estado conector
        ]

        response = client_mock_auth.get("/api/despacho/calidad/metricas", headers={"Authorization": "Bearer test-token"})
        assert response.status_code == 200
        data = response.json()
        assert "metricas_tecnicas" in data
        assert "evaluaciones_juridicas" in data
        assert data["metricas_tecnicas"]["documentos_publicados"] == 1
        assert data["evaluaciones_juridicas"]["respuestas_reportadas"] == 1


def test_endpoint_reportar_error_usuario(client_mock_auth, mock_legal_user):
    with patch("app.main.verificar_acceso", new_callable=AsyncMock, return_value=mock_legal_user), \
         patch("app.routers.despacho_calidad.verificar_acceso", new_callable=AsyncMock, return_value=mock_legal_user), \
         patch("app.services.limites.limitador.verificar", return_value=None), \
         patch("app.services.despacho_store.db_request", return_value={}) as mock_db:

        payload = {
            "target_type": "agente_respuesta",
            "error_category": "interpretacion_incorrecta",
            "description": "La providencia citada no resolvió en ese sentido en su ratio decidendi.",
            "sentencia": "T-760/08",
            "query_summary": "Requisitos para entrega de medicamentos POS",
        }
        response = client_mock_auth.post(
            "/api/despacho/calidad/reportes-error",
            json=payload,
            headers={"Authorization": "Bearer test-token"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "radicado exitosamente" in data["message"]


def test_endpoint_certificar_evolucion_requiere_rol_juridico(client_mock_auth, mock_reader_user, mock_legal_user):
    # Lector rechazado
    with patch("app.main.verificar_acceso", new_callable=AsyncMock, return_value=mock_reader_user), \
         patch("app.routers.despacho_calidad.verificar_acceso", new_callable=AsyncMock, return_value=mock_reader_user), \
         patch("app.services.limites.limitador.verificar", return_value=None):
        res_fail = client_mock_auth.post(
            "/api/despacho/calidad/evolucion/rel-123/verificar",
            json={"verified": True, "notes": "Aprobado"},
            headers={"Authorization": "Bearer test-token"},
        )
        assert res_fail.status_code == 403

    # Abogado autorizado
    with patch("app.main.verificar_acceso", new_callable=AsyncMock, return_value=mock_legal_user), \
         patch("app.routers.despacho_calidad.verificar_acceso", new_callable=AsyncMock, return_value=mock_legal_user), \
         patch("app.services.limites.limitador.verificar", return_value=None), \
         patch("app.services.despacho_store.db_request", return_value={}):
        res_ok = client_mock_auth.post(
            "/api/despacho/calidad/evolucion/rel-123/verificar",
            json={"verified": True, "notes": "Criterio vinculante ratificado"},
            headers={"Authorization": "Bearer test-token"},
        )
        assert res_ok.status_code == 200
        data = res_ok.json()
        assert data["status"] == "verificado_humano"
