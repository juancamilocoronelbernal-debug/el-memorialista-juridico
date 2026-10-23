"""Automation quota integration and task-local owner context, without providers."""
import asyncio
import types
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.services import despacho_quotas as quotas, despacho_agent as agent

OWNER, OTHER, JOB = [str(uuid4()) for _ in range(3)]


@pytest.fixture
def config(monkeypatch):
    s=types.SimpleNamespace(SUPABASE_URL="https://project.example.test", SUPABASE_SERVICE_ROLE_KEY="server-secret",
        DESPACHO_AUTOMATION_DAILY_USER_CALLS=100, DESPACHO_AUTOMATION_DAILY_GLOBAL_CALLS=1000)
    monkeypatch.setattr(quotas, "get_settings", lambda:s)
    return s


@pytest.mark.asyncio
async def test_interactive_calls_do_not_reserve_an_automation_budget(monkeypatch):
    db=AsyncMock()
    monkeypatch.setattr(quotas.store,"db_request",db)
    assert await quotas.reserve_for_call() is None
    db.assert_not_awaited()


def test_scope_always_restores_owner_even_when_work_fails():
    assert quotas.automation_owner.get() is None
    with pytest.raises(RuntimeError):
        with quotas.automation_scope(OWNER):
            assert quotas.automation_owner.get()==OWNER
            with quotas.automation_scope(OTHER):
                assert quotas.automation_owner.get()==OTHER
            assert quotas.automation_owner.get()==OWNER
            raise RuntimeError("failed work")
    assert quotas.automation_owner.get() is None


@pytest.mark.asyncio
async def test_reservation_is_a_service_rpc_with_configured_owner_limits(config,monkeypatch):
    db=AsyncMock(return_value={"allowed":True,"user_used":1,"global_used":1})
    monkeypatch.setattr(quotas.store,"db_request",db)
    with quotas.automation_scope(OWNER):
        result=await quotas.reserve_for_call()
    assert result["allowed"]
    db.assert_awaited_once_with("POST","rpc/despacho_automation_reserve","server-secret",service=True,
        json={"p_owner":OWNER,"p_user_limit":100,"p_global_limit":1000})


@pytest.mark.asyncio
async def test_parallel_automations_keep_their_own_account_context(config,monkeypatch):
    seen=[]
    async def db(*_,**kwargs):
        await asyncio.sleep(0)
        seen.append((quotas.automation_owner.get(),kwargs["json"]["p_owner"]))
        return {"allowed":True}
    monkeypatch.setattr(quotas.store,"db_request",db)
    async def work(owner):
        with quotas.automation_scope(owner):
            await asyncio.sleep(0)
            await quotas.reserve_for_call()
    await asyncio.gather(work(OWNER),work(OTHER))
    assert set(seen)=={(OWNER,OWNER),(OTHER,OTHER)} and quotas.automation_owner.get() is None


@pytest.mark.asyncio
async def test_denied_budget_blocks_call_with_utc_retry_delay(config,monkeypatch):
    tomorrow=(datetime.now(timezone.utc)+timedelta(days=1)).replace(hour=0,minute=0,second=0,microsecond=0)
    monkeypatch.setattr(quotas.store,"db_request",AsyncMock(return_value={"allowed":False,"scope":"user","reset_at":tomorrow.isoformat()}))
    with quotas.automation_scope(OWNER),pytest.raises(HTTPException) as exc:
        await quotas.reserve_for_call()
    assert exc.value.status_code==429 and "00:00 UTC" in exc.value.detail
    assert 1<=int(exc.value.headers["Retry-After"])<=86400


@pytest.mark.parametrize("response",[None,[],{}, {"allowed":"true"}])
@pytest.mark.asyncio
async def test_unconfirmed_reservation_fails_closed(config,monkeypatch,response):
    monkeypatch.setattr(quotas.store,"db_request",AsyncMock(return_value=response))
    with quotas.automation_scope(OWNER),pytest.raises(HTTPException) as exc:
        await quotas.reserve_for_call()
    assert exc.value.status_code==503


@pytest.mark.asyncio
async def test_missing_service_key_never_starts_a_billed_request(config,monkeypatch):
    config.SUPABASE_SERVICE_ROLE_KEY=""
    db=AsyncMock()
    monkeypatch.setattr(quotas.store,"db_request",db)
    with quotas.automation_scope(OWNER),pytest.raises(HTTPException) as exc:
        await quotas.reserve_for_call()
    assert exc.value.status_code==503
    db.assert_not_awaited()


@pytest.mark.parametrize("internal",[False,True])
@pytest.mark.asyncio
async def test_agent_only_marks_background_execution_as_automation(monkeypatch,internal):
    plan=[{"id":"step-1","tool":"analyze","title":"Analizar","instruction":"Hechos"}]
    job={"id":JOB,"owner_id":OWNER,"title":"Encargo","objective":"Revisar","state":"approved","version":2,
         "plan":plan,"plan_hash":agent.plan_hash(plan),"approved_hash":agent.plan_hash(plan),"cursor":0,"results":[],"document_ids":[]}
    monkeypatch.setattr(agent,"get_job",AsyncMock(return_value=job))
    monkeypatch.setattr(agent,"_rpc",AsyncMock(return_value=job))
    seen=[]
    async def execute(*_):
        seen.append(quotas.automation_owner.get())
        return {"answer":"Resultado"}
    monkeypatch.setattr(agent,"_execute_tool",execute)
    await agent.execute_step(OWNER,"server" if internal else "user",JOB,2,internal=internal)
    assert seen==[OWNER if internal else None] and quotas.automation_owner.get() is None
