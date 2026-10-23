"""Diagnóstico reproducible: configuración local y comprobaciones remotas opcionales.

Uso: python scripts/check_despacho.py [--live] [--json-out informe.json]
--live sólo lee modelos/esquemas/Auth y negocia SMTP; no envía correo, crea cuentas,
firma, radica ni modifica registros. Nunca imprime claves, tokens ni datos privados.
MEMORIALISTA_CHECK_USER_TOKEN permite comprobar una sesión de prueba ya existente.
Este diagnóstico no reemplaza la prueba funcional de dos cuentas y proveedores.
"""
from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import os
from pathlib import Path
import smtplib
import ssl
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import httpx
from app.config import get_settings
from app.services import despacho_agent, despacho_browser, despacho_connections, despacho_knowledge
from app.services import despacho_ocr, despacho_signing_v5, despacho_delivery


def local_checks():
    s = get_settings()
    records = []
    def add(name, ok, message):
        records.append({"check": name, "status": "configured" if ok else "pending", "message": message})
    add("supabase", bool(s.SUPABASE_URL and s.SUPABASE_ANON_KEY and s.SUPABASE_SERVICE_ROLE_KEY),
        "Se necesitan URL, clave pública y service_role. Las credenciales nunca se incluyen en este informe.")
    add("canonical_url", s.APP_BASE_URL.startswith("https://") if s.ENVIRONMENT == "production" else bool(s.APP_BASE_URL),
        "APP_BASE_URL debe coincidir con el dominio real; producción exige HTTPS.")
    add("ai", bool(s.GEMINI_API_KEY or s.GROQ_API_KEY), "Proveedor de chat configurado; su disponibilidad se verifica con una consulta real.")
    add("legal_web_research", bool(s.GEMINI_API_KEY), "La investigación web utiliza Gemini y Google Search; Groq es respaldo de análisis/redacción.")
    embedding = despacho_knowledge.embedding_status()
    add("semantic_search", embedding["configured"], embedding["message"])
    ocr = despacho_ocr.ocr_status()
    add("ocr", ocr["available"] and ocr["pdf_available"] and not ocr["missing_languages"],
        "Tesseract y Poppler. Idiomas disponibles: " + ", ".join(ocr["languages"]) +
        (". Faltan idiomas configurados: " + ", ".join(ocr["missing_languages"]) if ocr["missing_languages"] else ""))
    add("verified_signing", despacho_signing_v5.available()["configured"], despacho_signing_v5.available()["message"])
    add("monitor_worker", bool(s.DESPACHO_MONITORS_ENABLED and s.SUPABASE_SERVICE_ROLE_KEY),
        "El proceso debe permanecer en ejecución. Esta comprobación no acredita periodicidad en el alojamiento.")
    add("agent_worker", bool(s.DESPACHO_AGENT_WORKER_ENABLED and despacho_agent.status()["configured"]),
        "Programación persistida; requiere trabajador activo y proveedores operativos.")
    for provider in despacho_connections.capabilities():
        add("oauth_" + provider["id"], provider["configured"], provider["message"])
    browser = despacho_browser.status()
    add("supervised_browser", bool(browser.get("configured") or browser.get("available")), browser.get("message", "Comprueba proveedor, Playwright, navegador aislado y conectividad."))
    files = sorted(p.name for p in (ROOT / "supabase/migrations").glob("*.sql"))
    add("migration_files", len(files) >= 9, f"Archivos de migración incluidos: {len(files)}. Su presencia no acredita que estén aplicados.")
    return records, files


def smtp_probe():
    s = get_settings()
    if not despacho_delivery.status()["configured"]:
        return {"check": "live_smtp", "status": "pending", "message": "SMTP no configurado."}
    try:
        if s.SMTP_TLS_MODE not in {"tls", "starttls"}:
            raise ValueError()
        context = ssl.create_default_context()
        connection = smtplib.SMTP_SSL(s.SMTP_HOST, s.SMTP_PORT, timeout=15, context=context) if s.SMTP_TLS_MODE == "tls" else smtplib.SMTP(s.SMTP_HOST, s.SMTP_PORT, timeout=15)
        with connection:
            connection.ehlo()
            if s.SMTP_TLS_MODE == "starttls":
                connection.starttls(context=context)
                connection.ehlo()
            if s.SMTP_USERNAME:
                connection.login(s.SMTP_USERNAME, s.SMTP_PASSWORD)
        return {"check": "live_smtp", "status": "passed", "message": "Negociación TLS/autenticación aceptada. No se enviaron mensajes ni se comprobó la entrega al buzón."}
    except Exception:
        return {"check": "live_smtp", "status": "failed", "message": "No se completó la negociación SMTP. Revisa red, certificado, modo TLS y credenciales en el servidor."}


