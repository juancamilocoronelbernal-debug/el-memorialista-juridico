"""Lectura pública del catálogo ciudadano, sin datos de sesión ni del generador.

El JSON se reconstruye con scripts/build_asesor_paginas.cjs cuando cambia el
catálogo. Las URLs absolutas solo proceden de APP_BASE_URL; nunca de Host.
"""
from __future__ import annotations

from functools import lru_cache
from html import escape
import ipaddress
import json
from pathlib import Path
import re
from urllib.parse import urlsplit
from xml.sax.saxutils import escape as xml_escape

from app.config import get_settings


CATALOGO_PATH = Path(__file__).resolve().parents[1] / "data" / "asesor_paginas.json"
MARCA = "El Memorialista"
TUTELA_OFICIAL = "https://procesojudicial.ramajudicial.gov.co/TutelaEnLinea"
GUIAS = {
    "plantilla-tutela": {
        "titulo": "Plantillas de tutela: elige el modelo para tu situación",
        "descripcion": "Consulta los modelos de tutela, prepara tus datos y revisa el borrador antes de descargarlo y presentarlo.",
        "intro": "El asesor ofrece modelos por situación. Puedes leer qué información pide cada uno antes de abrir el formulario. La selección de un modelo no determina por sí sola que la tutela proceda.",
        "casos": "tutela",
    },
    "tutela-eps": {
        "titulo": "Tutela a la EPS: prepara la información de tu caso",
        "descripcion": "Organiza órdenes médicas, solicitudes, respuestas y fechas. Consulta los modelos de salud y los pasos para revisar tu borrador.",
        "intro": "Empieza por identificar el servicio solicitado, la entidad involucrada y lo que ocurrió. La guía de cada modelo distingue la solicitud a la EPS de la preparación de una tutela.",
        "casos": ["tut_salud_servicio", "tut_salud_integral", "pet_eps_servicio", "queja_supersalud"],
    },
    "ejemplo-derecho-de-peticion": {
        "titulo": "Derecho de petición: estructura y modelos para preparar tu solicitud",
        "descripcion": "Consulta un esquema de petición y elige un modelo según la entidad y tu situación. Revisa hechos, solicitudes y soportes antes de enviarlo.",
        "intro": "Una petición clara identifica a quién se dirige, explica lo que ocurrió y concreta lo que se solicita. El formulario adapta la redacción a las respuestas que aportes.",
        "casos": ["pet_general", "pet_eps_servicio", "pet_municipio_servicios", "pet_empleador", "pet_info_publica", "pet_copias"],
    },
    "accion-de-tutela": {
        "titulo": "Acción de tutela: cómo organizar y revisar el borrador",
        "descripcion": "Prepara los hechos, las solicitudes y los soportes de una tutela. Consulta modelos y el canal oficial de presentación.",
        "intro": "El modelo general organiza los datos de la persona afectada, los hechos, los derechos que se señalan y lo que se pide al juez. Conviene escoger un modelo específico cuando corresponda a la situación.",
        "casos": ["tut_general", "tut_peticion", "tut_salud_servicio", "impugnacion", "desacato"],
    },
}


@lru_cache(maxsize=1)
def catalogo_publico() -> dict:
    data = json.loads(CATALOGO_PATH.read_text(encoding="utf-8"))
    if data.get("version") != 1:
        raise ValueError("Versión no admitida del catálogo público.")
    ids, slugs = set(), set()
    for caso in data["casos"]:
        if not re.fullmatch(r"[a-z0-9_]+", caso["id"]) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", caso["slug"]):
            raise ValueError("Identificador no válido en el catálogo público.")
        if caso["id"] in ids or caso["slug"] in slugs:
            raise ValueError("Identificador duplicado en el catálogo público.")
        ids.add(caso["id"])
        slugs.add(caso["slug"])
    return data


