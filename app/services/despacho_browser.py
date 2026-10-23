"""Isolated, supervised web sessions for public, explicitly allowed sources.

Every HTTP request is fulfilled by a bounded HTTPS broker that pins a validated
public IP; Chromium never receives a direct network continuation. Service
workers, peer transports, WebSockets and private destinations are blocked.
Automated popups are closed; managed manual sessions can receive downloads.
Browser actions refer to observed controls, require a separate single-use
database approval and cannot be recovered by silently replaying an action.

An optional Browserbase session exposes a short-lived live-view to its owner.
During takeover the agent stops observing and acting; credentials are entered
by the person in that browser, never supplied to the model or these endpoints.
Authentication, CAPTCHAs, payments, signing, filing and acceptance of terms are
always manual actions. Provider recording and CAPTCHA solving are disabled.
"""
from __future__ import annotations

import asyncio
import contextlib
import hashlib
import importlib.util
import json
import re
import time
from dataclasses import dataclass, field
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from uuid import uuid4

import httpx
from fastapi import HTTPException

from app.config import get_settings
from app.services import despacho_store as store
from app.services.despacho_fetch import resolve_public

MAX_RESPONSE = 5 * 1024 * 1024
MAX_SESSION_BYTES = 30 * 1024 * 1024
MAX_SESSIONS = 6
SECRET_QUERY_NAMES = {"access_token", "id_token", "refresh_token", "token", "code", "api_key", "apikey", "password", "session", "sessionid"}
FORBIDDEN_CONTROL = re.compile(r"contraseñ|password|passkey|one.?time|verification.?code|código.{0,20}(?:verific|seguridad)|captcha|recaptcha|tarjeta|card.?number|cvv|iban|radicar|radicación|file.{0,8}(?:brief|case)|firmar|sign.{0,8}(?:document|contract)|pagar|pay\b|purchase|comprar|acept(?:o|ar)|accept\b|agree\b|términos|terms.{0,12}conditions|biométri|eliminar|borrar|delete\b|checkout|confirm(?:ar|ation)?\b|presentar.{0,15}(?:demanda|escrito)|enviar.{0,15}(?:demanda|escrito)", re.I)
QUERY_CONTROL = re.compile(r"\b(buscar|búsqueda|consulta(?:r)?|filtrar|search|find|filter|query)\b", re.I)
BOT_WALL = re.compile(r"verify you are human|verifica que eres humano|checking your browser|unusual traffic|captcha|access denied.{0,80}(?:security|bot)", re.I)
_sessions: dict[tuple[str, str], "Session"] = {}
_registry_lock = None

def _get_registry_lock() -> asyncio.Lock:
    global _registry_lock
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if _registry_lock is None or getattr(_registry_lock, "_loop", None) != loop:
        _registry_lock = asyncio.Lock()
    return _registry_lock


@dataclass
class Session:
    owner: str
    job: str
    session_id: str
    hosts: set[str]
    playwright: object
    browser: object
    context: object
    page: object
    client: httpx.AsyncClient
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    touched: float = field(default_factory=time.monotonic)
    bytes_received: int = 0
    mutating_request: tuple[str, str] | None = None
    warnings: list[str] = field(default_factory=list)
    provider: str = "local"
    remote_id: str = ""
    manual: bool = False


def _configured_hosts() -> set[str]:
    s = get_settings()
    value = getattr(s, "DESPACHO_BROWSER_ALLOWED_HOSTS", "") or getattr(s, "DESPACHO_MONITOR_ALLOWED_HOSTS", "")
    return {h.strip().lower().rstrip(".") for h in value.split(",") if re.fullmatch(r"[a-zA-Z0-9.-]+", h.strip()) and "." in h}


def validate_url(url: str, hosts: set[str] | None = None) -> str:
    if not isinstance(url, str) or len(url) > 2048 or re.search(r"[\s\x00-\x1f\\]", url):
        raise HTTPException(422, "La dirección del navegador no es válida.")
    try:
        p = urlsplit(url)
        host = (p.hostname or "").encode("idna").decode().lower().rstrip(".")
        if p.scheme != "https" or not host or p.username or p.password or p.port not in {None, 443}:
            raise ValueError()
        if not any(host == h or host.endswith("." + h) for h in _configured_hosts()):
            raise HTTPException(422, "El dominio no está habilitado para el navegador del despacho.")
        if hosts is not None and host not in hosts:
            raise HTTPException(422, "Este encargo no autorizó el dominio solicitado.")
        return urlunsplit(("https", host, p.path or "/", p.query, ""))
    except (ValueError, UnicodeError):
        raise HTTPException(422, "El navegador admite únicamente HTTPS en dominios autorizados.") from None


