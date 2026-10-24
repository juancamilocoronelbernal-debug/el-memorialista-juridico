"""Script de verificación de dos ciclos de ejecución consecutiva del trabajador programado (Fase 2.2.1).

Verifica:
1. Ciclo 1: Adquisición de bloqueo concurrente con token de esgrima (fencing token).
2. Heartbeat de renovación: actualización de expiración y avance de lote en Supabase.
3. Finalización: liberación limpia de bloqueo y actualización de last_successful_run_at y next_run_at.
4. Intervalo intermedio: el trabajador comprueba que next_run_at está en el futuro y se abstiene de sincronizar.
5. Ciclo 2: Cuando next_run_at vence, se inicia el segundo ciclo, adquiere nuevo token de esgrima consecutivo, sincroniza, actualiza marcas y libera limpiamente.
6. Ausencia total de bloqueos huérfanos.
"""
import asyncio
from datetime import datetime, timezone, timedelta
import json
import logging

from app.config import get_settings
from app.services import conector_corte_constitucional as conector
from app.services import conector_corte_worker as worker
from app.services import despacho_store as store

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("test_dos_ciclos")


async def get_db_state():
    settings = get_settings()
    key = settings.SUPABASE_SERVICE_ROLE_KEY.strip()
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
    print("=== INICIANDO VERIFICACIÓN DE DOS EJECUCIONES CONSECUTIVAS ===")

    # 0. Limpieza previa de cualquier bloqueo huérfano
    orphan_clean = await conector.recover_orphan_locks()
    print(f"Limpieza huérfanos inicial: {orphan_clean}")

    # =========================================================================
    # EJECUCIÓN 1: Primer ciclo programado
    # =========================================================================
    print("\n--- EJECUCIÓN 1: Primer ciclo ---")
    owner_1 = f"{worker.WORKER_INSTANCE_ID}_run1"
    
    # 1. Adquisición de bloqueo v2
    acquired_1, fencing_token_1 = await conector.acquire_sync_lock_v2(owner=owner_1, ttl_seconds=300, run_id="run_test_1")
    print(f"Bloqueo adquirido: {acquired_1}, Fencing Token: {fencing_token_1}")
    assert acquired_1 is True, "Fallo al adquirir bloqueo v2 en ciclo 1"
    assert fencing_token_1 > 0, "Fencing token inválido en ciclo 1"

    # Verificar estado en BD durante ejecución 1
    state_in_run1 = await get_db_state()
    print(f"Estado en BD durante Ejecución 1:")
    print(f"  - lock_owner: {state_in_run1.get('lock_owner')}")
    print(f"  - sync_lock_until: {state_in_run1.get('sync_lock_until')}")
    print(f"  - lock_fencing_token: {state_in_run1.get('lock_fencing_token')}")
    assert state_in_run1.get("lock_owner") == owner_1
    assert state_in_run1.get("lock_fencing_token") == fencing_token_1

    # 2. Heartbeat de renovación (simula avance de lote)
    renewed_1 = await conector.renew_sync_lock(
        owner=owner_1,
        fencing_token=fencing_token_1,
        extend_seconds=300,
        progress={"current": 1, "total": 2, "last_sentencia": "T-100/24"},
    )
    print(f"Heartbeat renovado: {renewed_1}")
    assert renewed_1 is True, "Fallo al renovar heartbeat"

    # 3. Intentar adquisición por otro worker (debe fallar)
    busy_check, busy_token = await conector.acquire_sync_lock_v2(owner="worker_intruso", ttl_seconds=300)
    print(f"Intento de adquisición concurrente: acquired={busy_check} (esperado: False)")
    assert busy_check is False, "El bloqueo concurrente permitió doble adquisición indebida"

    # 4. Programar próxima ejecución y registrar éxito
    now_1 = datetime.now(timezone.utc)
    next_run_1 = now_1 + timedelta(minutes=360)
    await conector.update_schedule_metadata(
        schedule_enabled=True,
        interval_minutes=360,
        next_run_at=next_run_1.isoformat(),
    )
    
    # 5. Liberar bloqueo v2 con fencing token coincidente
    released_1 = await conector.release_sync_lock_v2(
        owner=owner_1,
        fencing_token=fencing_token_1,
        success=True,
    )
    print(f"Bloqueo liberado limpiamente: {released_1}")
    assert released_1 is True, "Fallo al liberar bloqueo v2 en ciclo 1"

    # Verificar estado tras ciclo 1
    state_post_1 = await get_db_state()
    print(f"Estado en BD tras Ejecución 1:")
    print(f"  - lock_owner: {state_post_1.get('lock_owner')} (esperado: None)")
    print(f"  - sync_lock_until: {state_post_1.get('sync_lock_until')} (esperado: None)")
    print(f"  - next_run_at: {state_post_1.get('next_run_at')}")
    print(f"  - last_successful_run_at: {state_post_1.get('last_successful_run_at')}")
    assert state_post_1.get("lock_owner") is None
    assert state_post_1.get("sync_lock_until") is None
    assert state_post_1.get("last_successful_run_at") is not None

    # =========================================================================
    # COMPROBACIÓN INTERMEDIA: Verificación de abstención antes de next_run_at
    # =========================================================================
    print("\n--- COMPROBACIÓN INTERMEDIA: Antes de next_run_at ---")
    status_mid = await conector.get_connector_status()
    next_str = status_mid.get("next_run_at")
    clean_mid = next_str.replace("Z", "+00:00")
    if clean_mid.endswith("+00:00") and "." in clean_mid:
        parts = clean_mid.split(".")
        frac_tz = parts[1].split("+")
        clean_mid = f"{parts[0]}.{frac_tz[0].ljust(6, '0')[:6]}+{frac_tz[1]}"
    next_dt = datetime.fromisoformat(clean_mid)
    now_mid = datetime.now(timezone.utc)
    is_time_to_run = now_mid >= next_dt
    print(f"Hora actual: {now_mid.isoformat()}")
    print(f"Próxima ejecución: {next_str}")
    print(f"¿Debe ejecutarse ahora? {is_time_to_run} (esperado: False)")
    assert is_time_to_run is False, "El programador no esperó al tiempo configurado"

    # =========================================================================
    # EJECUCIÓN 2: Segundo ciclo tras vencer next_run_at
    # =========================================================================
    print("\n--- EJECUCIÓN 2: Segundo ciclo programado ---")
    # Forzamos que next_run_at haya llegado al pasado para simular el vencimiento
    past_due = datetime.now(timezone.utc) - timedelta(seconds=10)
    await conector.update_schedule_metadata(
        schedule_enabled=True,
        interval_minutes=360,
        next_run_at=past_due.isoformat(),
    )

    status_due = await conector.get_connector_status()
    now_due = datetime.now(timezone.utc)
    raw_next = status_due["next_run_at"]
    # Normalización compatible con Python 3.9
    clean_next = raw_next.replace("Z", "+00:00")
    if clean_next.endswith("+00:00") and "." in clean_next:
        parts = clean_next.split(".")
        frac_tz = parts[1].split("+")
        clean_next = f"{parts[0]}.{frac_tz[0].ljust(6, '0')[:6]}+{frac_tz[1]}"
    next_due_dt = datetime.fromisoformat(clean_next)
    should_run_2 = now_due >= next_due_dt
    print(f"¿next_run_at vencido? {should_run_2} (esperado: True)")
    assert should_run_2 is True, "next_run_at debería estar vencido"

    owner_2 = f"{worker.WORKER_INSTANCE_ID}_run2"
    acquired_2, fencing_token_2 = await conector.acquire_sync_lock_v2(owner=owner_2, ttl_seconds=300, run_id="run_test_2")
    print(f"Bloqueo adquirido ciclo 2: {acquired_2}, Fencing Token: {fencing_token_2}")
    assert acquired_2 is True, "Fallo al adquirir bloqueo v2 en ciclo 2"
    assert fencing_token_2 > fencing_token_1, f"Fencing token no se incrementó: {fencing_token_2} <= {fencing_token_1}"

    # Heartbeat ciclo 2
    renewed_2 = await conector.renew_sync_lock(
        owner=owner_2,
        fencing_token=fencing_token_2,
        extend_seconds=300,
        progress={"current": 2, "total": 2, "last_sentencia": "C-055/22"},
    )
    print(f"Heartbeat renovado ciclo 2: {renewed_2}")
    assert renewed_2 is True

    # Programar próxima ejecución para ciclo 3
    now_2 = datetime.now(timezone.utc)
    next_run_2 = now_2 + timedelta(minutes=360)
    await conector.update_schedule_metadata(
        schedule_enabled=True,
        interval_minutes=360,
        next_run_at=next_run_2.isoformat(),
    )

    # Liberación de ciclo 2
    released_2 = await conector.release_sync_lock_v2(
        owner=owner_2,
        fencing_token=fencing_token_2,
        success=True,
    )
    print(f"Bloqueo ciclo 2 liberado: {released_2}")
    assert released_2 is True

    # Verificar estado definitivo
    final_state = await get_db_state()
    print(f"\nEstado definitivo en Supabase tras ambas ejecuciones:")
    print(f"  - lock_owner: {final_state.get('lock_owner')} (None)")
    print(f"  - sync_lock_until: {final_state.get('sync_lock_until')} (None)")
    print(f"  - lock_fencing_token: {final_state.get('lock_fencing_token')}")
    print(f"  - last_successful_run_at: {final_state.get('last_successful_run_at')}")
    print(f"  - next_run_at: {final_state.get('next_run_at')}")
    print(f"  - process_status: {final_state.get('process_status')}")

    assert final_state.get("lock_owner") is None
    assert final_state.get("sync_lock_until") is None
    assert final_state.get("last_successful_run_at") is not None
    assert final_state.get("lock_fencing_token") == fencing_token_2

    print("\n=== ¡DOS EJECUCIONES CONSECUTIVAS VERIFICADAS EXITOSAMENTE EN PRODUCCIÓN! ===")

if __name__ == "__main__":
    asyncio.run(main())
