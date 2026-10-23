"""Manifiesto Word personalizado para el dominio configurado del despacho."""
from xml.sax.saxutils import escape

from fastapi import APIRouter, Request
from fastapi.responses import Response

from app.routers.despacho_signatures import _safe_origin

router = APIRouter(tags=["Complemento Word"])


@router.get("/word/manifest.xml", include_in_schema=False)
async def word_manifest(request: Request):
    origin = escape(_safe_origin(request), {'"': '&quot;'})
    text = f'''<?xml version="1.0" encoding="UTF-8"?>
<OfficeApp xmlns="http://schemas.microsoft.com/office/appforoffice/1.1" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:type="TaskPaneApp">
  <Id>8da5ae4c-1859-4359-a782-d9a9f7557e54</Id>
  <Version>4.0.0.0</Version><ProviderName>El Memorialista</ProviderName>
  <DefaultLocale>es-CO</DefaultLocale><DisplayName DefaultValue="El Memorialista"/>
  <Description DefaultValue="Revisa y mejora fragmentos jurídicos con aprobación y control de cambios."/>
  <SupportUrl DefaultValue="{origin}/word"/>
  <AppDomains><AppDomain>{origin}</AppDomain></AppDomains>
  <Hosts><Host Name="Document"/></Hosts>
  <Requirements><Sets DefaultMinVersion="1.4"><Set Name="WordApi" MinVersion="1.4"/></Sets></Requirements>
  <DefaultSettings><SourceLocation DefaultValue="{origin}/word"/></DefaultSettings>
  <Permissions>ReadWriteDocument</Permissions>
</OfficeApp>'''
    return Response(text, media_type="application/xml", headers={"Content-Disposition":'attachment; filename="el-memorialista-word.xml"',"Cache-Control":"private, no-store"})