def status() -> dict:
    s = get_settings()
    enabled = bool(getattr(s, "DESPACHO_BROWSER_ENABLED", False))
    installed = importlib.util.find_spec("playwright") is not None
    provider = getattr(s, "DESPACHO_BROWSER_PROVIDER", "local")
    remote_ready = bool(getattr(s, "BROWSERBASE_API_KEY", "").strip() and getattr(s, "BROWSERBASE_PROJECT_ID", "").strip())
    ready = enabled and installed and bool(_configured_hosts()) and (provider == "local" or (provider == "browserbase" and remote_ready))
    return {"enabled": enabled, "configured": ready, "provider": provider,
            "message": ("Navegador administrado con intervención personal y reanudación; cada dominio debe estar autorizado." if provider == "browserbase" else
                        "Navegación pública con acciones aprobadas una a una; requiere Chromium con sandbox.") if ready else
                       "Configura Playwright y el proveedor de navegador: Chromium local o clave y proyecto Browserbase.",
            "allowed_hosts": sorted(_configured_hosts()), "scope": "managed_takeover" if provider == "browserbase" else "local_public",
            "takeover_supported": ready and provider == "browserbase", "credentials_supported": False}


async def _browserbase(method: str, path: str, *, params: dict | None = None, payload: dict | None = None, binary: bool = False):
    key = getattr(get_settings(), "BROWSERBASE_API_KEY", "").strip()
    if not key:
        raise HTTPException(503, "Falta la clave de Browserbase en el servidor.")
    headers = {"X-BB-API-Key": key, "Accept": "application/octet-stream" if binary else "application/json"}
    try:
        async with httpx.AsyncClient(timeout=40, follow_redirects=False, trust_env=False) as client:
            async with client.stream(method, "https://api.browserbase.com/v1/" + path, headers=headers, params=params, json=payload) as response:
                if response.status_code not in {200, 201, 204}:
                    raise HTTPException(503, "Browserbase no pudo completar la operación. Comprueba cuenta, permisos y cuota.")
                chunks, length = [], 0
                async for chunk in response.aiter_bytes():
                    length += len(chunk)
                    if length > (store.MAX_UPLOAD_BYTES if binary else 1_000_000):
                        raise HTTPException(413, "La respuesta del navegador supera el límite permitido.")
                    chunks.append(chunk)
                data = b"".join(chunks)
        if binary:
            return data
        return json.loads(data) if data else {}
    except (httpx.HTTPError, ValueError):
        raise HTTPException(503, "No se pudo comunicar con Browserbase. Ninguna acción se confirmó.") from None


def _provider_url(value: str, *, websocket: bool = False) -> str:
    try:
        parsed = urlsplit(value)
        host = parsed.hostname or ""
        if parsed.scheme != ("wss" if websocket else "https") or parsed.username or parsed.password or parsed.port not in {None, 443}:
            raise ValueError()
        if host != "browserbase.com" and not host.endswith(".browserbase.com"):
            raise ValueError()
        return value
    except (ValueError, TypeError):
        raise HTTPException(502, "Browserbase devolvió un enlace fuera de su dominio autorizado.") from None


def _display_url(value: str) -> str:
    parsed = urlsplit(value)
    query = [(k, "[redactado]" if k.lower() in SECRET_QUERY_NAMES else v) for k, v in parse_qsl(parsed.query, keep_blank_values=True)]
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query), ""))


async def _dispose(session: Session) -> None:
    for obj, method in ((session.context, "close"), (session.browser, "close"), (session.playwright, "stop"), (session.client, "aclose")):
        with contextlib.suppress(Exception):
            await getattr(obj, method)()
    if session.remote_id:
        with contextlib.suppress(HTTPException):
            await _browserbase("POST", "sessions/" + session.remote_id, payload={"status": "REQUEST_RELEASE"})