def origen_publico() -> str:
    """Origen configurado, validado incluso si Settings acepta una cadena libre."""
    value = getattr(get_settings(), "APP_BASE_URL", "")
    if not isinstance(value, str) or not value or re.search(r"[\s\x00-\x1f\x7f\\]", value):
        return ""
    try:
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or parsed.username is not None or parsed.password is not None:
            return ""
        if parsed.path not in {"", "/"} or parsed.query or parsed.fragment or not parsed.hostname:
            return ""
        port = parsed.port  # Rechaza puertos fuera de rango o no numéricos.
        hostname = parsed.hostname.lower()
        if ":" in hostname:
            ipaddress.IPv6Address(hostname)
            host = f"[{hostname}]"
        else:
            if len(hostname) > 253 or not all(re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label) for label in hostname.split(".")):
                return ""
            host = hostname
        if port is not None:
            host += f":{port}"
        return f"{parsed.scheme}://{host}"
    except (ValueError, UnicodeError):
        return ""


def ruta_caso(caso: dict) -> str:
    return f"/plantillas/{caso['slug']}/"


def enlace_formulario(caso: dict) -> str:
    return f"/#caso/{caso['id']}"


def rutas_publicas() -> list[str]:
    return ["/", "/plantillas/", *(f"/{slug}/" for slug in GUIAS), *(ruta_caso(caso) for caso in catalogo_publico()["casos"])]


def _json_ld(data: dict) -> str:
    # Escapar el delimitador de script aunque en el futuro el catálogo incluya
    # texto aportado por otra fuente. HTML escaping rompería el JSON.
    return json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")


def metadatos_publicos(titulo: str, descripcion: str, ruta: str, tipo: str = "WebPage", elementos: list[dict] | None = None) -> str:
    """Canonical, Open Graph y JSON-LD para páginas públicas (también la portada).

    Sin APP_BASE_URL válido se omiten URLs absolutas; no se adivina el dominio.
    El llamador debe pasar una ruta conocida, no la URL del request.
    """
    if ruta not in rutas_publicas():
        raise ValueError("La ruta no pertenece al contenido público.")
    origen = origen_publico()
    canonical = origen + ruta if origen else ""
    data = {"@context": "https://schema.org", "@type": tipo, "name": titulo,
            "description": descripcion, "inLanguage": "es-CO",
            "isPartOf": {"@type": "WebSite", "name": MARCA}}
    tags = [f'<meta property="og:title" content="{escape(titulo, quote=True)}">',
            f'<meta property="og:description" content="{escape(descripcion, quote=True)}">',
            '<meta property="og:locale" content="es_CO">',
            f'<meta property="og:site_name" content="{MARCA}">',
            f'<meta property="og:type" content="{"article" if tipo == "Article" else "website"}">',
            '<meta name="twitter:card" content="summary">',
            f'<meta name="twitter:title" content="{escape(titulo, quote=True)}">',
            f'<meta name="twitter:description" content="{escape(descripcion, quote=True)}">']
    if canonical:
        data["url"] = canonical
        data["isPartOf"]["url"] = origen + "/"
        tags.extend([f'<link rel="canonical" href="{escape(canonical, quote=True)}">',
                     f'<meta property="og:url" content="{escape(canonical, quote=True)}">',
                     f'<meta property="og:image" content="{escape(origen, quote=True)}/static/asesor/pwa/icon-512.png">',
                     '<meta property="og:image:width" content="512">',
                     '<meta property="og:image:height" content="512">',
                     '<meta property="og:image:alt" content="El Memorialista, orientación ciudadana">',
                     f'<meta name="twitter:image" content="{escape(origen, quote=True)}/static/asesor/pwa/icon-512.png">'])
    if tipo == "Article":
        data["headline"] = titulo
    if elementos is not None:
        items = []
        for i, item in enumerate(elementos, 1):
            entry = {"@type": "ListItem", "position": i, "name": item["titulo"]}
            if origen:
                entry["url"] = origen + ruta_caso(item)
            items.append(entry)
        data["mainEntity"] = {"@type": "ItemList", "numberOfItems": len(items), "itemListElement": items}
    tags.append(f'<script type="application/ld+json">{_json_ld(data)}</script>')
    return "\n".join(tags)


def _enlace(url: str, texto: str, clase: str = "") -> str:
    return f'<a href="{escape(url, quote=True)}" class="{escape(clase, quote=True)}">{escape(texto)}</a>'


def _lista(textos: list[str], ordenada: bool = False) -> str:
    tag = "ol" if ordenada else "ul"
    return f"<{tag}>" + "".join(f"<li>{escape(texto)}</li>" for texto in textos) + f"</{tag}>"


