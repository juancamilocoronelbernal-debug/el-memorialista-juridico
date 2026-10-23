"""Browser security/approval/adapter tests with deterministic network doubles.

These tests exercise the HTTP broker and actual provider request construction.
They do not claim a live Browserbase account or real Chromium compatibility.
"""
import asyncio
import copy
import json
import sys
import types
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest
from fastapi import HTTPException

from app.services import despacho_agent as agent, despacho_browser as browser

OWNER, OTHER, JOB, REMOTE, ACTION, DOWNLOAD = [str(uuid4()) for _ in range(6)]
HOST = "corteconstitucional.gov.co"
URL = "https://" + HOST + "/relatoria/"
OTHER_URL = "https://funcionpublica.gov.co/consulta"


@pytest.fixture(autouse=True)
def config(monkeypatch):
    settings = types.SimpleNamespace(DESPACHO_BROWSER_ENABLED=True, DESPACHO_BROWSER_PROVIDER="local",
        DESPACHO_BROWSER_ALLOWED_HOSTS=HOST + ",funcionpublica.gov.co", DESPACHO_BROWSER_SESSION_TTL_SECONDS=900,
        DESPACHO_BROWSER_EXECUTABLE="", BROWSERBASE_API_KEY="provider-secret-test", BROWSERBASE_PROJECT_ID="project-test")
    monkeypatch.setattr(browser, "get_settings", lambda: settings)
    monkeypatch.setattr(browser, "_registry_lock", asyncio.Lock())
    browser._sessions.clear()
    yield settings
    browser._sessions.clear()


class Body(httpx.AsyncByteStream):
    def __init__(self, content=b"<p>Fuente oficial</p>"):
        self.content = content

    async def __aiter__(self):
        yield self.content


class Route:
    def __init__(self, url=URL, method="GET", headers=None, body=None):
        self.request = types.SimpleNamespace(url=url, method=method, post_data_buffer=body,
            all_headers=AsyncMock(return_value=headers or {}))
        self.fulfill = AsyncMock()
        self.abort = AsyncMock()


def control(**changes):
    return {"ref": "c0", "tag": "button", "role": "", "name": "Buscar", "field_type": "submit", "autocomplete": "",
            "href": "", "disabled": False, "form_action": URL, "form_method": "GET", "form_has_secret": False, **changes}


def page_state(controls=None, **changes):
    return {"url": URL, "title": "Fuente oficial", "text": "Consulta de providencias", "controls": controls or [control()], **changes}


def session(client=None, *, provider="local", manual=False):
    page = types.SimpleNamespace(evaluate=AsyncMock(side_effect=lambda *_: copy.deepcopy(page_state())),
        screenshot=AsyncMock(return_value=b"PNG"), locator=lambda _: object())
    instance = browser.Session(OWNER, JOB, str(uuid4()), {HOST, "funcionpublica.gov.co"},
        types.SimpleNamespace(stop=AsyncMock()), types.SimpleNamespace(close=AsyncMock()), types.SimpleNamespace(close=AsyncMock()),
        page, client or types.SimpleNamespace(aclose=AsyncMock()), provider=provider, remote_id=REMOTE if provider == "browserbase" else "", manual=manual)
    browser._sessions[(OWNER, JOB)] = instance
    return instance


@pytest.mark.parametrize("url", ["http://corteconstitucional.gov.co/", "https://127.0.0.1/", "https://user:pass@corteconstitucional.gov.co/", "https://corteconstitucional.gov.co:444/", "https://corteconstitucional.gov.co.evil.example/", "https://corteconstitucional.gov.co/\nadmin"])
def test_browser_url_is_https_authorized_and_not_a_credential_channel(url):
    with pytest.raises(HTTPException):
        browser.validate_url(url)


def test_browser_job_scope_does_not_expand_to_every_admin_host():
    assert browser.validate_url(URL, {HOST}) == URL
    with pytest.raises(HTTPException):
        browser.validate_url(OTHER_URL, {HOST})


