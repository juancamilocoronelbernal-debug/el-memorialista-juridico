"""El Memorialista · Módulo de Preparación de Radicación Judicial (v1.0).

Implementa la preparación integral de paquetes de radicación procesal conforme a:
- Ley 2213 de 2022 (art. 6: traslado simultáneo de demanda y excepciones por medidas cautelares previas; art. 8: canal digital).
- Código General del Proceso - Ley 1564 de 2012 (art. 74 y 77: poder especial judicial y facultades; art. 82: requisitos de demanda).
- Protocolos de Gestión Documental y Radicación Electrónica de la Rama Judicial de Colombia (CSJ).
- Generación de índice numerado de pruebas y anexos.
- Borradores de correos para radicación (despacho) y traslado simultáneo (contraparte) con enlaces mailto:.
"""
from __future__ import annotations

import re
import urllib.parse
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

# Palabras clave y expresiones que denotan solicitud de medidas cautelares previas
PATRONES_MEDIDAS_CAUTELARES = [
    r"medida[s]?\s+cautelar(?:es)?",
    r"embargo",
    r"secuestro\s+de\s+bienes",
    r"inscripci[oó]n\s+de\s+la\s+demanda",
    r"medida[s]?\s+innominada[s]?",
    r"cautela[s]?",
    r"decreto\s+de\s+embargo",
]


class AnexoIndiceItem(BaseModel):
    numero: int
    nombre_archivo: str
    descripcion: str
    tipo_documento: str = "Documental"
    folios_estimados: str = "1"


class PrepararRadicacionRequest(BaseModel):
    tipo: str = Field(description="Identificador del tipo de escrito (ej. demanda_verbal, tutela)")
    datos: Dict[str, Any] = Field(default_factory=dict, description="Datos del formulario del caso")
    texto: str = Field(description="Texto final del escrito redactado")
    perfil: Optional[Dict[str, Any]] = Field(default=None, description="Perfil del abogado y membrete")


class PrepararRadicacionResponse(BaseModel):
    nombre_paquete: str
    nombre_archivo_principal: str
    requiere_poder: bool
    texto_poder: Optional[str] = None
    nombre_archivo_poder: Optional[str] = None
    solicita_medidas_cautelares: bool
    aplica_traslado_contraparte: bool
    motivo_traslado_contraparte: str
    correo_despacho: str
    asunto_despacho: str
    cuerpo_despacho: str
    mailto_despacho: str
    correo_contraparte: Optional[str] = None
    asunto_contraparte: Optional[str] = None
    cuerpo_contraparte: Optional[str] = None
    mailto_contraparte: Optional[str] = None
    indice_anexos: List[AnexoIndiceItem]
    texto_indice: str


def limpiar_texto(valor: Any) -> str:
    """Limpia saltos de línea y espacios redundantes."""
    return str(valor or "").strip().replace("\r", "")


def extraer_correo(texto_o_campo: str) -> Optional[str]:
    """Extrae la primera dirección de correo electrónico válida de una cadena."""
    if not texto_o_campo:
        return None
    match = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", str(texto_o_campo))
    return match.group(0) if match else None


def detectar_medidas_cautelares(texto: str, datos: Dict[str, Any]) -> bool:
    """
    Detecta si en la demanda o memorial se solicitaron medidas cautelares previas,
    lo que exonera del traslado simultáneo a la contraparte conforme al art. 6 de la Ley 2213 de 2022.
    """
    texto_completo = (
        texto + " " + " ".join(str(v) for v in datos.values() if isinstance(v, (str, int, float)))
    ).lower()

    for patron in PATRONES_MEDIDAS_CAUTELARES:
        if re.search(patron, texto_completo, re.IGNORECASE):
            return True
    return False


def tipo_requiere_poder(tipo: str, datos: Dict[str, Any], perfil: Optional[Dict[str, Any]]) -> bool:
    """
    Determina si el escrito requiere anexar poder especial judicial:
    - No requiere si el escrito en sí es un poder ('poder_especial').
    - No requiere si la firma es expresamente en nombre propio ('propio').
    - Requiere si el abogado actúa como apoderado en demandas, tutelas, recursos o memoriales.
    """
    if tipo in ("poder_especial", "poder"):
        return False
    quien_firma = datos.get("_firma", "apoderado")
    if quien_firma == "propio":
        return False
    return True