async def live_checks():
    s = get_settings()
    records = []
    async with httpx.AsyncClient(timeout=20, follow_redirects=False, trust_env=False) as client:
        async def get(name, url, headers, params=None):
            try:
                response = await client.get(url, headers=headers, params=params)
                ok = response.status_code == 200
                records.append({"check": name, "status": "passed" if ok else "failed", "message": f"Respuesta HTTP {response.status_code}; no se registró el contenido ni credenciales."})
                return response if ok else None
            except httpx.HTTPError:
                records.append({"check": name, "status": "failed", "message": "No se pudo completar la conexión HTTP segura."})
                return None
        if s.SUPABASE_URL and s.SUPABASE_SERVICE_ROLE_KEY:
            headers = {"apikey": s.SUPABASE_SERVICE_ROLE_KEY, "Authorization": "Bearer " + s.SUPABASE_SERVICE_ROLE_KEY}
            for table in ["despacho_items", "despacho_indice", "despacho_agent_jobs", "despacho_agent_schedules", "despacho_conexiones", "despacho_firma_expedientes", "despacho_salas"]:
                await get("live_table_" + table, s.SUPABASE_URL.rstrip("/") + "/rest/v1/" + table, headers, {"select": "owner_id", "limit": 1})
        else:
            records.append({"check": "live_database", "status": "pending", "message": "Faltan credenciales de Supabase."})
        if s.GEMINI_API_KEY:
            await get("live_gemini_model_catalog", s.GEMINI_API_BASE.rstrip("/") + "/v1beta/models", {"x-goog-api-key": s.GEMINI_API_KEY}, {"pageSize": 100})
        if s.GROQ_API_KEY:
            await get("live_groq_model_catalog", s.GROQ_API_BASE.rstrip("/") + "/models", {"Authorization": "Bearer " + s.GROQ_API_KEY})
        token = os.environ.get("MEMORIALISTA_CHECK_USER_TOKEN", "")
        if token and s.SUPABASE_URL and s.SUPABASE_ANON_KEY:
            headers = {"apikey": s.SUPABASE_ANON_KEY, "Authorization": "Bearer " + token}
            result = await get("live_test_user_session", s.SUPABASE_URL.rstrip("/") + "/auth/v1/user", headers)
            if result:
                user = result.json()
                if user.get("id") and user.get("role") == "authenticated" and not user.get("is_anonymous"):
                    await get("live_private_read", s.SUPABASE_URL.rstrip("/") + "/rest/v1/despacho_items", headers, {"select": "id", "owner_id": "eq." + user["id"], "limit": 1})
                else:
                    records.append({"check": "live_test_user_role", "status": "failed", "message": "La cuenta de prueba no es una sesión profesional autenticada."})
        else:
            records.append({"check": "live_test_user_session", "status": "pending", "message": "No se proporcionó MEMORIALISTA_CHECK_USER_TOKEN; falta probar login y RLS con dos cuentas reales de prueba."})
    records.append(await asyncio.to_thread(smtp_probe))
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Lecturas remotas de comprobación, sin escribir datos ni enviar correo")
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    local, files = local_checks()
    remote = asyncio.run(live_checks()) if args.live else []
    report = {"version": "5.0.0", "remote_checks_requested": args.live, "checks": [*local, *remote], "migrations": files,
              "production_certified": False,
              "remaining_validation": "Acceso real, aislamiento entre dos cuentas, persistencia tras reinicio, ejecución IA, conexión OAuth, entrega OTP/firma y disponibilidad periódica. Este diagnóstico no certifica equivalencia con Magnar."}
    serialized = json.dumps(report, ensure_ascii=False, indent=2)
    if args.json_out:
        args.json_out.write_text(serialized + "\n", encoding="utf-8")
    print(serialized)
    return 1 if any(check["status"] in {"failed", "pending"} for check in report["checks"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