@pytest.mark.asyncio
async def test_dns_private_destination_is_blocked_before_http(monkeypatch):
    client = types.SimpleNamespace(stream=AsyncMock())
    current, route = session(client), Route()
    monkeypatch.setattr(browser, "resolve_public", AsyncMock(side_effect=HTTPException(422, "Destino no público")))
    await browser._broker(current, route)
    client.stream.assert_not_called()
    route.abort.assert_awaited_once()
    route.fulfill.assert_not_awaited()


@pytest.mark.asyncio
async def test_broker_pins_public_ip_and_preserves_sni_and_host(monkeypatch):
    observed = []
    async def transport(request):
        observed.append(request)
        return httpx.Response(200, stream=Body())
    monkeypatch.setattr(browser, "resolve_public", AsyncMock(return_value="93.184.216.34"))
    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
        route = Route()
        await browser._broker(session(client), route)
    assert str(observed[0].url) == "https://93.184.216.34/relatoria/"
    assert observed[0].headers["host"] == HOST
    assert observed[0].extensions["sni_hostname"] == HOST.encode()
    route.fulfill.assert_awaited_once()


@pytest.mark.asyncio
async def test_mutation_needs_exact_single_use_approval(monkeypatch):
    hits = []
    async def transport(request):
        hits.append(str(request.url))
        return httpx.Response(200, stream=Body())
    monkeypatch.setattr(browser, "resolve_public", AsyncMock(return_value="93.184.216.34"))
    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
        current = session(client)
        blocked = Route(method="POST", body=b"q=tema")
        await browser._broker(current, blocked)
        assert not hits
        current.mutating_request = ("POST", URL)
        wrong = Route(url=URL + "different", method="POST")
        await browser._broker(current, wrong)
        assert not hits and current.mutating_request == ("POST", URL)
        allowed = Route(method="POST", body=b"q=tema")
        await browser._broker(current, allowed)
        assert len(hits) == 1 and current.mutating_request is None
        replay = Route(method="POST")
        await browser._broker(current, replay)
        assert len(hits) == 1
        replay.abort.assert_awaited_once()


@pytest.mark.asyncio
async def test_browser_cookie_jar_never_leaks_between_domains_sharing_ip(monkeypatch):
    incoming = []
    async def transport(request):
        incoming.append(request.headers.get("cookie", ""))
        return httpx.Response(200, headers=[("set-cookie", "sid=secret-domain-a; Path=/"), ("set-cookie", "pref=one; Expires=Wed, 21 Oct 2037 07:28:00 GMT; Path=/")], stream=Body())
    monkeypatch.setattr(browser, "resolve_public", AsyncMock(return_value="93.184.216.34"))
    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
        current = session(client)
        first, second = Route(headers={"cookie": "origin=first"}), Route(url=OTHER_URL)
        await browser._broker(current, first)
        await browser._broker(current, second)
    assert incoming == ["origin=first", ""]
    cookies = first.fulfill.call_args.kwargs["headers"]["set-cookie"]
    assert "\npref=" in cookies and "Expires=Wed, 21 Oct 2037" in cookies


@pytest.mark.asyncio
async def test_authenticated_read_and_cors_preflight_preserve_transport_headers_only(monkeypatch):
    requests = []
    async def transport(request):
        requests.append(request)
        return httpx.Response(200, stream=Body())
    monkeypatch.setattr(browser, "resolve_public", AsyncMock(return_value="93.184.216.34"))
    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
        current = session(client, provider="browserbase")
        preflight = Route(method="OPTIONS", headers={"access-control-request-method": "GET", "access-control-request-headers": "authorization"})
        await browser._broker(current, preflight)
        read = Route(headers={"authorization": "Bearer person-entered-private-token"})
        await browser._broker(current, read)
        state = await browser._snapshot(current)
    assert len(requests) == 2
    assert requests[0].headers["access-control-request-method"] == "GET"
    assert requests[1].headers["authorization"] == "Bearer person-entered-private-token"
    assert "person-entered-private-token" not in json.dumps(state)


