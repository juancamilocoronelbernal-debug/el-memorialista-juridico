"""Authenticated endpoints for reviewed assignments and supervised browsing."""
from __future__ import annotations

from typing import Literal
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Query, Request, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.services import despacho_agent as agent, despacho_browser as browser
from app.services.limites import limitador, verificar_acceso
from app.services.sesiones import token_bearer

router = APIRouter(prefix="/api/despacho/agent", tags=["Agente supervisado"])


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CreateJob(StrictModel):
    objective: str = Field(min_length=1, max_length=12_000)
    document_ids: list[UUID] = Field(default_factory=list, max_length=20)
    matter_id: UUID | None = None
    playbook_id: UUID | None = None
    allowed_urls: list[str] = Field(default_factory=list, max_length=8)

    @field_validator("objective")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Describe el encargo.")
        return value.strip()


class Version(StrictModel):
    expected_version: int = Field(ge=1)


class PlanStep(StrictModel):
    id: str | None = None
    tool: str = Field(min_length=1, max_length=40)
    title: str = Field(min_length=1, max_length=200)
    instruction: str = Field(default="", max_length=6000)
    url: str | None = Field(None, max_length=2048)


class EditPlan(Version):
    steps: list[PlanStep] = Field(min_length=1, max_length=agent.MAX_STEPS)


class CreateSchedule(StrictModel):
    job_id: UUID
    interval_minutes: int = Field(ge=60, le=10080)
    next_run_at: str | None = Field(None, max_length=50)
    enabled: bool = True


class UpdateSchedule(Version):
    interval_minutes: int | None = Field(None, ge=60, le=10080)
    next_run_at: str | None = Field(None, max_length=50)
    enabled: bool | None = None


class BrowserAction(StrictModel):
    action: Literal["click", "fill"]
    ref: str = Field(pattern=r"^c[0-9]{1,3}$")
    value: str = Field(default="", max_length=2000)


class BrowserApproval(Version):
    action_id: UUID


class BrowserOpen(StrictModel):
    url: str = Field(max_length=2048)


async def identity(request: Request) -> tuple[str, str]:
    user = await verificar_acceso(request)
    return user["id"], token_bearer(request)


@router.get("/status")
async def status(request: Request):
    await identity(request)
    return agent.status()


@router.get("/jobs")
async def jobs(request: Request, limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0, le=100_000)):
    owner, token = await identity(request)
    return await agent.list_jobs(owner, token, limit=limit, offset=offset)


@router.post("/jobs", status_code=201)
async def create(payload: CreateJob, request: Request):
    owner, token = await identity(request)
    limitador.verificar(request, "redactar", user_id=owner)
    return await agent.create_job(owner, token, payload.model_dump(mode="json"))


@router.get("/jobs/{job_id}")
async def job(job_id: UUID, request: Request):
    owner, token = await identity(request)
    return await agent.get_job(owner, token, str(job_id))


@router.patch("/jobs/{job_id}/plan")
async def edit(job_id: UUID, payload: EditPlan, request: Request):
    owner, token = await identity(request)
    return await agent.edit_plan(owner, token, str(job_id), payload.expected_version,
                                 [step.model_dump(exclude_none=True) for step in payload.steps])


@router.post("/jobs/{job_id}/approve")
async def approve(job_id: UUID, payload: Version, request: Request):
    owner, token = await identity(request)
    return await agent.control(owner, token, str(job_id), payload.expected_version, "approve")


@router.post("/jobs/{job_id}/cancel")
async def cancel(job_id: UUID, payload: Version, request: Request):
    owner, token = await identity(request)
    return await agent.control(owner, token, str(job_id), payload.expected_version, "cancel")


@router.post("/jobs/{job_id}/retry")
async def retry(job_id: UUID, payload: Version, request: Request):
    owner, token = await identity(request)
    return await agent.control(owner, token, str(job_id), payload.expected_version, "retry")


@router.post("/jobs/{job_id}/step")
async def step(job_id: UUID, payload: Version, request: Request):
    owner, token = await identity(request)
    limitador.verificar(request, "redactar", user_id=owner)
    return await agent.execute_step(owner, token, str(job_id), payload.expected_version)


@router.get("/jobs/{job_id}/events")
async def events(job_id: UUID, request: Request):
    owner, token = await identity(request)
    return await agent.events(owner, token, str(job_id))


@router.get("/schedules")
async def schedules(request: Request):
    owner, token = await identity(request)
    return await agent.list_schedules(owner, token)


@router.post("/schedules", status_code=201)
async def schedule_create(payload: CreateSchedule, request: Request):
    owner, token = await identity(request)
    return await agent.create_schedule(owner, token, payload.model_dump(mode="json"))


@router.patch("/schedules/{schedule_id}")
async def schedule_update(schedule_id: UUID, payload: UpdateSchedule, request: Request):
    owner, token = await identity(request)
    return await agent.update_schedule(owner, token, str(schedule_id), payload.model_dump(exclude_unset=True))


@router.get("/jobs/{job_id}/browser")
async def browser_state(job_id: UUID, request: Request):
    owner, token = await identity(request)
    await agent.get_job(owner, token, str(job_id))
    return await browser.get_state(owner, str(job_id))


