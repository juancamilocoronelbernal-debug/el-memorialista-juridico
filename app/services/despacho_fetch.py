"""Bounded, HTTPS-only retrieval of explicitly allowed public legal sources.

DNS is resolved and checked before connecting to the selected numeric address;
TLS still verifies the original hostname. Redirects are checked at every hop.
No cookies, credentials, browser sessions, proxies or private addresses are used.
"""
from __future__ import annotations

import asyncio
import ipaddress
import re
import socket
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit, urlunsplit
from xml.etree import ElementTree

import httpx
from fastapi import HTTPException

from app.config import get_settings

DEFAULT_HOSTS = ("corteconstitucional.gov.co,cortesuprema.gov.co,consejodeestado.gov.co,"
                 "ramajudicial.gov.co,suin-juriscol.gov.co,funcionpublica.gov.co,"
                 "secretariasenado.gov.co,diariooficial.imprenta.gov.co,sic.gov.co,dian.gov.co,mintrabajo.gov.co")
MAX_FETCH_BYTES = 2 * 1024 * 1024


def allowed_hosts() -> list[str]:
    value = getattr(get_settings(), "DESPACHO_MONITOR_ALLOWED_HOSTS", DEFAULT_HOSTS)
    hosts = []
    for part in value.split(","):
        host = part.strip().lower().rstrip(".")
        if re.fullmatch(r"[a-z0-9]+(?:[a-z0-9.-]*[a-z0-9])?", host) and "." in host:
            hosts.append(host)
    return list(dict.fromkeys(hosts))