@pytest.mark.asyncio
async def test_redirect_is_not_followed_by_broker_and_target_is_revalidated(monkeypatch):
    hits = []
    async def transport(request):
        hits.append(request)
        return httpx.Response(302, headers={"location": "https://127.0.0.1/private"}, stream=Body(b""))
    monkeypatch.setattr(browser, "resolve_public", AsyncMock(return_value="93.184.216.34"))
    async with httpx.AsyncClient(transport=httpx.MockTransport(transport), follow_redirects=False) as client:
        current, first = session(client), Route()
        await browser._broker(current, first)
        second = Route(url="https://127.0.0.1/private")
        await browser._broker(current, second)
    assert len(hits) == 1 and first.fulfill.call_args.kwargs["status"] == 302
    second.abort.assert_awaited_once()


@pytest.mark.asyncio
async def test_response_budget_aborts_and_never_returns_partial_page(monkeypatch):
    monkeypatch.setattr(browser, "MAX_RESPONSE", 4)
    monkeypatch.setattr(browser, "resolve_public", AsyncMock(return_value="93.184.216.34"))
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200, stream=Body(b"too large")))) as client:
        current, route = session(client), Route()
        await browser._broker(current, route)
        assert current.warnings
        route.fulfill.assert_not_awaited()
        route.abort.assert_awaited_once()


@pytest.mark.asyncio
async def test_manual_control_pauses_dom_screenshots_and_automatic_approval(monkeypatch):
    current = session(provider="browserbase", manual=True)
    rpc = AsyncMock()
    monkeypatch.setattr(agent, "_rpc", rpc)
    state = await browser._snapshot(current)
    assert state["manual"] and not state["controls"]
    current.page.evaluate.assert_not_awaited()
    for action in (browser.screenshot(OWNER, JOB), browser.approve(OWNER, JOB, ACTION, 2)):
        with pytest.raises(HTTPException) as exc:
            await action
        assert exc.value.status_code == 409
    rpc.assert_not_awaited()


@pytest.mark.parametrize("changes", [{"field_type": "password"}, {"field_type": "file"}, {"name": "Firmar documento"}, {"name": "Pagar"}, {"name": "Acepto los términos"}, {"name": "Aceptar"}, {"name": "Confirmar"}, {"name": "Radicar escrito"}, {"form_has_secret": True}, {"name": "Enviar", "form_method": "POST"}])
@pytest.mark.asyncio
async def test_credentials_binding_actions_and_nonquery_mutations_require_person(changes):
    current = session()
    current.page.evaluate = AsyncMock(return_value=page_state([control(**changes)]))
    state = await browser._snapshot(current)
    assert state["controls"][0]["blocked"]
    with pytest.raises(HTTPException):
        browser.validate_action(state, {"action": "click", "ref": "c0"}, current.hosts)


@pytest.mark.asyncio
async def test_tokens_in_control_urls_are_not_returned_or_saved():
    current = session()
    current.page.evaluate = AsyncMock(return_value=page_state([control(href=URL + "?token=VERY_PRIVATE&topic=test")], url=URL + "?code=AUTH_CODE"))
    state = await browser._snapshot(current)
    assert "VERY_PRIVATE" not in json.dumps(state) and "AUTH_CODE" not in json.dumps(state)
    assert state["controls"][0]["blocked"]


@pytest.mark.asyncio
async def test_stale_page_approval_never_clicks_before_database_validation(monkeypatch):
    current = session()
    locate = AsyncMock()
    current.page.locator = locate
    monkeypatch.setattr(agent, "_rpc", AsyncMock(side_effect=HTTPException(409, "La página cambió")))
    with pytest.raises(HTTPException):
        await browser.approve(OWNER, JOB, ACTION, 2)
    locate.assert_not_called()


@pytest.mark.asyncio
async def test_browserbase_rest_request_is_server_authenticated_and_errors_hide_secrets(config, monkeypatch):
    requests = []
    async def handler(request):
        requests.append(request)
        return httpx.Response(403, text="provider-secret-test connectUrl=wss://secret")
    client_type = httpx.AsyncClient
    monkeypatch.setattr(browser.httpx, "AsyncClient", lambda **kwargs: client_type(transport=httpx.MockTransport(handler), **kwargs))
    with pytest.raises(HTTPException) as exc:
        await browser._browserbase("POST", "sessions", payload={"projectId": "project-test"})
    assert exc.value.status_code == 503
    assert "provider-secret-test" not in str(exc.value.detail) and "wss://" not in str(exc.value.detail)
    assert requests[0].headers["x-bb-api-key"] == "provider-secret-test"
    assert str(requests[0].url) == "https://api.browserbase.com/v1/sessions"


