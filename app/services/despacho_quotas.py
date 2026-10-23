"""Durable UTC daily quotas for scheduled/automatic AI work.

One unit reserves one logical model or embedding call, including failed
attempts. Provider fallbacks, batch size and tokens vary; these are not exact
financial limits. Interactive endpoints retain their own request limiter.
The owner is task-local, never inferred from an unverified request or saved JWT.
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone

from fastapi import HTTPException

from app.config import get_settings
from app.services import despacho_store as store

automation_owner: ContextVar[str | None] = ContextVar("memorialista_automation_owner", default=None)


@contextmanager
def automation_scope(owner: str):
    """Bind the already-verified owner to this task and its child tasks."""
    token = automation_owner.set(store.uuid_text(owner))
    try:
        yield
    finally:
        automation_owner.reset(token)


async def reserve_for_call() -> dict | None:
    owner = automation_owner.get()
    if owner is None:
        return None
    owner = store.uuid_text(owner)
    settings = get_settings()
    key = settings.SUPABASE_SERVICE_ROLE_KEY.strip()
    if not key or not settings.SUPABASE_URL:
        raise HTTPException(503, "La automatización necesita almacenamiento y una cuota duradera configurados antes de consumir IA.")
    user_limit = getattr(settings, "DESPACHO_AUTOMATION_DAILY_USER_CALLS", 100)
    global_limit = getattr(settings, "DESPACHO_AUTOMATION_DAILY_GLOBAL_CALLS", 1000)
    if any(type(value) is not int or not 0 <= value <= 1_000_000 for value in (user_limit, global_limit)):
        raise HTTPException(503, "Los límites diarios de automatización no son válidos.")
    result = await store.db_request("POST", "rpc/despacho_automation_reserve", key, service=True,
        json={"p_owner": owner, "p_user_limit": user_limit, "p_global_limit": global_limit})
    if isinstance(result, list) and len(result) == 1:
        result = result[0]
    if not isinstance(result, dict) or type(result.get("allowed")) is not bool:
        raise HTTPException(503, "No se confirmó la reserva de cuota. La automatización no llamó a la IA.")
    if result["allowed"]:
        return result
    retry = 3600
    try:
        reset = datetime.fromisoformat(str(result["reset_at"]).replace("Z", "+00:00"))
        if reset.tzinfo is not None:
            retry = max(1, min(86400, int((reset - datetime.now(timezone.utc)).total_seconds()) + 1))
    except (KeyError, ValueError, TypeError):
        pass
    message = ("Esta cuenta alcanzó su cuota diaria de llamadas automáticas a IA." if result.get("scope") == "user" else
               "El servicio alcanzó su cuota diaria de llamadas automáticas a IA.")
    raise HTTPException(429, message + " Se restablece a las 00:00 UTC; este intento no se ejecutó.", headers={"Retry-After": str(retry)})
