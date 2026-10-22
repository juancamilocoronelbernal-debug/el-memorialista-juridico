"""Servicio de catálogo y construcción de prompts en el servidor (app/services/prompt.py)."""
import datetime
import json
import os
import re
from typing import Any, Optional

CATALOGO_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "catalogo")
TIPOS_DIR = os.path.join(CATALOGO_DIR, "tipos")

MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
]

_CATALOGO_CACHE: dict[str, Any] = {}


def limpiar_cache():
    _CATALOGO_CACHE.clear()


def fecha_larga(d: Optional[datetime.date] = None) -> str:
    if d is None:
        d = datetime.date.today()
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}"


def pesos(n: Any) -> str:
    try:
        val = round(float(n or 0))
    except (ValueError, TypeError):
        val = 0
    # En es-CO los miles se separan con punto
    formatted = f"{val:,}".replace(",", ".")
    return f"${formatted}"


def genero_ab(genero: str) -> str:
    return "a" if genero == "f" else "o" if genero == "m" else "o(a)"


def cargar_formato_salida() -> str:
    if "formato_salida" not in _CATALOGO_CACHE:
        path = os.path.join(CATALOGO_DIR, "formato_salida.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            _CATALOGO_CACHE["formato_salida"] = data["texto"]
    return _CATALOGO_CACHE["formato_salida"]


def cargar_contexto_normativo(smmlv: int = 1750905) -> list[str]:
    path = os.path.join(CATALOGO_DIR, "contexto_normativo.json")
    with open(path, "r", encoding="utf-8") as f:
        reglas = json.load(f)
    lineas = []
    for r in reglas:
        if "plantilla" in r:
            lineas.append(r["plantilla"].format(smmlv=pesos(smmlv)))
        else:
            lineas.append(r["texto"])
    return lineas


def cargar_areas() -> list[str]:
    if "areas" not in _CATALOGO_CACHE:
        path = os.path.join(CATALOGO_DIR, "areas.json")
        with open(path, "r", encoding="utf-8") as f:
            _CATALOGO_CACHE["areas"] = json.load(f)
    return _CATALOGO_CACHE["areas"]


def cargar_grupo_redaccion() -> dict[str, Any]:
    if "grupo_redaccion" not in _CATALOGO_CACHE:
        path = os.path.join(CATALOGO_DIR, "grupo_redaccion.json")
        with open(path, "r", encoding="utf-8") as f:
            _CATALOGO_CACHE["grupo_redaccion"] = json.load(f)
    return _CATALOGO_CACHE["grupo_redaccion"]


def obtener_tipo(tipo_id: str) -> Optional[dict[str, Any]]:
    path = os.path.join(TIPOS_DIR, f"{tipo_id}.json")
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def listar_tipos(incluir_guia: bool = False) -> list[dict[str, Any]]:
    tipos = []
    if not os.path.isdir(TIPOS_DIR):
        return tipos
    for filename in sorted(os.listdir(TIPOS_DIR)):
        if filename.endswith(".json"):
            path = os.path.join(TIPOS_DIR, filename)
            with open(path, "r", encoding="utf-8") as f:
                tipo = json.load(f)
                if not incluir_guia:
                    tipo.pop("guia", None)
                tipos.append(tipo)
    return tipos


def grupo_redaccion_para_tipo(tipo: dict[str, Any]) -> dict[str, Any]:
    """Genera la estructura de campos del grupo 'Redacción' correspondiente a un tipo."""
    campos = [
        {
            "k": "fundamentos",
            "l": "Normas o jurisprudencia que quieres citar",
            "t": "area",
            "rows": 2,
            "ph": "Opcional. Ej.: Sentencia T-760 de 2008; art. 49 de la Constitución."
        },
        {
            "k": "_extension",
            "l": "Extensión",
            "t": "select",
            "opciones": [["concisa", "Concisa"], ["estandar", "Estándar"], ["extensa", "Extensa y exhaustiva"]],
            "def": "concisa" if tipo.get("breve") else "@extension"
        },
        {
            "k": "_juris",
            "l": "Jurisprudencia",
            "t": "select",
            "opciones": [
                ["verificables", "Solo citas verificables"],
                ["sugerir", "Sugerir sentencias, marcadas para verificar"],
                ["usuario", "Solo la que yo indique"],
                ["ninguna", "No citar jurisprudencia"]
            ],
            "def": tipo.get("juris") or "verificables"
        }
    ]
    if tipo.get("firma") != "poder":
        campos.append({
            "k": "_firma",
            "l": "Quién firma",
            "t": "select",
            "opciones": [
                ["apoderado", "Yo, como apoderado(a)"],
                ["propio", "Yo, en nombre propio"],
                ["cliente", "Mi cliente, en nombre propio"]
            ],
            "def": tipo.get("firma") or "apoderado"
        })
    campos.append({"k": "_membrete", "l": "Incluir mi membrete en este escrito", "t": "check", "def": True})
    campos.append({
        "k": "_notas",
        "l": "Indicaciones adicionales",
        "t": "area",
        "rows": 2,
        "ph": "Ej.: Enfatiza que la accionante es adulta mayor; no menciones el nombre del médico."
    })
    return {"n": "Redacción", "campos": campos}


def campos_tipo(tipo: dict[str, Any]) -> list[dict[str, Any]]:
    campos = []
    for g in tipo.get("grupos", []):
        campos.extend(g.get("campos", []))
    campos.extend(grupo_redaccion_para_tipo(tipo).get("campos", []))
    return campos


def validar_datos_tipo(tipo: dict[str, Any], datos: dict[str, Any]) -> list[str]:
    """Valida los campos obligatorios requeridos por el tipo. Devuelve lista de errores."""
    errores = []
    for g in tipo.get("grupos", []):
        for c in g.get("campos", []):
            k = c.get("k")
            v = datos.get(k)
            v_vacio = v is None or (isinstance(v, str) and not v.strip()) or (isinstance(v, list) and len(v) == 0)
            if c.get("req") and v_vacio:
                errores.append(f"El campo '{c.get('l', k)}' ({k}) es obligatorio.")
            elif not v_vacio and (c.get("t") == "radicado" or k == "radicado"):
                solo_dig = re.sub(r"\D", "", str(v))
                if len(solo_dig) != 23:
                    errores.append(
                        f"El radicado judicial debe tener exactamente 23 dígitos (actualmente tiene {len(solo_dig)})."
                    )
    return errores


def _formatear_fecha_iso_legible(iso_str: str) -> str:
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", str(iso_str or "").strip())
    if not m:
        return str(iso_str or "").strip()
    ano, mes, dia = int(m.group(1)), int(m.group(2)), int(m.group(3))
    meses = ("enero", "febrero", "marzo", "abril", "mayo", "junio",
             "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre")
    if 1 <= mes <= 12:
        return f"{dia} de {meses[mes - 1]} de {ano}"
    return str(iso_str)


def valor_legible(c: dict[str, Any], v: Any) -> str:
    t = c.get("t")
    k = c.get("k", "")
    if t == "check":
        return "Sí" if v else "No"
    if t == "select":
        for o in c.get("opciones", []):
            if isinstance(o, (list, tuple)) and len(o) >= 2 and o[0] == v:
                return str(o[1])
        return str(v) if v is not None else ""
    if t == "chips":
        if isinstance(v, list):
            return ", ".join(str(x) for x in v)
        return str(v or "").strip()
    if t == "date" or t == "fecha" or k.endswith("_fecha"):
        return _formatear_fecha_iso_legible(v)
    if t == "radicado" or k == "radicado":
        digitos = re.sub(r"\D", "", str(v or ""))
        if len(digitos) == 23:
            return f"{digitos[0:5]}-{digitos[5:7]}-{digitos[7:9]}-{digitos[9:12]}-{digitos[12:16]}-{digitos[16:21]}-{digitos[21:23]}"
    return str(v or "").strip()


def instruccion_firma(tipo: dict[str, Any], abogado: dict[str, Any], datos: dict[str, Any]) -> str:
    ab = abogado or {}
    g = genero_ab(ab.get("genero", ""))
    nombre = ab.get("nombre") or "el abogado"
    rol_cliente = tipo.get("rolCliente") or ""
    modo = "poder" if tipo.get("firma") == "poder" else (datos.get("_firma") or "apoderado")

    if modo == "poder":
        return (
            f"El poder lo otorga {rol_cliente} y lo acepta {nombre}. Al final escribe el bloque de firma del "
            f"poderdante (una línea de guiones bajos, su nombre en mayúsculas y su documento; si es persona jurídica, "
            f"el nombre del representante legal y el NIT), luego «Acepto,» en su propio párrafo y, en una línea sola, "
            f"[[FIRMA: Apoderad{g}]]."
        )
    if modo == "cliente":
        return (
            f"El escrito lo firma directamente {rol_cliente} en nombre propio; el abogado solo lo redacta y no se "
            f"menciona en el documento. No uses [[FIRMA]]. Al final, después de la despedida, escribe el bloque de "
            f"firma del firmante: una línea de guiones bajos, su nombre en mayúsculas y su documento de identidad, "
            f"cada dato en su propia línea dentro del mismo párrafo."
        )
    if modo == "propio":
        return (
            f"{nombre} actúa en nombre propio. Preséntalo con su nombre, cédula y tarjeta profesional. "
            f"Termina con [[FIRMA]] en una línea sola."
        )

    rol_firma = tipo.get("rolFirma") or "de su cliente"
    ident = "o(a)" if g == "o(a)" else g
    firma_rol_sufijo = tipo.get("rolFirma") or ""
    return (
        f"El escrito lo presenta {nombre} como apoderad{g} {rol_firma}. En el párrafo de presentación "
        f"identifícal{ident} con su nombre, cédula y tarjeta profesional e indica que actúa según el poder "
        f"que se anexa (inclúyelo en los anexos). Al final, después de la fórmula de despedida, escribe en "
        f"una línea sola: [[FIRMA: Apoderad{g} {firma_rol_sufijo}]]."
    )


def lineas_estilo(estilo: dict[str, Any]) -> list[str]:
    e = estilo or {}
    L = []
    tratamiento = e.get("tratamiento", "auto")
    if tratamiento and tratamiento != "auto":
        L.append(f"Dirígete al despacho como «{tratamiento}».")
    if e.get("persona") == "primera":
        L.append("Escribe en primera persona («me permito», «solicito», «manifiesto»).")
    elif e.get("persona") == "tercera":
        L.append("Escribe en tercera persona («el suscrito apoderado», «la parte que represento»).")

    num_hechos = e.get("numHechos")
    if num_hechos == "ordinal":
        L.append("Numera los hechos con ordinales en mayúscula y negrilla: **PRIMERO.**, **SEGUNDO.**")
    elif num_hechos == "numero":
        L.append("Numera los hechos con números arábigos: 1., 2., 3.")
    elif num_hechos == "hecho":
        L.append("Numera los hechos así: **Hecho 1.**, **Hecho 2.**")

    num_pret = e.get("numPretensiones")
    if num_pret == "ordinal":
        L.append("Numera las pretensiones con ordinales femeninos en mayúscula y negrilla: **PRIMERA.**, **SEGUNDA.**")
    elif num_pret == "numero":
        L.append("Numera las pretensiones con números arábigos: 1., 2., 3.")

    tono = e.get("tono")
    if tono == "contundente":
        L.append("Tono firme y contundente, sin perder el respeto por el despacho ni por la contraparte.")
    elif tono == "sencillo":
        L.append("Lenguaje claro y sencillo, comprensible para el cliente, sin perder rigor.")
    elif tono == "sobrio":
        L.append("Tono sobrio, técnico y respetuoso.")
    else:
        L.append("Tono sobrio y técnico.")

    lenguaje = e.get("lenguaje")
    if lenguaje == "claro":
        L.append("Lenguaje claro y moderno: evita latinismos innecesarios, fórmulas arcaicas y oraciones demasiado largas.")
    elif lenguaje == "tradicional":
        L.append("Estilo forense tradicional colombiano, con sus fórmulas clásicas («respetuosamente me permito», «con todo respeto»).")

    fecha = e.get("fecha")
    if fecha == "arriba":
        L.append("Escribe el lugar y la fecha al inicio, antes del destinatario.")
    elif fecha == "final":
        L.append("Escribe el lugar y la fecha al final, antes de la firma.")
    elif fecha == "no":
        L.append("No escribas lugar ni fecha.")

    if e.get("esd", True):
        L.append("En los escritos dirigidos a un despacho judicial, cierra el destinatario con «E. S. D.».")
    else:
        L.append("No uses «E. S. D.» en el destinatario.")

    cierre = e.get("cierre")
    if cierre:
        L.append(f"Fórmula de despedida antes de la firma: «{cierre}».")
    return L


def construir_prompt(
    tipo_id_o_meta: Any,
    datos: dict[str, Any],
    perfil: Optional[dict[str, Any]] = None,
    fecha_ref: Optional[datetime.date] = None,
) -> str:
    """Construye el prompt exacto para Claude o Gemini en el servidor."""
    if isinstance(tipo_id_o_meta, str):
        tipo = obtener_tipo(tipo_id_o_meta)
        if not tipo:
            raise ValueError(f"Tipo desconocido: {tipo_id_o_meta}")
    else:
        tipo = tipo_id_o_meta

    p = perfil or {}
    ab = p.get("abogado") or {}
    estilo = p.get("estilo") or {}
    ia = p.get("ia") or {}
    d = datos or {}

    L = []
    L.append("Eres un abogado litigante colombiano con amplia experiencia. Redactas escritos jurídicos impecables, listos para radicar. Redacta completo el documento descrito abajo.")
    L.append("")
    hoy_str = fecha_larga(fecha_ref)
    L.append(f"FECHA DE HOY: {hoy_str}. Úsala si el escrito lleva fecha.")
    tipo_libre_str = f" ({d['tipo_libre']})" if d.get("tipo_libre") else ""
    L.append(f"DOCUMENTO: {tipo.get('nombre', '')}{tipo_libre_str}")
    L.append("")
    L.append("CONTEXTO NORMATIVO VIGENTE (octubre de 2026; prevalece sobre lo que recuerdes):")
    smmlv_val = ia.get("smmlv", 1750905)
    for x in cargar_contexto_normativo(smmlv=smmlv_val):
        L.append("- " + x)
    L.append("")
    L.append("GUÍA JURÍDICA Y ESTRUCTURA PARA ESTE ESCRITO:")
    L.append(tipo.get("guia", ""))
    L.append("")
    L.append("ABOGADO(A) QUE REDACTA:")
    if ab.get("nombre"):
        genero = ab.get("genero")
        if genero == "f":
            g_desc = "abogada; trátala en femenino: la suscrita, apoderada"
        elif genero == "m":
            g_desc = "abogado; trátalo en masculino: el suscrito, apoderado"
        else:
            g_desc = "usa la forma «apoderado(a)» si necesitas nombrarlo"
        L.append(f"- Nombre: {ab['nombre']} ({g_desc})")

        cedula_lugar = ab.get("cedulaLugar")
        ced_str = f"{ab['cedula']}{' de ' + cedula_lugar if cedula_lugar else ''}" if ab.get("cedula") else "[COMPLETAR]"
        L.append(f"- Cédula: {ced_str}")

        tp = ab.get("tp")
        L.append(f"- Tarjeta profesional: {tp + ' del Consejo Superior de la Judicatura' if tp else '[COMPLETAR]'}")
        if ab.get("correo"):
            L.append(f"- Correo de notificaciones (inscrito en el Registro Nacional de Abogados): {ab['correo']}")
        if ab.get("telefono"):
            L.append(f"- Teléfono: {ab['telefono']}")
        if ab.get("direccion"):
            ciudad_str = f", {ab['ciudad']}" if ab.get("ciudad") else ""
            L.append(f"- Dirección: {ab['direccion']}{ciudad_str}")
    else:
        L.append("- Sus datos no están configurados: donde debas mencionarlos escribe [COMPLETAR: nombre del abogado], [COMPLETAR: cédula] y [COMPLETAR: tarjeta profesional].")

    L.append("")
    L.append("QUIÉN FIRMA:")
    L.append(instruccion_firma(tipo, ab, d))
    L.append("")
    L.append("ESTILO DEL ABOGADO (síguelo):")
    for x in lineas_estilo(estilo):
        L.append("- " + x)

    ficha = (estilo.get("ficha") or "").strip()
    if ficha:
        L.append("")
        L.append("FICHA DE ESTILO DEL ABOGADO (prevalecen las preferencias anteriores si chocan):")
        L.append(ficha[:4000])

    muestra = (estilo.get("muestra") or "").strip()
    if muestra:
        L.append("")
        L.append("MUESTRA DE UN ESCRITO DEL ABOGADO. Imita su voz, sus fórmulas, el orden de sus capítulos y su nivel de formalidad. No copies sus hechos, nombres ni datos:")
        L.append("<<<")
        L.append(muestra[:9000])
        L.append(">>>")

    L.append("")
    L.append("DATOS DEL CASO (los escribió el abogado; pueden estar en borrador o con errores de digitación: corrígelos al redactar sin cambiar su sentido):")
    for c in campos_tipo(tipo):
        k = c.get("k", "")
        if k.startswith("_") and k != "_notas":
            continue
        v = d.get(k)
        if v is None or v == "" or (isinstance(v, list) and not v):
            continue
        if c.get("t") == "check" and k == "juramento":
            L.append(f"### {c.get('l', '')}")
            L.append("Sí, inclúyelo." if v else "No lo incluyas.")
            continue
        etiqueta = "Indicaciones adicionales del abogado" if k == "_notas" else c.get("l", "")
        L.append(f"### {etiqueta}")
        L.append(valor_legible(c, v))

    L.append("")
    ext = d.get("_extension") or estilo.get("extension") or "estandar"
    juris = d.get("_juris") or "sugerir"
    n_sent = 2 if ext == "concisa" else 6 if ext == "extensa" else 4

    L.append("REGLAS OBLIGATORIAS:")
    L.append("1. Usa únicamente los hechos, nombres, cifras, fechas y documentos que aparecen en los datos del caso. No inventes nada. Si falta un dato necesario, escribe en su lugar [COMPLETAR: descripción breve del dato].")
    L.append("2. Puedes ordenar, depurar y redactar con lenguaje jurídico los hechos y las pretensiones, sin alterar su sentido ni agregar hechos nuevos.")
    L.append("3. Cita solo normas colombianas que existan y estén vigentes. Si dudas del número de un artículo o de su vigencia, escribe [VERIFICAR] inmediatamente después de la cita.")
    if juris == "verificables":
        L.append(f"4. Jurisprudencia: además de la que indique el abogado, puedes citar hasta {n_sent} pronunciamientos de la Corte Constitucional, la Corte Suprema de Justicia o el Consejo de Estado que conozcas con certeza y que sean pertinentes; el sistema verificará automáticamente su existencia en relatoría oficial. Nunca inventes números de sentencia, radicados, fechas ni magistrados ponentes.")
    elif juris == "sugerir":
        L.append(f"4. Jurisprudencia: además de la que indique el abogado, puedes citar hasta {n_sent} pronunciamientos de la Corte Constitucional, la Corte Suprema de Justicia o el Consejo de Estado que conozcas con certeza y que sean pertinentes; prefiere sentencias de unificación y precedentes muy reconocidos. Escribe [VERIFICAR] inmediatamente después de cada sentencia que cites y que no haya suministrado el abogado. Nunca inventes números de sentencia, radicados, fechas ni magistrados ponentes.")
    elif juris == "usuario":
        L.append("4. Jurisprudencia: cita únicamente la que indicó el abogado en los datos del caso; no agregues otras sentencias.")
    else:
        L.append("4. Jurisprudencia: no cites sentencias. Funda el escrito en la Constitución, la ley y los hechos.")

    L.append("5. Nunca pongas entre comillas un texto atribuido a una sentencia, a una norma o a un autor, salvo que el abogado lo haya suministrado textualmente o estés seguro de su texto exacto; en caso contrario, parafrasea.")
    L.append("6. No escribas el membrete ni el encabezado o pie de página con los datos de contacto del abogado: se agregan automáticamente. Sí escribe el destinatario y la referencia.")

    desc_extension = {
        "concisa": "concisa y directa, solo lo esencial de cada capítulo.",
        "estandar": "completa pero sin relleno ni repeticiones.",
        "extensa": "exhaustiva: desarrolla a fondo cada argumento."
    }.get(ext, "completa pero sin relleno.")
    L.append(f"7. Extensión: {desc_extension}")
    L.append("8. Escribe solo el documento: sin comentarios, notas, advertencias ni explicaciones antes o después.")
    L.append("")
    L.append(cargar_formato_salida())

    return "\n".join(L)
