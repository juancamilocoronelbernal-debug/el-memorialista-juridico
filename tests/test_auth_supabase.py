"""Pruebas unitarias e integrales para Supabase: Auth (Magic Link), RLS, Storage privado y endpoints.

Verifica:
- Configuración de Supabase expuesta al cliente web (GET /api/auth/config).
- Validación de sesiones de usuario vía Bearer tokens y control de acceso.
- Límites de uso aplicados por usuario autenticado.
- Exportación total de datos del usuario ("Exportar todos mis datos").
- Eliminación irrevocable de cuenta y datos ("Eliminar mi cuenta").
- Integridad del esquema SQL (tablas perfiles, firmas, clientes, casos, documentos, versiones, RLS y storage).
"""

import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import app
from app.services.supabase_service import (
    validar_token_supabase,
    exportar_todos_los_datos,
    eliminar_cuenta_usuario,
)
from app.services.limites import limitador

client = TestClient(app)


def test_schema_sql_valido_y_completo():
    """Verifica que el archivo schema.sql contenga todas las tablas, RLS y Storage requeridos."""
    schema_path = Path(__file__).resolve().parent.parent / "supabase" / "schema.sql"
    assert schema_path.exists(), "El archivo supabase/schema.sql debe existir."

    sql = schema_path.read_text(encoding="utf-8")

    # 1. Tablas requeridas
    assert "CREATE TABLE IF NOT EXISTS public.firmas" in sql
    assert "CREATE TABLE IF NOT EXISTS public.perfiles" in sql
    assert "CREATE TABLE IF NOT EXISTS public.clientes" in sql
    assert "CREATE TABLE IF NOT EXISTS public.casos" in sql
    assert "CREATE TABLE IF NOT EXISTS public.documentos" in sql
    assert "CREATE TABLE IF NOT EXISTS public.versiones" in sql

    # 2. Campos clave de clientes
    assert "tipo_persona" in sql
    assert "numero_documento" in sql
    assert "dv" in sql
    assert "representante_legal" in sql

    # 3. Campos clave de casos y documentos
    assert "contraparte" in sql
    assert "radicado" in sql
    assert "despacho" in sql
    assert "estado" in sql
    assert "creado_por" in sql
    assert "version" in sql

    # 4. Row Level Security (RLS)
    assert "ALTER TABLE public.firmas ENABLE ROW LEVEL SECURITY;" in sql
    assert "ALTER TABLE public.perfiles ENABLE ROW LEVEL SECURITY;" in sql
    assert "ALTER TABLE public.clientes ENABLE ROW LEVEL SECURITY;" in sql
    assert "ALTER TABLE public.casos ENABLE ROW LEVEL SECURITY;" in sql
    assert "ALTER TABLE public.documentos ENABLE ROW LEVEL SECURITY;" in sql
    assert "ALTER TABLE public.versiones ENABLE ROW LEVEL SECURITY;" in sql
    assert "obtener_mi_firma_id()" in sql

    # 5. Storage privado para logo, firma y plantilla
    assert "archivos-privados" in sql
    assert "storage.buckets" in sql
    assert "storage.objects" in sql


def test_endpoint_auth_config():
    """Verifica que GET /api/auth/config devuelva la configuración pública de Supabase."""
    resp = client.get("/api/auth/config")
    assert resp.status_code == 200
    data = resp.json()
    assert "supabase_url" in data
    assert "supabase_anon_key" in data
    assert "auth_requerido" in data
    assert "limite_diario_usuario" in data
    assert data["limite_diario_usuario"] >= 10


@pytest.mark.asyncio
async def test_validar_token_supabase_mock():
    """Verifica que validar_token_supabase resuelva tokens mock de prueba."""
    user = await validar_token_supabase("mock-user123-token")
    assert user is not None
    assert user["id"] == "user123"
    assert user["email"] == "user123@memorialista.test"

    # Token vacío
    assert await validar_token_supabase("") is None
    assert await validar_token_supabase("   ") is None


def test_endpoint_perfil_usuario_autenticado():
    """Verifica que GET /api/usuario/perfil responda con el usuario autenticado."""
    headers = {"Authorization": "Bearer mock-abogado456-token"}
    resp = client.get("/api/usuario/perfil", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["id"] == "abogado456"
    assert "email" in data
    assert data["limite_diario"] > 0


def test_endpoint_exportar_datos_usuario():
    """Verifica que GET /api/usuario/exportar-datos retorne el archivo JSON con todas las tablas."""
    headers = {"Authorization": "Bearer mock-abogado789-token"}
    resp = client.get("/api/usuario/exportar-datos", headers=headers)
    assert resp.status_code == 200
    assert "attachment" in resp.headers.get("content-disposition", "")
    assert "el_memorialista_mis_datos" in resp.headers.get("content-disposition", "")

    data = resp.json()
    assert "exportado_el" in data
    assert "usuario_id" in data
    assert data["usuario_id"] == "abogado789"
    assert "perfil" in data
    assert "firma" in data
    assert "clientes" in data
    assert "casos" in data
    assert "documentos" in data
    assert "versiones" in data


def test_endpoint_eliminar_cuenta_usuario():
    """Verifica que DELETE /api/usuario/eliminar-cuenta procese la baja del usuario."""
    headers = {"Authorization": "Bearer mock-abogadoborra-token"}
    resp = client.delete("/api/usuario/eliminar-cuenta", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert "eliminados definitivamente" in data["mensaje"]


def test_limite_uso_por_usuario():
    """Verifica que el Limitador aplique la cuota diaria basada en el ID del usuario."""
    limitador.reiniciar()
    from starlette.requests import Request
    from fastapi import HTTPException

    # Crear una solicitud simulada con request.state.user_id
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/redactar",
        "headers": [(b"host", b"testserver")],
        "client": ("127.0.0.1", 12345),
    }
    req = Request(scope)
    req.state.user_id = "user-cuota-test"

    # Verificar que el limitador use user_id en lugar de IP
    limitador.verificar(req, "redactar", user_id="user-cuota-test")

    # Verificar que la clave u:user-cuota-test esté en el limitador
    claves = [k for k in limitador._eventos.keys()]
    assert any("u:user-cuota-test" in k for k in claves)


def test_frontend_html_auth_y_cuenta_modales():
    """Verifica que el frontend contenga los modales de autenticación, cuenta, exportación y eliminación."""
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.text

    # SDK Supabase y elementos de cabecera
    assert "supabase-js" in html
    assert 'id="btnAuthHeader"' in html
    assert "iniciarSupabase" in html

    # Modal de Auth con Magic Link
    assert 'id="modalAuth"' in html
    assert 'id="authEmail"' in html
    assert 'id="formAuthMagicLink"' in html
    assert "enlace mágico" in html.lower()

    # Modal de Cuenta y Privacidad
    assert 'id="modalCuenta"' in html
    assert 'id="btnExportarDatosCuenta"' in html
    assert 'id="btnEliminarCuentaModal"' in html
    assert 'id="btnSincronizarNube"' in html

    # Funciones de migración, exportación y borrado
    assert "migrarDatosNavegadorASupabase" in html
    assert "exportarTodosMisDatos" in html
    assert "eliminarMiCuenta" in html
    assert "archivos-privados" in html

