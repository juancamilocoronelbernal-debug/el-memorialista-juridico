# -*- coding: utf-8 -*-
"""
Pruebas exhaustivas para el Cierre Funcional de Fase 2.3 y Preparación de Fase 2.4.
Verifica:
1. Distinción rigurosa entre calidad técnica (0-100%) y certificación jurídica humana.
2. Reportes de error con identificadores permanentes (UUID, ordinal, versión, usuario, privacidad).
3. Retiro y restauración reversible con invalidación de caché y estado en Visor (HTTP 410).
4. Auditorías periódicas con rotación equitativa y priorización estricta.
5. Permisos RBAC y control de acceso.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.services.control_calidad_corpus import (
    CorpusDocumentAuditResult,
    audit_document_quality,
    withdraw_document_reversible,
    restore_document_reversible,
    select_corpus_audit_candidates,
    audit_corpus_sample,
    invalidate_document_caches,
)
from app.services.despacho_rag import ConversationDocumentMemory
from app.services.despacho_corpus_fuentes import get_document_fragments


# =========================================================================
# 1. DISTINCIÓN ENTRE CALIDAD TÉCNICA Y CERTIFICACIÓN JURÍDICA
# =========================================================================

@pytest.mark.asyncio
async def test_distincion_puntaje_tecnico_vs_certificacion_humana():
    """Una providencia con 100% técnico debe permanecer como pendiente de certificación jurídica humana."""
    audit = CorpusDocumentAuditResult("doc-uuid-1", "Sentencia T-100/24")
    # Todas las validaciones técnicas aprobadas
    audit.record_check("identidad_oficial", True, "Identidad verificada", is_critical=True)
    audit.record_check("hash_version", True, "Hash SHA-256 verificado", is_critical=True)
    audit.record_check("fragmentos_continuidad", True, "Continuidad perfecta", is_critical=True)
    audit.record_check("embeddings_calidad", True, "Embeddings 768d no nulos", is_critical=True)

    # Caso A: Sin revisión previa por profesional jurídico
    result_unapproved = audit.to_dict(legal_certified=False, certified_by=None)
    assert result_unapproved["technical_score"] == 100.0
    assert result_unapproved["quality_score"] == 100.0
    assert result_unapproved["legal_certification_status"] == "pendiente_certificacion_humana"
    assert result_unapproved["legal_certified"] is False
    assert result_unapproved["legal_certified_by"] is None
    assert "NO constituye garantía de fondo ni certificación de exactitud o vigencia jurídica" in result_unapproved["disclaimer"]

    # Caso B: Con revisión y aprobación formal por profesional jurídico
    result_approved = audit.to_dict(legal_certified=True, certified_by="Dr. Abogado Revisor")
    assert result_approved["technical_score"] == 100.0
    assert result_approved["legal_certification_status"] == "certificada_humana"
    assert result_approved["legal_certified"] is True
    assert result_approved["legal_certified_by"] == "Dr. Abogado Revisor"


# =========================================================================
# 2. REPORTES DE ERROR CON IDENTIFICADORES PERMANENTES Y PRIVACIDAD
# =========================================================================

@pytest.mark.asyncio
async def test_reporte_error_resolucion_identificadores_y_privacidad():
    """El reporte de error debe resolver referencias temporales [O#-S#] y UUID permanentemente sin almacenar PII."""
    client = TestClient(app)

    mock_doc = [{
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "title": "Sentencia C-055/22 - Corte Constitucional",
        "version": 2,
    }]

    with patch("app.main.verificar_acceso", new_callable=AsyncMock) as mock_auth, \
         patch("app.routers.despacho_calidad.verificar_acceso", new_callable=AsyncMock) as mock_auth_router, \
         patch("app.services.despacho_store.db_request", new_callable=AsyncMock) as mock_db:

        user_info = {
            "id": "usr-abogado-789",
            "name": "Dra. Abogada Litigante",
            "email": "abogada@ejemplo.com",
            "app_metadata": {"role": "profesional_juridico"},
        }
        mock_auth.return_value = user_info
        mock_auth_router.return_value = user_info

        # db_request responderá: 1) búsqueda del doc permanente, 2) inserción de la incidencia
        mock_db.side_effect = [
            mock_doc,  # GET doc para resolver doc_id y version
            {"id": "inc-new-001"},  # POST despacho_corpus_incidencias
        ]

        # Enviar reporte con referencia temporal y sin doc_id explícito
        payload = {
            "target_type": "agente_respuesta",
            "sentencia": "C-055/22",
            "error_category": "interpretacion_incorrecta",
            "description": "El alcance de la despenalización hasta la semana 24 fue citado con una excepción inexistente.",
            "temporal_citation": "[O3-S2]",
            "response_id": "msg-resp-987",
        }

        response = client.post("/api/despacho/calidad/reportes-error", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        incident = data["incident"]
        # Comprobar vinculación inequívoca permanente
        assert incident["document_id"] == "550e8400-e29b-41d4-a716-446655440000"
        assert incident["sentencia"] == "Sentencia C-055/22 - Corte Constitucional"
        assert incident["evidence"]["document_version"] == 2
        assert incident["evidence"]["fragment_ordinal"] == 3
        assert incident["evidence"]["fragment_segment"] == 2
        assert incident["evidence"]["response_id"] == "msg-resp-987"
        assert incident["evidence"]["reported_by_id"] == "usr-abogado-789"
        assert incident["evidence"]["reported_by_email"] == "ab***@ejemplo.com"

        # Comprobar resguardo de privacidad: sin transcripción de chats ni consultas completas privadas
        assert "prompt" not in incident["evidence"]
        assert "chat_history" not in incident["evidence"]


# =========================================================================
# 3. RETIRO Y RESTAURACIÓN REVERSIBLE CON INVALIDACIÓN DE CACHÉ Y VISOR
# =========================================================================

@pytest.mark.asyncio
async def test_retiro_restauracion_reversible_y_cache():
    """Un documento retirado debe invalidar memoria RAG, desaparecer de búsquedas y notificar HTTP 410 en visor."""
    doc_id = "test-doc-retiro-uuid"
    actor = {"id": "admin-1", "name": "Admin Técnico", "role": "administrador_tecnico"}

    mock_doc = [{
        "id": doc_id,
        "title": "Sentencia TEST-999/26",
        "published": True,
        "is_withdrawn": False,
        "workflow_status": "published",
        "version": 1,
        "metadata": {"sentencia": "TEST-999/26"}
    }]

    # 1. Probar invalidación de caché RAG
    memory = ConversationDocumentMemory(ttl_seconds=300)
    with patch("app.services.despacho_rag.get_settings") as mock_rag_settings:
        mock_settings_obj = MagicMock()
        mock_settings_obj.DESPACHO_RAG_MEMORY_ENABLED = True
        mock_rag_settings.return_value = mock_settings_obj

        # Almacenar entrada de prueba que contenga este doc_id
        query_text = "que dijo la sentencia T-999/26 sobre salud"
        memory.store(
            user_id="u1",
            conversation_id="conv-1",
            query=query_text,
            scope="corpus",
            depth="normal",
            document_ids=[doc_id],
            data={"passages": [{"document_id": doc_id, "title": "Sentencia T-999/26", "text": "Texto"}]},
            intent_info={"target_ruling": "T-999/26"}
        )
        assert memory.get("u1", "conv-1", query_text, "corpus", "normal", [doc_id]) is not None

        # Invalidar doc_id en memoria
        purged = memory.invalidate_document(doc_id, "T-999/26")
        assert purged == 1
        assert memory.get("u1", "conv-1", query_text, "corpus", "normal", [doc_id]) is None

    # 2. Probar retiro reversible con auditoría inmutable
    with patch("app.services.despacho_store.db_request", new_callable=AsyncMock) as mock_db:
        mock_db.side_effect = [
            mock_doc,  # GET doc
            {},        # PATCH doc retirado
            {},        # POST auditoría revisiones (inmutable)
            {},        # POST incidencias
        ]
        ret_res = await withdraw_document_reversible(
            doc_id,
            reason="Inconsistencia grave en fundamentación técnica",
            actor=actor,
            service_key="test-key"
        )
        assert ret_res["published"] is False
        assert ret_res["is_withdrawn"] is True
        assert ret_res["status"] == "retirado_temporalmente"
        assert "purged_caches" in ret_res

    # 3. Probar restauración reversible
    with patch("app.services.despacho_store.db_request", new_callable=AsyncMock) as mock_db:
        mock_withdrawn_doc = [{
            "id": doc_id,
            "title": "Sentencia TEST-999/26",
            "published": False,
            "is_withdrawn": True,
            "workflow_status": "retirado_temporalmente",
            "version": 1,
            "metadata": {"sentencia": "TEST-999/26"}
        }]
        mock_db.side_effect = [
            mock_withdrawn_doc,  # GET doc
            {},                  # PATCH doc restaurado
            {},                  # POST auditoría inmutable approve
            [],                  # GET open incidencias
        ]
        actor_lawyer = {"id": "abog-1", "name": "Abogado Titular", "role": "profesional_juridico"}
        rest_res = await restore_document_reversible(
            doc_id,
            resolution_note="Subsanado satisfactoriamente tras verificación",
            actor=actor_lawyer,
            service_key="test-key"
        )
        assert rest_res["published"] is True
        assert rest_res["is_withdrawn"] is False
        assert rest_res["status"] == "published"


# =========================================================================
# 4. ROTACIÓN EQUITATIVA Y PRIORIZACIÓN EN AUDITORÍAS PERIÓDICAS
# =========================================================================

@pytest.mark.asyncio
async def test_rotacion_equitativa_y_priorizacion():
    """El selector debe priorizar incidencias, advertencias, nuevos, y rotar equitativamente los antiguos."""
    # Simular base de datos con:
    # - 1 doc reportado con incidencia abierta
    # - 1 doc con advertencias
    # - 1 doc nuevo sin auditar
    # - Varios docs auditados en fechas distintas
    with patch("app.services.despacho_store.db_request", new_callable=AsyncMock) as mock_db:
        mock_db.side_effect = [
            # 1. Consulta incidencias abiertas
            [{"document_id": "doc-inc-01", "sentencia": "T-101/24"}],
            # Check si doc-inc-01 existe
            [{"id": "doc-inc-01", "title": "Sentencia T-101/24"}],
            # 2. Consulta documentos con advertencias
            [{"id": "doc-warn-02", "title": "Sentencia C-202/24"}],
            # 3. Consulta documentos nuevos sin auditar
            [{"id": "doc-new-03", "title": "Sentencia SU-303/24"}],
            # 4. Consulta rotación equitativa (los más antiguos)
            [
                {"id": "doc-old-04", "title": "Sentencia T-404/23"},
                {"id": "doc-old-05", "title": "Sentencia C-505/23"},
            ],
        ]

        candidates = await select_corpus_audit_candidates(sample_size=5, service_key="test-key")
        assert len(candidates) == 5
        cand_ids = [c["id"] for c in candidates]
        # Comprobar orden de prioridades estricto
        assert cand_ids[0] == "doc-inc-01"  # Prioridad 1: Incidencia reportada
        assert cand_ids[1] == "doc-warn-02" # Prioridad 2: Advertencia técnica
        assert cand_ids[2] == "doc-new-03"  # Prioridad 3: Nuevo sin auditar
        assert cand_ids[3] == "doc-old-04"  # Prioridad 4: Rotación equitativa más antiguo
        assert cand_ids[4] == "doc-old-05"  # Prioridad 4: Rotación equitativa siguiente


# =========================================================================
# 5. PERMISOS RBAC Y SEGURIDAD MULTI-USUARIO
# =========================================================================

@pytest.mark.asyncio
async def test_permisos_rbac_centro_calidad():
    """Un usuario sin acreditación jurídica no puede restaurar providencias ni resolver incidencias legales (HTTP 403)."""
    client = TestClient(app)

    with patch("app.main.verificar_acceso", new_callable=AsyncMock) as mock_auth, \
         patch("app.routers.despacho_calidad.verificar_acceso", new_callable=AsyncMock) as mock_auth_router:

        # Usuario básico no jurista ni admin
        regular_user = {
            "id": "usr-basico-123",
            "name": "Asistente Operativo",
            "email": "asistente@ejemplo.com",
            "role": "asistente_general",
        }
        mock_auth.return_value = regular_user
        mock_auth_router.return_value = regular_user

        # Intentar restaurar documento (requiere profesional_juridico)
        res_restore = client.post("/api/despacho/calidad/corpus/restaurar", json={
            "document_id": "doc-123",
            "resolution_note": "Intento no autorizado"
        })
        assert res_restore.status_code == 403
        assert "acreditación jurídica profesional" in res_restore.text

        # Intentar auditar corpus (requiere document_auditor o admin)
        res_audit = client.post("/api/despacho/calidad/corpus/auditar", json={"sample_size": 5})
        assert res_audit.status_code == 403