@pytest.mark.parametrize("url", ["https://evil.example/session", "http://browserbase.com/", "https://browserbase.com.evil.example/", "https://name:pass@browserbase.com/", "https://browserbase.com:444/"])
def test_liveview_url_cannot_redirect_user_to_other_origins(url):
    with pytest.raises(HTTPException):
        browser._provider_url(url)


@pytest.mark.asyncio
async def test_takeover_returns_short_lived_capability_only_after_job_pause(monkeypatch):
    current = session(provider="browserbase")
    order = []
    async def provider(method, path, **kwargs):
        order.append((method, path, kwargs))
        return {"debuggerFullscreenUrl": "https://www.browserbase.com/devtools?token=short-secret"}
    async def rpc(name, payload):
        assert not current.manual
        order.append((name, payload))
        return {}
    monkeypatch.setattr(browser, "_browserbase", provider)
    monkeypatch.setattr(agent, "_rpc", rpc)
    result = await browser.takeover(OWNER, JOB)
    assert current.manual and result["expires_in"] == 60
    assert order[0][2]["params"] == {"expiresIn": 60}
    assert order[1][0] == "despacho_agent_browser_manual" and order[1][1]["p_manual"]
    assert "short-secret" not in json.dumps(order[1])


@pytest.mark.asyncio
async def test_takeover_database_failure_never_hands_out_control(monkeypatch):
    current = session(provider="browserbase")
    monkeypatch.setattr(browser, "_browserbase", AsyncMock(return_value={"debuggerFullscreenUrl": "https://www.browserbase.com/devtools?token=short-secret"}))
    monkeypatch.setattr(agent, "_rpc", AsyncMock(side_effect=HTTPException(409, "El paso está ejecutándose")))
    with pytest.raises(HTTPException):
        await browser.takeover(OWNER, JOB)
    assert not current.manual


@pytest.mark.asyncio
async def test_resume_failure_keeps_manual_pause_and_never_claims_success(monkeypatch):
    current = session(provider="browserbase", manual=True)
    monkeypatch.setattr(agent, "_rpc", AsyncMock(side_effect=HTTPException(503, "Sin base de datos")))
    with pytest.raises(HTTPException):
        await browser.resume(OWNER, JOB)
    assert current.manual
    monkeypatch.setattr(agent, "_rpc", AsyncMock(return_value={}))
    state = await browser.resume(OWNER, JOB)
    assert not current.manual and "no presume" in state["message"]


@pytest.mark.asyncio
async def test_resume_keeps_agent_paused_until_manual_popup_is_closed(monkeypatch):
    current = session(provider="browserbase", manual=True)
    current.context.pages = [current.page, types.SimpleNamespace(is_closed=lambda: False)]
    rpc = AsyncMock()
    monkeypatch.setattr(agent, "_rpc", rpc)
    with pytest.raises(HTTPException) as exc:
        await browser.resume(OWNER, JOB)
    assert exc.value.status_code == 409 and current.manual
    rpc.assert_not_awaited()
    current.page.evaluate.assert_not_awaited()


@pytest.mark.asyncio
async def test_cross_owner_session_cannot_be_observed():
    current = session(provider="browserbase")
    state = await browser.get_state(OTHER, JOB)
    assert state["active"] is False
    current.page.evaluate.assert_not_awaited()


