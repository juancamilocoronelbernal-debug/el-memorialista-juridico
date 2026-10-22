"""
Servicio de revisión de requisitos legales y procesales para escritos jurídicos.
Evalúa el cumplimiento de los requisitos del catálogo según la norma de cada tipo.
"""
import json
import logging
import re
from typing import Any, Tuple

from app.services.prompt import obtener_tipo
from app.services.gemini_service import gemini_service

log = logging.getLogger("memorialista.revisor")


def _evaluacion_heuristica(req: dict[str, Any], texto_lower: str) -> Tuple[str, str, str]:
    """Evaluación heurística de respaldo en caso de que no haya conexión con el modelo de IA."""
    rid = req.get("id", "")
    critico = bool(req.get("critico", False))
    norma = req.get("norma", "")

    if "juramento" in rid and ("otra_tutela" in rid or "art37" in rid or "2591" in norma):
        if ("juramento" in texto_lower or "juró" in texto_lower) and ("otra" in texto_lower or "2591" in texto_lower or "misma" in texto_lower):
            return "cumple", "Contiene manifestación bajo juramento de no haber interpuesto otra tutela.", ""
        return "no_cumple", "No se encontró la manifestación bajo juramento del art. 37 del Decreto 2591 de 1991.", "Agrega en acápite de JURAMENTO: 'Manifiesto bajo la gravedad del juramento que no he presentado otra acción de tutela por los mismos hechos y derechos ante ninguna autoridad judicial (art. 37 del Decreto 2591 de 1991)'."

    if "juramento_estimatorio" in rid or "206" in norma:
        if "juramento estimatorio" in texto_lower or "artículo 206" in texto_lower or "art. 206" in texto_lower:
            return "cumple", "Incluye acápite de juramento estimatorio.", ""
        if any(p in texto_lower for p in ("perjuicio", "daño emergente", "lucro cesante", "indemniza")):
            return "no_cumple", "Se reclaman perjuicios pero se omitió el juramento estimatorio.", "Agrega acápite de JURAMENTO ESTIMATORIO discriminando concepto por concepto la cuantía razonada de los perjuicios reclamados (art. 206 CGP)."
        return "no_aplica", "No se evidencian pretensiones de condena en perjuicios materiales.", ""

    if "canal_digital" in rid or "juramento_canal" in rid or "2213" in norma:
        tiene_correo = "@" in texto_lower or "correo" in texto_lower or "canal digital" in texto_lower
        tiene_juramento = "juramento" in texto_lower and ("dirección" in texto_lower or "canal" in texto_lower or "obtuvo" in texto_lower)
        if "juramento_canal" in rid:
            if tiene_juramento:
                return "cumple", "Contiene afirmación sobre el canal digital del demandado.", ""
            return "no_cumple", "Falta la afirmación bajo juramento sobre cómo se obtuvo la dirección electrónica.", "Agrega en notificaciones: 'Afirmo bajo la gravedad del juramento que la dirección electrónica indicada para el demandado es la que utiliza para sus comunicaciones y fue obtenida [indicar medio o evidencia], conforme al art. 8 de la Ley 2213 de 2022'."
        if tiene_correo:
            return "cumple", "Se indican canales digitales de las partes.", ""
        return "no_cumple", "No se identificaron direcciones electrónicas para las partes.", "Incluye los canales digitales (correos electrónicos) de las partes y sus apoderados (art. 6 Ley 2213 de 2022)."

    if "conciliacion" in rid or "2220" in norma:
        if "concilia" in texto_lower:
            return "cumple", "Se menciona el trámite o constancia de conciliación prejudicial.", ""
        if "cautelar" in texto_lower or "embargo" in texto_lower or "secuestro" in texto_lower:
            return "no_aplica", "Se solicitan medidas cautelares previas, lo cual exceptúa el requisito de procedibilidad.", ""
        return "no_cumple", "No se indica si se agotó la conciliación previa obligatoria.", "Indica que se agotó la conciliación extrajudicial en derecho aportando la constancia de no acuerdo o imposibilidad (Ley 2220 de 2022)."

    if "contraprestacion" in rid or "420" in norma and "5" in norma:
        if "contraprestación" in texto_lower or "contraprestacion" in texto_lower or "no depende" in texto_lower:
            return "cumple", "Contiene manifestación de no depender de contraprestación pendiente (art. 420 num. 5 CGP).", ""
        return "no_cumple", "Falta manifestación expresa de que el pago no depende de contraprestación pendiente del acreedor.", "Incluye en los hechos o acápite de juramento: 'Manifiesto que el pago de la suma demandada no depende del cumplimiento de una contraprestación pendiente a cargo del acreedor (art. 420 num. 5 del CGP)'."

    if "apercibimiento" in rid or "421" in norma:
        if "apercibimiento" in texto_lower or "fuerza de sentencia" in texto_lower or "auto con fuerza" in texto_lower or ("421" in texto_lower and "silencio" in texto_lower):
            return "cumple", "Incluye solicitud de apercibimiento legal del art. 421 del CGP.", ""
        return "no_cumple", "Falta solicitud expresa de apercibimiento legal del art. 421 del CGP.", "Agrega en pretensiones: 'Solicito apercibir al demandado conforme al artículo 421 del CGP, advirtiéndole que si no paga o guarda silencio dentro del término de 10 días, se dictará auto con fuerza de sentencia condenatoria'."

    if "pruebas_o_juramento" in rid or ("420" in norma and "6" in norma):
        if "prueba" in texto_lower or "anexo" in texto_lower or "juramento" in texto_lower or "document" in texto_lower:
            return "cumple", "Se relacionan pruebas documentales o juramento de carecer de ellas.", ""
        return "no_cumple", "Se omitieron las pruebas documentales o el juramento de no poseerlas.", "Relaciona los documentos contractuales o manifiesta bajo juramento que careces de ellos (art. 420 num. 6 CGP)."

    if "procedencia" in rid or "subsidiariedad" in rid:
        if "subsidiariedad" in texto_lower or "inmediatez" in texto_lower or "perjuicio irremediable" in texto_lower or "otro medio" in texto_lower:
            return "cumple", "Desarrolla los requisitos de procedencia, inmediatez y subsidiariedad.", ""
        return "no_cumple", "Falta fundamentación explícita sobre la procedencia de la tutela.", "Agrega acápite de PROCEDENCIA justificando la inmediatez y la falta de otro mecanismo judicial idóneo y eficaz o la configuración de un perjuicio irremediable."

    if "notificaciones" in rid:
        if "notificaci" in texto_lower or "direcci" in texto_lower:
            return "cumple", "Contiene acápite de notificaciones.", ""
        return "no_cumple", "Se omitió el acápite de notificaciones.", "Incluye acápite de NOTIFICACIONES con dirección física y electrónica de las partes."

    if "juez" in rid or "destinatario" in rid or "autoridad" in rid:
        if any(j in texto_lower for j in ("juez", "tribunal", "magistrad", "señor", "señores", "fiscalía", "procuraduría", "alcaldía")):
            return "cumple", "Contiene designación de la autoridad o despacho judicial.", ""
        return "no_cumple", "Falta la designación del juez o autoridad a quien se dirige.", "Indica expresamente el juez o entidad competente a quien se dirige el escrito."

    if "pretension" in rid or "objeto" in rid or "mandamiento" in rid:
        if "pretensi" in texto_lower or "pido" in texto_lower or "solicito" in texto_lower or "mandamiento" in texto_lower:
            return "cumple", "Pretensiones formuladas en el texto.", ""
        return "no_cumple", "No se identificaron pretensiones claras.", "Formula con precisión y claridad lo que se pretende de manera numerada y clasificada."

    if "hecho" in rid:
        if "hecho" in texto_lower or "1." in texto_lower:
            return "cumple", "Contiene narración de hechos.", ""
        return "no_cumple", "Falta la relación numerada de hechos.", "Expón los hechos en orden cronológico, numerados y clasificados."

    if "cuantia" in rid or "competencia" in rid:
        if "cuantía" in texto_lower or "cuantia" in texto_lower or "competencia" in texto_lower or "$" in texto_lower or "smmlv" in texto_lower:
            return "cumple", "Se estima la cuantía o se indica la competencia.", ""
        return "no_cumple" if critico else "no_aplica", "No se indica la cuantía o competencia.", "Incluye acápite de CUANTÍA Y COMPETENCIA indicando el valor de las pretensiones para fijar el trámite."

    # Heurística genérica
    palabras_clave = [p for p in re.findall(r'\b[a-zA-ZáéíóúÁÉÍÓÚñÑ]{4,}\b', req.get("texto", "").lower()) if p not in ("para", "cada", "este", "cual", "como", "sobre", "entre")]
    coincidencias = sum(1 for p in palabras_clave if p in texto_lower)
    if coincidencias >= max(1, len(palabras_clave) // 3):
        return "cumple", "El escrito aborda los elementos esenciales del requisito.", ""
    if critico:
        return "no_cumple", f"No se evidencia el cumplimiento claro de este requisito ({norma}).", f"Revisa e incorpora lo exigido por {norma}: {req.get('texto', '')}."
    return "no_aplica", "Requisito no evidenciado o no exigible en este trámite concreto.", ""


async def revisar_requisitos(escrito: str, tipo_id: str) -> list[dict[str, Any]]:
    """
    Evalúa el cumplimiento de cada requisito normativo del tipo para el escrito dado.
    Utiliza un modelo de IA económico (gemini-3.5-flash-lite) con salida JSON estructurada,
    respaldado por verificación heurística determinista.
    """
    tipo = obtener_tipo(tipo_id)
    if not tipo:
        return []

    requisitos = tipo.get("requisitos", [])
    if not requisitos:
        return []

    prompt = (
        "Eres un auditor jurídico colombiano experto en técnica procesal y derecho procesal civil, laboral, penal y administrativo.\n"
        f"Tu tarea es evaluar si el siguiente escrito jurídico cumple con cada uno de los requisitos normativos del tipo de escrito '{tipo.get('nombre', tipo_id)}'.\n\n"
        f"NORMA BASE DEL TIPO: {tipo.get('norma', '')}\n\n"
        "REQUISITOS A EVALUAR:\n"
        f"{json.dumps(requisitos, ensure_ascii=False, indent=2)}\n\n"
        "ESCRITO JURÍDICO A REVISAR:\n<<<\n"
        f"{escrito[:35000]}\n>>>\n\n"
        "INSTRUCCIONES DE EVALUACIÓN:\n"
        "Para CADA requisito de la lista debes determinar:\n"
        '- "id": el ID exacto del requisito evaluado.\n'
        '- "estado": "cumple" si el escrito contiene el requisito; "no_cumple" si fue omitido o está defectuoso; "no_aplica" si por las particularidades del escrito no es exigible (ej.: juramento estimatorio cuando no se cobran perjuicios, conciliación previa cuando se piden medidas cautelares).\n'
        '- "evidencia": fragmento breve del texto (máx 200 caracteres) que demuestra el cumplimiento o explica brevemente la omisión.\n'
        '- "sugerencia": si el estado es "no_cumple", redacta la sugerencia o fórmula jurídica exacta para subsanarlo. Si cumple o no aplica, deja una cadena vacía o breve nota.\n\n'
        "Responde EXCLUSIVAMENTE con un arreglo JSON válido con este esquema:\n"
        "[\n"
        '  {\n    "id": "identificador",\n    "estado": "cumple" | "no_cumple" | "no_aplica",\n    "evidencia": "texto",\n    "sugerencia": "texto"\n  }\n'
        "]"
    )

    datos_eval = None
    try:
        datos_eval = await gemini_service.evaluar_requisitos_json(prompt)
    except Exception as exc:  # noqa: BLE001
        log.warning("Evaluación de requisitos con IA omitida o falló: %s", exc)

    eval_map = {}
    if isinstance(datos_eval, list):
        for item in datos_eval:
            if isinstance(item, dict) and "id" in item:
                eval_map[item["id"]] = item

    resultado = []
    texto_lower = escrito.lower()
    for req in requisitos:
        rid = req["id"]
        ev = eval_map.get(rid)

        if ev and isinstance(ev, dict):
            estado = str(ev.get("estado", "")).lower().strip()
            if estado not in ("cumple", "no_cumple", "no_aplica"):
                estado = "cumple" if "cumple" in estado else "no_cumple"
            evidencia = str(ev.get("evidencia", ""))[:300]
            sugerencia = str(ev.get("sugerencia", ""))[:500]
        else:
            estado, evidencia, sugerencia = _evaluacion_heuristica(req, texto_lower)

        resultado.append({
            "id": rid,
            "texto": req.get("texto", ""),
            "norma": req.get("norma", ""),
            "critico": bool(req.get("critico", False)),
            "estado": estado,
            "evidencia": evidencia,
            "sugerencia": sugerencia,
        })

    return resultado
