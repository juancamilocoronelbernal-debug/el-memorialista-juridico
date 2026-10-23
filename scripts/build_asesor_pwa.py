#!/usr/bin/env python3
"""Build the public-only PWA after changing the public HTML or advisor assets.

No package dependencies. Outputs a static shell, manifest and service worker
with an exact URL + SHA-256 allowlist. Never fetches live/session-dependent HTML.
Run after build_asesor_offline.py and all public source changes.
"""
from __future__ import annotations

import hashlib
import json
from html.parser import HTMLParser
from pathlib import Path
import re
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
SHELL_URL = "/asesor/offline-shell.html"
MANIFEST_URL = "/asesor/manifest.webmanifest"
PWA_SCRIPT = "/static/asesor/js/pwa.js"


class Assets(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "script" and attrs.get("src"):
            self.urls.append(attrs["src"])
        elif tag == "link" and attrs.get("rel") in {"stylesheet", "icon", "apple-touch-icon"}:
            self.urls.append(attrs["href"])


def asset_path(root: Path, url: str) -> Path:
    parsed = urlsplit(url)
    if parsed.scheme or parsed.netloc or parsed.fragment or not parsed.path.startswith("/static/asesor/"):
        raise ValueError(f"Non-advisor resource refused: {url}")
    base = (root / "app/static/asesor").resolve()
    path = (root / "app" / parsed.path.lstrip("/")).resolve()
    if not path.is_relative_to(base) or not path.is_file():
        raise ValueError(f"Missing or escaped public resource: {url}")
    return path


def build(root: Path = ROOT) -> Path:
    output = root / "app/static/asesor/pwa"
    output.mkdir(parents=True, exist_ok=True)
    html = (root / "app/static/index.html").read_text(encoding="utf-8")
    # The source is a build-time public template, never a server response.
    if 'rel="manifest"' not in html:
        html = html.replace("</head>", f'<link rel="manifest" href="{MANIFEST_URL}">\n</head>')
    if not re.search(r'<script\b[^>]*src="/static/asesor/js/pwa\.js(?:\?[^\"]*)?"', html):
        html = html.replace("</head>", f'<script defer src="{PWA_SCRIPT}"></script>\n</head>')
    # /asesor/ is the application entry. Public SEO pages use their own URLs.
    html = re.sub(r'<link\b[^>]*rel="canonical"[^>]*>\s*', '', html)
    html = re.sub(r'<meta\b[^>]*name="robots"[^>]*>\s*', '', html)
    html = html.replace("</head>", '<meta name="robots" content="noindex, follow">\n</head>')
    # This policy travels with the cached shell even when no HTTP response
    # header is available. Public scripts are local, never inline/eval.
    shell_policy = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self' data:; connect-src 'self'; worker-src 'self'; object-src 'none'; base-uri 'none'; form-action 'none'; frame-src 'none'"
    html = html.replace('<meta charset="utf-8">', '<meta charset="utf-8">\n<meta http-equiv="Content-Security-Policy" content="' + shell_policy + '">', 1)
    parser = Assets(); parser.feed(html)
    assets = {url: asset_path(root, url) for url in parser.urls}
    # CSS dependencies must also be explicit: new fonts/images cannot silently
    # make the supposedly complete offline copy depend on another server.
    for url, path in assets.items():
        if path.suffix == ".css":
            css = path.read_text(encoding="utf-8")
            if re.search(r'@import\b|url\(\s*[\'"]?(?!data:|#)', css, re.I):
                raise ValueError(f"Declare CSS subresources explicitly before adding them: {url}")
    (output / "shell.html").write_text(html, encoding="utf-8")
    manifest = {
        "id": "/asesor/", "name": "El Memorialista · Orientación ciudadana",
        "short_name": "El Memorialista", "lang": "es-CO",
        "description": "Casos, formularios y guías de orientación jurídica ciudadana en Colombia. Gratis y sin registro.",
        "start_url": "/asesor/", "scope": "/asesor/", "display": "standalone",
        "background_color": "#f7f6f2", "theme_color": "#f7f6f2",
        "icons": [
            {"src": "/static/asesor/pwa/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
            {"src": "/static/asesor/pwa/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
            {"src": "/static/asesor/pwa/icon-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
        ],
        "shortcuts": [
            {"name": "Explorar casos", "url": "/asesor/#catalogo"},
            {"name": "Orientador paso a paso", "url": "/asesor/#orientador"},
            {"name": "Mis borradores", "url": "/asesor/#mis-documentos"},
            {"name": "Calculadora de plazos", "url": "/asesor/#guia/plazos"},
        ],
    }
    (output / "manifest.webmanifest").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    assets[SHELL_URL] = output / "shell.html"
    assets[MANIFEST_URL] = output / "manifest.webmanifest"
    for icon in manifest["icons"]:
        assets[icon["src"]] = asset_path(root, icon["src"])
    entries = [{"url": url, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()} for url, path in sorted(assets.items())]
    serialized = json.dumps(entries, ensure_ascii=False, indent=2)
    template = (root / "scripts/asesor_pwa_worker.js").read_text(encoding="utf-8")
    version = hashlib.sha256((template + serialized).encode()).hexdigest()[:20]
    worker = template.replace("__PUBLIC_VERSION__", json.dumps(version)).replace("__PUBLIC_ASSETS__", serialized)
    (output / "sw.js").write_text(worker, encoding="utf-8")
    return output


if __name__ == "__main__":
    path = build()
    print(f"Created public PWA in {path.relative_to(ROOT)}")
