"""Fixtures explícitas para tests de comportamiento del generador.

Los tests de seguridad NO usan este fixture y verifican el validador real.
La sustitución se limita al test que lo solicita; jamás existe en producción.
"""
from unittest.mock import AsyncMock

import pytest

from app.services import supabase_service
from app.services.gemini_service import gemini_service

TEST_AUTH_TOKEN = "unit-test-bearer"
TEST_USER = {"id": "unit-test-user", "email": "abogada@example.test", "role": "authenticated", "user_metadata": {"nombre": "Abogada de prueba", "rol": "abogado"}}


@pytest.fixture
def autenticacion_pruebas(monkeypatch, request):
    async def verificar_proveedor(token):
        return dict(TEST_USER) if token == TEST_AUTH_TOKEN else None
    monkeypatch.setattr(supabase_service, "validar_token_supabase", verificar_proveedor)
    # Las pruebas de streaming inyectan su propio transporte y conservan la
    # consulta de modelos. Las de formularios/cálculos no necesitan red.
    if not request.module.__name__.endswith("test_backend"):
        monkeypatch.setattr(gemini_service, "descubrir_modelos", AsyncMock(return_value=None))
    yield TEST_USER
