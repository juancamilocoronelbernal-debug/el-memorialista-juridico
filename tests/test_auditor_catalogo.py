import json
from pathlib import Path
import pytest
from starlette.testclient import TestClient
from app.main import app
from app.services.prompt import listar_tipos

def test_tipo_proceso_monitorio_estructura():
    ruta = Path("app/catalogo/tipos/proceso_monitorio.json")
    assert ruta.exists(), "El archivo proceso_monitorio.json debe existir"

    with open(ruta, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["id"] == "proceso_monitorio"
    assert "419" in data["norma"] and "421" in data["norma"]
    assert data["area"] == "Civil y comercial"
    assert "revisado_por" in data
    assert "auditoria_ia" in data
    assert data["auditoria_ia"]["aprobado"] is True
    assert data["auditoria_ia"]["puntuacion"] >= 90

    # Verificar que los grupos cubran los presupuestos procesales de los arts. 419-421 CGP
    keys = [c["k"] for g in data["grupos"] for c in g["campos"]]
    assert "capital" in keys
    assert "fecha_exigibilidad" in keys
    assert "contraprestacion_satisfecha" in keys
    assert "pretensiones" in keys
    assert "hechos" in keys
    assert "demandado_correo" in keys
    assert "demandado_correo_origen" in keys

    # Verificar que el apercibimiento del art. 421 CGP esté en la guía
    assert "421" in data["guia"]
    assert "fuerza de sentencia" in data["guia"]
    assert "contraprestación" in data["guia"]

def test_listar_tipos_incluye_proceso_monitorio():
    tipos = listar_tipos(incluir_guia=False)
    ids = [t["id"] for t in tipos]
    assert "proceso_monitorio" in ids

    mon = next(t for t in tipos if t["id"] == "proceso_monitorio")
    assert "Auditado con IA Jurídica" in mon["revisado_por"]
    assert mon["auditoria_ia"]["puntuacion"] >= 90
    assert "guia" not in mon  # incluir_guia=False la debe remover

def test_api_catalogo_entrega_proceso_monitorio():
    with TestClient(app) as client:
        res = client.get("/api/catalogo")
        assert res.status_code == 200
        data = res.json()
        tipos = data.get("tipos", [])
        mon = next((t for t in tipos if t["id"] == "proceso_monitorio"), None)
        assert mon is not None, "proceso_monitorio debe figurar en el endpoint /api/catalogo"
        assert mon["nombre"] == "Demanda de proceso monitorio"
        assert mon["auditoria_ia"]["puntuacion"] >= 90
