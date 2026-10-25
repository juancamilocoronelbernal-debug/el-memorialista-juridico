# -*- coding: utf-8 -*-
"""
Script de procesamiento controlado del lote de hasta 25 providencias (Fase 2.4 Preparación).
Procesa sentencias de muestra diversa (T, C, SU), validando metadatos y extrayendo sin truncamiento.
Quedan estrictamente en bandeja de triage (workflow_status='pending_legal_review', published=False).
"""

import asyncio
import logging
from app.services.conector_corte_constitucional import validate_and_stage_ruling

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("memorialista.lote25")

PROCESAR_BATCH = [
    {
        "sentencia": "C-577/11",
        "url": "https://www.corteconstitucional.gov.co/relatoria/2011/C-577-11.htm",
        "tipo": "C",
        "anio": 2011,
        "fecha": "2011-07-26",
        "magistrado": "Gabriel Eduardo Mendoza Martelo",
        "sala": "Sala Plena",
        "proceso": "Demanda de inconstitucionalidad",
        "tema": "Protección a las parejas del mismo sexo e institución del matrimonio",
    },
    {
        "sentencia": "C-029/09",
        "url": "https://www.corteconstitucional.gov.co/relatoria/2009/C-029-09.htm",
        "tipo": "C",
        "anio": 2009,
        "fecha": "2009-01-28",
        "magistrado": "Rodrigo Escobar Gil",
        "sala": "Sala Plena",
        "proceso": "Demanda de inconstitucionalidad",
        "tema": "Ampliación de derechos patrimoniales y civiles para parejas del mismo sexo",
    },
    {
        "sentencia": "C-221/94",
        "url": "https://www.corteconstitucional.gov.co/relatoria/1994/C-221-94.htm",
        "tipo": "C",
        "anio": 1994,
        "fecha": "1994-05-05",
        "magistrado": "Carlos Gaviria Díaz",
        "sala": "Sala Plena",
        "proceso": "Demanda de inconstitucionalidad",
        "tema": "Despenalización del porte y consumo de la dosis personal",
    },
    {
        "sentencia": "C-591/05",
        "url": "https://www.corteconstitucional.gov.co/relatoria/2005/C-591-05.htm",
        "tipo": "C",
        "anio": 2005,
        "fecha": "2005-06-09",
        "magistrado": "Clara Inés Vargas Hernández",
        "sala": "Sala Plena",
        "proceso": "Demanda de inconstitucionalidad",
        "tema": "Implementación del sistema penal acusatorio y garantías constitucionales",
    },
    {
        "sentencia": "C-084/20",
        "url": "https://www.corteconstitucional.gov.co/relatoria/2020/C-084-20.htm",
        "tipo": "C",
        "anio": 2020,
        "fecha": "2020-03-04",
        "magistrado": "Diana Fajardo Rivera",
        "sala": "Sala Plena",
        "proceso": "Demanda de inconstitucionalidad",
        "tema": "Juicio de sustitución de la Constitución y límites competenciales del Congreso",
    },
    {
        "sentencia": "C-258/13",
        "url": "https://www.corteconstitucional.gov.co/relatoria/2013/C-258-13.htm",
        "tipo": "C",
        "anio": 2013,
        "fecha": "2013-05-07",
        "magistrado": "Jorge Ignacio Pretelt Chaljub",
        "sala": "Sala Plena",
        "proceso": "Demanda de inconstitucionalidad",
        "tema": "Topes constitucionales a pensiones del régimen de transición de congresistas",
    },
    {
        "sentencia": "SU-096/18",
        "url": "https://www.corteconstitucional.gov.co/relatoria/2018/SU096-18.htm",
        "tipo": "SU",
        "anio": 2018,
        "fecha": "2018-10-11",
        "magistrado": "José Fernando Reyes Cuartas",
        "sala": "Sala Plena",
        "proceso": "Acción de tutela",
        "tema": "Consulta previa de comunidades étnicas y megaproyectos extractivos",
    },
    {
        "sentencia": "SU-049/17",
        "url": "https://www.corteconstitucional.gov.co/relatoria/2017/SU049-17.htm",
        "tipo": "SU",
        "anio": 2017,
        "fecha": "2017-02-02",
        "magistrado": "María Victoria Calle Correa",
        "sala": "Sala Plena",
        "proceso": "Acción de tutela",
        "tema": "Unificación de reglas sobre estabilidad laboral reforzada por debilidad manifiesta",
    },
    {
        "sentencia": "SU-241/15",
        "url": "https://www.corteconstitucional.gov.co/relatoria/2015/SU241-15.htm",
        "tipo": "SU",
        "anio": 2015,
        "fecha": "2015-04-30",
        "magistrado": "Gloria Stella Ortiz Delgado",
        "sala": "Sala Plena",
        "proceso": "Acción de tutela",
        "tema": "Derecho a la indexación de la primera mesada pensional en regímenes especiales",
    },
    {
        "sentencia": "SU-440/21",
        "url": "https://www.corteconstitucional.gov.co/relatoria/2021/SU440-21.htm",
        "tipo": "SU",
        "anio": 2021,
        "fecha": "2021-12-09",
        "magistrado": "Antonio José Lizarazo Ocampo",
        "sala": "Sala Plena",
        "proceso": "Acción de tutela",
        "tema": "Contratos de prestación de servicios y primacía de la realidad en entidades públicas",
    },
    {
        "sentencia": "SU-073/20",
        "url": "https://www.corteconstitucional.gov.co/relatoria/2020/SU073-20.htm",
        "tipo": "SU",
        "anio": 2020,
        "fecha": "2020-02-27",
        "magistrado": "Alejandro Linares Cantillo",
        "sala": "Sala Plena",
        "proceso": "Acción de tutela",
        "tema": "Mora patronal en aportes pensionales y deber de cobro de las administradoras",
    },
    {
        "sentencia": "C-355/06",
        "url": "https://www.corteconstitucional.gov.co/relatoria/2006/C-355-06.htm",
        "tipo": "C",
        "anio": 2006,
        "fecha": "2006-05-10",
        "magistrado": "Jaime Araújo Rentería y Clara Inés Vargas",
        "sala": "Sala Plena",
        "proceso": "Demanda de inconstitucionalidad",
        "tema": "Despenalización del aborto en tres circunstancias extremas",
    },
]

async def main():
    log.info("Iniciando procesamiento controlado de 12 providencias C y SU para completar lote de 25 en triage...")
    results = []
    for item in PROCESAR_BATCH:
        sent = item["sentencia"]
        log.info("Procesando providencia: %s (%s)", sent, item["tipo"])
        try:
            res = await validate_and_stage_ruling(item, auto_publish=False, semantic=True)
            log.info("Resultado %s: status=%s, validation_status=%s, published=%s",
                     sent, res.get("status"), res.get("validation_status"), res.get("published"))
            results.append({"sentencia": sent, "status": res.get("status"), "passed": res.get("passed")})
        except Exception as exc:
            log.error("Fallo al procesar %s: %s", sent, exc)
            results.append({"sentencia": sent, "status": "error", "error": str(exc)})
        await asyncio.sleep(2)

    log.info("Procesamiento finalizado. Total providencias procesadas en este ciclo: %d", len(results))
    for r in results:
        log.info("  - %s: %s", r["sentencia"], r.get("status"))

if __name__ == "__main__":
    asyncio.run(main())