async def close_session(owner: str, job: str) -> None:
    async with _get_registry_lock():
        session = _sessions.pop((owner, job), None)
    if session:
        async with session.lock:
            await _dispose(session)


async def close_all() -> None:
    for owner, job in list(_sessions):
        await close_session(owner, job)


async def close_owner(owner: str) -> None:
    """Close remote/live-view capabilities when the account is being removed."""
    for session_owner, job in list(_sessions):
        if session_owner == owner:
            await close_session(owner, job)


async def _session(owner: str, job: str) -> Session:
    key = (store.uuid_text(owner), store.uuid_text(job))
    session = _sessions.get(key)
    ttl = max(60, int(getattr(get_settings(), "DESPACHO_BROWSER_SESSION_TTL_SECONDS", 900)))
    if session is None or time.monotonic() - session.touched > ttl:
        if session:
            await close_session(*key)
        raise HTTPException(410, "La sesión de navegador terminó. Abre de nuevo una fuente y revisa sus controles; las acciones anteriores no se repiten.")
    session.touched = time.monotonic()
    return session


async def _broker(session: Session, route) -> None:
    request = route.request
    try:
        url = validate_url(request.url, session.hosts)
        method = request.method.upper()
        if method not in {"GET", "HEAD", "OPTIONS"} and not session.manual:
            if session.mutating_request != (method, url):
                raise HTTPException(403, "La página intentó una transmisión no aprobada.")
            # Only one exact HTTP mutation is permitted per approved action.
            session.mutating_request = None
        parsed = urlsplit(url)
        ip = await resolve_public(parsed.hostname)
        authority = f"[{ip}]" if ":" in ip else ip
        pinned = urlunsplit(("https", authority, parsed.path, parsed.query, ""))
        incoming = await request.all_headers()
        # Authentication created by the person in the isolated browser must
        # reach its authorized origin. These values remain transport-only:
        # they are never included in snapshots, model context, database or logs.
        allowed = {"accept", "accept-language", "content-type", "cookie", "origin", "referer", "user-agent",
                   "authorization", "x-csrf-token", "x-xsrf-token", "x-requested-with",
                   "access-control-request-method", "access-control-request-headers", "sec-fetch-mode", "sec-fetch-site", "sec-fetch-dest"}
        headers = {k: v for k, v in incoming.items() if k.lower() in allowed}
        headers["host"] = parsed.hostname
        headers["accept-encoding"] = "identity"
        # The broker uses numeric origins; never let its own cookie jar merge
        # cookies for two unrelated domains hosted on the same public IP.
        headers["cookie"] = incoming.get("cookie", "")
        body = request.post_data_buffer
        if body and len(body) > (store.MAX_UPLOAD_BYTES if session.manual else 64_000):
            raise HTTPException(413, "El formulario excede el límite permitido.")
        async with session.client.stream(method, pinned, headers=headers, content=body,
                extensions={"sni_hostname": parsed.hostname.encode("ascii")}) as response:
            chunks, size = [], 0
            async for chunk in response.aiter_raw():
                size += len(chunk)
                session.bytes_received += len(chunk)
                if size > MAX_RESPONSE or session.bytes_received > MAX_SESSION_BYTES:
                    raise HTTPException(413, "La navegación alcanzó su límite de descarga.")
                chunks.append(chunk)
            response_headers = {k: v for k, v in response.headers.items() if k.lower() not in {"content-length", "transfer-encoding", "connection", "alt-svc", "set-cookie"}}
            # Playwright represents repeated Set-Cookie with newlines. Joining
            # with commas breaks Expires dates and authenticated multi-cookies.
            cookies = response.headers.get_list("set-cookie")
            if cookies:
                response_headers["set-cookie"] = "\n".join(cookies)
            await route.fulfill(status=response.status_code, headers=response_headers, body=b"".join(chunks))
    except Exception as exc:
        message = str(exc.detail) if isinstance(exc, HTTPException) else "No se pudo cargar un recurso autorizado."
        if message not in session.warnings and len(session.warnings) < 12:
            session.warnings.append(message)
        with contextlib.suppress(Exception):
            await route.abort("blockedbyclient")


