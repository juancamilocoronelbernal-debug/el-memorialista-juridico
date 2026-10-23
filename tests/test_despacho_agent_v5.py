"""Review boundaries and durable agent behavior with controlled providers.

These tests do not claim deployment or live-provider availability. PostgreSQL
RPC/role behavior is exercised separately by the database integration suite.
"""
import asyncio
import copy
import json
import types
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI, HTTPException

from app.routers import despacho_agent as routes
from app.services import despacho_agent as agent, despacho_browser as browser

OWNER, OTHER, JOB, DOC = [str(uuid4()) for _ in range(4)]
URL = "https://corteconstitucional.gov.co/relatoria/"


@pytest.fixture
def config(monkeypatch):
    settings = types.SimpleNamespace(SUPABASE_URL="https://project.example.test", SUPABASE_ANON_KEY="anon-test",
        SUPABASE_SERVICE_ROLE_KEY="service-test", GEMINI_API_KEY="gemini-test", GROQ_API_KEY="",
        DESPACHO_AGENT_WORKER_ENABLED=False, DESPACHO_AGENT_POLL_SECONDS=30,
        DESPACHO_BROWSER_ENABLED=False, DESPACHO_BROWSER_PROVIDER="local", DESPACHO_BROWSER_EXECUTABLE="",
        DESPACHO_BROWSER_ALLOWED_HOSTS="corteconstitucional.gov.co,funcionpublica.gov.co",
        DESPACHO_MONITOR_ALLOWED_HOSTS="corteconstitucional.gov.co,funcionpublica.gov.co",
        DESPACHO_BROWSER_SESSION_TTL_SECONDS=900, BROWSERBASE_API_KEY="", BROWSERBASE_PROJECT_ID="")
    monkeypatch.setattr(agent, "get_settings", lambda: settings)
    monkeypatch.setattr(browser, "get_settings", lambda: settings)
    from app.services import despacho_fetch
    monkeypatch.setattr(despacho_fetch, "get_settings", lambda: settings)
    return settings


def make_job(tool="analyze", *, state="approved", results=None):
    plan = agent.normalize_plan([{"tool": tool, "title": "Revisar expediente", "instruction": "Identifica hechos documentados."}], [])
    return {"id": JOB, "owner_id": OWNER, "title": "Encargo", "objective": "Revisa el contrato", "plan": plan,
        "plan_hash": agent.plan_hash(plan), "approved_hash": agent.plan_hash(plan), "state": state, "version": 2,
        "cursor": 0, "results": results or [], "document_ids": [DOC], "matter_id": None,
        "playbook_id": None, "allowed_urls": [], "last_error": "", "manual_control": False}


@pytest.mark.parametrize("tool", ["eval", "shell", "send_email", "submit_court", "sign_document", "delete_document", "upload_private_files"])
def test_model_cannot_introduce_arbitrary_tools(config, tool):
    with pytest.raises(HTTPException) as exc:
        agent.normalize_plan([{"tool": tool, "title": "Ejecutar", "instruction": "hazlo"}], [])
    assert exc.value.status_code == 422


def test_web_plan_requires_exact_preapproved_url(config):
    with pytest.raises(HTTPException):
        agent.normalize_plan([{"tool": "fetch_source", "title": "Leer", "url": URL + "otra"}], [URL])
    plan = agent.normalize_plan([{"tool": "browser_read", "title": "Leer", "url": URL}], [URL])
    assert plan[0]["url"] == URL


def test_save_step_cannot_precede_a_real_text_result(config):
    with pytest.raises(HTTPException):
        agent.normalize_plan([{"tool": "save_document", "title": "Guardar"}], [])


def test_plan_hash_covers_the_actual_reviewed_instruction(config):
    plan = agent.normalize_plan([{"tool": "analyze", "title": "Revisar", "instruction": "hechos"}], [])
    changed = copy.deepcopy(plan)
    changed[0]["instruction"] = "Enviar a un tercero"
    assert agent.plan_hash(plan) != agent.plan_hash(changed)
    assert agent.plan_hash(plan) == agent.plan_hash(copy.deepcopy(plan))