def generar_texto_poder_especial(
    tipo: str, datos: Dict[str, Any], perfil: Optional[Dict[str, Any]]
) -> str:
    """
    Genera el texto legal de un Poder Especial Judicial conforme al art. 74 y 77 del CGP
    y al art. 5 de la Ley 2213 de 2022 (presentación y envío por canal digital).
    """
    abogado = (perfil or {}).get("abogado", {})
    nom_abogado = abogado.get("nombre") or "[COMPLETAR: Nombre del Abogado]"
    cc_abogado = abogado.get("cedula") or "[COMPLETAR: C.C. Abogado]"
    lugar_cc_abogado = abogado.get("cedulaLugar") or ""
    tp_abogado = abogado.get("tp") or "[COMPLETAR: T.P. Abogado]"
    correo_abogado = abogado.get("correo") or "[COMPLETAR: Correo Abogado]"

    cliente = limpiar_texto(datos.get("cliente") or "El (La) Poderdante")
    nom_cliente = cliente.split("\n")[0].split(",")[0].strip()
    contraparte = limpiar_texto(datos.get("contraparte") or "La Contraparte")
    nom_contraparte = contraparte.split("\n")[0].split(",")[0].strip()
    despacho = limpiar_texto(datos.get("destinatario") or "JUEZ O DESPACHO JUDICIAL COMPETENTE")
    ciudad = limpiar_texto(datos.get("ciudad") or abogado.get("ciudad") or "Bogotá D.C.")
    radicado = limpiar_texto(datos.get("radicado") or "")

    ref_radicado = f"\n| **Radicado:** {radicado}" if radicado else ""

    texto = f"""Señor(a)
{despacho}
E. S. D.

| **Referencia:** Poder Especial, Amplio y Suficiente
| **Poderdante:** {nom_cliente}
| **Apoderado(a):** {nom_abogado}
| **Contraparte:** {nom_contraparte}{ref_radicado}
| **Asunto:** Otorgamiento de poder judicial (Art. 74 CGP y Ley 2213 de 2022)

**{nom_cliente}**, mayor de edad, domiciliado(a) en {ciudad}, actuando en nombre propio (o en representación de quien corresponda según la calidad informada), por medio del presente escrito manifiesto que confiero **PODER ESPECIAL, AMPLIO Y SUFICIENTE** al(a la) doctor(a) **{nom_abogado}**, mayor de edad, identificado(a) con la Cédula de Ciudadanía No. {cc_abogado} {f'de {lugar_cc_abogado}' if lugar_cc_abogado else ''}, abogado(a) en ejercicio con Tarjeta Profesional No. {tp_abogado} del Consejo Superior de la Judicatura, con dirección electrónica para notificaciones judiciales en {correo_abogado}, para que en mi nombre y representación inicie, tramite y lleve hasta su total culminación procesal la acción judicial de la referencia contra **{nom_contraparte}**.

## Facultades Conferidas

El(la) apoderado(a) queda expresamente facultado(a) para ejercer todas las atribuciones inherentes al mandato judicial previstas en el artículo 77 del Código General del Proceso (CGP), especialmente para:
1. Presentar demanda, memoriales, recursos ordinarios y extraordinarios, solicitudes y alegatos.
2. Recibir notificaciones judiciales y administrativas.
3. Desistir, transigir, conciliar judicial y extrajudicialmente.
4. Solicitar, controvertir, aportar y tachar pruebas.
5. Solicitar medidas cautelares y formular incidentes.
6. Sustituir o reasumir el presente mandato judicial cuando lo estime conveniente.
7. Cobrar y recibir las sumas de dinero que se reconozcan a mi favor en el proceso.

## Mensaje de Datos y Validez (Ley 2213 de 2022)

El presente poder se otorga y remite mediante mensaje de datos desde la dirección electrónica del(de la) poderdante conforme al artículo 5 de la Ley 2213 de 2022, sin que se requiera presentación personal ni reconocimiento de firma ante notaría.

Del señor Juez o funcionario, respetuosamente,

[[FIRMA: Poderdante]]
**{nom_cliente}**

Acepto el poder conferido:

[[FIRMA: Apoderado(a)]]
**{nom_abogado}**
C.C. {cc_abogado}
T.P. {tp_abogado} del C. S. de la J.
Correo electrónico: {correo_abogado}
"""
    return texto.strip()


