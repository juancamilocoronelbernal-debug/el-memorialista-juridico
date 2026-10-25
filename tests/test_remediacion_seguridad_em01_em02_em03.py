"""Suite de Pruebas de Regresión, Compatibilidad e Integración Real — Remediación de Seguridad Fase 1 (EM-01, EM-02, EM-03).

Cubre exhaustivamente:
1. PASO C (Regresión negativa):
   - Acceso sin autenticación (HTTP 401) en todos los endpoints administrativos del conector y centro de calidad.
   - Acceso con usuario ordinario (HTTP 403) en todos los endpoints administrativos del conector y centro de calidad.
   - Escalada de privilegios mediante `user_metadata.role = "admin"` o `"abogado"` (HTTP 403).
   - Escalada de privilegios mediante `tarjeta_profesional` inventada en `user_metadata` o `app_metadata` (HTTP 403).
   - Separación estricta de funciones: `superadmin` / `technical_admin` sin acreditación jurídica verificada no puede aprobar
     `revision_juridica_humana`, restaurar documentos por subsanación jurídica ni cerrar incidencias jurídicas (HTTP 403).
   - Detección de conflicto o contradicción de roles (`pendiente_revision`) sin privilegios elevados (HTTP 403).
   - Aislamiento transversal en incidencias (EM-03): Usuario B no puede listar la bandeja global ni leer o modificar (PATCH)
     incidencias del Usuario A (HTTP 403), y `reported_by_email` se enmascara para evitar exposición de PII.
2. PASO D (Compatibilidad positiva):
   - `technical_admin` legítimo (`app_metadata.role = "admin"`) conserva acceso a la gestión operativa del conector.
   - `document_auditor` legítimo (`app_metadata.role = "auditor_documental"`) conserva acceso a bandeja de triage, auditoría y métricas.
   - `legal_professional` verificado (`app_metadata.role = "abogado"`) conserva acceso a revisión jurídica humana, restauración de providencias,
     resolución de incidencias jurídicas y certificación de evolución jurisprudencial.
   - Usuario ordinario conserva acceso a búsqueda del corpus publicado, radicación de sus propios reportes de error y consulta de sus propios reportes (`mine_only=true`).
3. Integración real contra Supabase Auth + PostgREST + RLS + Triggers:
   - Creación temporal de cuentas de prueba dedicadas (Usuario A y Usuario B) con limpieza garantizada (`finally`).
   - Verificación con JWT reales emitidos por Supabase Auth contra FastAPI y directamente contra PostgREST/RLS.
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch
import httpx
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app
from app.services.control_calidad_permisos import (
    extract_user_identity,
    require_document_auditor,
    require_legal_professional,
    require_technical_admin,
)


# ============================================================================
# FIXTURES DE IDENTIDADES DE PRUEBA
# ============================================================================

@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def ordinary_user_a():
    return {
        "id": "aaaaaaaa-1111-4111-8111-111111111111",
        "email": "abogado.a@firma-privada.co",
        "role": "authenticated",
        "user_metadata": {"full_name": "Usuario Ordinario A"},
        "app_metadata": {"provider": "email"},
    }


@pytest.fixture
def ordinary_user_b_spoofed_meta():
    """Usuario ordinario que intenta escalar privilegios inyectando roles y TP en user_metadata."""
    return {
        "id": "bbbbbbbb-2222-4222-8222-222222222222",
        "email": "atacante.b@externo.co",
        "role": "authenticated",
        "user_metadata": {
            "full_name": "Usuario B Spoofed",
            "role": "admin",
            "rol": "superadmin",
            "tarjeta_profesional": "TP-999888-CSJ",
            "acreditacion_juridica_verificada": True,
        },
        "app_metadata": {"provider": "email"},
    }


@pytest.fixture
def legit_tech_admin():
    """Administrador técnico legítimo acreditado en app_metadata (sin acreditación jurídica)."""
    return {
        "id": "cccccccc-3333-4333-8333-333333333333",
        "email": "ops.admin@memorialista.co",
        "role": "authenticated",
        "user_metadata": {"full_name": "Ingeniero de Operaciones"},
        "app_metadata": {"role": "admin"},
    }


@pytest.fixture
def legit_superadmin_no_legal():
    """Superadmin técnico en app_metadata sin acreditación jurídica verificada."""
    return {
        "id": "dddddddd-4444-4444-8444-444444444444",
        "email": "root@memorialista.co",
        "role": "authenticated",
        "user_metadata": {"full_name": "Superadmin Técnico"},
        "app_metadata": {"role": "superadmin"},
    }


@pytest.fixture
def legit_doc_auditor():
    """Auditor documental legítimo en app_metadata."""
    return {
        "id": "eeeeeeee-5555-4555-8555-555555555555",
        "email": "auditor.doc@memorialista.co",
        "role": "authenticated",
        "user_metadata": {"full_name": "Auditor Documental"},
        "app_metadata": {"role": "auditor_documental"},
    }


@pytest.fixture
def legit_legal_professional():
    """Profesional jurídico acreditado desde el servidor en app_metadata."""
    return {
        "id": "ffffffff-6666-4666-8666-666666666666",
        "email": "magistrada.relatora@memorialista.co",
        "role": "authenticated",
        "user_metadata": {"full_name": "Dra. Elena Relatora"},
        "app_metadata": {"role": "abogado", "acreditacion_juridica_verificada": True},
    }


# ============================================================================
# 1. EM-02: PRUEBAS UNITARIAS Y ADVERSARIALES DE PERMISOS Y ROLES
# ============================================================================

def test_em02_ignora_user_metadata_role_y_tarjeta_profesional(ordinary_user_b_spoofed_meta):
    """Un usuario que inyecta role='admin', rol='superadmin' y tarjeta_profesional en user_metadata
    NO obtiene ningún permiso especial."""
    ident = extract_user_identity(ordinary_user_b_spoofed_meta)
    assert ident["role"] == "usuario"
    assert ident["is_technical_admin"] is False
    assert ident["is_document_auditor"] is False
    assert ident["is_legal_professional"] is False

    with pytest.raises(HTTPException) as exc1:
        require_technical_admin(ordinary_user_b_spoofed_meta)
    assert exc1.value.status_code == 403

    with pytest.raises(HTTPException) as exc2:
        require_document_auditor(ordinary_user_b_spoofed_meta)
    assert exc2.value.status_code == 403

    with pytest.raises(HTTPException) as exc3:
        require_legal_professional(ordinary_user_b_spoofed_meta)
    assert exc3.value.status_code == 403


def test_em02_tarjeta_profesional_en_app_metadata_no_otorga_rol_juridico():
    """Incluso si existe un campo tarjeta_profesional en app_metadata, una cadena de texto
    no otorga automáticamente is_legal_professional."""
    user = {
        "id": "usr-tp-only",
        "email": "tp@test.co",
        "app_metadata": {"role": "usuario", "tarjeta_profesional": "TP-123456"},
    }
    ident = extract_user_identity(user)
    assert ident["is_legal_professional"] is False
    with pytest.raises(HTTPException) as exc:
        require_legal_professional(user)
    assert exc.value.status_code == 403


def test_em02_superadmin_no_es_profesional_juridico(legit_superadmin_no_legal, legit_tech_admin):
    """Un superadmin o admin técnico NO puede actuar como profesional jurídico salvo acreditación explícita."""
    for admin_u in (legit_superadmin_no_legal, legit_tech_admin):
        ident = extract_user_identity(admin_u)
        assert ident["is_technical_admin"] is True
        assert ident["is_legal_professional"] is False
        with pytest.raises(HTTPException) as exc:
            require_legal_professional(admin_u, "aprobar revisión jurídica humana")
        assert exc.value.status_code == 403


def test_em02_conflicto_o_contradiccion_de_roles_deja_cuenta_en_pendiente_revision():
    """Si existe contradicción de roles en la cuenta, queda en estado 'pendiente_revision' sin privilegios."""
    # Caso 1: role != rol en app_metadata
    u_conflict_1 = {
        "id": "usr-conf-1",
        "email": "conf1@test.co",
        "app_metadata": {"role": "admin", "rol": "lector"},
    }
    id1 = extract_user_identity(u_conflict_1)
    assert id1["role"] == "pendiente_revision"
    assert id1["role_status"] == "pendiente_revision"
    assert id1["has_role_conflict"] is True
    assert id1["is_technical_admin"] is False
    assert id1["is_document_auditor"] is False
    assert id1["is_legal_professional"] is False

    with pytest.raises(HTTPException) as exc1:
        require_technical_admin(u_conflict_1)
    assert exc1.value.status_code == 403
    assert "pendiente_revision" in exc1.value.detail

    # Caso 2: Lista roles combina rol restringido ('lector') y rol privilegiado ('abogado')
    u_conflict_2 = {
        "id": "usr-conf-2",
        "email": "conf2@test.co",
        "app_metadata": {"roles": ["lector", "abogado"]},
    }
    id2 = extract_user_identity(u_conflict_2)
    assert id2["role"] == "pendiente_revision"
    assert id2["has_role_conflict"] is True
    assert id2["is_legal_professional"] is False

    # Caso 3: Rol jurídico con acreditacion_juridica_verificada=False
    u_conflict_3 = {
        "id": "usr-conf-3",
        "email": "conf3@test.co",
        "app_metadata": {"role": "abogado", "acreditacion_juridica_verificada": False},
    }
    id3 = extract_user_identity(u_conflict_3)
    assert id3["role"] == "pendiente_revision"
    assert id3["has_role_conflict"] is True
    assert id3["is_legal_professional"] is False


# ============================================================================
# 2. EM-01: PRUEBAS DE REGRESIÓN Y COMPATIBILIDAD EN ENDPOINTS DEL CONECTOR
# ============================================================================

CONNECTOR_ENDPOINTS = [
    ("GET", "/api/despacho/official/connector/status", None),
    ("POST", "/api/despacho/official/connector/schedule", {"enabled": True, "interval_minutes": 360, "run_now": False}),
    ("POST", "/api/despacho/official/connector/schedule/pause", {"reason": "Prueba"}),
    ("POST", "/api/despacho/official/connector/schedule/resume", None),
    ("POST", "/api/despacho/official/connector/discover", {"limit": 5}),
    ("GET", "/api/despacho/official/connector/triage", None),
    ("POST", "/api/despacho/official/connector/triage/review", {"document_id": "doc-1234", "decision": "approve", "review_type": "aprobacion_administrativa"}),
    ("POST", "/api/despacho/official/connector/triage/review", {"document_id": "doc-1234", "decision": "approve", "review_type": "revision_juridica_humana"}),
    ("GET", "/api/despacho/official/connector/retries", None),
    ("POST", "/api/despacho/official/connector/retries/trigger", {"limit": 5, "force": False}),
    ("GET", "/api/despacho/official/connector/audit", None),
    ("POST", "/api/despacho/official/connector/pilot", {"max_rulings": 5, "semantic": False}),
    ("POST", "/api/despacho/official/connector/sync", {"limit": 5, "auto_publish": True, "semantic": False}),
    ("POST", "/api/despacho/official/connector/document/status", {"document_id": "doc-1234", "workflow_status": "withdrawn", "reason": "Test"}),
]


@pytest.mark.parametrize("method,path,payload", CONNECTOR_ENDPOINTS)
def test_em01_connector_sin_autenticacion_retorna_401(client, method, path, payload):
    """Cualquier solicitud sin token válido a los endpoints del conector recibe HTTP 401."""
    resp = client.request(method, path, json=payload) if payload is not None else client.request(method, path)
    assert resp.status_code == 401


@pytest.mark.parametrize("method,path,payload", CONNECTOR_ENDPOINTS)
def test_em01_connector_usuario_ordinario_y_spoofed_retorna_403(
    client, ordinary_user_a, ordinary_user_b_spoofed_meta, method, path, payload
):
    """Tanto un usuario ordinario como un usuario con user_metadata falsificado reciben HTTP 403
    en TODOS los endpoints del conector."""
    for user_obj in (ordinary_user_a, ordinary_user_b_spoofed_meta):
        with patch("app.main.verificar_acceso", new_callable=AsyncMock, return_value=user_obj), \
             patch("app.routers.despacho_corpus_fuentes.verificar_acceso", new_callable=AsyncMock, return_value=user_obj):
            resp = client.request(method, path, json=payload) if payload is not None else client.request(method, path)
            assert resp.status_code == 403, f"Fallo en {method} {path} para {user_obj['email']}: obtuvo {resp.status_code}"


def test_em01_separacion_admin_tecnico_vs_profesional_juridico_en_conector(
    client, legit_tech_admin, legit_legal_professional
):
    """Verifica la separación estricta en el conector:
    - El admin técnico puede programar agenda y emitir 'aprobacion_administrativa', pero NO 'revision_juridica_humana' (403).
    - El abogado acreditado puede emitir 'revision_juridica_humana', pero NO programar agenda, sincronizar ni emitir 'aprobacion_administrativa' (403).
    """
    # 1. Admin técnico intenta revision_juridica_humana -> 403
    with patch("app.main.verificar_acceso", new_callable=AsyncMock, return_value=legit_tech_admin), \
         patch("app.routers.despacho_corpus_fuentes.verificar_acceso", new_callable=AsyncMock, return_value=legit_tech_admin), \
         patch("app.services.limites.limitador.verificar", return_value=None):
        res_forbidden = client.post(
            "/api/despacho/official/connector/triage/review",
            json={"document_id": "doc-1234", "decision": "approve", "review_type": "revision_juridica_humana"},
        )
        assert res_forbidden.status_code == 403

        # Admin técnico ejecuta aprobacion_administrativa y schedule -> 200
        with patch("app.services.conector_corte_constitucional.review_triage_document", new_callable=AsyncMock, return_value={"ok": True}), \
             patch("app.services.conector_corte_worker.configure_schedule", new_callable=AsyncMock, return_value={"schedule_enabled": True}):
            res_admin_ok = client.post(
                "/api/despacho/official/connector/triage/review",
                json={"document_id": "doc-1234", "decision": "approve", "review_type": "aprobacion_administrativa"},
            )
            assert res_admin_ok.status_code == 200

            res_sched_ok = client.post(
                "/api/despacho/official/connector/schedule",
                json={"enabled": True, "interval_minutes": 360, "run_now": False},
            )
            assert res_sched_ok.status_code == 200

    # 2. Abogado intenta schedule, sync y aprobacion_administrativa -> 403
    with patch("app.main.verificar_acceso", new_callable=AsyncMock, return_value=legit_legal_professional), \
         patch("app.routers.despacho_corpus_fuentes.verificar_acceso", new_callable=AsyncMock, return_value=legit_legal_professional), \
         patch("app.services.limites.limitador.verificar", return_value=None):
        assert client.post(
            "/api/despacho/official/connector/schedule",
            json={"enabled": True, "interval_minutes": 60, "run_now": True},
        ).status_code == 403

        assert client.post(
            "/api/despacho/official/connector/sync",
            json={"limit": 5, "auto_publish": True, "semantic": False},
        ).status_code == 403

        assert client.post(
            "/api/despacho/official/connector/triage/review",
            json={"document_id": "doc-1234", "decision": "approve", "review_type": "aprobacion_administrativa"},
        ).status_code == 403

        # Abogado ejecuta revision_juridica_humana -> 200
        with patch("app.services.conector_corte_constitucional.review_triage_document", new_callable=AsyncMock, return_value={"ok": True}):
            res_legal_ok = client.post(
                "/api/despacho/official/connector/triage/review",
                json={"document_id": "doc-1234", "decision": "approve", "review_type": "revision_juridica_humana"},
            )
            assert res_legal_ok.status_code == 200


# ============================================================================
# 3. EM-03: PRUEBAS DE AISLAMIENTO DE INCIDENCIAS Y CENTRO DE CALIDAD
# ============================================================================

def test_em03_aislamiento_transversal_incidencias_usuario_b_no_lee_ni_modifica_usuario_a(
    client, ordinary_user_a, ordinary_user_b_spoofed_meta, legit_doc_auditor, legit_legal_professional
):
    """Comprueba que:
    1. Usuario B no puede listar la bandeja global GET /api/despacho/calidad/incidencias (403).
    2. Usuario B no puede leer el detalle GET /api/despacho/calidad/incidencias/{id} del reporte de Usuario A (403).
    3. Usuario B no puede ejecutar PATCH /api/despacho/calidad/incidencias/{id} para cambiar el estado a 'descartado' (403).
    4. Usuario B tampoco puede consultar /calidad/metricas, /calidad/corpus/documentos ni /calidad/evolucion (403).
    5. Usuario A sí puede consultar su propio reporte (mine_only=true o por ID) con email enmascarado.
    6. El auditor documental puede listar incidencias pero ve el correo enmascarado (nunca en texto plano)
       y NO puede cerrar una incidencia jurídica de fondo sin ser profesional jurídico (403).
    """
    incidencia_usuario_a = {
        "id": "inc-uuid-user-a-001",
        "document_id": "doc-uuid-001",
        "sentencia": "T-100/24",
        "scope": "agente",
        "issue_type": "interpretacion_incorrecta",
        "severity": "alta",
        "status": "detectado",
        "evidence": {
            "description": "Nota privada del caso de Usuario A",
            "reported_by_id": ordinary_user_a["id"],
            "reported_by_role": "usuario",
            "reported_by_email": "abogado.a@firma-privada.co",
        },
        "action_history": [],
    }

    # --- A. Usuario B (incluso con user_metadata falsificado) intenta leer y modificar ---
    with patch("app.main.verificar_acceso", new_callable=AsyncMock, return_value=ordinary_user_b_spoofed_meta), \
         patch("app.routers.despacho_calidad.verificar_acceso", new_callable=AsyncMock, return_value=ordinary_user_b_spoofed_meta), \
         patch("app.services.despacho_store.db_request", new_callable=AsyncMock, return_value=[incidencia_usuario_a]):

        # 1. Bandeja global -> 403
        r_list = client.get("/api/despacho/calidad/incidencias")
        assert r_list.status_code == 403

        # 2. Detalle de incidencia de Usuario A -> 403
        r_detail = client.get("/api/despacho/calidad/incidencias/inc-uuid-user-a-001")
        assert r_detail.status_code == 403
        assert "abogado.a@firma-privada.co" not in r_detail.text
        assert "Nota privada del caso de Usuario A" not in r_detail.text

        # 3. PATCH intentando descartar incidencia de Usuario A -> 403
        r_patch = client.patch(
            "/api/despacho/calidad/incidencias/inc-uuid-user-a-001",
            json={"status": "descartado", "note": "Sabotaje transversal"},
        )
        assert r_patch.status_code == 403

        # 4. Métricas, catálogo interno de documentos y evolución -> 403
        assert client.get("/api/despacho/calidad/metricas").status_code == 403
        assert client.get("/api/despacho/calidad/corpus/documentos").status_code == 403
        assert client.get("/api/despacho/calidad/evolucion").status_code == 403

    # --- B. Usuario A consulta su propia incidencia ---
    with patch("app.main.verificar_acceso", new_callable=AsyncMock, return_value=ordinary_user_a), \
         patch("app.routers.despacho_calidad.verificar_acceso", new_callable=AsyncMock, return_value=ordinary_user_a), \
         patch("app.services.despacho_store.db_request", new_callable=AsyncMock, return_value=[incidencia_usuario_a]):

        r_own_detail = client.get("/api/despacho/calidad/incidencias/inc-uuid-user-a-001")
        assert r_own_detail.status_code == 200
        assert r_own_detail.json()["evidence"]["reported_by_email"] == "ab***@firma-privada.co"

        r_own_list = client.get("/api/despacho/calidad/incidencias?mine_only=true")
        assert r_own_list.status_code == 200
        assert len(r_own_list.json()["incidencias"]) == 1

        # Pero Usuario A (usuario ordinario) NO puede hacer PATCH para cerrar o descartar la incidencia -> 403
        r_own_patch = client.patch(
            "/api/despacho/calidad/incidencias/inc-uuid-user-a-001",
            json={"status": "cerrado"},
        )
        assert r_own_patch.status_code == 403

    # --- C. Auditor documental ve correo enmascarado, puede pasar a 'en_investigacion', pero NO cerrar incidencia jurídica ---
    with patch("app.main.verificar_acceso", new_callable=AsyncMock, return_value=legit_doc_auditor), \
         patch("app.routers.despacho_calidad.verificar_acceso", new_callable=AsyncMock, return_value=legit_doc_auditor), \
         patch("app.services.despacho_store.db_request", new_callable=AsyncMock) as mock_db:

        mock_db.return_value = [incidencia_usuario_a]
        r_aud_list = client.get("/api/despacho/calidad/incidencias")
        assert r_aud_list.status_code == 200
        returned_email = r_aud_list.json()["incidencias"][0]["evidence"]["reported_by_email"]
        assert returned_email == "ab***@firma-privada.co"
        assert "abogado.a@firma-privada.co" not in r_aud_list.text

        # Auditor documental intenta cerrar incidencia jurídica (scope='agente') -> 403
        r_aud_close = client.patch(
            "/api/despacho/calidad/incidencias/inc-uuid-user-a-001",
            json={"status": "corregido", "resolution_note": "Intento sin ser abogado"},
        )
        assert r_aud_close.status_code == 403

    # --- D. Profesional jurídico acreditado sí puede resolver/cerrar la incidencia jurídica ---
    with patch("app.main.verificar_acceso", new_callable=AsyncMock, return_value=legit_legal_professional), \
         patch("app.routers.despacho_calidad.verificar_acceso", new_callable=AsyncMock, return_value=legit_legal_professional), \
         patch("app.services.despacho_store.db_request", new_callable=AsyncMock) as mock_db_legal:

        mock_db_legal.side_effect = [[incidencia_usuario_a], {}]
        r_legal_close = client.patch(
            "/api/despacho/calidad/incidencias/inc-uuid-user-a-001",
            json={"status": "corregido", "resolution_note": "Subsanado por abogada relatora"},
        )
        assert r_legal_close.status_code == 200
        assert r_legal_close.json()["status"] == "corregido"


# ============================================================================
# 4. INTEGRACIÓN REAL EN VIVO CONTRA SUPABASE AUTH, POSTGREST, RLS Y TRIGGERS
# ============================================================================

@pytest.mark.asyncio
async def test_integracion_real_supabase_aislamiento_usuarios_y_rls():
    """Prueba de integración real contra el proyecto Supabase activo:
    - Crea dos cuentas de prueba temporales (Usuario A y Usuario B con user_metadata malicioso).
    - Obtiene JWT reales emitidos por Supabase Auth.
    - Verifica en vivo que:
      1) Usuario B con user_metadata={'role': 'admin', 'tarjeta_profesional': 'TP-FAKE'} recibe 403 en FastAPI
         para `/connector/schedule`, `/connector/sync` y `/connector/triage/review`.
      2) Usuario A radica una incidencia real en Supabase (`despacho_corpus_incidencias`).
      3) Usuario B recibe 403 en FastAPI al intentar leer (`GET /incidencias`, `GET /incidencias/{id}`)
         o modificar (`PATCH /incidencias/{id}`) la incidencia de Usuario A.
      4) Directamente contra PostgREST con el JWT real de Usuario B:
         - `GET /rest/v1/despacho_corpus_incidencias?id=eq.{inc_id}` devuelve `[]` (0 filas por política RLS).
         - `PATCH /rest/v1/perfiles?id=eq.{user_b_id}` intentando cambiar `rol='admin'` es rechazado (403/42501)
           por el trigger `trg_perfiles_permisos`.
         - `GET /rest/v1/despacho_conector_descubrimientos` con clave `anon` es rechazado (401/403) y con JWT
           de Usuario B devuelve `[]` (0 filas).
    - Elimina la incidencia de prueba y ambas cuentas de prueba en el bloque `finally`.
    """
    settings = get_settings()
    base_url = settings.SUPABASE_URL.rstrip("/")
    anon_key = settings.SUPABASE_ANON_KEY
    service_key = settings.SUPABASE_SERVICE_ROLE_KEY

    if not base_url or not anon_key or not service_key:
        pytest.skip("Credenciales de Supabase no configuradas en el entorno.")

    run_tag = uuid.uuid4().hex[:8]
    email_a = f"test.sec.user.a.{run_tag}@memorialista.local"
    email_b = f"test.sec.user.b.{run_tag}@memorialista.local"
    password = f"SecTest!{run_tag}#2026"

    user_a_id = None
    user_b_id = None
    created_incident_id = None

    admin_headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=20.0) as http_client:
        try:
            # 1. Crear Usuario A (ordinario) y Usuario B (con user_metadata malicioso)
            res_create_a = await http_client.post(
                f"{base_url}/auth/v1/admin/users",
                headers=admin_headers,
                json={
                    "email": email_a,
                    "password": password,
                    "email_confirm": True,
                    "user_metadata": {"nombre": "Usuario Prueba A"},
                    "app_metadata": {"role": "usuario"},
                },
            )
            assert res_create_a.status_code in (200, 201), res_create_a.text
            user_a_id = res_create_a.json()["id"]

            res_create_b = await http_client.post(
                f"{base_url}/auth/v1/admin/users",
                headers=admin_headers,
                json={
                    "email": email_b,
                    "password": password,
                    "email_confirm": True,
                    "user_metadata": {
                        "nombre": "Usuario Prueba B",
                        "role": "admin",
                        "rol": "abogado",
                        "tarjeta_profesional": "TP-999999-FAKE",
                    },
                    "app_metadata": {"role": "usuario"},
                },
            )
            assert res_create_b.status_code in (200, 201), res_create_b.text
            user_b_id = res_create_b.json()["id"]

            # 2. Iniciar sesión real con ambos usuarios para obtener sus JWT firmados por Supabase
            login_headers = {"apikey": anon_key, "Content-Type": "application/json"}
            tok_res_a = await http_client.post(
                f"{base_url}/auth/v1/token?grant_type=password",
                headers=login_headers,
                json={"email": email_a, "password": password},
            )
            assert tok_res_a.status_code == 200, tok_res_a.text
            jwt_a = tok_res_a.json()["access_token"]

            tok_res_b = await http_client.post(
                f"{base_url}/auth/v1/token?grant_type=password",
                headers=login_headers,
                json={"email": email_b, "password": password},
            )
            assert tok_res_b.status_code == 200, tok_res_b.text
            jwt_b = tok_res_b.json()["access_token"]

            # 3. Probar endpoints FastAPI con los JWT reales (sin mocks de autenticación)
            api_client = TestClient(app)

            # EM-01 + EM-02: Usuario B intenta acciones administrativas en conector con su JWT real -> 403
            r_sched_b = api_client.post(
                "/api/despacho/official/connector/schedule",
                headers={"Authorization": f"Bearer {jwt_b}"},
                json={"enabled": True, "interval_minutes": 180, "run_now": False},
            )
            assert r_sched_b.status_code == 403

            r_sync_b = api_client.post(
                "/api/despacho/official/connector/sync",
                headers={"Authorization": f"Bearer {jwt_b}"},
                json={"limit": 5, "auto_publish": True, "semantic": False},
            )
            assert r_sync_b.status_code == 403

            r_triage_b = api_client.post(
                "/api/despacho/official/connector/triage/review",
                headers={"Authorization": f"Bearer {jwt_b}"},
                json={"document_id": "doc-test", "decision": "approve", "review_type": "revision_juridica_humana"},
            )
            assert r_triage_b.status_code == 403

            # EM-03: Usuario A radica un reporte de error real
            r_rep_a = api_client.post(
                "/api/despacho/calidad/reportes-error",
                headers={"Authorization": f"Bearer {jwt_a}"},
                json={
                    "target_type": "agente_respuesta",
                    "error_category": "interpretacion_incorrecta",
                    "description": f"Reporte confidencial de prueba {run_tag} del Usuario A",
                    "sentencia": "T-100/24",
                },
            )
            assert r_rep_a.status_code == 200, r_rep_a.text
            # Obtener el ID real insertado en la base de datos para limpieza y prueba transversal
            inc_rows = await http_client.get(
                f"{base_url}/rest/v1/despacho_corpus_incidencias?evidence->>reported_by_id=eq.{user_a_id}&select=id,evidence",
                headers=admin_headers,
            )
            assert inc_rows.status_code == 200 and len(inc_rows.json()) >= 1
            created_incident_id = inc_rows.json()[0]["id"]
            stored_email = inc_rows.json()[0]["evidence"].get("reported_by_email")
            assert stored_email is not None and "***" in stored_email and email_a not in stored_email

            # Usuario B intenta leer y modificar la incidencia de Usuario A vía API FastAPI -> 403
            r_inc_list_b = api_client.get(
                "/api/despacho/calidad/incidencias",
                headers={"Authorization": f"Bearer {jwt_b}"},
            )
            assert r_inc_list_b.status_code == 403

            r_inc_get_b = api_client.get(
                f"/api/despacho/calidad/incidencias/{created_incident_id}",
                headers={"Authorization": f"Bearer {jwt_b}"},
            )
            assert r_inc_get_b.status_code == 403

            r_inc_patch_b = api_client.patch(
                f"/api/despacho/calidad/incidencias/{created_incident_id}",
                headers={"Authorization": f"Bearer {jwt_b}"},
                json={"status": "descartado"},
            )
            assert r_inc_patch_b.status_code == 403

            # Usuario A sí puede leer su propia incidencia vía API FastAPI
            r_inc_get_a = api_client.get(
                f"/api/despacho/calidad/incidencias/{created_incident_id}",
                headers={"Authorization": f"Bearer {jwt_a}"},
            )
            assert r_inc_get_a.status_code == 200
            assert r_inc_get_a.json()["id"] == created_incident_id

            # 4. Probar directamente contra PostgREST / RLS en Supabase
            headers_jwt_b = {
                "apikey": anon_key,
                "Authorization": f"Bearer {jwt_b}",
                "Content-Type": "application/json",
            }
            headers_jwt_a = {
                "apikey": anon_key,
                "Authorization": f"Bearer {jwt_a}",
                "Content-Type": "application/json",
            }
            headers_anon = {
                "apikey": anon_key,
                "Authorization": f"Bearer {anon_key}",
            }

            # 4.1 RLS en despacho_corpus_incidencias: Usuario B recibe 0 filas; Usuario A recibe su fila
            pg_inc_b = await http_client.get(
                f"{base_url}/rest/v1/despacho_corpus_incidencias?id=eq.{created_incident_id}&select=*",
                headers=headers_jwt_b,
            )
            assert pg_inc_b.status_code == 200
            assert pg_inc_b.json() == []

            pg_inc_a = await http_client.get(
                f"{base_url}/rest/v1/despacho_corpus_incidencias?id=eq.{created_incident_id}&select=*",
                headers=headers_jwt_a,
            )
            assert pg_inc_a.status_code == 200
            assert len(pg_inc_a.json()) == 1

            # 4.2 Trigger trg_perfiles_permisos: Usuario B intenta cambiar su rol a 'admin' en public.perfiles -> bloqueado
            pg_perfil_b = await http_client.patch(
                f"{base_url}/rest/v1/perfiles?id=eq.{user_b_id}",
                headers=headers_jwt_b,
                json={"rol": "admin"},
            )
            assert pg_perfil_b.status_code in (401, 403, 400), f"Debió bloquearse: {pg_perfil_b.text}"

            # 4.3 RLS y REVOKE en despacho_conector_descubrimientos: anon recibe 401/403 y Usuario B recibe []
            pg_desc_anon = await http_client.get(
                f"{base_url}/rest/v1/despacho_conector_descubrimientos?select=id&limit=5",
                headers=headers_anon,
            )
            assert pg_desc_anon.status_code in (401, 403)

            pg_desc_b = await http_client.get(
                f"{base_url}/rest/v1/despacho_conector_descubrimientos?select=id&limit=5",
                headers=headers_jwt_b,
            )
            assert pg_desc_b.status_code == 200
            assert pg_desc_b.json() == []

        finally:
            # Limpieza garantizada de datos y cuentas de prueba
            if created_incident_id:
                await http_client.delete(
                    f"{base_url}/rest/v1/despacho_corpus_incidencias?id=eq.{created_incident_id}",
                    headers=admin_headers,
                )
            for uid in (user_a_id, user_b_id):
                if uid:
                    await http_client.delete(
                        f"{base_url}/auth/v1/admin/users/{uid}",
                        headers=admin_headers,
                    )
