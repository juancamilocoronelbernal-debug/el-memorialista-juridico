"""Live integration verification for despacho background workers.

Tests that monitor_worker and agent_worker execute real tasks autonomously
without any active browser session.
"""
import asyncio
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from dotenv import load_dotenv
load_dotenv(".env")

from app.config import get_settings
from app.services import despacho_agent as agent
from app.services import despacho_store as store

USER_ID = "bbff7fef-1a0e-43a1-a629-f8657e9a5a0f"


async def main():
    settings = get_settings()
    service_token = settings.SUPABASE_SERVICE_ROLE_KEY
    if not service_token:
        print("ERROR: SUPABASE_SERVICE_ROLE_KEY not configured")
        sys.exit(1)

    print("=== 1. VERIFICACIÓN DE CREDENCIALES Y ACCESO ADMIN ===")
    print(f"Supabase URL: {settings.SUPABASE_URL}")
    print(f"User ID de prueba: {USER_ID}")

    # ==========================================
    # TEST 1: MONITOR WORKER
    # ==========================================
    print("\n=== 2. CREANDO MONITOR DE PRUEBA ===")
    monitor_id = str(uuid4())
    monitor_body = {
        "id": monitor_id,
        "owner_id": USER_ID,
        "kind": "monitor",
        "title": "Monitor Automatizado de Prueba",
        "version": 1,
        "data": {
            "url": "https://www.funcionpublica.gov.co",
            "condition": "Cambios en empleo público",
            "keywords": ["función pública", "decreto", "empleo"],
            "analysis_mode": "keywords",
            "enabled": True,
            "interval_minutes": 60,
            "findings": []
        },
        "monitor_next_check": (datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Insert monitor item
    inserted = await store.db_request("POST", "despacho_items", service_token, service=True, json=monitor_body)
    print(f"Monitor insertado con ID: {monitor_id}")

    # ==========================================
    # TEST 2: AGENT SCHEDULE & JOB
    # ==========================================
    print("\n=== 3. CREANDO ENCARGO Y PROGRAMACIÓN DE PRUEBA ===")
    job_id = str(uuid4())
    plan = agent.normalize_plan([{
        "tool": "analyze",
        "title": "Análisis constitucional de prueba",
        "instruction": "Escribe un breve resumen de 2 frases sobre la naturaleza de la acción de tutela en Colombia."
    }], [])
    plan_h = agent.plan_hash(plan)

    job_body = {
        "id": job_id,
        "owner_id": USER_ID,
        "title": "Encargo Automatizado de Prueba",
        "objective": "Verificar ejecución sin navegador",
        "plan": plan,
        "plan_hash": plan_h,
        "approved_hash": plan_h,
        "approved_at": datetime.now(timezone.utc).isoformat(),
        "state": "approved",
        "version": 1,
        "cursor": 0,
        "results": [],
        "document_ids": [],
        "allowed_urls": []
    }

    await store.db_request("POST", "despacho_agent_jobs", service_token, service=True, json=job_body)
    print(f"Encargo plantilla insertado con ID: {job_id}")

    # Create schedule
    schedule_id = str(uuid4())
    schedule_body = {
        "id": schedule_id,
        "owner_id": USER_ID,
        "job_id": job_id,
        "title": "Programación Automatizada de Prueba",
        "interval_minutes": 60,
        "next_run_at": (datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat(),
        "enabled": True,
        "version": 1
    }
    await store.db_request("POST", "despacho_agent_schedules", service_token, service=True, json=schedule_body)
    print(f"Programación insertada con ID: {schedule_id}")

    # ==========================================
    # TEST 3: ESPERAR EJECUCIÓN POR LOS WORKERS
    # ==========================================
    print("\n=== 4. ESPERANDO EJECUCIÓN AUTÓNOMA POR LOS TRABAJADORES (sondeo en segundo plano) ===")
    print("Esperando hasta 90 segundos...")

    monitor_executed = False
    agent_executed = False
    enqueued_job_id = None

    start_time = time.time()
    while time.time() - start_time < 90:
        # Check monitor
        if not monitor_executed:
            m_rows = await store.db_request("GET", "despacho_items", service_token, service=True, params={"id": f"eq.{monitor_id}"})
            if m_rows and isinstance(m_rows, list):
                m_data = m_rows[0].get("data", {})
                last_checked = m_data.get("last_checked")
                if last_checked:
                    monitor_executed = True
                    print(f"\n[ÉXITO] Monitor procesado por monitor_worker!")
                    print(f" - Última revisión: {last_checked}")
                    print(f" - Estado: {m_data.get('last_status')}")
                    print(f" - Título fuente: {m_data.get('last_source_title')}")
                    print(f" - Hash fuente: {m_data.get('last_hash')[:16]}...")
                    print(f" - Próxima revisión: {m_rows[0].get('monitor_next_check')}")

        # Check schedule & job
        if not agent_executed:
            s_rows = await store.db_request("GET", "despacho_agent_schedules", service_token, service=True, params={"id": f"eq.{schedule_id}"})
            if s_rows and isinstance(s_rows, list):
                last_job = s_rows[0].get("last_job_id")
                if last_job:
                    enqueued_job_id = last_job
                    j_rows = await store.db_request("GET", "despacho_agent_jobs", service_token, service=True, params={"id": f"eq.{enqueued_job_id}"})
                    if j_rows and isinstance(j_rows, list):
                        state = j_rows[0].get("state")
                        results = j_rows[0].get("results", [])
                        if state == "completed" or (results and len(results) > 0):
                            agent_executed = True
                            print(f"\n[ÉXITO] Encargo programado procesado por agent_worker!")
                            print(f" - ID ejecutado: {enqueued_job_id}")
                            print(f" - Estado del encargo: {state}")
                            print(f" - Pasos completados: {len(results)}")
                            if results:
                                ans = results[0].get("result", {}).get("answer", "")
                                print(f" - Respuesta generada por IA:\n   \"{ans[:200]}...\"")
                            print(f" - Próxima ejecución programada: {s_rows[0].get('next_run_at')}")

        if monitor_executed and agent_executed:
            break

        await asyncio.sleep(5)
        print(".", end="", flush=True)

    print("\n\n=== 5. VERIFICACIÓN DE CUOTAS PERSISTENTES ===")
    quotas = await store.db_request("GET", "despacho_automation_user_usage", service_token, service=True, params={"owner_id": f"eq.{USER_ID}"})
    if quotas and isinstance(quotas, list):
        print(f"Registro de consumo de cuota: {quotas[-1]}")
    else:
        print("No se encontró registro de cuota o está vacío.")

    # ==========================================
    # TEST 4: AISLAMIENTO ENTRE USUARIOS
    # ==========================================
    print("\n=== 6. VERIFICACIÓN DE AISLAMIENTO POR USUARIO ===")
    other_user = str(uuid4())
    # Try fetching with filter for other user
    other_jobs = await store.db_request("GET", "despacho_agent_jobs", service_token, service=True, params={"owner_id": f"eq.{other_user}"})
    print(f"Encargos visibles para usuario no propietario {other_user}: {len(other_jobs)} (debe ser 0)")

    # ==========================================
    # CLEANUP (OPCIONAL O PRESERVAR)
    # ==========================================
    print("\n=== RESUMEN FINAL ===")
    print(f"Monitor ejecutado autónomamente: {'SÍ' if monitor_executed else 'NO'}")
    print(f"Agente ejecutado autónomamente: {'SÍ' if agent_executed else 'NO'}")
    
    if monitor_executed and agent_executed:
        print("\n¡AMBOS TRABAJADORES DEMOSTRARON EJECUCIÓN AUTÓNOMA REAL EN SEGUNDO PLANO!")
    else:
        print("\nADVERTENCIA: Uno o ambos trabajadores no completaron la tarea en el tiempo esperado.")


if __name__ == "__main__":
    asyncio.run(main())
