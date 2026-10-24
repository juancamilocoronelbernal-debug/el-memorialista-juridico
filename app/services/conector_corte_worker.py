"""Trabajador Automático en Segundo Plano para el Conector de la Corte Constitucional (Fase 2.2).

Ejecuta el descubrimiento y sincronización incremental programada sin intervención
de usuario, respetando:
1. Bloqueo distribuido concurrente en Supabase (impide dos trabajadores simultáneos).
2. Conservación estricta de cursores y estado entre ejecuciones.
3. Validación previa obligatoria de 10 puntos (validador_documental_corpus).
4. Ninguna publicación desatendida automática sin autorización previa expresa (auto_publish=False por defecto).
5. Cortesía de red y protección de cuotas de APIs oficiales.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone, timedelta
import logging
from typing import Any, Optional

from app.config import get_settings
from app.services import conector_corte_constitucional as conector

log = logging.getLogger("memorialista.despacho.worker")

# Identificador único de este proceso trabajador
WORKER_INSTANCE_ID = "render_worker_instance"


async def conector_corte_worker():
    """Bucle principal del trabajador programado en segundo plano."""
    log.info("Conector Corte Constitucional: Trabajador en segundo plano iniciado.")
    # Espera inicial de 15 segundos tras el arranque del servidor para estabilizar conexiones
    await asyncio.sleep(15)

    while True:
        try:
            status = await conector.get_connector_status()
            schedule_enabled = bool(status.get("schedule_enabled", False))
            interval_min = int(status.get("schedule_interval_minutes") or 360)
            next_run_str = status.get("next_run_at")

            now = datetime.now(timezone.utc)
            should_run = False

            if schedule_enabled:
                if not next_run_str:
                    should_run = True
                else:
                    try:
                        next_run = datetime.fromisoformat(next_run_str.replace("Z", "+00:00"))
                        if now >= next_run:
                            should_run = True
                    except Exception:
                        should_run = True

            if should_run:
                log.info("Conector Corte: Ejecutando ciclo de sincronización programada...")
                settings = get_settings()
                batch_limit = getattr(settings, "CONECTOR_CORTE_PILOT_MAX_BATCH", 20)
                auto_publish = getattr(settings, "CONECTOR_CORTE_AUTO_PUBLISH_DEFAULT", False)

                try:
                    sync_report = await conector.run_incremental_sync(
                        limit=batch_limit,
                        auto_publish=auto_publish,
                        owner=WORKER_INSTANCE_ID,
                    )
                    log.info(
                        "Conector Corte: Ciclo completado. Descubiertos=%d, Validados=%d, Triage=%d, Publicados=%d",
                        sync_report.get("discovered_count", 0),
                        sync_report.get("validated_count", 0),
                        sync_report.get("triage_count", 0),
                        sync_report.get("published_count", 0),
                    )
                except Exception as ex:
                    log.error("Conector Corte: Error en sincronización programada: %s", ex, exc_info=True)

                # Calcular y programar próxima ejecución
                next_run_time = now + timedelta(minutes=interval_min)
                await conector.update_schedule_metadata(
                    schedule_enabled=True,
                    interval_minutes=interval_min,
                    next_run_at=next_run_time.isoformat(),
                )

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
    )

    if run_now:
        settings = get_settings()
        batch_limit = getattr(settings, "CONECTOR_CORTE_PILOT_MAX_BATCH", 20)
        auto_publish = getattr(settings, "CONECTOR_CORTE_AUTO_PUBLISH_DEFAULT", False)
        report = await conector.run_incremental_sync(
            limit=batch_limit,
            auto_publish=auto_publish,
            owner="admin_manual_trigger",
        )
        return {
            "schedule": updated,
            "immediate_sync_report": report,
        }

    return {"schedule": updated}
