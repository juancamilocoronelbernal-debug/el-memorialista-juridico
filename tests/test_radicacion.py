import pytest
"""
Pruebas unitarias para el módulo de preparación de radicación judicial
y aplicación del artículo 6 de la Ley 2213 de 2022 (El Memorialista).
"""
import urllib.parse
from fastapi.testclient import TestClient

from app.main import app
from app.services.radicacion import (
    preparar_radicacion,
    detectar_medidas_cautelares,
    tipo_requiere_poder,
    generar_texto_poder_especial,
    extraer_capitulo_pruebas_y_anexos,
    construir_indice_anexos,
    PrepararRadicacionRequest,
)

client = TestClient(app, headers={"Authorization": "Bearer unit-test-bearer"})


def test_demanda_verbal_traslado_simultaneo():
    """Caso 1: Demanda verbal ordinaria sin cautelares con correo de contraparte -> Requiere poder y aplica traslado simultáneo art. 6."""
    texto_escrito = """Señor Juez Civil del Circuito de Bogotá
E. S. D.

REF: Demanda Verbal de Mayor Cuantía
Demandante: Carlos Alberto Gómez
Demandado: Inversiones Los Andes S.A.S.

HECHOS
1. El día 15 de enero de 2024 se celebró contrato de compraventa...

## Pruebas y Anexos
1. Copia íntegra del contrato de compraventa de fecha 15 de enero de 2024.
2. Certificado de existencia y representación legal de la demandada expedido por la Cámara de Comercio.
3. Comprobantes de transferencia bancaria por valor de $50.000.000.
"""
    datos = {
        "cliente": "Carlos Alberto Gómez, C.C. 79.123.456",
        "contraparte": "Inversiones Los Andes S.A.S., NIT 900.123.456-7",
        "correo_contraparte": "notificacionesjudiciales@inversioneslosandes.com",
        "destinatario": "JUZGADO CIVIL DEL CIRCUITO DE BOGOTÁ (REPARTO)",
        "correo_despacho": "reparto.civilbogota@cendoj.ramajudicial.gov.co",
        "ciudad": "Bogotá D.C.",
    }
    perfil = {
        "abogado": {
            "nombre": "Dra. Laura Camila Martínez",
            "cedula": "52.987.654",
            "cedulaLugar": "Bogotá",
            "tp": "284910",
            "correo": "laura.martinez@abogados.com",
            "telefono": "3101234567",
            "ciudad": "Bogotá D.C.",
        }
    }

    req = PrepararRadicacionRequest(
        tipo="verbal",
        datos=datos,
        texto=texto_escrito,
        perfil=perfil,
    )
    resp = preparar_radicacion(req)

    # 1. Verificación del poder
    assert resp.requiere_poder is True
    assert resp.texto_poder is not None
    assert "PODER ESPECIAL, AMPLIO Y SUFICIENTE" in resp.texto_poder
    assert "Dra. Laura Camila Martínez" in resp.texto_poder
    assert "Carlos Alberto Gómez" in resp.texto_poder
    assert "artículo 77 del Código General del Proceso" in resp.texto_poder
    assert "artículo 5 de la Ley 2213 de 2022" in resp.texto_poder
    assert resp.nombre_archivo_poder.startswith("02_Poder_Especial_Judicial_")

    # 2. Verificación de medidas cautelares y traslado
    assert resp.solicita_medidas_cautelares is False
    assert resp.aplica_traslado_contraparte is True
    assert "Art. 6 Ley 2213 de 2022" in resp.motivo_traslado_contraparte
    assert resp.correo_contraparte == "notificacionesjudiciales@inversioneslosandes.com"
    assert resp.asunto_contraparte is not None
    assert "Traslado Simultáneo" in resp.asunto_contraparte
    assert resp.mailto_contraparte.startswith("mailto:notificacionesjudiciales@inversioneslosandes.com")

    # 3. Verificación de Despacho y Correo Radicación
    assert resp.correo_despacho == "reparto.civilbogota@cendoj.ramajudicial.gov.co"
    assert resp.mailto_despacho.startswith("mailto:reparto.civilbogota@cendoj.ramajudicial.gov.co")
    assert "Carlos Alberto Gómez vs Inversiones Los Andes S.A.S." in resp.asunto_despacho

    # 4. Índice de anexos
    assert len(resp.indice_anexos) >= 4  # Principal + Poder + 3 pruebas
    assert resp.indice_anexos[0].tipo_documento == "Principal"
    assert resp.indice_anexos[1].tipo_documento == "Poder"
    assert any("contrato" in a.descripcion.lower() for a in resp.indice_anexos)
    assert any("cámara de comercio" in a.descripcion.lower() for a in resp.indice_anexos)

    # 5. Texto del índice CSJ
    assert "ÍNDICE DE EXPEDIENTE ELECTRÓNICO" in resp.texto_indice
    assert "Carlos Alberto Gómez" in resp.texto_indice


