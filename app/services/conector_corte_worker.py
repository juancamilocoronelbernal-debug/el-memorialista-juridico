"""Trabajador Automático en Segundo Plano para el Conector de la Corte Constitucional (Fase 2.2.1).

Fortalecimiento integral:
1. Identificador único por instancia de proceso (evita colisiones entre réplicas).
2. Recuperación ante caídas o reinicios de Render (limpieza de bloqueos huérfanos).
3. Renovación periódica del bloqueo distribuido (heartbeat anti-expiración con fencing token).
4. Persistencia estricta en Supabase (fechas UTC, marcas de agua, avance de lotes).
5. Cola de reintentos con retroceso exponencial para providencias pendientes en Relatoría.
6. Pausa y reanudación administrativa sin pérdida de estado.
7. Independencia total de las comprobaciones de salud de UptimeRobot (pings a /api/health).
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone, timedelta
import logging
import os
import time
from typing import Any, Optional
import uuid

from app.config import get_settings
from app.services import conector_corte_constitucional as conector

log = logging.getLogger("memorialista.despacho.worker")

# Identificador único de este proceso trabajador (PID + UUID + timestamp)
WORKER_INSTANCE_ID = f"worker_{os.getpid()}_{uuid.uuid4().hex[:8]}"


async def conector_corte_worker():
    """Bucle principal del trabajador programado en segundo plano."""
    log.info("Conector Corte Constitucional: Trabajador en segundo plano iniciado (ID: %s).", WORKER_INSTANCE_ID)
    # Espera inicial de 15 segundos tras el arranque para estabilizar conexiones
    await asyncio.sleep(15)

    # 1. Recuperación tras reinicio: limpiar bloqueos huérfanos de instancias anteriores
    try:
        orphan_res = await conector.recover_orphan_locks()
        if orphan_res.get("cleared"):
            log.warning("Conector Corte: Se limpió un bloqueo huérfano anterior: %s", orphan_res)
    except Exception as e:
        log.warning("Conector Corte: Aviso comprobando bloqueos huérfanos al iniciar: %s", e)

    while True:
        try:
            status = await conector.get_connector_status()
            process_status = status.get("process_status", "idle")
            schedule_enabled = bool(status.get("schedule_enabled", False))
            interval_min = int(status.get("schedule_interval_minutes") or 360)
            next_run_str = status.get("next_run_at")

            now = datetime.now(timezone.utc)
            should_run = False

            # Si el proceso está pausado administrativamente, respetar la pausa
            if process_status == "paused" or not schedule_enabled:
                await asyncio.sleep(60)
                continue

            if not next_run_str:
                should_run = True
            else:
                try:
                    clean_str = next_run_str.replace("Z", "+00:00")
                    if clean_str.endswith("+00:00") and "." in clean_str:
                        p = clean_str.split(".")
                        ft = p[1].split("+")
                        clean_str = f"{p[0]}.{ft[0].ljust(6, '0')[:6]}+{ft[1]}"
                    next_run = datetime.fromisoformat(clean_str)
                    if now >= next_run:
                        should_run = True
                except Exception:
                    should_run = True

            if should_run:
                log.info("Conector Corte: Hora de ejecución alcanzada. Iniciando ciclo programado...")
                settings = get_settings()
                batch_limit = int(
                    status.get("batch_limit")
                    or (status.get("details") or {}).get("batch_limit")
                    or getattr(settings, "CONECTOR_CORTE_PILOT_MAX_BATCH", 20)
                )
                auto_publish = getattr(settings, "CONECTOR_CORTE_AUTO_PUBLISH_DEFAULT", False)

                # Programar inmediatamente la próxima ejecución para evitar tormentas de reintentos
                next_run_time = now + timedelta(minutes=interval_min)
                await conector.update_schedule_metadata(
                    schedule_enabled=True,
                    interval_minutes=interval_min,
                    next_run_at=next_run_time.isoformat(),
                )

                # 1. Procesar reintentos pendientes de providencias en trámite editorial
                try:
                    retry_report = await conector.retry_pending_source_rulings(limit=10, owner=WORKER_INSTANCE_ID)
                    if retry_report.get("processed_count", 0) > 0:
                        log.info(
                            "Conector Corte: Reintentos procesados: %d, Recuperadas: %d, Fallidas: %d",
                            retry_report.get("processed_count", 0),
                            retry_report.get("recovered_count", 0),
                            retry_report.get("failed_count", 0),
                        )
                except Exception as ex_retry:
                    log.warning("Conector Corte: Aviso en cola de reintentos: %s", ex_retry)

                # 2. Ejecutar descubrimiento incremental por marcas de agua
                try:
                    sync_report = await conector.run_incremental_sync(
                        limit=batch_limit,
                        auto_publish=auto_publish,
                        owner=WORKER_INSTANCE_ID,
                    )
                    log.info(
                        "Conector Corte: Ciclo completado. Descubiertos=%d, Validados=%d, Triage=%d, Publicados=%d, Reintentos=%d",
                        sync_report.get("discovered_count", 0),
                        sync_report.get("validated_count", 0),
                        sync_report.get("triage_count", 0),
                        sync_report.get("published_count", 0),
                        sync_report.get("pending_source_count", 0),
                    )
                except Exception as ex:
                    log.error("Conector Corte: Error en sincronización programada: %s", ex, exc_info=True)

        except asyncio.CancelledError:
            log.info("Conector Corte: Trabajador cancelado limpiamente por apagado del servidor.")
            break
        except Exception as e:
            log.warning("Conector Corte: Excepción en bucle del trabajador: %s", e)

        # Sondeo periódico cada 60 segundos
        await asyncio.sleep(60)


async def configure_schedule(
    enabled: bool,
    interval_minutes: int = 360,
    run_now: bool = False,
) -> dict:
    """Configura la frecuencia y activación del trabajador programado."""
    now = datetime.now(timezone.utc)
    next_run = now if run_now else (now + timedelta(minutes=interval_minutes))

    updated = await conector.update_schedule_metadata(
        schedule_enabled=enabled,
        interval_minutes=interval_minutes,
        next_run_at=next_run.isoformat() if enabled else None,
        process_status="idle" if enabled else "paused",
    )

    if run_now and enabled:
        settings = get_settings()
        batch_limit = getattr(settings, "CONECTOR_CORTE_PILOT_MAX_BATCH", 20)
        auto_publish = getattr(settings, "CONECTOR_CORTE_AUTO_PUBLISH_DEFAULT", False)
        report = await conector.run_incremental_sync(
            limit=batch_limit,
            auto_publish=auto_publish,
            owner=f"{WORKER_INSTANCE_ID}_manual",
        )
        return {
            "schedule": updated,
            "immediate_sync_report": report,
        }

    return {"schedule": updated}


async def pause_schedule(reason: Optional[str] = None) -> dict:
    """Pausa administrativamente la sincronización automática sin alterar marcas de agua."""
    return await conector.update_schedule_metadata(
        schedule_enabled=False,
        process_status="paused",
    )


async def resume_schedule(run_now: bool = False, interval_minutes: Optional[int] = None) -> dict:
    """Reanuda la sincronización automática respetando el cursor y la marca de agua."""
    status = await conector.get_connector_status()
    interval = interval_minutes or int(status.get("schedule_interval_minutes") or 360)
    now = datetime.now(timezone.utc)
    next_run = now if run_now else (now + timedelta(minutes=interval))

    return await conector.update_schedule_metadata(
        schedule_enabled=True,
        interval_minutes=interval,
        next_run_at=next_run.isoformat(),
        process_status="idle",
    )
