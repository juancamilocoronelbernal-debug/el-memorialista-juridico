#!/usr/bin/env python3
"""Build the public citizen advisor as a single local HTML file.

Only public assets explicitly referenced by app/static/index.html are embedded.
The private generator, login page, auth code, and API routes are never bundled.
Run again after modifying public advisor assets: python scripts/build_asesor_offline.py
"""
from pathlib import Path
import base64
import hashlib
import html as html_module
import re

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "app" / "static"
OUTPUT = STATIC / "asesor" / "descargas" / "el-memorialista-ciudadano-sin-internet.html"


def asset(url: str) -> str:
    path = url.split("?", 1)[0]
    if not path.startswith("/static/asesor/"):
        raise ValueError(f"Non-advisor resource refused: {path}")
    resolved = (STATIC / path.removeprefix("/static/")).resolve()
    if not resolved.is_relative_to((STATIC / "asesor").resolve()):
        raise ValueError("Asset escaped the public directory")
    return resolved.read_text(encoding="utf-8")


def build() -> Path:
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    html = re.sub(r'<a\b[^>]*\bdata-online-only\b[^>]*>.*?</a>', '', html, flags=re.S)
    html = re.sub(r'<link\b[^>]*rel="(?:icon|manifest|apple-touch-icon)"[^>]*>', '', html)
    html = re.sub(r'<script\b[^>]*src="/static/asesor/js/pwa\.js[^"]*"[^>]*></script>', '', html)
    html = html.replace('<!-- PUBLIC_META -->', '')
    html = html.replace('<meta charset="utf-8">', '<meta charset="utf-8">\n<script>window.AJ_SIN_INTERNET=true;</script>', 1)
    html = re.sub(r'<link\b[^>]*rel="stylesheet"[^>]*href="([^"]+)"[^>]*>',
                  lambda m: '<style>\n' + asset(m.group(1)) + '\n</style>', html)
    html = re.sub(r'<script\b[^>]*src="([^"]+)"[^>]*></script>',
                  lambda m: '<script>\n' + asset(m.group(1)).replace('</script', '<\\/script') + '\n</script>', html)
    # A local file has no server headers. Authorize only the exact embedded
    # program, preserving the same script restriction in the standalone copy.
    hashes = ["'sha256-" + base64.b64encode(hashlib.sha256(code.encode("utf-8")).digest()).decode("ascii") + "'"
              for code in re.findall(r'<script\b[^>]*>(.*?)</script>', html, flags=re.S | re.I)]
    policy = ("default-src 'none'; script-src " + ' '.join(hashes) + "; "
              "style-src 'unsafe-inline'; img-src data: blob:; font-src data:; "
              "connect-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'; frame-src 'none'; worker-src 'none'")
    html = html.replace('<meta charset="utf-8">', '<meta charset="utf-8">\n<meta http-equiv="Content-Security-Policy" content="' + html_module.escape(policy, quote=True) + '">', 1)
    # The code has an online-only download branch; it remains inert under this flag.
    if re.search(r'<(?:script|link)\b[^>]*(?:src|href)="/static/', html):
        raise ValueError("An asset is still external")
    if re.search(r'<a\b[^>]*href="/(?:login|app|api)(?:["/?#])', html):
        raise ValueError("A private route leaked into the offline page")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(html, encoding="utf-8")
    return OUTPUT


if __name__ == "__main__":
    result = build()
    print(f"Created {result.relative_to(ROOT)} ({result.stat().st_size:,} bytes)")