def test_result_coverage_cannot_disappear_when_truncated():
    result = agent._bound_result({"answer": "a" * 90_000, "warnings": [], "internal_secret": "NEVER"})
    assert len(result["answer"]) == 80_000 and result["warnings"]
    assert "internal_secret" not in result


def test_public_job_never_returns_internal_lease_or_other_account():
    row = make_job()
    row["lease_token"] = "private-server-lease"
    assert "lease_token" not in agent.public_job(row, OWNER)
    with pytest.raises(HTTPException):
        agent.public_job(row, OTHER)


@pytest.mark.asyncio
async def test_get_job_always_filters_owner_before_display(monkeypatch):
    database = AsyncMock(return_value=[make_job()])
    monkeypatch.setattr(agent.store, "db_request", database)
    await agent.get_job(OWNER, "jwt", JOB)
    assert database.call_args.kwargs["params"]["owner_id"] == "eq." + OWNER
    with pytest.raises(HTTPException):
        await agent.get_job(OTHER, "jwt-b", JOB)


@pytest.mark.asyncio
async def test_planning_verifies_document_ownership_before_provider(config, monkeypatch):
    context = AsyncMock(side_effect=HTTPException(404, "No existe"))
    provider = AsyncMock()
    monkeypatch.setattr(agent.ai, "load_context", context)
    monkeypatch.setattr(agent.ai, "_call_provider", provider)
    with pytest.raises(HTTPException):
        await agent.create_job(OWNER, "jwt", {"objective": "Consulta", "document_ids": [DOC]})
    provider.assert_not_awaited()


@pytest.mark.asyncio
async def test_planning_stores_reviewable_draft_and_does_not_execute(config, monkeypatch):
    context = AsyncMock(return_value=([{"id": DOC, "title": "Contrato", "data": {"text": "SECRET_DOCUMENT_BODY"}}], None, "", []))
    provider = AsyncMock(return_value={"answer": json.dumps({"steps": [{"tool": "analyze", "title": "Analizar", "instruction": "Hechos"}]})})
    rows = []
    async def service(method, path, **kwargs):
        rows.append(kwargs["json"])
        return [kwargs["json"]]
    execute = AsyncMock()
    monkeypatch.setattr(agent.ai, "load_context", context)
    monkeypatch.setattr(agent.ai, "_call_provider", provider)
    monkeypatch.setattr(agent, "_service", service)
    monkeypatch.setattr(agent, "_execute_tool", execute)
    job = await agent.create_job(OWNER, "jwt", {"objective": "Consulta", "document_ids": [DOC]})
    assert job["state"] == "draft" and job["cursor"] == 0
    assert rows[0]["owner_id"] == OWNER and rows[0]["results"] == []
    assert "SECRET_DOCUMENT_BODY" not in provider.call_args.args[0][0][1]
    execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_missing_service_configuration_does_not_call_ai(config, monkeypatch):
    config.SUPABASE_SERVICE_ROLE_KEY = ""
    provider = AsyncMock()
    monkeypatch.setattr(agent.ai, "_call_provider", provider)
    with pytest.raises(HTTPException) as exc:
        await agent.create_job(OWNER, "jwt", {"objective": "Consulta"})
    assert exc.value.status_code == 503
    provider.assert_not_awaited()