@pytest.mark.asyncio
async def test_download_is_bound_to_current_provider_session(monkeypatch):
    session(provider="browserbase")
    provider = AsyncMock(return_value={"downloads": [{"id": DOWNLOAD, "filename": "constancia.pdf", "sessionId": str(uuid4())}]})
    monkeypatch.setattr(browser, "_browserbase", provider)
    with pytest.raises(HTTPException) as exc:
        await browser.download(OWNER, JOB, DOWNLOAD)
    assert exc.value.status_code == 502 and provider.await_count == 1
    provider.return_value = {"downloads": []}
    with pytest.raises(HTTPException) as exc:
        await browser.download(OWNER, JOB, DOWNLOAD)
    assert exc.value.status_code == 404 and provider.await_count == 2


@pytest.mark.asyncio
async def test_close_owner_revokes_only_that_accounts_remote_capabilities(monkeypatch):
    current = session(provider="browserbase")
    untouched = copy.copy(current)
    untouched.owner, untouched.job = OTHER, str(uuid4())
    browser._sessions[(OTHER, untouched.job)] = untouched
    provider = AsyncMock(return_value={})
    monkeypatch.setattr(browser, "_browserbase", provider)
    await browser.close_owner(OWNER)
    assert (OWNER, JOB) not in browser._sessions and (OTHER, untouched.job) in browser._sessions
    provider.assert_awaited_once_with("POST", "sessions/" + REMOTE, payload={"status": "REQUEST_RELEASE"})


@pytest.mark.asyncio
async def test_real_managed_adapter_disables_recording_and_replaces_sessions_atomically(config, monkeypatch):
    config.DESPACHO_BROWSER_PROVIDER = "browserbase"
    monkeypatch.setattr(browser, "status", lambda: {"configured": True})
    monkeypatch.setattr(browser, "resolve_public", AsyncMock(return_value="93.184.216.34"))
    clients, contexts, payloads = [], [], []
    async def provider(method, path, **kwargs):
        payloads.append((method, path, kwargs))
        return {"id": REMOTE, "connectUrl": "wss://connect.browserbase.com?apiKey=do-not-expose"}
    monkeypatch.setattr(browser, "_browserbase", provider)
    async def start():
        page = types.SimpleNamespace(evaluate=AsyncMock(side_effect=lambda *_: page_state()), goto=AsyncMock(),
            on=lambda *_: None, set_default_timeout=lambda *_: None)
        context = types.SimpleNamespace(pages=[page], new_cdp_session=AsyncMock(return_value=types.SimpleNamespace(send=AsyncMock())),
            clear_permissions=AsyncMock(), route=AsyncMock(), route_web_socket=AsyncMock(), add_init_script=AsyncMock(), on=lambda *_: None, close=AsyncMock())
        contexts.append(context)
        remote_browser = types.SimpleNamespace(contexts=[context], close=AsyncMock())
        return types.SimpleNamespace(chromium=types.SimpleNamespace(connect_over_cdp=AsyncMock(return_value=remote_browser)), stop=AsyncMock())
    package = types.ModuleType("playwright")
    module = types.ModuleType("playwright.async_api")
    module.async_playwright = lambda: types.SimpleNamespace(start=start)
    monkeypatch.setitem(sys.modules, "playwright", package)
    monkeypatch.setitem(sys.modules, "playwright.async_api", module)
    def make_client(**_):
        instance = types.SimpleNamespace(aclose=AsyncMock())
        clients.append(instance)
        return instance
    monkeypatch.setattr(browser.httpx, "AsyncClient", make_client)
    results = await asyncio.gather(browser.open_session(OWNER, JOB, URL, [URL]), browser.open_session(OWNER, JOB, URL, [URL]))
    assert len(browser._sessions) == 1 and contexts[0].close.await_count == 1 and contexts[1].close.await_count == 0
    created = next(p for m, path, p in payloads if path == "sessions")["payload"]
    assert created["keepAlive"] is False
    assert created["browserSettings"]["recordSession"] is False and created["browserSettings"]["logSession"] is False
    assert created["browserSettings"]["solveCaptchas"] is False
    assert created["browserSettings"]["allowedDomains"] == [HOST]
    assert "do-not-expose" not in json.dumps(results)
    assert contexts[1].route.await_count == 1 and contexts[1].route_web_socket.await_count == 1
    assert "serviceWorker" in contexts[1].add_init_script.call_args.kwargs["script"]