_NETWORK_GUARDS = r"""(() => {
  // These transports bypass ordinary intercepted HTTP. The application uses
  // the supervised page, never page-created workers or peer connections.
  for (const key of ['RTCPeerConnection','webkitRTCPeerConnection','WebTransport','Worker','SharedWorker']) {
    try { Object.defineProperty(globalThis,key,{value:undefined,configurable:false,writable:false}); } catch {}
  }
  try { Object.defineProperty(Navigator.prototype,'serviceWorker',{get:()=>undefined,configurable:false}); } catch {}
})();"""

_SNAPSHOT = r"""() => {
  const visible = e => { const r=e.getBoundingClientRect(); const s=getComputedStyle(e); return r.width>0&&r.height>0&&s.visibility!=='hidden'&&s.display!=='none'; };
  const nodes=[...document.querySelectorAll('a[href],button,input:not([type=hidden]),textarea,select,[role=button]')].filter(visible).slice(0,120);
  const controls=nodes.map((e,i)=>{const ref='c'+i; e.setAttribute('data-memorialista-ref',ref); const label=e.labels?.[0]?.innerText||e.getAttribute('aria-label')||e.innerText||e.getAttribute('placeholder')||e.name||e.type||e.tagName;
    const f=e.form; const secret=!!f?.querySelector('input[type=password],input[autocomplete=one-time-code]');
    return {ref,tag:e.tagName.toLowerCase(),role:e.getAttribute('role')||'',name:String(label).trim().slice(0,220),field_type:e.type||'',autocomplete:e.autocomplete||'',href:e.href||'',disabled:!!e.disabled,form_action:f?.action||'',form_method:(f?.method||'get').toUpperCase(),form_has_secret:secret};});
  return {url:location.href,title:document.title,text:document.body?.innerText?.slice(0,40000)||'',controls};
}"""


