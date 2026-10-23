"""Opt-in real local-browser smoke; never disables Chromium's sandbox.

Run from the project root with a non-root runtime capable of Chromium sandbox:
python -m tests.smoke_despacho_browser_v5 --executable /path/to/chromium
Only a public allowed source is read. No credentials, clicking or forms.
"""
import argparse
import asyncio
import json
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

from fastapi import HTTPException

from app.config import get_settings
from app.services import despacho_browser as browser


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--executable", required=True)
    parser.add_argument("--url", default="https://www.corteconstitucional.gov.co/")
    parser.add_argument("--screenshot", default="/tmp/memorialista-browser-smoke.png")
    args = parser.parse_args()
    settings = get_settings().model_copy(update={"DESPACHO_BROWSER_ENABLED": True, "DESPACHO_BROWSER_PROVIDER": "local",
        "DESPACHO_BROWSER_EXECUTABLE": args.executable, "DESPACHO_BROWSER_ALLOWED_HOSTS": urlsplit(args.url).hostname})
    browser.get_settings = lambda: settings
    owner, job = str(uuid4()), str(uuid4())
    try:
        async with asyncio.timeout(60):
            state = await browser.open_session(owner, job, args.url, [args.url])
            png = await browser.screenshot(owner, job)
            assert state["active"] and state.get("text") and png.startswith(b"\x89PNG")
            Path(args.screenshot).write_bytes(png)
            print(json.dumps({"ok": True, "provider": "local", "sandbox": True, "url": state["url"], "title": state["title"],
                "characters": len(state["text"]), "controls": len(state["controls"]), "warnings": state["warnings"], "screenshot": args.screenshot}, ensure_ascii=False))
    except (HTTPException, TimeoutError) as exc:
        print(json.dumps({"ok": False, "sandbox": True, "status": getattr(exc, "status_code", 504),
            "message": getattr(exc, "detail", "Tiempo agotado; no se confirmó la navegación.")}, ensure_ascii=False))
        # This read-only diagnostic uses the same sandbox requirement and no
        # network navigation, exposing the environmental launch failure only.
        from playwright.async_api import async_playwright
        async with async_playwright() as pw:
            try:
                launched = await pw.chromium.launch(executable_path=args.executable, headless=True, chromium_sandbox=True)
                await launched.close()
            except Exception as launch_error:
                print(json.dumps({"launch_diagnostic": str(launch_error)[:2500]}, ensure_ascii=False))
        raise SystemExit(1)
    finally:
        await browser.close_all()


if __name__ == "__main__":
    asyncio.run(main())