def test_demanda_con_medidas_cautelares_exonerada_de_traslado():
    """Caso 2: Demanda que solicita medidas cautelares previas -> Exonerada de traslado previo según art. 6 inc. 4 Ley 2213/2022."""
    texto_escrito = """Señor Juez Civil Municipal de Medellín
E. S. D.

REF: Demanda Ejecutiva Singular de Menor Cuantía
Demandante: Banco Comercial S.A.
Demandado: Pedro Pérez Gómez

## Medidas Cautelares Previas
Solicito respetuosamente se decrete el embargo y retención de las cuentas bancarias del demandado,
así como el embargo y secuestro del inmueble identificado con folio de matrícula 001-12345.

## Pruebas
1. Pagaré No. 45892 debidamente suscrito.
"""
    datos = {
        "cliente": "Banco Comercial S.A.",
        "contraparte": "Pedro Pérez Gómez",
        "correo_contraparte": "pedro.perez@email.com",
    }
    perfil = {
        "abogado": {"nombre": "Dr. Fernando Soto", "tp": "194820", "correo": "fsoto@banco.com"}
    }

    assert detectar_medidas_cautelares(texto_escrito, datos) is True

    req = PrepararRadicacionRequest(
        tipo="ejecutivo",
        datos=datos,
        texto=texto_escrito,
        perfil=perfil,
    )
    resp = preparar_radicacion(req)

    assert resp.solicita_medidas_cautelares is True
    assert resp.aplica_traslado_contraparte is False
    assert "Exonerado de traslado previo" in resp.motivo_traslado_contraparte
    assert "medidas cautelares previas" in resp.motivo_traslado_contraparte
    assert resp.asunto_contraparte is None
    assert resp.mailto_contraparte is None


def test_tutela_sin_traslado_simultaneo():
    """Caso 3: Acción de tutela -> No aplica traslado simultáneo porque el juez constitucional lo ordena de oficio (Decreto 2591 de 1991)."""
    texto_escrito = """Señor Juez Constitucional (Reparto)
E. S. D.

REF: Acción de Tutela
Accionante: María Rodríguez
Accionado: EPS Sanitas

## Hechos
...
"""
    datos = {
        "cliente": "María Rodríguez",
        "contraparte": "EPS Sanitas",
        "correo_contraparte": "notificaciones@epssanitas.com",
    }
    req = PrepararRadicacionRequest(
        tipo="tutela",
        datos=datos,
        texto=texto_escrito,
    )
    resp = preparar_radicacion(req)

    assert resp.aplica_traslado_contraparte is False
    assert "tutela" in resp.motivo_traslado_contraparte.lower()
    assert "2591" in resp.motivo_traslado_contraparte


def test_actuacion_en_nombre_propio_o_tipo_poder():
    """Caso 4: Si actúa en nombre propio o el tipo es poder, no genera poder anexo."""
    req_propio = PrepararRadicacionRequest(
        tipo="tutela",
        datos={"cliente": "Juan", "contraparte": "EPS", "_firma": "propio"},
        texto="Texto tutela...",
    )
    resp_propio = preparar_radicacion(req_propio)
    assert resp_propio.requiere_poder is False
    assert resp_propio.texto_poder is None

    req_poder = PrepararRadicacionRequest(
        tipo="poder_especial",
        datos={"cliente": "Juan", "contraparte": "Pedro"},
        texto="Poder...",
    )
    resp_poder = preparar_radicacion(req_poder)
    assert resp_poder.requiere_poder is False


def test_endpoint_api_radicacion_preparar():
    """Caso 5: Llamada HTTP al endpoint POST /api/radicacion/preparar."""
    payload = {
        "tipo": "verbal",
        "datos": {
            "cliente": "Construcciones Alfa S.A.S.",
            "contraparte": "Ferretería Beta Ltda.",
            "correo_contraparte": "gerencia@ferreteriabeta.com",
            "destinatario": "JUZGADO 15 CIVIL DEL CIRCUITO DE CALI",
            "radicado": "76001310301520240012300",
        },
        "texto": """Señor Juez
REF: Proceso Verbal - Rad. 76001310301520240012300

## Pruebas
1. Factura cambiaria de compraventa No. 1290.
2. Acta de entrega de obra con firma de recibo.
""",
        "perfil": {
            "abogado": {
                "nombre": "Andrés Felipe Castro",
                "cedula": "16.789.012",
                "tp": "312456",
                "correo": "andres.castro@litigios.com",
            }
        },
    }

    resp = client.post("/api/radicacion/preparar", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["requiere_poder"] is True
    assert data["solicita_medidas_cautelares"] is False
    assert data["aplica_traslado_contraparte"] is True
    assert "Rad_76001310301520240012300" in data["nombre_paquete"]
    assert data["correo_contraparte"] == "gerencia@ferreteriabeta.com"
    assert data["mailto_contraparte"].startswith("mailto:gerencia@ferreteriabeta.com")
    assert "mailto:radicacion@ramajudicial.gov.co" in data["mailto_despacho"]
    assert len(data["indice_anexos"]) >= 3

pytestmark = pytest.mark.usefixtures("autenticacion_pruebas")