@router.post("/jobs/{job_id}/browser/open")
async def browser_open(job_id: UUID, payload: BrowserOpen, request: Request):
    from fastapi import HTTPException
    owner, token = await identity(request)
    current = await agent.get_job(owner, token, str(job_id))
    if current["state"] in {"draft", "cancelled", "running", "waiting_approval"}:
        raise HTTPException(409, "Aprueba el plan y resuelve la ejecución pendiente antes de abrir el navegador.")
    # Opening a browser requires that exact URL to occur in the approved plan.
    if not any(s["tool"] == "browser_read" and s.get("url") == payload.url for s in current["plan"]):
        raise HTTPException(422, "Esta fuente no tiene un paso de navegación aprobado.")
    return await browser.open_session(owner, str(job_id), payload.url, current["allowed_urls"])


@router.post("/jobs/{job_id}/browser/close")
async def browser_close(job_id: UUID, request: Request):
    owner, token = await identity(request)
    await agent.get_job(owner, token, str(job_id))
    await browser.close_session(owner, str(job_id))
    updated = await agent._rpc("despacho_agent_browser_reset", {"p_owner": owner, "p_job": str(job_id)})
    return {"active": False, "job": agent.public_job(updated, owner)}


@router.get("/jobs/{job_id}/browser/screenshot")
async def browser_screenshot(job_id: UUID, request: Request):
    owner, token = await identity(request)
    await agent.get_job(owner, token, str(job_id))
    return Response(await browser.screenshot(owner, str(job_id)), media_type="image/png", headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})


@router.post("/jobs/{job_id}/browser/propose")
async def browser_propose(job_id: UUID, payload: BrowserAction, request: Request):
    owner, token = await identity(request)
    await agent.get_job(owner, token, str(job_id))
    return await browser.propose(owner, str(job_id), payload.model_dump())


@router.post("/jobs/{job_id}/browser/approve")
async def browser_approve(job_id: UUID, payload: BrowserApproval, request: Request):
    owner, token = await identity(request)
    await agent.get_job(owner, token, str(job_id))
    return await browser.approve(owner, str(job_id), str(payload.action_id), payload.expected_version)


@router.post("/jobs/{job_id}/browser/takeover")
async def browser_takeover(job_id: UUID, request: Request):
    from fastapi.responses import JSONResponse
    owner, token = await identity(request)
    await agent.get_job(owner, token, str(job_id))
    return JSONResponse(await browser.takeover(owner, str(job_id)), headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"})


@router.post("/jobs/{job_id}/browser/resume")
async def browser_resume(job_id: UUID, request: Request):
    owner, token = await identity(request)
    await agent.get_job(owner, token, str(job_id))
    return await browser.resume(owner, str(job_id))


@router.get("/jobs/{job_id}/browser/downloads")
async def browser_downloads(job_id: UUID, request: Request):
    owner, token = await identity(request)
    await agent.get_job(owner, token, str(job_id))
    return await browser.list_downloads(owner, str(job_id))


@router.get("/jobs/{job_id}/browser/downloads/{download_id}")
async def browser_download(job_id: UUID, download_id: UUID, request: Request):
    owner, token = await identity(request)
    await agent.get_job(owner, token, str(job_id))
    content, item = await browser.download(owner, str(job_id), str(download_id))
    from app.routers.despacho_data import _filename
    return Response(content, media_type="application/octet-stream", headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
        "Content-Disposition": "attachment; filename*=UTF-8''" + quote(_filename(item["filename"]))})


@router.post("/jobs/{job_id}/browser/downloads/{download_id}/save")
async def browser_download_save(job_id: UUID, download_id: UUID, request: Request):
    import anyio
    from uuid import NAMESPACE_URL, uuid4, uuid5
    from fastapi import HTTPException
    from app.services import despacho_ai, despacho_store
    from app.routers.despacho_data import _filename
    owner, token = await identity(request)
    current = await agent.get_job(owner, token, str(job_id))
    item_id = str(uuid5(NAMESPACE_URL, "memorialista-download:" + owner + ":" + str(job_id) + ":" + str(download_id)))
    try:
        return await despacho_store.fetch_item(owner, token, item_id, kind="document")
    except HTTPException as exc:
        if exc.status_code != 404:
            raise
    content, item = await browser.download(owner, str(job_id), str(download_id))
    name = _filename(item["filename"])
    parsed = await anyio.to_thread.run_sync(despacho_ai.extract_document, content, name)
    suffix = {"application/pdf": "pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx", "text/markdown": "md"}.get(parsed.get("mime"), "txt")
    path = f"{owner}/{item_id}/{uuid4()}.{suffix}"
    await despacho_store.upload_bytes(owner, token, path, content, parsed["mime"])
    try:
        return await despacho_store.create_item(owner, token, {"kind": "document", "title": name, "matter_id": current.get("matter_id"),
            "data": {**parsed, "filename": name, "storage_path": path, "versions": [], "agent_job_id": str(job_id), "browser_download_id": str(download_id)}}, item_id=item_id)
    except HTTPException:
        try:
            await despacho_store.remove_storage_paths(owner, token, [path])
        except HTTPException:
            pass
        raise