def extraer_capitulo_pruebas_y_anexos(texto: str) -> List[str]:
    """
    Extrae los ítems listados en el capítulo de Pruebas o Anexos del escrito redactado.
    """
    items: List[str] = []
    # Buscar secciones de pruebas o anexos
    patron_seccion = re.compile(
        r"(?:##\s*(?:Pruebas|Anexos|Documentos|Relación de Pruebas|Material Probatorio)[\s\S]*?)(?=(?:##|\Z))",
        re.IGNORECASE,
    )
    coincidencias = patron_seccion.findall(texto)
    for bloque in coincidencias:
        # Extraer líneas con numeración o viñetas
        lineas = bloque.split("\n")
        for linea in lineas:
            linea_limpia = linea.strip()
            # Numerales: 1. Documento... o - Documento...
            m = re.match(r"^(?:\d+[\.\)]|\-|\*)\s+(.*)$", linea_limpia)
            if m:
                desc = m.group(1).strip()
                if desc and not desc.lower().startswith("se solicita") and not desc.lower().startswith("pruebas"):
                    items.append(desc)

    return items


def construir_indice_anexos(
    tipo: str,
    datos: Dict[str, Any],
    texto: str,
    requiere_poder: bool,
    nombre_archivo_principal: str,
    nombre_archivo_poder: Optional[str],
) -> List[AnexoIndiceItem]:
    """
    Construye la lista estructurada y numerada de anexos que conformarán el paquete de radicación.
    """
    anexos: List[AnexoIndiceItem] = []
    num = 1

    # 1. Escrito Principal
    anexos.append(
        AnexoIndiceItem(
            numero=num,
            nombre_archivo=nombre_archivo_principal,
            descripcion="Escrito principal de la acción judicial o memorial",
            tipo_documento="Principal",
            folios_estimados="Principal",
        )
    )
    num += 1

    # 2. Poder Especial Judicial (si aplica)
    if requiere_poder and nombre_archivo_poder:
        anexos.append(
            AnexoIndiceItem(
                numero=num,
                nombre_archivo=nombre_archivo_poder,
                descripcion="Poder especial amplio y suficiente conferido al apoderado judicial (art. 74 CGP y Ley 2213/2022)",
                tipo_documento="Poder",
                folios_estimados="1",
            )
        )
        num += 1

    # 3. Anexos y pruebas extraídos del escrito
    pruebas_detectadas = extraer_capitulo_pruebas_y_anexos(texto)
    if pruebas_detectadas:
        for idx, p in enumerate(pruebas_detectadas, start=1):
            # Normalizar nombre seguro de archivo
            desc_corta = re.sub(r"[^\w\s-]", "", p)[:30].strip().replace(" ", "_")
            nombre_anexo = f"{num:02d}_Anexo_{idx}_{desc_corta}.pdf"
            anexos.append(
                AnexoIndiceItem(
                    numero=num,
                    nombre_archivo=nombre_anexo,
                    descripcion=p,
                    tipo_documento="Prueba Documental",
                    folios_estimados="Por foliar",
                )
            )
            num += 1
    else:
        # Anexos estándar si no se discriminaron en el texto
        anexos.append(
            AnexoIndiceItem(
                numero=num,
                nombre_archivo=f"{num:02d}_Documentos_Identificacion_y_Soporte.pdf",
                descripcion="Documentos de identificación de las partes y soportes del litigio",
                tipo_documento="Prueba Documental",
                folios_estimados="Por foliar",
            )
        )
        num += 1

    return anexos


