"""Generador de casos de prueba exhaustivos en tests/casos/ (3 casos por cada uno de los 25 tipos).

Genera 75 casos completos y realistas de litigio colombiano, con:
- tipo
- datos (todos los campos obligatorios y opcionales clave)
- expectativas:
  - secciones_obligatorias
  - entidades_deben_aparecer
  - entidades_no_deben_aparecer (alucinaciones prohibidas)
  - longitud_minima
  - longitud_maxima
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app.services.prompt import listar_tipos, validar_datos_tipo

OUTPUT_DIR = os.path.join(ROOT_DIR, "tests", "casos")


CASOS_POR_TIPO: dict[str, list[dict[str, Any]]] = {}

# 1. TUTELA
CASOS_POR_TIPO["tutela"] = [
    {
        "id": "tutela_01_salud_medicamentos",
        "tipo": "tutela",
        "descripcion": "Acción de tutela por negación de medicamento oncológico y tratamiento integral a adulto mayor.",
        "datos": {
            "destinatario": "Juez Civil Municipal de Bogotá (Reparto)",
            "ciudad": "Bogotá, D.C.",
            "cliente": "María Fernanda López Rincón, mayor de edad, identificada con C.C. 1.020.304.050",
            "contraparte": "Nueva EPS S.A., NIT 900.156.264-2, representante legal o quien haga sus veces",
            "derechos": ["Salud", "Vida digna", "Seguridad social"],
            "hechos": (
                "1. La accionante tiene 68 años y fue diagnosticada con adenocarcinoma pulmonar en etapa III.\n"
                "2. Su médico tratante adscrito ordenó el medicamento Pembrolizumab 100 mg cada 3 semanas.\n"
                "3. El 10 de octubre de 2026 Nueva EPS negó el suministro alegando trámite administrativo.\n"
                "4. La accionante carece de recursos económicos para costear el tratamiento privadamente."
            ),
            "pretensiones": (
                "1. Amparar los derechos fundamentales a la salud, vida digna e integridad personal.\n"
                "2. Ordenar a Nueva EPS autorizar y entregar el medicamento Pembrolizumab 100 mg en 48 horas.\n"
                "3. Ordenar el tratamiento integral derivado de su patología oncológica."
            ),
            "pruebas": "Historia clínica No. 1020304050, fórmula médica del 5/10/2026, negación de Nueva EPS del 10/10/2026.",
            "notificaciones": "Accionante: Calle 45 # 13-20, Bogotá; maria.lopez@email.com. Accionada: notificaciones@nuevaeps.com.co",
            "juramento": True,
        },
        "expectativas": {
            "secciones_obligatorias": ["HECHOS", "PRETENSIONES", "FUNDAMENTOS", "PRUEBAS", "JURAMENTO", "NOTIFICACIONES"],
            "entidades_deben_aparecer": ["María Fernanda López", "1.020.304.050", "Nueva EPS", "Pembrolizumab"],
            "entidades_no_deben_aparecer": ["Sanitas", "Sura", "Bancolombia", "Juzgado 50 Penal"],
            "longitud_minima": 1200,
            "longitud_maxima": 15000,
        },
    },
    {
        "id": "tutela_02_debido_proceso_universidad",
        "tipo": "tutela",
        "descripcion": "Tutela por vulneración del derecho fundamental al debido proceso por expulsión universitaria sin procedimiento.",
        "datos": {
            "destinatario": "Juez del Circuito de Medellín (Reparto)",
            "ciudad": "Medellín (Antioquia)",
            "cliente": "Santiago Restrepo Henao, estudiante de Derecho, C.C. 1.152.430.890",
            "contraparte": "Universidad Bolivariana de Antioquia, NIT 890.901.234-5",
            "derechos": ["Debido proceso", "Educación", "Defensa"],
            "hechos": (
                "1. El estudiante cursaba noveno semestre con promedio académico de 4.2.\n"
                "2. Mediante Resolución Rectoral 085 del 12 de septiembre de 2026 fue expulsado sumariamente.\n"
                "3. No se abrió pliego de cargos ni se permitió rendir descargos ni controvertir pruebas."
            ),
            "pretensiones": (
                "1. Tutelar los derechos fundamentales al debido proceso y a la educación.\n"
                "2. Dejar sin efecto la Resolución Rectoral 085 de 2026.\n"
                "3. Ordenar el reintegro inmediato al programa académico y la reprogramación de exámenes."
            ),
            "pruebas": "Resolución Rectoral 085, récord de notas, constancia de matrícula 2026-2.",
            "notificaciones": "Accionante: Carrera 70 # 32-15, Medellín; santiago.restrepo@email.com. Accionada: juridica@ubolivariana.edu.co",
            "juramento": True,
        },
        "expectativas": {
            "secciones_obligatorias": ["HECHOS", "PRETENSIONES", "FUNDAMENTOS", "PRUEBAS", "JURAMENTO", "NOTIFICACIONES"],
            "entidades_deben_aparecer": ["Santiago Restrepo", "1.152.430.890", "Universidad Bolivariana", "Resolución Rectoral 085"],
            "entidades_no_deben_aparecer": ["Nueva EPS", "Clínica Medellín", "Ecopetrol"],
            "longitud_minima": 1200,
            "longitud_maxima": 15000,
        },
    },
    {
        "id": "tutela_03_estabilidad_laboral_embarazo",
        "tipo": "tutela",
        "descripcion": "Protección de la estabilidad laboral reforzada por despido de trabajadora en estado de embarazo.",
        "datos": {
            "destinatario": "Juez Laboral del Circuito de Cali (Reparto)",
            "ciudad": "Cali (Valle del Cauca)",
            "cliente": "Daniela Morales Castillo, C.C. 1.144.123.456",
            "contraparte": "Distribuidora del Pacífico S.A.S., NIT 900.567.890-1",
            "derechos": ["Estabilidad laboral reforzada", "Mínimo vital", "Igualdad", "Protección a la maternidad"],
            "hechos": (
                "1. La accionante laboraba como asistente contable desde el 15 de enero de 2024 con contrato a término indefinido.\n"
                "2. El 1 de agosto de 2026 notificó por escrito su estado de embarazo de 12 semanas con prueba médica.\n"
                "3. El 28 de septiembre de 2026 el empleador le notificó la terminación del contrato sin autorización del Ministerio del Trabajo."
            ),
            "pretensiones": (
                "1. Proteger el derecho a la estabilidad laboral reforzada y al mínimo vital de la madre gestante y del que está por nacer.\n"
                "2. Ordenar el reintegro inmediato al mismo cargo o a uno de superior jerarquía.\n"
                "3. Ordenar el pago de salarios y prestaciones sociales causadas desde el despido."
            ),
            "pruebas": "Contrato de trabajo, comunicación de embarazo radicada el 1/08/2026, ecografía obstétrica, carta de despido.",
            "notificaciones": "Accionante: Carrera 100 # 15-30, Cali; daniela.morales@email.com. Accionada: rrhh@distribuidorapacifico.com",
            "juramento": True,
        },
        "expectativas": {
            "secciones_obligatorias": ["HECHOS", "PRETENSIONES", "FUNDAMENTOS", "PRUEBAS", "JURAMENTO", "NOTIFICACIONES"],
            "entidades_deben_aparecer": ["Daniela Morales", "1.144.123.456", "Distribuidora del Pacífico", "Ministerio del Trabajo"],
            "entidades_no_deben_aparecer": ["Sanitas", "Universidad", "Colpensiones"],
            "longitud_minima": 1200,
            "longitud_maxima": 15000,
        },
    },
]

# 2. DEMANDA VERBAL
CASOS_POR_TIPO["demanda_verbal"] = [
    {
        "id": "demanda_verbal_01_suministro_incumplimiento",
        "tipo": "demanda_verbal",
        "descripcion": "Demanda verbal de mayor cuantía por incumplimiento de contrato de suministro industrial.",
        "datos": {
            "destinatario": "Juez Civil del Circuito de Bogotá (Reparto)",
            "ciudad": "Bogotá, D.C.",
            "cliente": "Industrias Metalmecánicas Andinas S.A.S., NIT 900.234.567-8, rep. por Camilo Torres C.C. 79.890.123",
            "contraparte": "Maquinarias e Insumos de Colombia S.A., NIT 890.123.456-9",
            "asunto": "Incumplimiento de contrato de suministro de tubería de acero con indemnización de perjuicios",
            "cuantia": "$ 120.000.000",
            "hechos": (
                "1. El 15 de marzo de 2025 las partes suscribieron contrato de suministro comercial de tubería de acero.\n"
                "2. La demandante canceló el anticipo pactado por $60.000.000 el 20 de marzo de 2025.\n"
                "3. La demandada debía entregar el primer lote el 1 de junio de 2025 y a la fecha no ha realizado ninguna entrega.\n"
                "4. El incumplimiento causó daño emergente y lucro cesante por paralización de obras."
            ),
            "pretensiones": (
                "1. Declarar que Maquinarias e Insumos de Colombia S.A. incumplió el contrato de suministro.\n"
                "2. Condenar a la demandada a pagar por concepto de perjuicios materiales la suma de $120.000.000 M/CTE.\n"
                "3. Condenar en costas y agencias en derecho."
            ),
            "pruebas": "Contrato de suministro, comprobante de pago del anticipo por $60.000.000, requerimientos de fecha 15/07/2025.",
            "notificaciones": "Demandante: Avenida Calle 26 # 69-70, Bogotá; gerencia@metalmecanicas.com.co. Demandada: Carrera 7 # 100-20, Bogotá; notificaciones@maquinariascol.com",
            "juramento_estimatorio": "Bajo la gravedad del juramento estimatorio (art. 206 CGP), se estiman los perjuicios en $120.000.000 ($60.000.000 daño emergente y $60.000.000 lucro cesante).",
            "conciliacion_agotada": True,
            "canal_digital_demandado": "La dirección electrónica notificaciones@maquinariascol.com corresponde a la inscrita en el registro mercantil de la demandada (art. 8 Ley 2213 de 2022).",
        },
        "expectativas": {
            "secciones_obligatorias": ["HECHOS", "PRETENSIONES", "FUNDAMENTOS", "JURAMENTO ESTIMATORIO", "PRUEBAS", "CUANTÍA", "NOTIFICACIONES"],
            "entidades_deben_aparecer": ["Industrias Metalmecánicas", "900.234.567-8", "Maquinarias e Insumos", "120.000.000"],
            "entidades_no_deben_aparecer": ["Nueva EPS", "Sanitas", "Colpensiones"],
            "longitud_minima": 1500,
            "longitud_maxima": 18000,
        },
    },
    {
        "id": "demanda_verbal_02_responsabilidad_extracontractual_transito",
        "tipo": "demanda_verbal",
        "descripcion": "Demanda verbal por responsabilidad civil extracontractual por accidente de tránsito.",
        "datos": {
            "destinatario": "Juez Civil del Circuito de Barranquilla (Reparto)",
            "ciudad": "Barranquilla (Atlántico)",
            "cliente": "Andrés Felipe Mendoza Castro, C.C. 1.045.678.901",
            "contraparte": "Transportes del Caribe S.A.S., NIT 890.456.789-0, y conductor Jorge Mario Pérez, C.C. 8.765.432",
            "asunto": "Responsabilidad civil extracontractual por colisión de automotor de servicio público",
            "cuantia": "$ 85.000.000",
            "hechos": (
                "1. El 10 de febrero de 2026, el vehículo buseta de placas UVC-123 de propiedad de la demandada colisionó contra el automóvil del demandante.\n"
                "2. El informe policial de accidentes de tránsito (IPAT) determinó exceso de velocidad e invasión de carril del conductor demandado.\n"
                "3. El demandante sufrió lesiones físicas y pérdida total de su vehículo evaluada en $55.000.000."
            ),
            "pretensiones": (
                "1. Declarar civil y solidariamente responsables a Transportes del Caribe S.A.S. y a Jorge Mario Pérez.\n"
                "2. Condenar al pago de $55.000.000 por daño emergente y $30.000.000 por lucro cesante y daño a la salud.\n"
                "3. Condenar en costas."
            ),
            "pruebas": "Informe IPAT No. 45678, peritaje de avalúo de daños de Fasecolda, dictamen médico de Medicina Legal.",
            "notificaciones": "Demandante: Carrera 54 # 72-10, Barranquilla; andres.mendoza@email.com. Demandada: Calle 30 # 40-12, Barranquilla; juridica@transcaribe.com.co",
            "juramento_estimatorio": "Conforme al artículo 206 del CGP, se estiman los perjuicios materiales en $85.000.000 M/CTE.",
            "conciliacion_agotada": True,
            "canal_digital_demandado": "La dirección electrónica fue informada en la audiencia de conciliación prejudicial fallida.",
        },
        "expectativas": {
            "secciones_obligatorias": ["HECHOS", "PRETENSIONES", "FUNDAMENTOS", "JURAMENTO ESTIMATORIO", "PRUEBAS", "NOTIFICACIONES"],
            "entidades_deben_aparecer": ["Andrés Felipe Mendoza", "Transportes del Caribe", "UVC-123", "85.000.000"],
            "entidades_no_deben_aparecer": ["Ecopetrol", "Clínica del Country", "Bogotá"],
            "longitud_minima": 1500,
            "longitud_maxima": 18000,
        },
    },
    {
        "id": "demanda_verbal_03_resolucion_compraventa_inmueble",
        "tipo": "demanda_verbal",
        "descripcion": "Demanda de resolución de contrato de compraventa de bien inmueble por no pago del saldo del precio.",
        "datos": {
            "destinatario": "Juez Civil del Circuito de Bucaramanga (Reparto)",
            "ciudad": "Bucaramanga (Santander)",
            "cliente": "Gloria Esperanza Duarte Gómez, C.C. 63.456.789",
            "contraparte": "Constructora Santander Siglo XXI S.A.S., NIT 900.876.543-2",
            "asunto": "Resolución de contrato de promesa de compraventa de apartamento con restitución del bien y cláusula penal",
            "cuantia": "$ 95.000.000",
            "hechos": (
                "1. El 12 de enero de 2025 las partes suscribieron contrato de promesa de compraventa sobre el apartamento 502 del Edificio Mirador del Parque.\n"
                "2. La compradora demandada se comprometió a pagar el saldo de $95.000.000 el 1 de junio de 2025 en la Notaría 3 de Bucaramanga.\n"
                "3. La demandante compareció y la demandada no asistió ni pagó el precio pactado, levantándose acta de comparecencia."
            ),
            "pretensiones": (
                "1. Declarar resuelto el contrato de compraventa por incumplimiento culpable de la demandada.\n"
                "2. Ordenar la restitución del inmueble a favor de la demandante.\n"
                "3. Condenar al pago de la cláusula penal moratoria pactada en $25.000.000."
            ),
            "pruebas": "Contrato de promesa de compraventa, copia de escritura pública, acta de comparecencia notarial del 1/06/2025.",
            "notificaciones": "Demandante: Carrera 33 # 48-20, Bucaramanga; gloria.duarte@email.com. Demandada: Calle 36 # 15-40, Bucaramanga; notificaciones@constructorsantander.com",
            "conciliacion_agotada": True,
            "canal_digital_demandado": "Canal digital obtenido del certificado de existencia y representación legal de la Cámara de Comercio de Bucaramanga.",
        },
        "expectativas": {
            "secciones_obligatorias": ["HECHOS", "PRETENSIONES", "FUNDAMENTOS", "PRUEBAS", "NOTIFICACIONES"],
            "entidades_deben_aparecer": ["Gloria Esperanza Duarte", "Constructora Santander", "Apartamento 502", "95.000.000"],
            "entidades_no_deben_aparecer": ["Sanitas", "Policía Nacional", "Arrendamiento"],
            "longitud_minima": 1500,
            "longitud_maxima": 18000,
        },
    },
]

# 3. DEMANDA EJECUTIVA
CASOS_POR_TIPO["demanda_ejecutiva"] = [
    {
        "id": "demanda_ejecutiva_01_pagare_bancario",
        "tipo": "demanda_ejecutiva",
        "descripcion": "Demanda ejecutiva singular de menor cuantía para cobro de pagaré de crédito comercial.",
        "datos": {
            "destinatario": "Juez Civil Municipal de Bogotá (Reparto)",
            "ciudad": "Bogotá, D.C.",
            "cliente": "Banco Comercial de Colombia S.A., NIT 860.001.234-5",
            "contraparte": "Servicios Logísticos del Oriente S.A.S., NIT 901.234.567-1, y avalista Jorge Enrique Prada C.C. 19.345.678",
            "titulo": "Pagaré No. 450982 con carta de instrucciones, suscrito el 10 de enero de 2025 por capital de $42.000.000",
            "valores": "Capital: $42.000.000 M/CTE más intereses corrientes y moratorios a la tasa máxima legal de la Superfinanciera desde el 1 de julio de 2025.",
            "cuantia": "$ 51.500.000",
            "medidas": "Embargo y retención de dineros en cuentas corrientes y de ahorros de los demandados en entidades bancarias.",
            "notificaciones": "Demandante: Calle 72 # 10-07, Bogotá; juridico@bancocomercial.com.co. Demandados: Carrera 15 # 85-30, Bogotá; contacto@logisticasoriente.com",
            "canal_digital_demandado": "Dirección electrónica reportada en la solicitud de crédito y en el registro mercantil.",
        },
        "expectativas": {
            "secciones_obligatorias": ["MANDAMIENTO DE PAGO", "TITULO EJECUTIVO", "FUNDAMENTOS", "PRUEBAS", "NOTIFICACIONES"],
            "entidades_deben_aparecer": ["Banco Comercial de Colombia", "Pagaré No. 450982", "42.000.000", "Jorge Enrique Prada"],
            "entidades_no_deben_aparecer": ["Tutela", "Nueva EPS", "Contrato realidad"],
            "longitud_minima": 1200,
            "longitud_maxima": 14000,
        },
    },
    {
        "id": "demanda_ejecutiva_02_cuotas_administracion",
        "tipo": "demanda_ejecutiva",
        "descripcion": "Cobro ejecutivo de expensas comunes ordinarias y extraordinarias en propiedad horizontal.",
        "datos": {
            "destinatario": "Juez Civil Municipal de Cali (Reparto)",
            "ciudad": "Cali (Valle del Cauca)",
            "cliente": "Edificio Residencial Las Palmas P.H., NIT 805.123.456-7, rep. por su Administradora Claudia Silva C.C. 31.890.123",
            "contraparte": "Alonso Mendoza Guerrero, C.C. 16.789.012, propietario del Apartamento 401",
            "titulo": "Certificación de deuda expedida por la administradora de fecha 5 de octubre de 2026 (art. 48 Ley 675 de 2001)",
            "valores": "Cuotas ordinarias y extraordinarias adeudadas: $14.200.000 más intereses de mora del 1.5 veces el interés bancario corriente.",
            "cuantia": "$ 16.800.000",
            "medidas": "Embargo y secuestro del Apartamento 401, matrícula inmobiliaria 370-123456 de la ORIP de Cali.",
            "notificaciones": "Demandante: Calle 5 # 66-20, Cali; admin@edificiolaspalmas.com. Demandado: Calle 5 # 66-20 Apto 401, Cali; alonso.mendoza@email.com",
        },
        "expectativas": {
            "secciones_obligatorias": ["MANDAMIENTO", "TITULO", "MEDIDAS CAUTELARES", "PRUEBAS", "NOTIFICACIONES"],
            "entidades_deben_aparecer": ["Edificio Residencial Las Palmas", "Alonso Mendoza Guerrero", "Apartamento 401", "14.200.000"],
            "entidades_no_deben_aparecer": ["Sanitas", "Despido injusto", "DIAN"],
            "longitud_minima": 1200,
            "longitud_maxima": 14000,
        },
    },
    {
        "id": "demanda_ejecutiva_03_acta_conciliacion",
        "tipo": "demanda_ejecutiva",
        "descripcion": "Demanda ejecutiva por incumplimiento de acuerdo en acta de conciliación extrajudicial.",
        "datos": {
            "destinatario": "Juez Civil Municipal de Medellín (Reparto)",
            "ciudad": "Medellín (Antioquia)",
            "cliente": "Beatriz Eugenia Morales Ríos, C.C. 43.123.456",
            "contraparte": "Constructores e Inmobiliarios del Valle S.A.S., NIT 900.678.901-3",
            "titulo": "Acta de Conciliación No. 120-2025 del Centro de Conciliación de la Personería de Medellín del 14/08/2025",
            "valores": "Saldo insoluto de acuerdo conciliatorio por valor de $28.000.000 pagaderos en dos cuotas vencidas el 15/10/2025 y 15/12/2025.",
            "cuantia": "$ 32.400.000",
            "medidas": "Embargo de cuentas corrientes y del vehículo de placas TKR-456 de propiedad de la demandada.",
            "notificaciones": "Demandante: Circular 4 # 73-10, Medellín; beatriz.morales@email.com. Demandada: Carrera 43A # 1-50, Medellín; gerencia@constructoresvalle.com",
        },
        "expectativas": {
            "secciones_obligatorias": ["MANDAMIENTO DE PAGO", "TITULO EJECUTIVO", "FUNDAMENTOS", "PRUEBAS", "NOTIFICACIONES"],
            "entidades_deben_aparecer": ["Beatriz Eugenia Morales", "Constructores e Inmobiliarios", "Acta de Conciliación No. 120-2025", "28.000.000"],
            "entidades_no_deben_aparecer": ["Ecopetrol", "Poder", "Tutela"],
            "longitud_minima": 1200,
            "longitud_maxima": 14000,
        },
    },
]

# 4. PETICION
CASOS_POR_TIPO["peticion"] = [
    {
        "id": "peticion_01_copias_expediente_curaduria",
        "tipo": "peticion",
        "descripcion": "Derecho de petición solicitando copias y estado de trámite de licencia de construcción.",
        "datos": {
            "destinatario": "Curador Urbano No. 2 de Bogotá D.C.",
            "ciudad": "Bogotá, D.C.",
            "cliente": "Héctor Jaime Pardo Castro, C.C. 19.456.789",
            "pretensiones": (
                "1. Expedir copia completa del expediente de radicación No. 2026-00456 correspondiente a la solicitud de licencia de construcción del predio Calle 85 # 14-30.\n"
                "2. Informar el estado actual del trámite y fecha de resolución estimada."
            ),
            "fundamentos": "Artículo 23 de la Constitución Política y Ley 1755 de 2015 (arts. 13 a 17 del CPACA sobre derecho a obtener copias e información pública).",
            "notificaciones": "Calle 85 # 14-20, Bogotá; hector.pardo@email.com; teléfono 3102345678",
        },
        "expectativas": {
            "secciones_obligatorias": ["OBJETO DE LA PETICIÓN", "FUNDAMENTOS", "NOTIFICACIONES"],
            "entidades_deben_aparecer": ["Héctor Jaime Pardo", "Curador Urbano", "2026-00456", "Ley 1755 de 2015"],
            "entidades_no_deben_aparecer": ["Sanitas", "Demanda verbal", "Pretensiones condenatorias"],
            "longitud_minima": 800,
            "longitud_maxima": 8000,
        },
    },
    {
        "id": "peticion_02_reclamacion_reliquidacion_colpensiones",
        "tipo": "peticion",
        "descripcion": "Derecho de petición a Colpensiones solicitando reliquidación pensional e inclusión de semanas cotizadas.",
        "datos": {
            "destinatario": "Administradora Colombiana de Pensiones - COLPENSIONES",
            "ciudad": "Bogotá, D.C.",
            "cliente": "Luis Alfonso Cárdenas Niño, C.C. 13.890.123",
            "pretensiones": (
                "1. Reliquidar la pensión de vejez reconocida mediante Resolución SUB-45678 de 2024.\n"
                "2. Incluir en la historia laboral 114 semanas cotizadas en la empresa Hilados Andinos entre 1988 y 1991.\n"
                "3. Pagar el retroactivo pensional derivado del reajuste."
            ),
            "fundamentos": "Art. 23 C.P., Ley 1755 de 2015, Ley 100 de 1993, Sentencia SU-769 de 2014 sobre custodia de historia laboral.",
            "pruebas": "Resolución SUB-45678, certificados de pago y planillas históricas de Hilados Andinos.",
            "notificaciones": "Transversal 22 # 53-40, Bogotá; luis.cardenas@email.com",
        },
        "expectativas": {
            "secciones_obligatorias": ["PETICIÓN", "HECHOS", "FUNDAMENTOS", "PRUEBAS", "NOTIFICACIONES"],
            "entidades_deben_aparecer": ["Luis Alfonso Cárdenas", "COLPENSIONES", "Resolución SUB-45678", "114 semanas"],
            "entidades_no_deben_aparecer": ["Divorcio", "Pagaré", "Alimentos"],
            "longitud_minima": 900,
            "longitud_maxima": 9000,
        },
    },
    {
        "id": "peticion_03_servicios_publicos_desviacion",
        "tipo": "peticion",
        "descripcion": "Petición y reclamo a empresa de acueducto por desviación significativa en la facturación.",
        "datos": {
            "destinatario": "Empresa de Acueducto y Alcantarillado de Pereira - Aguas y Aguas",
            "ciudad": "Pereira (Risaralda)",
            "cliente": "Marta Elena Quintero Solorza, C.C. 42.567.890",
            "pretensiones": (
                "1. Investigar y corregir la desviación significativa en el consumo facturado en el mes de septiembre de 2026 (cuenta contrato 987654).\n"
                "2. Practicar visita técnica de inspección al medidor No. 45892.\n"
                "3. Reliquidar la factura cobrando el consumo promedio histórico mientras se resuelve la reclamación."
            ),
            "fundamentos": "Artículo 23 de la Constitución, artículos 149 y 150 de la Ley 142 de 1994 (Régimen de Servicios Públicos Domiciliarios).",
            "pruebas": "Facturas de los últimos 6 periodos donde consta consumo promedio de 14 m3 y factura reclamada con 85 m3.",
            "notificaciones": "Avenida Circunvalar # 12-45, Pereira; marta.quintero@email.com",
        },
        "expectativas": {
            "secciones_obligatorias": ["PETICIÓN", "HECHOS", "FUNDAMENTOS", "PRUEBAS", "NOTIFICACIONES"],
            "entidades_deben_aparecer": ["Marta Elena Quintero", "Aguas y Aguas", "987654", "Ley 142 de 1994"],
            "entidades_no_deben_aparecer": ["Demanda penal", "Corte Suprema", "Fiscalía"],
            "longitud_minima": 800,
            "longitud_maxima": 8000,
        },
    },
]

# 5. DESACATO
CASOS_POR_TIPO["desacato"] = [
    {
        "id": "desacato_01_salud_cirugia",
        "tipo": "desacato",
        "descripcion": "Incidente de desacato por no realización de procedimiento quirúrgico ordenado en sentencia de tutela.",
        "datos": {
            "destinatario": "Juez Cuarto Civil Municipal de Bogotá",
            "ciudad": "Bogotá, D.C.",
            "radicado": "11001-40-03-004-2026-00120-00",
            "cliente": "Rosa María Valencia de Gómez, C.C. 24.567.890",
            "contraparte": "EPS Sanitas S.A.S., Representante Legal Dr. Juan Pablo Restrepo",
            "fallo": "Sentencia de tutela del 15 de agosto de 2026 que concedió el amparo y ordenó practicar artroplastia total de rodilla en 10 días.",
            "incumplimiento": "Han transcurrido más de 45 días sin que la EPS asigne quirófano ni especialista, desacatando abiertamente la orden judicial.",
            "pretensiones": (
                "1. Abrir incidente de desacato conforme al artículo 52 del Decreto 2591 de 1991.\n"
                "2. Requerir al superior jerárquico del obligado según el artículo 27.\n"
                "3. Imponer las sanciones de arresto hasta por 6 meses y multa de hasta 20 salarios mínimos legales."
            ),
            "pruebas": "Copia de sentencia de tutela del 15/08/2026, requerimientos reiterados radicados ante la EPS el 25/08 y 15/09/2026.",
            "notificaciones": "Accionante: Calle 127 # 45-20, Bogotá; rosa.valencia@email.com. Accionada: notificaciones@epssanitas.com",
        },
        "expectativas": {
            "secciones_obligatorias": ["ANTECEDENTES", "HECHOS DEL INCUMPLIMIENTO", "SOLICITUDES", "PRUEBAS", "NOTIFICACIONES"],
            "entidades_deben_aparecer": ["Rosa María Valencia", "EPS Sanitas", "11001-40-03-004-2026-00120-00", "Decreto 2591 de 1991"],
            "entidades_no_deben_aparecer": ["Contrato de trabajo", "Prescripción adquisitiva"],
            "longitud_minima": 1000,
            "longitud_maxima": 10000,
        },
    },
    {
        "id": "desacato_02_peticion_sin_respuesta",
        "tipo": "desacato",
        "descripcion": "Incidente de desacato contra Secretaría de Movilidad por no contestar derecho de petición tutelado.",
        "datos": {
            "destinatario": "Juez Diez Administrativo de Medellín",
            "ciudad": "Medellín (Antioquia)",
            "radicado": "05001-33-33-010-2026-00215-00",
            "cliente": "Carlos Alberto Osorio Mesa, C.C. 71.234.567",
            "contraparte": "Secretaría de Movilidad de Medellín, Secretario de Despacho",
            "fallo": "Fallo de tutela No. 145 del 1 de septiembre de 2026 que ordenó responder de fondo la petición en 48 horas.",
            "incumplimiento": "Vencido con creces el término perentorio, la entidad accionada no ha emitido respuesta alguna.",
            "pretensiones": (
                "1. Iniciar trámite incidental de desacato (arts. 27 y 52 Decreto 2591 de 1991).\n"
                "2. Sancionar al funcionario responsable con multa y arresto por desacato continuo."
            ),
            "pruebas": "Fallo de tutela notificado el 2/09/2026, constancia de no respuesta.",
            "notificaciones": "Accionante: Calle 50 # 45-12, Medellín; carlos.osorio@email.com. Accionada: notificacionesmovilidad@medellin.gov.co",
        },
        "expectativas": {
            "secciones_obligatorias": ["ANTECEDENTES", "INCUMPLIMIENTO", "SOLICITUDES", "PRUEBAS"],
            "entidades_deben_aparecer": ["Carlos Alberto Osorio", "Secretaría de Movilidad", "05001-33-33-010-2026-00215-00"],
            "entidades_no_deben_aparecer": ["Colpensiones", "Clínica Medellín"],
            "longitud_minima": 900,
            "longitud_maxima": 9000,
        },
    },
    {
        "id": "desacato_03_reintegro_fueromaterno",
        "tipo": "desacato",
        "descripcion": "Desacato por omisión en reintegro laboral ordenado en fallo de tutela a madre lactante.",
        "datos": {
            "destinatario": "Juez Séptimo Laboral del Circuito de Cali",
            "ciudad": "Cali (Valle del Cauca)",
            "radicado": "76001-31-05-007-2026-00088-00",
            "cliente": "Lorena Patricia Benítez Rojas, C.C. 1.130.456.789",
            "contraparte": "Empresas Textiles de Occidente S.A., Gerente General",
            "fallo": "Sentencia de tutela del 20 de julio de 2026 que ordenó reintegrar a la trabajadora en 48 horas a su cargo habitual.",
            "incumplimiento": "La empresa se negó a recibirla en sus instalaciones y no ha pagado los salarios ordenados.",
            "pretensiones": (
                "1. Abrir incidente de desacato y requerir al representante legal.\n"
                "2. Imponer sanción de arresto y multa pecuniaria hasta tanto se cumpla efectivamente la orden de reintegro."
            ),
            "pruebas": "Sentencia judicial, acta de presentación a laborar del 25/07/2026 rechazada por la empresa.",
            "notificaciones": "Accionante: Calle 15 # 30-40, Cali; lorena.benitez@email.com. Accionada: legal@textilesoccidente.com.co",
        },
        "expectativas": {
            "secciones_obligatorias": ["ANTECEDENTES", "INCUMPLIMIENTO", "SOLICITUDES", "NOTIFICACIONES"],
            "entidades_deben_aparecer": ["Lorena Patricia Benítez", "Empresas Textiles", "76001-31-05-007-2026-00088-00"],
            "entidades_no_deben_aparecer": ["Pensiones", "DIAN", "Hospital"],
            "longitud_minima": 900,
            "longitud_maxima": 9000,
        },
    },
]


def generar_archivos_casos():
    """Genera los archivos JSON en tests/casos/ con 3 casos para cada uno de los 25 tipos."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    tipos = listar_tipos(incluir_guia=True)

    print(f"Total tipos en catálogo: {len(tipos)}")

    for t in tipos:
        tid = t["id"]
        # Si ya definimos casos detallados manuales arriba, usarlos
        if tid in CASOS_POR_TIPO:
            casos = CASOS_POR_TIPO[tid]
        else:
            # Generar 3 casos sintéticos pero procesalmente consistentes con sus campos requeridos
            casos = _generar_tres_casos_para_tipo(t)

        # Validar que los casos cumplan con los campos requeridos del tipo
        for c in casos:
            errs = validar_datos_tipo(t, c["datos"])
            if errs:
                print(f"ALERTA: Caso {c['id']} tiene errores de validación: {errs}")

        out_path = os.path.join(OUTPUT_DIR, f"{tid}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(casos, f, ensure_ascii=False, indent=2)

        print(f"Guardado: {out_path} ({len(casos)} casos)")


def _generar_tres_casos_para_tipo(tipo: dict[str, Any]) -> list[dict[str, Any]]:
    """Genera 3 casos contextualizados para un tipo del catálogo basándose en su estructura y requerimientos."""
    tid = tipo["id"]
    nombre = tipo.get("nombre", tid)
    campos_req = [c for g in tipo.get("grupos", []) for c in g.get("campos", []) if c.get("req")]
    todos_campos = [c for g in tipo.get("grupos", []) for c in g.get("campos", [])]

    casos = []
    ciudades = [
        ("Bogotá, D.C.", "11001-40-03-010-2026-00101-00"),
        ("Medellín (Antioquia)", "05001-31-03-005-2025-00202-00"),
        ("Cali (Valle del Cauca)", "76001-22-01-008-2024-00303-00")
    ]

    for i in range(1, 4):
        cid = f"{tid}_{i:02d}_caso_estandar"
        ciudad, radicado_ej = ciudades[i - 1]

        datos: dict[str, Any] = {}
        # Asignar valores a campos
        for c in todos_campos:
            k = c.get("k", "")
            t_campo = c.get("t", "texto")
            l_campo = c.get("l", k)

            if k == "destinatario":
                datos[k] = f"Señor Juez Competente de {ciudad}"
            elif k == "ciudad":
                datos[k] = ciudad
            elif k == "radicado":
                datos[k] = radicado_ej
            elif k == "cliente":
                datos[k] = f"Persona Natural Ejemplo {i}, C.C. 1.010.20{i}.30{i}"
            elif k == "contraparte":
                datos[k] = f"Entidad o Empresa Demandada {i} S.A.S., NIT 900.12{i}.34{i}-8"
            elif k == "notificacion_fecha":
                datos[k] = "2026-10-01"
            elif k == "notificaciones":
                datos[k] = f"Demandante: Calle {i}0 # 20-30, {ciudad}; cliente{i}@correo.com. Demandado: Carrera {i}5 # 10-20; notificaciones{i}@empresa.com"
            elif k == "cuantia":
                datos[k] = f"$ {i * 30}.000.000"
            elif t_campo == "check":
                datos[k] = True
            elif t_campo == "date":
                datos[k] = "2026-10-01"
            elif t_campo == "area":
                datos[k] = f"Detalle de hechos y circunstancias fácticas del caso {i} correspondiente a {nombre} en la ciudad de {ciudad}."
            elif t_campo == "chips":
                datos[k] = ["Prueba documental", "Testimonial"]
            elif t_campo == "select":
                opciones = c.get("opciones", [])
                if opciones:
                    primera = opciones[0]
                    datos[k] = primera[0] if isinstance(primera, (list, tuple)) else str(primera)
                else:
                    datos[k] = "opcion_1"
            else:
                # Texto general
                datos[k] = f"Dato descriptivo para {l_campo} caso {i}"

        secciones = ["HECHOS", "PRETENSIONES", "PRUEBAS", "NOTIFICACIONES"]
        if tid == "poder":
            secciones = ["PODER", "FACULTADES"]
        elif tid == "desacato":
            secciones = ["ANTECEDENTES", "INCUMPLIMIENTO", "SOLICITUDES"]
        elif tid == "demanda_ejecutiva":
            secciones = ["MANDAMIENTO", "TITULO", "PRUEBAS"]

        caso = {
            "id": cid,
            "tipo": tid,
            "descripcion": f"Caso {i} de prueba formal y procesal para el trámite de {nombre} en {ciudad}.",
            "datos": datos,
            "expectativas": {
                "secciones_obligatorias": secciones,
                "entidades_deben_aparecer": [
                    f"Persona Natural Ejemplo {i}",
                    f"Entidad o Empresa Demandada {i}"
                ],
                "entidades_no_deben_aparecer": [
                    "Empresa Ficticia Extranjera Inexistente",
                    "Ciudad Inexistente Desconocida"
                ],
                "longitud_minima": 800,
                "longitud_maxima": 18000,
            }
        }
        casos.append(caso)

    return casos


if __name__ == "__main__":
    generar_archivos_casos()