def validate_url(url: str) -> str:
    if not isinstance(url, str) or len(url) > 2048 or any(c.isspace() or ord(c) < 32 for c in url) or "\\" in url:
        raise HTTPException(422, "La dirección de la fuente no es válida.")
    try:
        parsed = urlsplit(url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.port not in (None, 443):
            raise ValueError()
        host = parsed.hostname.encode("idna").decode("ascii").lower().rstrip(".")
        if not any(host == allowed or host.endswith("." + allowed) for allowed in allowed_hosts()):
            raise HTTPException(422, "Elige una fuente oficial habilitada en esta instalación.")
        try:
            ipaddress.ip_address(host)
            raise ValueError()
        except ValueError:
            if re.fullmatch(r"[0-9.]+", host) or ":" in host:
                raise ValueError()
        return urlunsplit(("https", host, parsed.path or "/", parsed.query, ""))
    except (ValueError, UnicodeError):
        raise HTTPException(422, "La fuente debe usar HTTPS, un dominio oficial habilitado y el puerto estándar.") from None


async def resolve_public(host: str) -> str:
    try:
        addresses = await asyncio.wait_for(asyncio.get_running_loop().getaddrinfo(host, 443, type=socket.SOCK_STREAM), timeout=8)
    except (OSError, asyncio.TimeoutError):
        raise HTTPException(502, "No se pudo resolver la dirección de la fuente oficial.") from None
    ips = list(dict.fromkeys(row[4][0] for row in addresses))
    if not ips or any(not ipaddress.ip_address(ip).is_global for ip in ips):
        raise HTTPException(422, "La fuente resuelve a una dirección privada o no permitida.")
    return ips[0]


class _Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.title_parts, self.skip = [], [], 0
        self.in_title = False

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript", "svg", "template"}:
            self.skip += 1
        if tag == "title":
            self.in_title = True
        if tag in {"p", "div", "li", "h1", "h2", "h3", "br", "tr", "article", "section"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript", "svg", "template"}:
            self.skip = max(0, self.skip - 1)
        if tag == "title":
            self.in_title = False
        if tag in {"p", "div", "li", "tr", "article", "section"}:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)
            if self.in_title:
                self.title_parts.append(data)


def html_to_text(html: str) -> tuple[str, str]:
    parser = _Text()
    parser.feed(html)
    text = "\n".join(line.strip() for line in "".join(parser.parts).splitlines() if line.strip())
    text = re.sub(r"[ \t]+", " ", text)
    return text, " ".join(parser.title_parts).strip()[:240]


class _Links(HTMLParser):
    def __init__(self, base: str):
        super().__init__(convert_charrefs=True)
        self.base, self.links, self.href, self.label = base, [], None, []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.href = dict(attrs).get("href")
            self.label = []

    def handle_data(self, data):
        if self.href is not None:
            self.label.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self.href:
            try:
                url = validate_url(urljoin(self.base, self.href))
                title = " ".join(" ".join(self.label).split())[:240]
                if url != self.base and title and len(self.links) < 100 and not any(link["url"] == url for link in self.links):
                    self.links.append({"url": url, "title": title})
            except HTTPException:
                pass
            self.href = None


def source_links(content: str, base: str, *, xml: bool = False) -> list[dict]:
    if not xml:
        parser = _Links(base)
        parser.feed(content)
        # Los documentos y artículos se priorizan respecto de navegación general.
        return sorted(parser.links, key=lambda link: (not bool(re.search(r"\.pdf(?:\?|$)|sentencia|relatoria|providencia|resoluci|boletin|norma", link["url"], re.I)), link["url"]))
    if "<!DOCTYPE" in content.upper() or "<!ENTITY" in content.upper():
        raise HTTPException(422, "El feed contiene definiciones XML no admitidas.")
    try:
        root = ElementTree.fromstring(content)
    except ElementTree.ParseError:
        raise HTTPException(422, "El feed no contiene XML válido.") from None
    links = []
    for entry in root.iter():
        if entry.tag.split("}")[-1] not in {"item", "entry"}:
            continue
        title, url = "", ""
        for child in entry:
            name = child.tag.split("}")[-1]
            if name == "title":
                title = " ".join("".join(child.itertext()).split())[:240]
            if name == "link" and child.attrib.get("rel", "alternate") in {"alternate", "enclosure"}:
                url = child.attrib.get("href") or (child.text or "").strip()
            if name == "enclosure" and child.attrib.get("type", "") == "application/pdf":
                url = child.attrib.get("url", url)
        if url:
            try:
                url = validate_url(urljoin(base, url))
                if not any(link["url"] == url for link in links):
                    links.append({"url": url, "title": title or "Publicación oficial"})
            except HTTPException:
                pass
        if len(links) >= 100:
            break
    return links


async def fetch_source(url: str) -> dict:
    current = validate_url(url)
    try:
        # trust_env=False prevents an environment proxy from bypassing IP pinning.
        async with httpx.AsyncClient(timeout=httpx.Timeout(20, connect=10), follow_redirects=False,
                                     trust_env=False, transport=httpx.AsyncHTTPTransport(retries=0,
                                         limits=httpx.Limits(max_keepalive_connections=0))) as client:
            for hop in range(4):
                parsed = urlsplit(current)
                ip = await resolve_public(parsed.hostname)
                target = httpx.URL(current).copy_with(host=ip)
                async with client.stream("GET", target,
                    headers={"Host": parsed.hostname, "User-Agent": "ElMemorialista-Monitor/2.0", "Accept": "text/html,text/plain,application/pdf,application/rss+xml,application/atom+xml,application/xml,text/xml", "Accept-Encoding": "identity"},
                    extensions={"sni_hostname": parsed.hostname}) as response:
                    if response.status_code in (301, 302, 303, 307, 308):
                        if hop == 3:
                            raise HTTPException(502, "La fuente redirige demasiadas veces.")
                        current = validate_url(urljoin(current, response.headers.get("location", "")))
                        continue
                    if response.status_code != 200:
                        raise HTTPException(502, f"La fuente oficial respondió HTTP {response.status_code}. No se registró una novedad.")
                    mime = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
                    if mime not in {"text/html", "application/xhtml+xml", "text/plain", "application/pdf", "application/rss+xml", "application/atom+xml", "application/xml", "text/xml"}:
                        raise HTTPException(422, "Esta fuente no devuelve una página, feed, texto o PDF compatible.")
                    if response.headers.get("content-encoding", "identity").lower() not in {"", "identity"}:
                        raise HTTPException(502, "La fuente devuelve contenido comprimido no admitido por el monitor seguro.")
                    chunks, size = [], 0
                    async for chunk in response.aiter_raw():
                        size += len(chunk)
                        if size > MAX_FETCH_BYTES:
                            raise HTTPException(413, "La publicación supera el límite de 2 MB del monitor.")
                        chunks.append(chunk)
                    content = b"".join(chunks)
                    pages, warnings, links, pagination = [], [], [], "segments"
                    extraction_coverage = {"complete": True}
                    if mime == "application/pdf":
                        from app.services.despacho_ai import extract_document
                        import anyio
                        document = await anyio.to_thread.run_sync(extract_document, content, "publicacion.pdf")
                        text, title = document["text"], "Publicación PDF"
                        pages, warnings, pagination = document["pages"], document["warnings"], "pages"
                        extraction_coverage = document["extraction_coverage"]
                    else:
                        encoding = response.encoding or "utf-8"
                        if mime in {"text/html", "application/xhtml+xml"}:
                            meta_charset = re.search(rb"<meta[^>]+charset=[\"']?([a-zA-Z0-9_-]+)", content[:2048], re.I)
                            if meta_charset:
                                try:
                                    declared = meta_charset.group(1).decode("ascii", errors="ignore").lower()
                                    content.decode(declared)
                                    encoding = declared
                                except (LookupError, UnicodeDecodeError):
                                    pass
                        decoded = content.decode(encoding, errors="replace")
                        text, title = html_to_text(decoded) if mime != "text/plain" else (decoded, "Publicación oficial")
                        if mime != "text/plain":
                            links = source_links(decoded, current, xml=mime in {"application/rss+xml", "application/atom+xml", "application/xml", "text/xml"})
                    if not text.strip():
                        raise HTTPException(422, "La fuente no contiene texto legible. Puede requerir JavaScript, OCR o acceso manual.")
                    if len(text) > 300_000:
                        raise HTTPException(413, "La fuente supera 300.000 caracteres. Selecciona una publicación más concreta.")
                    return {"url": current, "title": title or parsed.hostname, "text": text, "mime": mime,
                            "pages": pages, "pagination": pagination, "warnings": warnings, "links": links,
                            "extraction_coverage": extraction_coverage}
    except httpx.HTTPError:
        raise HTTPException(502, "No se pudo consultar la fuente oficial. Revisa su disponibilidad e inténtalo de nuevo.") from None
    raise HTTPException(502, "La fuente no produjo una respuesta utilizable.")