@pytest.mark.asyncio
async def test_claim_rejection_blocks_ai_and_any_side_effect(config, monkeypatch):
    monkeypatch.setattr(agent, "get_job", AsyncMock(return_value=agent.public_job(make_job(state="draft"), OWNER)))
    monkeypatch.setattr(agent, "_rpc", AsyncMock(side_effect=HTTPException(409, "No aprobado")))
    execute = AsyncMock()
    monkeypatch.setattr(agent, "_execute_tool", execute)
    with pytest.raises(HTTPException):
        await agent.execute_step(OWNER, "jwt", JOB, 2)
    execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_changed_plan_is_not_executed_even_after_a_claim(config, monkeypatch):
    row = make_job()
    row["plan"][0]["instruction"] = "CAMBIO NO APROBADO"
    monkeypatch.setattr(agent, "get_job", AsyncMock(return_value=agent.public_job(row, OWNER)))
    calls = []
    async def rpc(name, payload):
        calls.append((name, payload))
        return row
    monkeypatch.setattr(agent, "_rpc", rpc)
    execute = AsyncMock()
    monkeypatch.setattr(agent, "_execute_tool", execute)
    await agent.execute_step(OWNER, "jwt", JOB, 2)
    execute.assert_not_awaited()
    assert "no coincide" in calls[1][1]["p_error"]


@pytest.mark.asyncio
async def test_provider_error_is_a_failed_step_not_fake_completion(config, monkeypatch):
    row = make_job()
    monkeypatch.setattr(agent, "get_job", AsyncMock(return_value=agent.public_job(row, OWNER)))
    records = []
    async def rpc(name, payload):
        if name.endswith("finish_step"):
            records.append(payload)
            return {**row, "state": "failed", "last_error": payload["p_error"], "version": 4}
        return row
    monkeypatch.setattr(agent, "_rpc", rpc)
    monkeypatch.setattr(agent, "_execute_tool", AsyncMock(side_effect=HTTPException(503, "Sin cuota")))
    result = await agent.execute_step(OWNER, "jwt", JOB, 2)
    assert result["state"] == "failed" and result["cursor"] == 0
    assert records[0]["p_error"] == "Sin cuota" and records[0]["p_result"]["result"] == {}


@pytest.mark.asyncio
async def test_simultaneous_step_calls_only_execute_the_winning_claim(config, monkeypatch):
    row = make_job()
    monkeypatch.setattr(agent, "get_job", AsyncMock(return_value=agent.public_job(row, OWNER)))
    claimed = False
    async def rpc(name, payload):
        nonlocal claimed
        if name.endswith("claim_step"):
            if claimed:
                raise HTTPException(409, "Already claimed")
            claimed = True
            return row
        return {**row, "state": "completed", "cursor": 1}
    execute = AsyncMock(return_value={"answer": "Resultado"})
    monkeypatch.setattr(agent, "_rpc", rpc)
    monkeypatch.setattr(agent, "_execute_tool", execute)
    results = await asyncio.gather(agent.execute_step(OWNER, "jwt", JOB, 2), agent.execute_step(OWNER, "jwt", JOB, 2), return_exceptions=True)
    assert execute.await_count == 1 and sum(isinstance(r, HTTPException) for r in results) == 1


@pytest.mark.asyncio
async def test_research_does_not_send_private_previous_results_in_search_question(config, monkeypatch):
    job = make_job()
    job["results"] = [{"step_id": "step-1", "tool": "analyze", "result": {"answer": "PRIVATE_PREVIOUS_TEXT"}}]
    chat = AsyncMock(return_value={"answer": "Fuentes"})
    monkeypatch.setattr(agent.ai, "chat", chat)
    await agent._execute_tool(OWNER, "jwt", job, {"tool": "research", "instruction": "Criterio público", "title": "Investigar"})
    request = chat.call_args.args[2]
    assert request["message"] == "Criterio público" and request["mode"] == "research"
    assert "PRIVATE_PREVIOUS_TEXT" not in request["message"]


@pytest.mark.asyncio
async def test_saved_output_retry_reuses_existing_document(config, monkeypatch):
    job = make_job()
    job["results"] = [{"step_id": "step-1", "tool": "draft", "result": {"answer": "Texto aprobado para revisión"}}]
    existing = {"id": DOC, "data": {"agent_job_id": JOB, "text": "Texto aprobado para revisión"}}
    monkeypatch.setattr(agent.store, "fetch_item", AsyncMock(return_value=existing))
    create = AsyncMock()
    monkeypatch.setattr(agent.store, "create_item", create)
    result = await agent._execute_tool(OWNER, "jwt", job, {"id": "step-2", "tool": "save_document", "title": "Borrador"})
    assert result["document_id"]
    create.assert_not_awaited()