def formatear_texto_indice(
    tipo: str,
    datos: Dict[str, Any],
    anexos: List[AnexoIndiceItem],
    perfil: Optional[Dict[str, Any]],
) -> str:
    """Genera el texto del Índice de Anexos y Archivos Electrónicos conforme al protocolo CSJ."""
    abogado = (perfil or {}).get("abogado", {})
    nom_abogado = abogado.get("nombre") or "Apoderado Judicial"
    tp_abogado = abogado.get("tp") or ""
    correo_abogado = abogado.get("correo") or ""

    cliente = limpiar_texto(datos.get("cliente") or "Demandante")
    nom_cliente = cliente.split("\n")[0].split(",")[0].strip()
    contraparte = limpiar_texto(datos.get("contraparte") or "Demandado")
    nom_contraparte = contraparte.split("\n")[0].split(",")[0].strip()
    despacho = limpiar_texto(datos.get("destinatario") or "Despacho Judicial")
    radicado = limpiar_texto(datos.get("radicado") or "Para Reparto")

    sep = "=" * 80
    sep_sub = "-" * 80

    lineas = [
        sep,
        "ÍNDICE DE EXPEDIENTE ELECTRÓNICO Y RELACIÓN DE ANEXOS RADICADOS",
        "(Protocolo de Gestión de Documentos Electrónicos - Consejo Superior de la Judicatura)",
        sep,
        f"Proceso / Tipo: {tipo.replace('_', ' ').capitalize()}",
        f"Despacho:       {despacho}",
        f"Radicado:       {radicado}",
        f"Demandante:     {nom_cliente}",
        f"Demandado:      {nom_contraparte}",
        f"Apoderado(a):   {nom_abogado} {f'(T.P. {tp_abogado})' if tp_abogado else ''}",
        f"Canal Digital:  {correo_abogado}",
        sep_sub,
        f"{'NO.':<4} {'NOMBRE DEL ARCHIVO':<38} {'TIPO':<18} {'DESCRIPCIÓN':<20}",
        sep_sub,
    ]

    for a in anexos:
        nombre_trunc = a.nombre_archivo[:36]
        desc_trunc = a.descripcion[:30]
        lineas.append(f"{a.numero:<4} {nombre_trunc:<38} {a.tipo_documento:<18} {desc_trunc}")

    lineas.extend([
        sep_sub,
        f"Total de archivos integrantes del paquete: {len(anexos)} documento(s)",
        "",
        "CERTIFICACIÓN DEL CANAL DIGITAL Y REMISIÓN (Artículos 6 y 8 Ley 2213 de 2022):",
        "Se certifica que los archivos relacionados corresponden fielmente a los documentos adjuntos",
        "al mensaje de datos remitido para la radicación electrónica ante la autoridad judicial.",
        sep,
    ])

    return "\n".join(lineas)