def _tarjetas(casos: list[dict]) -> str:
    return '<div class="public-grid">' + "".join(
        '<article class="public-card">'
        f'<p class="public-label">{escape(caso["tipo_nombre"])}</p>'
        f'<h3>{_enlace(ruta_caso(caso), caso["titulo"])}</h3>'
        f'<p>{escape(caso["resumen"])}</p>'
        f'{_enlace(enlace_formulario(caso), "Abrir formulario →", "public-text-link")}</article>'
        for caso in casos) + '</div>'


def _pagina(titulo: str, descripcion: str, ruta: str, contenido: str, *, elementos: list[dict] | None = None) -> str:
    metadata = metadatos_publicos(titulo, descripcion, ruta, "CollectionPage" if elementos is not None else "Article", elementos)
    return f'''<!doctype html>
<html lang="es-CO"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(titulo)} · {MARCA}</title><meta name="description" content="{escape(descripcion, quote=True)}">
<meta name="robots" content="index,follow"><meta name="theme-color" content="#f7f6f2">
{metadata}
<link rel="icon" href="/static/asesor/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="/static/asesor/css/paginas.css">
</head><body><a class="public-skip" href="#contenido">Ir al contenido</a>
<header class="public-header"><a class="public-brand" href="/"><span class="public-mark" aria-hidden="true">m<span>.</span></span><span>El Memorialista<small>Orientación ciudadana</small></span></a>
<nav aria-label="Navegación principal"><a href="/plantillas/">Plantillas</a><a href="/#catalogo">Buscar mi caso</a><a href="/login">Iniciar sesión</a></nav></header>
<main id="contenido" tabindex="-1"><nav class="public-breadcrumb" aria-label="Ubicación"><a href="/">Inicio</a><span aria-hidden="true">/</span><a href="/plantillas/">Plantillas ciudadanas</a></nav>
{contenido}
<aside class="public-note"><strong>Revisa antes de presentar.</strong> Este contenido ayuda a preparar un borrador. Comprueba los hechos, el destinatario y las referencias aplicables a tu situación. Descargar un documento no lo radica ante ninguna entidad.</aside>
</main><footer class="public-footer"><div><strong>{MARCA}</strong><p>Documentos más claros, decisiones informadas.</p></div><nav aria-label="Información"><a href="/#acerca">Sobre esta herramienta</a><a href="/#acerca/privacidad-integracion">Privacidad</a><a href="/plantillas/">Todas las plantillas</a><a href="/#acerca/legal">Información legal</a></nav><p>Orientación ciudadana gratuita. Tus derechos, en palabras claras.</p></footer>
</body></html>'''


def pagina_indice() -> str:
    data = catalogo_publico()
    casos = data["casos"]
    title = f"{len(casos)} plantillas de documentos para la ciudadanía"
    description = "Explora modelos de peticiones, tutelas, contratos, quejas y solicitudes de familia. Lee las indicaciones y abre el formulario de tu caso."
    guides = "".join(f'<li>{_enlace("/" + slug + "/", guia["titulo"])}</li>' for slug, guia in GUIAS.items())
    groups = []
    for tipo in data["tipos"]:
        selected = [c for c in casos if c["tipo"] == tipo["id"]]
        if selected:
            groups.append(f'<section class="public-section" id="tipo-{escape(tipo["id"])}"><h2>{escape(tipo["nombre"])} <span class="public-count">{len(selected)}</span></h2>{_tarjetas(selected)}</section>')
    filters = "".join(f'<a href="#tipo-{escape(t["id"], quote=True)}">{escape(t["nombre"])}</a>' for t in data["tipos"])
    content = f'<section class="public-hero"><p class="public-eyebrow">Orientación ciudadana · Colombia</p><h1>{escape(title)}</h1><p class="public-lead">{escape(description)}</p><p>Las indicaciones de esta página se pueden leer sin JavaScript. Para completar y generar el borrador, abre el formulario interactivo.</p></section><nav class="public-types" aria-label="Tipos de documentos">{filters}</nav><section class="public-section"><h2>Guías para empezar</h2><ul class="public-guides">{guides}</ul></section>' + "".join(groups)
    return _pagina(title, description, "/plantillas/", content, elementos=casos)