@pytest.mark.asyncio
async def test_saved_output_retry_never_overwrites_a_user_edit(config, monkeypatch):
    job = make_job()
    job["results"] = [{"step_id": "step-1", "tool": "draft", "result": {"answer": "Texto IA"}}]
    monkeypatch.setattr(agent.store, "fetch_item", AsyncMock(return_value={"data": {"agent_job_id": JOB, "text": "Texto editado por abogada"}}))
    with pytest.raises(HTTPException) as exc:
        await agent._execute_tool(OWNER, "jwt", job, {"id": "step-2", "tool": "save_document", "title": "Borrador"})
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_recurring_jobs_reject_browser_execution(config, monkeypatch):
    row = make_job()
    row["plan"] = [{"tool": "browser_read", "title": "Abrir", "url": URL}]
    monkeypatch.setattr(agent, "get_job", AsyncMock(return_value=row))
    rpc = AsyncMock()
    monkeypatch.setattr(agent, "_rpc", rpc)
    with pytest.raises(HTTPException):
        await agent.create_schedule(OWNER, "jwt", {"job_id": JOB, "interval_minutes": 60})
    rpc.assert_not_awaited()


@pytest.mark.parametrize("value", ["2026-01-01T10:00:00", "not-a-date", "2000-01-01T10:00:00Z"])
def test_schedule_requires_future_aware_time(value):
    with pytest.raises(HTTPException):
        agent.schedule_time(value, 60)


def test_schedule_time_preserves_the_requested_instant():
    future = datetime.now(timezone.utc) + timedelta(days=2)
    assert datetime.fromisoformat(agent.schedule_time(future.isoformat(), 60)) == future


@pytest.fixture
def api(monkeypatch):
    app = FastAPI()
    app.include_router(routes.router)
    monkeypatch.setattr(routes, "identity", AsyncMock(return_value=(OWNER, "jwt")))
    monkeypatch.setattr(routes.limitador, "verificar", lambda *a, **k: None)
    return app


@pytest.mark.asyncio
async def test_unknown_credential_fields_are_rejected_before_browser(api, monkeypatch):
    act = AsyncMock()
    monkeypatch.setattr(browser, "propose", act)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=api), base_url="http://test") as client:
        response = await client.post(f"/api/despacho/agent/jobs/{JOB}/browser/propose", json={"action": "fill", "ref": "c1", "value": "x", "password": "never-accepted"})
    assert response.status_code == 422
    act.assert_not_awaited()


@pytest.mark.asyncio
async def test_browser_route_rejects_another_owners_job_before_observing(api, monkeypatch):
    monkeypatch.setattr(agent, "get_job", AsyncMock(side_effect=HTTPException(404, "No existe")))
    observe = AsyncMock()
    monkeypatch.setattr(browser, "get_state", observe)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=api), base_url="http://test") as client:
        response = await client.get(f"/api/despacho/agent/jobs/{JOB}/browser")
    assert response.status_code == 404
    observe.assert_not_awaited()


@pytest.mark.asyncio
async def test_plan_edit_preserves_optimistic_version_contract(api, monkeypatch):
    edit = AsyncMock(return_value={"version": 6, "state": "draft"})
    monkeypatch.setattr(agent, "edit_plan", edit)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=api), base_url="http://test") as client:
        response = await client.patch(f"/api/despacho/agent/jobs/{JOB}/plan", json={"expected_version": 5, "steps": [{"tool": "analyze", "title": "Revisión", "instruction": "Hechos"}]})
    assert response.status_code == 200
    assert edit.call_args.args[:4] == (OWNER, "jwt", JOB, 5)