def preparar_radicacion(req: PrepararRadicacionRequest) -> PrepararRadicacionResponse:
    """
    Construye el paquete completo de radicación, incluyendo nombres, poder, índice y correos mailto:.
    """
    tipo = req.tipo
    datos = req.datos or {}
    texto = req.texto or ""
    perfil = req.perfil or {}
    abogado = perfil.get("abogado", {})

    cliente = limpiar_texto(datos.get("cliente") or "Demandante")
    nom_cliente = cliente.split("\n")[0].split(",")[0].strip()
    nom_cliente_safe = re.sub(r"[^\w\s-]", "", nom_cliente)[:25].strip().replace(" ", "_")

    contraparte = limpiar_texto(datos.get("contraparte") or "Contraparte")
    nom_contraparte = contraparte.split("\n")[0].split(",")[0].strip()
    nom_contraparte_safe = re.sub(r"[^\w\s-]", "", nom_contraparte)[:25].strip().replace(" ", "_")

    radicado = limpiar_texto(datos.get("radicado") or "")
    despacho = limpiar_texto(datos.get("destinatario") or "Despacho Judicial")
    ciudad = limpiar_texto(datos.get("ciudad") or abogado.get("ciudad") or "Bogotá D.C.")

    # 1. Nombres estandarizados de archivos
    tipo_desc = tipo.replace("_", " ").title().replace(" ", "_")
    prefijo_radicado = f"Rad_{radicado}_" if radicado else ""
    nombre_base = f"{prefijo_radicado}{tipo_desc}_{nom_cliente_safe}_vs_{nom_contraparte_safe}"
    nombre_paquete = f"Paquete_Radicacion_{nombre_base}.zip"
    nombre_archivo_principal = f"01_{tipo_desc}_{nom_cliente_safe}.pdf"

    # 2. Poder especial judicial
    requiere_poder = tipo_requiere_poder(tipo, datos, perfil)
    texto_poder = None
    nombre_archivo_poder = None
    if requiere_poder:
        nombre_archivo_poder = f"02_Poder_Especial_Judicial_{nom_cliente_safe}.pdf"
        texto_poder = generar_texto_poder_especial(tipo, datos, perfil)

    # 3. Índice de anexos
    anexos = construir_indice_anexos(
        tipo=tipo,
        datos=datos,
        texto=texto,
        requiere_poder=requiere_poder,
        nombre_archivo_principal=nombre_archivo_principal,
        nombre_archivo_poder=nombre_archivo_poder,
    )
    texto_indice = formatear_texto_indice(tipo, datos, anexos, perfil)

    # 4. Análisis de medidas cautelares y traslado simultáneo (Art. 6 Ley 2213 de 2022)
    solicita_cautelares = detectar_medidas_cautelares(texto, datos)

    # Correos de contacto
    correo_despacho_detectado = (
        extraer_correo(datos.get("correo_despacho") or datos.get("correo_destinatario") or despacho)
        or "radicacion@ramajudicial.gov.co"
    )

    correo_contraparte_detectado = (
        extraer_correo(datos.get("correo_contraparte") or datos.get("notificaciones_contraparte") or contraparte)
    )

    es_tutela = (tipo == "tutela" or "tutela" in tipo)
    es_peticion = (tipo == "derecho_peticion" or "peticion" in tipo)

    aplica_traslado = False
    motivo_traslado = ""

    if es_tutela:
        aplica_traslado = False
        motivo_traslado = "No aplica traslado previo: en acción de tutela el traslado y vinculación son ordenados de oficio por el Juez en el auto admisorio (Decreto 2591 de 1991)."
    elif es_peticion:
        aplica_traslado = False
        motivo_traslado = "No aplica traslado judicial: es un derecho de petición directo a la entidad o particular (Ley 1755 de 2015)."
    elif solicita_cautelares:
        aplica_traslado = False
        motivo_traslado = "Exonerado de traslado previo (Art. 6 Inc. 4 Ley 2213 de 2022): se solicitaron medidas cautelares previas que perderían efectividad si se entera al demandado."
    elif not correo_contraparte_detectado:
        aplica_traslado = False
        motivo_traslado = "Exonerado de traslado previo (Art. 6 Inc. 4 Ley 2213 de 2022): se desconoce el canal digital / correo electrónico de la contraparte demandada."
    else:
        aplica_traslado = True
        motivo_traslado = "Aplica traslado simultáneo obligatorio (Art. 6 Ley 2213 de 2022): demanda sin medidas cautelares previas con canal digital del demandado identificado."

    # 5. Borrador y mailto para radicación al Despacho Judicial
    nom_tipo_formal = tipo.replace("_", " ").title()
    if radicado:
        asunto_despacho = f"Memorial: {nom_tipo_formal} - Rad. {radicado} - {nom_cliente} vs {nom_contraparte}"
    else:
        asunto_despacho = f"Demanda para Reparto: {nom_tipo_formal} - {nom_cliente} vs {nom_contraparte} - {ciudad}"

    lista_adjuntos_txt = "\n".join([f"  {a.numero}. {a.nombre_archivo} ({a.descripcion})" for a in anexos])

    nom_abogado = abogado.get("nombre") or "Apoderado Judicial"
    cc_abogado = abogado.get("cedula") or ""
    tp_abogado = abogado.get("tp") or ""
    tel_abogado = abogado.get("telefono") or ""
    dir_abogado = abogado.get("direccion") or ""
    correo_abogado = abogado.get("correo") or ""

    cuerpo_despacho = f"""Señores
{despacho}
E. S. D.

REF: {asunto_despacho}

Respetados señores:

En calidad de apoderado(a) judicial de {nom_cliente}, por medio de la presente radico formalmente el escrito de {nom_tipo_formal} de la referencia para el trámite judicial correspondiente.

ARCHIVOS ADJUNTOS AL MENSAJE DE DATOS (PAQUETE DE RADICACIÓN):
{lista_adjuntos_txt}

Se deja constancia de que los documentos se remiten en formato electrónico accesible y foliado conforme a las directrices de la Ley 2213 de 2022 y del Consejo Superior de la Judicatura.

CANAL DIGITAL PARA NOTIFICACIONES JUDICIALES (Art. 8 Ley 2213 de 2022):
- Apoderado(a): {nom_abogado}
- C.C.: {cc_abogado} | T.P.: {tp_abogado}
- Correo Electrónico: {correo_abogado}
- Teléfono / Móvil: {tel_abogado}
- Dirección: {dir_abogado} - {ciudad}

Agradezco confirmar el recibo, número de radicación y despacho asignado.

Cordialmente,

{nom_abogado}
T.P. No. {tp_abogado} del C. S. de la J.
"""

    mailto_despacho = (
        f"mailto:{correo_despacho_detectado}"
        f"?subject={urllib.parse.quote(asunto_despacho)}"
        f"&body={urllib.parse.quote(cuerpo_despacho)}"
    )

    # 6. Borrador y mailto para traslado simultáneo a la contraparte (si aplica)
    asunto_contraparte = None
    cuerpo_contraparte = None
    mailto_contraparte = None

    if aplica_traslado and correo_contraparte_detectado:
        asunto_contraparte = (
            f"Traslado Simultáneo de Demanda: {nom_tipo_formal} - {nom_cliente} vs {nom_contraparte} (Art. 6 Ley 2213 de 2022)"
        )
        cuerpo_contraparte = f"""Señores
{nom_contraparte}
Atn. Notificaciones Judiciales

REF: Traslado simultáneo de demanda judicial (Artículo 6 de la Ley 2213 de 2022)
Demandante: {nom_cliente}
Demandado:  {nom_contraparte}
Despacho:   {despacho}

Por medio de la presente, en cumplimiento expreso del artículo 6 de la Ley 2213 de 2022, me permito remitirles de manera simultánea a la radicación ante la autoridad judicial, copia íntegra de la demanda de la referencia y de la totalidad de sus anexos y pruebas documentales.

DOCUMENTOS TRASLADADOS ADJUNTOS:
{lista_adjuntos_txt}

CANAL DIGITAL DEL DEMANDANTE (Art. 8 Ley 2213 de 2022):
- Apoderado(a): {nom_abogado} (T.P. {tp_abogado})
- Correo Electrónico: {correo_abogado}
- Teléfono: {tel_abogado}

La presente comunicación constituye traslado simultáneo formal con plenos efectos legales y probatorios ante el despacho judicial de conocimiento.

Atentamente,

{nom_abogado}
Apoderado(a) Judicial de la parte demandante
"""
        mailto_contraparte = (
            f"mailto:{correo_contraparte_detectado}"
            f"?subject={urllib.parse.quote(asunto_contraparte)}"
            f"&body={urllib.parse.quote(cuerpo_contraparte)}"
        )

    return PrepararRadicacionResponse(
        nombre_paquete=nombre_paquete,
        nombre_archivo_principal=nombre_archivo_principal,
        requiere_poder=requiere_poder,
        texto_poder=texto_poder,
        nombre_archivo_poder=nombre_archivo_poder,
        solicita_medidas_cautelares=solicita_cautelares,
        aplica_traslado_contraparte=aplica_traslado,
        motivo_traslado_contraparte=motivo_traslado,
        correo_despacho=correo_despacho_detectado,
        asunto_despacho=asunto_despacho,
        cuerpo_despacho=cuerpo_despacho,
        mailto_despacho=mailto_despacho,
        correo_contraparte=correo_contraparte_detectado,
        asunto_contraparte=asunto_contraparte,
        cuerpo_contraparte=cuerpo_contraparte,
        mailto_contraparte=mailto_contraparte,
        indice_anexos=anexos,
        texto_indice=texto_indice,
    )
