"""Endpoints de lectura pública. No montan carpetas ni consultan sesiones."""
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, PlainTextResponse, Response

from app.services import asesor_paginas as paginas

router = APIRouter(include_in_schema=False)
PUBLIC_HEADERS = {
    "Cache-Control": "public, max-age=300",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "X-Frame-Options": "DENY",
    "Content-Security-Policy": "default-src 'none'; style-src 'self'; img-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'",
}


@router.api_route("/plantillas/", methods=["GET", "HEAD"])
async def indice_plantillas():
    return HTMLResponse(paginas.pagina_indice(), headers=PUBLIC_HEADERS)


@router.api_route("/plantillas/{slug}/", methods=["GET", "HEAD"])
async def plantilla_publica(slug: str):
    caso = next((c for c in paginas.catalogo_publico()["casos"] if c["slug"] == slug), None)
    if caso is None:
        raise HTTPException(status_code=404, detail="La plantilla solicitada no está disponible.")
    return HTMLResponse(paginas.pagina_caso(caso), headers=PUBLIC_HEADERS)


def _endpoint_guia(slug: str):
    async def guia():
        return HTMLResponse(paginas.pagina_guia(slug), headers=PUBLIC_HEADERS)
    return guia


for slug in paginas.GUIAS:
    router.add_api_route(f"/{slug}/", _endpoint_guia(slug), methods=["GET", "HEAD"], name=f"guia_{slug.replace('-', '_')}")


@router.api_route("/sitemap.xml", methods=["GET", "HEAD"])
async def sitemap():
    xml = paginas.sitemap_publico()
    if xml is None:
        return PlainTextResponse("El mapa del sitio estará disponible cuando se configure la URL pública canónica.\n", status_code=503, headers={"Cache-Control": "no-store", "Retry-After": "3600", "X-Robots-Tag": "noindex"})
    return Response(xml, media_type="application/xml", headers=PUBLIC_HEADERS)


@router.api_route("/robots.txt", methods=["GET", "HEAD"])
async def robots():
    return PlainTextResponse(paginas.robots_publico(), headers=PUBLIC_HEADERS)


@router.api_route("/llms.txt", methods=["GET", "HEAD"])
async def llms():
    return PlainTextResponse(paginas.llms_publico(), headers=PUBLIC_HEADERS)