def pagina_caso(caso: dict) -> str:
    fields = []
    for field in caso["campos"]:
        qualifier = " Según tus respuestas." if field["condicional"] else ""
        options = f'<p class="public-field-options">Opciones: {escape(" · ".join(field["opciones"]))}.</p>' if field["opciones"] else ""
        fields.append(f'<li><strong>{escape(field["etiqueta"])}</strong>{escape(qualifier)}{options}</li>')
    sections = f'<section class="public-section"><h2>Qué información conviene preparar</h2><p>Ten a mano los datos de quienes intervienen, el destinatario cuando corresponda y los soportes de tu situación. Estas son las preguntas específicas del modelo; algunas se muestran según tus respuestas.</p><ul class="public-fields">{"".join(fields)}</ul></section>'
    if caso["peticiones"]:
        sections += '<section class="public-section"><h2>Solicitudes que puedes revisar en el formulario</h2><p>Selecciona únicamente las que correspondan a tu situación.</p>' + _lista([p["texto"] + (" (Según tus respuestas.)" if p["condicional"] else "") for p in caso["peticiones"]]) + '</section>'
    if caso["anexos"]:
        sections += '<section class="public-section"><h2>Documentos que puedes relacionar como anexos</h2><p>La lista orienta la preparación. Marca únicamente los documentos que realmente acompañarán tu escrito.</p>' + _lista([a["texto"] + (" (Según tu situación.)" if a["condicional"] else "") for a in caso["anexos"]]) + '</section>'
    if caso["guia"]["nota"]:
        sections += f'<section class="public-section public-guidance"><h2>Orientación del modelo</h2><p>{escape(caso["guia"]["nota"])}</p>'
        if caso["guia"]["siguiente"]:
            sections += f'<h3>Qué revisar después</h3><p>{escape(caso["guia"]["siguiente"])}</p>'
        sections += '</section>'
    if caso["normas"]:
        sections += '<section class="public-section"><h2>Referencias contempladas por este modelo</h2><p>La selección final puede variar según las respuestas. Comprueba su aplicación al caso antes de presentar el documento.</p>' + _lista([n["cita"] for n in caso["normas"]]) + '</section>'
    content = f'<section class="public-hero"><p class="public-eyebrow">{escape(caso["tipo_nombre"])} · {escape(caso["categoria"])}</p><h1>{escape(caso["titulo"])}</h1><p class="public-lead">{escape(caso["resumen"])}</p>{_enlace(enlace_formulario(caso), "Preparar este documento", "public-button")}<p class="public-caption">Acceso ciudadano sin inicio de sesión. El formulario interactivo requiere JavaScript.</p></section>' + sections
    content += '<section class="public-next"><h2>Completa, revisa y descarga</h2><p>El formulario organiza tus respuestas y permite revisar el documento antes de guardarlo o descargarlo. La presentación se realiza después por el canal que corresponda.</p>' + _enlace(enlace_formulario(caso), "Abrir el formulario", "public-button") + '</section>'
    return _pagina(caso["titulo"], caso["resumen"], ruta_caso(caso), content)


