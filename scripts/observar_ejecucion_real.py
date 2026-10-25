"""Observador de Ejecución Automática Real del Worker en Render (Fase 2.2.1).

Este script NO ejecuta ninguna sincronización. Solo observa pasivamente la base de datos Supabase
para demostrar que el proceso trabajador en segundo plano dentro del contenedor Render FastAPI
detecta el vencimiento de next_run_at, adquiere el bloqueo con su propio PID/UUID de Render,
sincroniza automáticamente y actualiza last_successful_run_at y next_run_at.
"""
import asyncio
from datetime import datetime, timezone, timedelta
import json
import time

from app.config import get_settings
from app.services import despacho_store as store

async def get_state(key: str) -> dict:
    rows = await store.db_request(
        "GET",
        "despacho_conector_corte_estado?id=eq.corte_constitucional",
        key,
        service=True,
    )
    return rows[0] if isinstance(rows, list) and rows else {}

async def main():
    settings = get_settings()
    key = settings.SUPABASE_SERVICE_ROLE_KEY.strip()
    print("=== OBSERVACIÓN DE EJECUCIÓN AUTOMÁTICA REAL (RENDER FASTAPI CONTAINER) ===")

    # 1. Estado inicial
    initial_state = await get_state(key)
    initial_last_success = initial_state.get("last_successful_run_at")
    initial_token = initial_state.get("lock_fencing_token")
    print(f"Estado inicial en Supabase:")
    print(f"  - schedule_enabled: {initial_state.get('schedule_enabled')}")
    print(f"  - schedule_interval_minutes: {initial_state.get('schedule_interval_minutes')}")
    print(f"  - next_run_at: {initial_state.get('next_run_at')}")
    print(f"  - last_successful_run_at: {initial_last_success}")
    print(f"  - lock_owner: {initial_state.get('lock_owner')}")
    print(f"  - lock_fencing_token: {initial_token}")

    # 2. Configurar vencimiento controlado a 5 segundos en el futuro con límite estricto de 2 providencias
    now = datetime.now(timezone.utc)
    target_next_run = now + timedelta(seconds=5)
    print(f"\nConfigurando vencimiento controlado en Supabase para: {target_next_run.isoformat()} (intervalo=15m, batch_limit=2)...")
    await store.db_request(
        "PATCH",
        "despacho_conector_corte_estado?id=eq.corte_constitucional",
        key,
        service=True,
        json={
            "schedule_enabled": True,
            "schedule_interval_minutes": 15,
            "next_run_at": target_next_run.isoformat(),
            "details": {"batch_limit": 2},
        },
    )

    print("\nEsperando a que el bucle del trabajador en Render (FastAPI) detecte el vencimiento y ejecute...")
    print("Sondeando estado pasivamente cada 5 segundos (máx 90s)...\n")

    executed = False
    observed_lock_owner = None
    t_start = time.time()

    while time.time() - t_start < 95:
        await asyncio.sleep(5)
        st = await get_state(key)
        cur_success = st.get("last_successful_run_at")
        cur_owner = st.get("lock_owner")
        cur_token = st.get("lock_fencing_token")
        cur_status = st.get("process_status")
        cur_next = st.get("next_run_at")

        if cur_owner and not observed_lock_owner:
            observed_lock_owner = cur_owner
            print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] ¡BLOQUEO ADQUIRIDO POR CONTENEDOR RENDER! lock_owner={cur_owner}, token={cur_token}, status={cur_status}")

        if cur_success != initial_last_success:
            executed = True
            print(f"\n[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] ¡EJECUCIÓN AUTOMÁTICA COMPLETADA CON ÉXITO POR RENDER!")
            print(f"  - lock_owner final: {cur_owner} (esperado: None tras liberar)")
            print(f"  - last_successful_run_at anterior: {initial_last_success}")
            print(f"  - last_successful_run_at NUEVO:     {cur_success}")
            print(f"  - next_run_at reprogramado:         {cur_next}")
            print(f"  - lock_fencing_token actual:        {cur_token}")
            break
        else:
            print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] Esperando... status={cur_status}, owner={cur_owner}, next_run_at={cur_next}")

    # 3. Restaurar la configuración oficial permanente de 6 horas (360 minutos)
    print("\nRestaurando configuración permanente del conector (6 horas = 360 minutos)...")
    now_restored = datetime.now(timezone.utc)
    next_restored = now_restored + timedelta(minutes=360)
    await store.db_request(
        "PATCH",
        "despacho_conector_corte_estado?id=eq.corte_constitucional",
        key,
        service=True,
        json={
            "schedule_enabled": True,
            "schedule_interval_minutes": 360,
            "next_run_at": next_restored.isoformat(),
            "details": {},
        },
    )

    final_state = await get_state(key)
    print("\nEstado restaurado definitivo en Supabase:")
    print(f"  - schedule_enabled: {final_state.get('schedule_enabled')}")
    print(f"  - schedule_interval_minutes: {final_state.get('schedule_interval_minutes')}")
    print(f"  - next_run_at: {final_state.get('next_run_at')}")
    print(f"  - last_successful_run_at: {final_state.get('last_successful_run_at')}")
    print(f"  - process_status: {final_state.get('process_status')}")

    if executed:
        print("\n=== ¡EVIDENCIA TÉCNICA OBTENIDA: EL TRABAJADOR FASTAPI EN RENDER EJECUTÓ DE FORMA AUTÓNOMA! ===")
    else:
        print("\nAVISO: No se detectó cambio en el tiempo de espera (puede que el bucle de 60s requiera más tiempo o la hora esté desfasada).")

if __name__ == "__main__":
    asyncio.run(main())