async def _snapshot(session: Session) -> dict:
    if session.manual:
        return {"active": True, "manual": True, "provider": session.provider, "controls": [],
                "message": "Tienes el control del navegador. El agente no observa ni actúa hasta que pulses Retomar."}
    try:
        raw = await asyncio.wait_for(session.page.evaluate(_SNAPSHOT), timeout=15)
    except TimeoutError:
        raise HTTPException(504, "La página no respondió a tiempo. No se confirmó ninguna interacción.") from None
    raw["url"] = _display_url(validate_url(raw["url"], session.hosts))
    for control in raw["controls"]:
        sensitive_url = False
        for key in ("href", "form_action"):
            original = str(control.get(key) or "")
            control[key] = _display_url(original) if original else ""
            parsed = urlsplit(original)
            sensitive_url = sensitive_url or any(k.lower() in SECRET_QUERY_NAMES for k, _ in parse_qsl(parsed.query + "&" + parsed.fragment, keep_blank_values=True))
        control["blocked"] = (control["field_type"].lower() in {"password", "file"} or control["form_has_secret"] or
            sensitive_url or bool(FORBIDDEN_CONTROL.search(" ".join(str(control.get(k, "")) for k in ("name", "field_type", "autocomplete", "href", "form_action")))) or
            (control["form_method"] not in {"GET", "HEAD"} and control["tag"] not in {"input", "textarea"} and not QUERY_CONTROL.search(control["name"])))
    raw["blocked_page"] = bool(BOT_WALL.search(raw["text"]))
    raw["page_hash"] = hashlib.sha256(json.dumps(raw, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    raw.update(active=True, manual=False, provider=session.provider, session_id=session.session_id, warnings=list(session.warnings))
    return raw


async def open_session(owner: str, job: str, url: str, allowed_urls: list[str]) -> dict:
    owner, job = store.uuid_text(owner), store.uuid_text(job)
    if not status()["configured"]:
        raise HTTPException(503, status()["message"])
    permitted = [validate_url(value) for value in allowed_urls]
    current = validate_url(url)
    if current not in permitted:
        raise HTTPException(422, "La URL no forma parte del encargo aprobado.")
    hosts = {urlsplit(value).hostname for value in permitted}
    await resolve_public(urlsplit(current).hostname)
    # Lazy import leaves the ordinary generator usable without browser packages.
    from playwright.async_api import async_playwright
    async with _get_registry_lock():
        # Replacement is atomic: two simultaneous opens must not overwrite a
        # still-live remote context and leave its live-view capability orphaned.
        previous = _sessions.pop((owner, job), None)
        if previous:
            async with previous.lock:
                await _dispose(previous)
        expired = [(k, v) for k, v in _sessions.items() if time.monotonic() - v.touched > 900]
        for key, old in expired:
            _sessions.pop(key, None)
            async with old.lock:
                await _dispose(old)
        if len(_sessions) >= MAX_SESSIONS:
            raise HTTPException(429, "El navegador está ocupado. Cierra otra sesión o inténtalo más tarde.")
        pw = await async_playwright().start()
        browser, context, client, remote_id = None, None, None, ""
        try:
            provider = getattr(get_settings(), "DESPACHO_BROWSER_PROVIDER", "local")
            if provider == "browserbase":
                created = await _browserbase("POST", "sessions", payload={"projectId": get_settings().BROWSERBASE_PROJECT_ID,
                    "timeout": max(60, min(3600, int(getattr(get_settings(), "DESPACHO_BROWSER_SESSION_TTL_SECONDS", 900)))),
                    "keepAlive": False, "browserSettings": {"viewport": {"width": 1280, "height": 850},
                    "solveCaptchas": False, "recordSession": False, "logSession": False, "advancedStealth": False,
                    "ignoreCertificateErrors": False, "allowedDomains": sorted(hosts)}})
                remote_id = store.uuid_text(created.get("id"), "sesión del proveedor")
                browser = await pw.chromium.connect_over_cdp(_provider_url(created.get("connectUrl", ""), websocket=True))
                if not browser.contexts:
                    raise HTTPException(502, "Browserbase no entregó un contexto de navegación.")
                context = browser.contexts[0]
                page = context.pages[0] if context.pages else await context.new_page()
                cdp = await context.new_cdp_session(page)
                await cdp.send("Browser.setDownloadBehavior", {"behavior": "allow", "downloadPath": "downloads", "eventsEnabled": True})
                await cdp.send("Network.setBypassServiceWorker", {"bypass": True})
                await context.clear_permissions()
            else:
                executable = getattr(get_settings(), "DESPACHO_BROWSER_EXECUTABLE", "").strip()
                options = {"headless": True, "chromium_sandbox": True,
                           "args": ["--disable-quic", "--force-webrtc-ip-handling-policy=disable_non_proxied_udp", "--host-resolver-rules=MAP * ~NOTFOUND"]}
                if executable:
                    options["executable_path"] = executable
                browser = await pw.chromium.launch(**options)
                context = await browser.new_context(accept_downloads=False, service_workers="block", viewport={"width": 1280, "height": 850}, permissions=[])
                page = await context.new_page()
            client = httpx.AsyncClient(timeout=httpx.Timeout(20, connect=8), trust_env=False, follow_redirects=False)
            session = Session(owner, job, str(uuid4()), hosts, pw, browser, context, page, client, provider=provider, remote_id=remote_id)
            await context.add_init_script(script=_NETWORK_GUARDS)
            await context.route("**/*", lambda route: _broker(session, route))
            await context.route_web_socket("**/*", lambda websocket: websocket.close())
            def dialog_handler(dialog):
                # During takeover the person handles native confirmations.
                # Never silently accept (or cancel) a manual legal operation.
                if not session.manual:
                    asyncio.create_task(dialog.dismiss())

            def popup_handler(popup):
                if popup == page:
                    return
                if session.manual:
                    # OAuth popups remain in this isolated, brokered context.
                    popup.on("dialog", dialog_handler)
                else:
                    asyncio.create_task(popup.close())
            context.on("page", popup_handler)
            page.on("dialog", dialog_handler)
            page.set_default_timeout(12_000)
            await page.goto(current, wait_until="domcontentloaded", timeout=30_000)
            _sessions[(owner, job)] = session
            return await _snapshot(session)
        except Exception as exc:
            for obj, method in ((context, "close"), (browser, "close"), (pw, "stop"), (client, "aclose")):
                if obj:
                    with contextlib.suppress(Exception):
                        await getattr(obj, method)()
            if remote_id:
                with contextlib.suppress(HTTPException):
                    await _browserbase("POST", "sessions/" + remote_id, payload={"status": "REQUEST_RELEASE"})
            if isinstance(exc, HTTPException):
                raise
            raise HTTPException(503, "No se pudo iniciar el navegador aislado. Comprueba Chromium, su sandbox y las dependencias del servidor.") from None


async def get_state(owner: str, job: str) -> dict:
    try:
        session = await _session(owner, job)
    except HTTPException as exc:
        if exc.status_code == 410:
            return {"active": False, "message": exc.detail, "controls": []}
        raise
    async with session.lock:
        state = await _snapshot(session)
    if session.manual:
        return state
    from app.services import despacho_agent as agent
    rows = await agent._service("GET", "despacho_agent_browser_actions", params={"owner_id": "eq." + owner,
        "job_id": "eq." + job, "session_id": "eq." + session.session_id, "state": "eq.pending", "order": "created_at.desc", "limit": 1})
    if isinstance(rows, list) and rows:
        row = rows[0]
        state["pending_action"] = {"action_id": row["id"], **row["action"], "expires_at": row["expires_at"], "requires_approval": True}
    return state


async def screenshot(owner: str, job: str) -> bytes:
    session = await _session(owner, job)
    async with session.lock:
        if session.manual:
            raise HTTPException(409, "Las capturas están pausadas durante tu intervención personal.")
        # Mask all editable values; never expose credentials or form contents
        # inadvertently embedded in a browser capture.
        return await session.page.screenshot(type="png", full_page=False, mask=[session.page.locator("input,textarea,[contenteditable=true]")])


def validate_action(state: dict, payload: dict, hosts: set[str]) -> dict:
    if state.get("manual"):
        raise HTTPException(409, "Retoma el control del agente antes de proponer acciones.")
    if state.get("blocked_page"):
        raise HTTPException(409, "El sitio muestra una verificación humana o restricción. Continúa directamente en el sitio original.")
    control = next((c for c in state["controls"] if c["ref"] == payload.get("ref")), None)
    if not control or control.get("disabled") or control.get("blocked"):
        raise HTTPException(422, "El control no está disponible o requiere una intervención personal en el sitio original.")
    action = payload.get("action")
    if action not in {"click", "fill"}:
        raise HTTPException(422, "Acción de navegador no admitida.")
    value = payload.get("value", "")
    if not isinstance(value, str) or len(value) > 2000:
        raise HTTPException(422, "El valor admite hasta 2.000 caracteres.")
    if action == "fill" and (control["tag"] not in {"input", "textarea"} or control["field_type"] not in {"", "text", "search", "number", "date", "textarea"}):
        raise HTTPException(422, "Solo se admite texto de consulta; no credenciales, archivos ni información de pago.")
    proposed = {"action": action, "ref": control["ref"], "label": control["name"], "url": state["url"], "value": value if action == "fill" else ""}
    if action == "click" and control.get("form_action") and control.get("form_method") not in {"GET", "HEAD"}:
        proposed["request_url"] = validate_url(control["form_action"], hosts)
        proposed["request_method"] = control["form_method"]
    if control.get("href"):
        proposed["destination"] = validate_url(control["href"], hosts)
    return proposed


async def propose(owner: str, job: str, payload: dict) -> dict:
    from app.services import despacho_agent as agent
    session = await _session(owner, job)
    async with session.lock:
        state = await _snapshot(session)
        action = validate_action(state, payload, session.hosts)
        row = await agent._rpc("despacho_agent_browser_propose", {"p_owner": owner, "p_job": job, "p_session": session.session_id, "p_action": action, "p_hash": state["page_hash"]})
        return {"action_id": row["id"], **action, "expires_at": row["expires_at"], "requires_approval": True}


async def approve(owner: str, job: str, action_id: str, expected_version: int) -> dict:
    from app.services import despacho_agent as agent
    session = await _session(owner, job)
    async with session.lock:
        before = await _snapshot(session)
        if before.get("manual"):
            raise HTTPException(409, "La aprobación está pausada durante tu intervención personal.")
        row = await agent._rpc("despacho_agent_browser_claim", {"p_owner": owner, "p_job": job, "p_action": store.uuid_text(action_id),
            "p_session": session.session_id, "p_hash": before["page_hash"], "p_version": expected_version})
        action = row["action"]
        result, error = {}, ""
        try:
            validate_action(before, action, session.hosts)
            locator = session.page.locator('[data-memorialista-ref="' + action["ref"] + '"]')
            if await locator.count() != 1:
                raise HTTPException(409, "El control cambió después de la revisión.")
            if action["action"] == "fill":
                await locator.fill(action["value"])
            else:
                if action.get("request_url"):
                    session.mutating_request = (action["request_method"], action["request_url"])
                await locator.click(timeout=12_000)
            result = await _snapshot(session)
        except Exception:
            error = "No se pudo confirmar el resultado de la interacción. No se repetirá automáticamente; revisa el sitio antes de proponer otra acción."
        finally:
            session.mutating_request = None
        updated = await agent._rpc("despacho_agent_browser_finish", {"p_owner": owner, "p_job": job, "p_action": action_id,
            "p_result": {"url": result.get("url"), "title": result.get("title"), "warnings": session.warnings}, "p_error": error})
        if not result:
            with contextlib.suppress(Exception):
                result = await _snapshot(session)
        return {"job": agent.public_job(updated, owner), "browser": result, "warning": error}


async def takeover(owner: str, job: str) -> dict:
    session = await _session(owner, job)
    if session.provider != "browserbase" or not session.remote_id:
        raise HTTPException(503, "La intervención en el mismo navegador requiere configurar Browserbase.")
    async with session.lock:
        # Close any previous proposed action before permitting manual changes.
        from app.services import despacho_agent as agent
        links = await _browserbase("GET", "sessions/" + session.remote_id + "/debug", params={"expiresIn": 60})
        link = _provider_url(links.get("debuggerFullscreenUrl", ""))
        await agent._rpc("despacho_agent_browser_manual", {"p_owner": owner, "p_job": job, "p_manual": True})
        session.manual = True
        return {"manual": True, "takeover_url": link, "expires_in": 60,
                "message": "El enlace permite controlar tu sesión privada. No lo compartas. Introduce credenciales y completa trámites personalmente; el agente está pausado. Cierra esa ventana antes de retomar."}


async def resume(owner: str, job: str) -> dict:
    session = await _session(owner, job)
    async with session.lock:
        if not session.manual:
            return await _snapshot(session)
        additional = [page for page in getattr(session.context, "pages", []) if page != session.page and not page.is_closed()]
        if additional:
            raise HTTPException(409, "Cierra las pestañas adicionales de la intervención personal y vuelve a la fuente original antes de retomar.")
        session.manual = False
        try:
            state = await _snapshot(session)
        except Exception:
            session.manual = True
            raise
        from app.services import despacho_agent as agent
        try:
            await agent._rpc("despacho_agent_browser_manual", {"p_owner": owner, "p_job": job, "p_manual": False})
        except Exception:
            session.manual = True
            raise
        state["message"] = "Control retomado. Revisa el estado observado: la aplicación no presume que el trámite haya finalizado correctamente."
        return state


async def list_downloads(owner: str, job: str) -> dict:
    session = await _session(owner, job)
    if not session.remote_id:
        return {"items": [], "message": "Las descargas administradas requieren Browserbase."}
    payload = await _browserbase("GET", "downloads", params={"sessionId": session.remote_id, "limit": 100})
    rows = payload.get("downloads", [])
    if not isinstance(rows, list):
        raise HTTPException(502, "El proveedor devolvió una lista de descargas inválida.")
    items = []
    for row in rows:
        if row.get("sessionId") not in {None, session.remote_id}:
            raise HTTPException(502, "El proveedor devolvió un archivo de otra sesión.")
        items.append({"id": store.uuid_text(row.get("id"), "descarga"), "filename": str(row.get("filename", "documento"))[:200],
                      "size": row.get("size"), "mime": row.get("mimeType") or "application/octet-stream"})
    return {"items": items, "has_more": int(payload.get("total", len(items))) > len(items)}


async def download(owner: str, job: str, download_id: str) -> tuple[bytes, dict]:
    download_id = store.uuid_text(download_id)
    listing = await list_downloads(owner, job)
    item = next((row for row in listing["items"] if row["id"] == download_id), None)
    if not item:
        raise HTTPException(404, "El archivo no pertenece a la sesión de este encargo o no está disponible.")
    content = await _browserbase("GET", "downloads/" + download_id, binary=True)
    return content, item