def pagina_guia(slug: str) -> str:
    guide = GUIAS[slug]
    cases = catalogo_publico()["casos"]
    selected = [c for c in cases if c["tipo"] == guide["casos"]] if isinstance(guide["casos"], str) else [next(c for c in cases if c["id"] == key) for key in guide["casos"]]
    steps = ["Elige un modelo que corresponda a lo que ocurrió y a la entidad involucrada.",
             "Prepara los nombres, las fechas, las solicitudes y las respuestas que puedas documentar.",
             "Completa el formulario con hechos que conozcas y revisa las solicitudes seleccionadas.",
             "Lee el borrador completo, relaciona solo los anexos que aportarás y descarga una copia.",
             "Consulta el canal de presentación que corresponda y conserva la constancia de entrega."]
    extra = ""
    if slug == "tutela-eps":
        health = next(c for c in cases if c["id"] == "pet_eps_servicio")
        tutela = next(c for c in cases if c["id"] == "tut_salud_servicio")
        extra = f'<section class="public-section public-guidance"><h2>Si el caso es urgente</h2><p>{escape(health["resumen"])}</p><h3>Después de una decisión</h3><p>{escape(tutela["guia"]["siguiente"])}</p></section>'
    elif slug == "ejemplo-derecho-de-peticion":
        outline = "[Ciudad y fecha]\n[Destinatario]\nAsunto: [solicitud concreta]\n\nQuien presenta: [datos de identificación y contacto que correspondan]\nHechos: [explica lo ocurrido en orden y con fechas]\nSolicitudes: [indica qué información, respuesta o actuación pides]\nAnexos: [relaciona únicamente lo que acompañas]\nNotificaciones: [medio para recibir la respuesta]\n[Firma o identificación que corresponda]"
        extra = f'<section class="public-section"><h2>Esquema para organizar la información</h2><p>Este esquema es una guía de preparación. El modelo específico incorpora los apartados y referencias que correspondan a las respuestas.</p><pre class="public-example">{escape(outline)}</pre><p>Revisa el plazo y las indicaciones del modelo elegido. No todos los trámites tienen el mismo término ni la falta de respuesta produce el mismo efecto.</p></section>'
    else:
        extra = '<section class="public-section"><h2>Antes de terminar la tutela</h2>' + _lista(["Comprueba quién presenta y quién es la persona afectada.", "Identifica con precisión la entidad o persona a la que atribuyes los hechos.", "Revisa los derechos y las solicitudes seleccionadas, la urgencia indicada y las declaraciones del formulario.", "No incluyas hechos o anexos que no correspondan a tu situación."]) + '</section>'
    official = "" if slug == "ejemplo-derecho-de-peticion" else f'<section class="public-section"><h2>Canal oficial de presentación</h2><p>Consulta las instrucciones y requisitos vigentes en <a href="{TUTELA_OFICIAL}" rel="noopener noreferrer">Tutela en Línea de la Rama Judicial</a>. Este sitio no presenta el documento por ti.</p></section>'
    content = f'<section class="public-hero"><p class="public-eyebrow">Guía ciudadana</p><h1>{escape(guide["titulo"])}</h1><p class="public-lead">{escape(guide["intro"])}</p></section><section class="public-section"><h2>Prepara el documento paso a paso</h2>{_lista(steps, True)}</section>{extra}<section class="public-section"><h2>Modelos relacionados</h2>{_tarjetas(selected)}</section>{official}'
    return _pagina(guide["titulo"], guide["descripcion"], f"/{slug}/", content)


def sitemap_publico() -> str | None:
    origin = origen_publico()
    if not origin:
        return None
    urls = "".join(f"<url><loc>{xml_escape(origin + path)}</loc></url>" for path in rutas_publicas())
    return '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + urls + '</urlset>\n'


def robots_publico() -> str:
    text = "User-agent: *\nAllow: /\n" + "".join(f"Disallow: {path}\n" for path in ["/api/", "/app", "/generador", "/login", "/auth/", "/auditor.js", "/static/auditor.js", "/docs", "/openapi.json", "/redoc"])
    origin = origen_publico()
    if origin:
        text += f"\nSitemap: {origin}/sitemap.xml\n"
    return text


def llms_publico() -> str:
    origin = origen_publico()
    data = catalogo_publico()
    def label(value: str) -> str:
        return value.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]").replace("\n", " ").replace("\r", " ")
    lines = ["# El Memorialista · Orientación ciudadana", "",
             "> Catálogo público para preparar borradores de documentos en Colombia. La orientación y las plantillas se pueden leer sin iniciar sesión. Cada persona debe revisar su documento y presentarlo por el canal correspondiente.", "",
             "Las referencias y los textos dependen del modelo y de las respuestas. No se afirma que todos los casos procedan ni que su resultado esté garantizado.", "", "## Guías", ""]
    for slug, guide in GUIAS.items():
        lines.append(f"- [{label(guide['titulo'])}]({origin}/{slug}/)")
    lines.extend([f"- [Índice de las {len(data['casos'])} plantillas]({origin}/plantillas/)", "", "## Plantillas", ""])
    for case in data["casos"]:
        lines.append(f"- [{label(case['titulo'])}]({origin}{ruta_caso(case)}): {label(case['resumen'])}")
    return "\n".join(lines) + "\n"
