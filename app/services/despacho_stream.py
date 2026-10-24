"""Transmisión real y progresiva del chat profesional.

El consumidor recibe eventos status/delta/done/error, nunca una simulación
con el texto previamente generado. El contexto privado mantiene los mismos
controles que el endpoint /chat original. Una respuesta parcial NO es final.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime, timezone
from typing import AsyncIterator

import httpx
from fastapi import HTTPException

from app.config import get_settings
from app.services import despacho_ai as ai
from app.services.gemini_service import gemini_service

log = logging.getLogger("memorialista.despacho.stream")


async def parse_provider_sse(lines) -> AsyncIterator[dict]:
    """Lee frames `data:` SSE divididos arbitrariamente en líneas."""
    pending: list[str] = []
    async for raw in lines:
        line = raw.rstrip("\r")
        if not line:
            if pending:
                payload = "\n".join(pending)
                pending.clear()
                if payload == "[DONE]":
                    return
                yield json.loads(payload)
            continue
        if line.startswith("data:"):
            pending.append(line[5:].lstrip(" "))
    if pending:
        payload = "\n".join(pending)
        if payload != "[DONE]":
            yield json.loads(payload)


def _result(answer: str, *, motor, finish: str, usage: dict, metadata, search: bool) -> dict:
    sources, queries, suggestions = ai.grounding_sources(metadata)
    warnings = []
    if finish in {"MAX_TOKENS", "length", "CONTINUATION"} or len(answer) >= ai.MAX_REPLY_CHARS:
        warnings.append("La respuesta alcanzó el límite de salida. Revisa su final antes de utilizarla.")
    if search and not sources:
        warnings.append("La búsqueda web no devolvió fuentes verificables; comprueba el alcance antes de utilizar la respuesta.")
    return {
        "answer": answer,
        "sources": sources,
        "warnings": warnings,
        "provider": motor.proveedor,
        "model": motor.modelo,
        "usage": usage,
        "search_queries": queries,
        "search_suggestions_html": suggestions,
        "search_performed": bool(sources or queries),
        "finish_reason": finish,
    }


async def provider_events(messages: list[tuple[str, str]], *, mode: str, search: bool = False) -> AsyncIterator[dict]:
    """Retransmite deltas del proveedor; sólo cambia de motor antes del primer token.

    El evento interno `provider_done` marca salida válida y completa. Nunca
    presenta una respuesta truncada por error de red como si fuera definitiva.
    """
    motors = gemini_service.candidatos("complex" if mode in {"draft", "analyze", "timeline"} else "default")
    if search:
        motors = [motor for motor in motors if motor.proveedor == "gemini"]
    if not motors:
        raise HTTPException(503, "Configura un proveedor de IA compatible en el servidor.")

    from app.services.despacho_quotas import reserve_for_call
    await reserve_for_call()
    settings = get_settings()
    client = await gemini_service._cliente()
    available, gemini_count = [], 0
    for motor in motors:
        if motor.proveedor == "gemini":
            gemini_count += 1
            if gemini_count > 3:
                continue
        available.append(motor)
    status = 503
    try:
        async with ai.async_timeout(150):
            for motor in available:
                text = ""
                finish = ""
                usage = {}
                metadata = None
                try:
                    if motor.proveedor == "gemini":
                        url = f"{settings.GEMINI_API_BASE.rstrip('/')}/v1beta/models/{motor.modelo}:streamGenerateContent"
                        headers = {**gemini_service._cab_gemini(), "Accept": "text/event-stream"}
                        payload = {
                            "systemInstruction": {"parts": [{"text": ai._system(mode, search=search)}]},
                            "contents": [{"role": role, "parts": [{"text": value}]} for role, value in messages],
                            "generationConfig": {"maxOutputTokens": 16384},
                        }
                        if search:
                            payload["tools"] = [{"googleSearch": {}}]
                        params = {"alt": "sse"}
                    else:
                        url = f"{settings.GROQ_API_BASE.rstrip('/')}/chat/completions"
                        headers = {"Authorization": "Bearer " + settings.GROQ_API_KEY.strip(),
                                   "Content-Type": "application/json", "Accept": "text/event-stream"}
                        payload = {
                            "model": motor.modelo,
                            "messages": [{"role": "system", "content": ai._system(mode)}] + [
                                {"role": "assistant" if role == "model" else "user", "content": value}
                                for role, value in messages
                            ],
                            "max_completion_tokens": min(settings.GROQ_MAX_TOKENS, 8192),
                            "stream": True,
                        }
                        params = None
                    yield {"event": "status", "data": {"stage": "provider", "message": "Generando respuesta…"}}
                    async with client.stream("POST", url, json=payload, headers=headers, params=params,
                                             timeout=httpx.Timeout(90.0, connect=15.0)) as response:
                        if response.status_code != 200:
                            status = response.status_code
                            log.warning("Streaming IA: proveedor=%s status=%s", motor.proveedor, status)
                            if search and status in (400, 403, 429):
                                raise HTTPException(status, "La investigación web no está disponible con la cuota o configuración actual.")
                            continue
                        async for packet in parse_provider_sse(response.aiter_lines()):
                            if not isinstance(packet, dict):
                                continue
                            if motor.proveedor == "gemini":
                                raw_usage = packet.get("usageMetadata") or {}
                                if raw_usage:
                                    usage = {"input_tokens": raw_usage.get("promptTokenCount"),
                                             "output_tokens": raw_usage.get("candidatesTokenCount")}
                                candidates = packet.get("candidates") or []
                                candidate = candidates[0] if candidates else {}
                                finish = candidate.get("finishReason") or finish
                                metadata = candidate.get("groundingMetadata") or metadata
                                parts = (candidate.get("content") or {}).get("parts") or []
                                fragment = "".join(str(part.get("text") or "") for part in parts
                                                   if isinstance(part, dict) and not part.get("thought"))
                            else:
                                raw_usage = packet.get("usage") or {}
                                if raw_usage:
                                    usage = {"input_tokens": raw_usage.get("prompt_tokens"),
                                             "output_tokens": raw_usage.get("completion_tokens")}
                                choices = packet.get("choices") or []
                                choice = choices[0] if choices else {}
                                finish = choice.get("finish_reason") or finish
                                fragment = (choice.get("delta") or {}).get("content") or ""
                                if not isinstance(fragment, str):
                                    fragment = ""
                            if fragment:
                                fragment = fragment[:max(0, ai.MAX_REPLY_CHARS - len(text))]
                                text += fragment
                                if fragment:
                                    yield {"event": "delta", "data": {"text": fragment}}
                            if len(text) >= ai.MAX_REPLY_CHARS:
                                finish = finish or "MAX_TOKENS"
                                break
                    if text.strip() and not finish:
                        raise HTTPException(502, "La conexión terminó sin confirmar el final de la respuesta. No se guardó como completa.")
                    if text.strip():
                        yield {"event": "provider_done", "data": _result(
                            text, motor=motor, finish=finish, usage=usage, metadata=metadata, search=search)}
                        return
                    log.warning("Streaming IA: proveedor=%s sin texto utilizable", motor.proveedor)
                except HTTPException:
                    raise
                except (httpx.HTTPError, ValueError, TypeError, KeyError):
                    log.warning("Streaming IA: fallo en proveedor=%s con salida=%s", motor.proveedor, bool(text))
                    if text:
                        raise HTTPException(502, "El proveedor interrumpió la respuesta. El texto parcial no se guardó como final.") from None
                    continue
    except TimeoutError:
        raise HTTPException(504, "La IA superó el tiempo disponible. No se guardó una respuesta incompleta.") from None
    if status == 429:
        raise HTTPException(429, "El proveedor agotó su cuota. Consulta los límites de consumo.")
    raise HTTPException(503, "No se pudo obtener una respuesta de los modelos configurados.")


async def stream_chat(user_id: str, token: str, request: dict) -> AsyncIterator[dict]:
    """Prepara el mismo contexto que /chat, emite texto real y cierra con metadatos."""
    async with ai.async_timeout(195):
        yield {"event": "status", "data": {"stage": "context", "message": "Preparando contexto autorizado…"}}
        documents, matter, playbook, warnings = await ai.load_context(
            user_id, token, document_ids=request.get("document_ids") or [],
            matter_id=request.get("matter_id"), playbook_id=request.get("playbook_id"))
        message, mode = request["message"], request.get("mode", "general")
        context = ai.build_context(documents, message)
        yield {"event": "status", "data": {"stage": "retrieval", "message": "Recuperando fuentes autorizadas…"}}
        
        # RAG 2.0: Transmisión reactiva de etapas (análisis, recuperación, reranking, selección)
        rag_queue = asyncio.Queue()
        async def on_rag_progress(stage: str, msg: str):
            await rag_queue.put({"event": "status", "data": {"stage": stage, "message": msg}})

        async def _run_rag():
            try:
                import inspect
                sig = inspect.signature(ai.augment_indexed_context)
                if "on_progress" in sig.parameters:
                    return await ai.augment_indexed_context(user_id, token, request, context, on_progress=on_rag_progress)
                return await ai.augment_indexed_context(user_id, token, request, context)
            except TypeError:
                return await ai.augment_indexed_context(user_id, token, request, context)
            finally:
                await rag_queue.put(None)

        rag_task = asyncio.create_task(_run_rag())
        while True:
            evt = await rag_queue.get()
            if evt is None:
                break
            yield evt
        context = await rag_task
        warnings += context["warnings"]
        history, history_cut = ai._history_messages(request.get("history") or [])
        if history_cut:
            warnings.append("Se utilizó únicamente el historial reciente disponible para esta consulta.")
        research = None
        search = False
        needs_synthesis = False
        if mode == "research":
            needs_synthesis = bool(context["payload"] or matter or playbook or history)
            if needs_synthesis:
                yield {"event": "status", "data": {"stage": "research", "message": "Consultando fuentes web…"}}
                research = await asyncio.wait_for(ai._call_provider([("user", message)], mode="research", search=True), 60)
                warnings.append("La búsqueda web recibió únicamente la consulta actual; no se enviaron archivos privados ni historial.")
            else:
                search = True
        provider_messages = history + [("user", ai._query_payload(message, context, matter, playbook, research))]
        if search:
            provider_messages = [("user", message)]
        complete = None
        async for event in provider_events(provider_messages, mode=mode, search=search):
            if event["event"] == "provider_done":
                complete = event["data"]
            else:
                yield event
        if not complete:
            raise HTTPException(503, "No se obtuvo una respuesta completa del proveedor.")
        if research is not None:
            complete["sources"] = research["sources"]
            complete["search_queries"] = research["search_queries"]
            complete["search_suggestions_html"] = research["search_suggestions_html"]
            complete["search_performed"] = research["search_performed"]
            complete["research_usage"] = research["usage"]
            warnings += research["warnings"]
        complete["sources"] = context["sources"] + complete["sources"]
        valid_refs = {source["id"] for source in complete["sources"]}
        cited_refs = set(re.findall(r"\[((?:D\d+-S\d+)|(?:W\d+)|(?:O\d+-S\d+))\]", complete["answer"]))
        if cited_refs - valid_refs:
            warnings.append("La respuesta contiene referencias no presentes en el contexto: " + ", ".join(sorted(cited_refs - valid_refs)))
        complete["warnings"] = list(dict.fromkeys(warnings + complete["warnings"]))
        complete["coverage"] = context["coverage"]
        from app.services import despacho_rag
        complete["cost_metrics"] = despacho_rag.estimate_tokens_and_cost(
            prompt_chars=context.get("coverage", {}).get("chars_sent", 0),
            input_tokens=complete.get("usage", {}).get("input_tokens"),
            output_tokens=complete.get("usage", {}).get("output_tokens"),
            model=complete.get("model", "gemini-3.6-flash")
        )
        complete["plan"] = [
            {"label": "Preparar contexto autorizado", "status": "completed"},
            {"label": "Consultar fuentes web" if mode == "research" else "Analizar el encargo",
             "status": "completed" if mode != "research" or complete.get("search_performed") else "unverified"},
            {"label": "Revisión y aprobación del abogado", "status": "pending"},
        ]
        yield {"event": "done", "data": complete}
