"""Supabase Auth, exportación sujeta a RLS y eliminación comprobada.

No contiene accesos de demostración. Un JWT se admite únicamente después de que
Supabase Auth lo reconozca. La expiración se usa también para limitar la caché;
leer el payload sin verificar jamás autentica una petición.
"""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import math
import time
from typing import Any, Optional
from urllib.parse import quote

import httpx
from fastapi import HTTPException

from app.config import get_settings

log = logging.getLogger("memorialista.supabase")
_TOKEN_CACHE: dict[str, tuple[dict[str, Any], float]] = {}
CACHE_TTL_SEGUNDOS = 30.0
MAX_CACHE_TOKENS = 2000


class ErrorSupabase(Exception):
    """Error público sin tokens, cuerpos remotos ni detalles internos."""


def expiracion_token(token: str) -> Optional[float]:
    """Obtiene exp SOLO como límite temporal. No prueba firma ni identidad."""
    try:
        if not isinstance(token, str) or len(token) > 8192:
            return None
        parts = token.split(".")
        if len(parts) != 3 or not all(parts):
            return None
        raw = parts[1] + "=" * (-len(parts[1]) % 4)
        payload = json.loads(base64.urlsafe_b64decode(raw))
        exp = payload.get("exp")
        if isinstance(exp, bool) or not isinstance(exp, (int, float)) or not math.isfinite(exp):
            return None
        return float(exp)
    except (ValueError, TypeError, UnicodeError, AttributeError):
        return None


def _clave_cache(token: str) -> str:
    s = get_settings()
    return hashlib.sha256((s.SUPABASE_URL + "\0" + token).encode()).hexdigest()


def invalidar_token(token: str) -> None:
    if token:
        _TOKEN_CACHE.pop(_clave_cache(token), None)


def _limpiar_cache_tokens(ahora: float) -> None:
    for key in [k for k, (_, exp) in _TOKEN_CACHE.items() if ahora >= exp]:
        _TOKEN_CACHE.pop(key, None)
    while len(_TOKEN_CACHE) >= MAX_CACHE_TOKENS:
        _TOKEN_CACHE.pop(next(iter(_TOKEN_CACHE)))


async def validar_token_supabase(token: str) -> Optional[dict[str, Any]]:
    if not isinstance(token, str) or not token.strip():
        return None
    token = token.strip()
    s = get_settings()
    if not s.SUPABASE_URL or not s.SUPABASE_ANON_KEY:
        return None
    expiracion = expiracion_token(token)
    if expiracion is None or expiracion <= time.time():
        return None
    # Los únicos datos de usuario que se aceptan vienen del proveedor Auth.
    ahora = time.monotonic()
    _limpiar_cache_tokens(ahora)
    clave = _clave_cache(token)
    entrada = _TOKEN_CACHE.get(clave)
    if entrada and ahora < entrada[1]:
        return entrada[0]
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=False) as client:
            response = await client.get(
                f"{s.SUPABASE_URL.rstrip('/')}/auth/v1/user",
                headers={"Authorization": f"Bearer {token}", "apikey": s.SUPABASE_ANON_KEY},
            )
        if response.status_code in (401, 403):
            return None
        if response.status_code != 200:
            log.warning("Supabase Auth no disponible (HTTP %s)", response.status_code)
            raise ErrorSupabase("No se pudo comprobar la sesión. Inténtalo de nuevo en unos momentos.")
        data = response.json()
        if not isinstance(data, dict) or not isinstance(data.get("id"), str) or not data["id"] or data.get("is_anonymous"):
            return None
        ttl = min(CACHE_TTL_SEGUNDOS, expiracion - time.time())
        if ttl <= 0:
            return None
        _TOKEN_CACHE[clave] = (data, time.monotonic() + ttl)
        return data
    except httpx.HTTPError as exc:
        log.warning("Fallo de comunicación con Supabase Auth (%s)", type(exc).__name__)
        raise ErrorSupabase("No se pudo comprobar la sesión. Inténtalo de nuevo en unos momentos.") from None
    except (ValueError, TypeError):
        raise ErrorSupabase("El servicio de autenticación devolvió una respuesta no válida.") from None


def _configurar_datos(token: str):
    s = get_settings()
    if not s.SUPABASE_URL or not s.SUPABASE_ANON_KEY:
        raise ErrorSupabase("La conexión con la base de datos aún no está configurada.")
    # La exportación usa SIEMPRE la clave pública y el JWT del usuario: RLS activo.
    return s.SUPABASE_URL.rstrip("/"), {
        "Authorization": f"Bearer {token}",
        "apikey": s.SUPABASE_ANON_KEY,
        "Content-Type": "application/json",
    }


async def _filas(client, url: str, headers: dict, filtros: dict) -> list:
    """Recorre páginas completas; no etiqueta como completo un export truncado."""
    rows, offset = [], 0
    for _ in range(1000):
        response = await client.get(url, headers={**headers, "Prefer": "count=exact"}, params={
            "select": "*", "order": "id.asc", "limit": 1000, "offset": offset, **filtros,
        })
        if response.status_code not in (200, 206):
            raise ErrorSupabase("No se pudo leer toda la información. Ningún archivo parcial se presenta como completo.")
        batch = response.json()
        if not isinstance(batch, list):
            raise ErrorSupabase("La base de datos devolvió un formato inesperado.")
        rows.extend(batch)
        offset += len(batch)
        rango = response.headers.get("content-range", "")
        total = rango.rsplit("/", 1)[-1]
        if total.isdigit():
            if offset >= int(total):
                return rows
            if not batch:
                raise ErrorSupabase("No fue posible completar la paginación de tus datos.")
        elif len(batch) < 1000:
            return rows
    raise ErrorSupabase("La exportación supera el tamaño disponible. Solicita una exportación administrativa.")


async def exportar_todos_los_datos(user_id: str, token: str) -> dict[str, Any]:
    base, headers = _configurar_datos(token)
    result = {
        "exportado_el": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "aplicacion": "El Memorialista Jurídico", "version_esquema": "5.0.0",
        "usuario_id": user_id, "perfil": {}, "firma": {}, "clientes": [],
        "casos": [], "documentos": [], "versiones": [],
        "despacho": {"elementos": [], "auditoria": [], "firmas_electronicas": []},
        "alcance": "Registros propios, despacho privado, evidencias de firma y perfil de la firma accesibles mediante tu sesión. Los binarios del almacenamiento y los secretos de acceso a firmas no se incluyen en este JSON. Para restaurar el despacho usa su copia de respaldo específica.",
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            perfiles = await _filas(client, f"{base}/rest/v1/perfiles", headers, {"id": f"eq.{user_id}"})
            if perfiles:
                result["perfil"] = perfiles[0]
                firma_id = perfiles[0].get("firma_id")
                if firma_id:
                    firmas = await _filas(client, f"{base}/rest/v1/firmas", headers, {"id": f"eq.{firma_id}"})
                    result["firma"] = firmas[0] if firmas else {}
            for tabla, campo in [("clientes", "user_id"), ("casos", "user_id"), ("documentos", "creado_por"), ("versiones", "creado_por")]:
                result[tabla] = await _filas(client, f"{base}/rest/v1/{tabla}", headers, {campo: f"eq.{user_id}"})
            for tabla, campo in [("despacho_items", "elementos"), ("despacho_auditoria", "auditoria")]:
                result["despacho"][campo] = await _filas(client, f"{base}/rest/v1/{tabla}", headers, {"owner_id": f"eq.{user_id}"})
            # El hash del enlace secreto no aporta evidencia documental y nunca
            # debe salir en una exportación. La huella del documento sí se incluye.
            result["despacho"]["firmas_electronicas"] = await _filas(
                client, f"{base}/rest/v1/despacho_firmas", headers,
                {"owner_id": f"eq.{user_id}", "select":
                 "id,owner_id,title,document_text,document_hash,signer_name,signer_email,status,created_at,expires_at,signed_at,signed_name,signed_email,signer_ip,signer_agent,consent_text,audit"},
            )
            from app.services.despacho_agent import PUBLIC_JOB_KEYS, PUBLIC_SCHEDULE_KEYS
            for table, field, columns in [
                ("despacho_agent_jobs", "encargos", PUBLIC_JOB_KEYS),
                ("despacho_agent_schedules", "programaciones", PUBLIC_SCHEDULE_KEYS),
                ("despacho_agent_events", "eventos_agente", ("id", "job_id", "owner_id", "at", "event", "detail")),
            ]:
                result["despacho"][field] = await _filas(client, f"{base}/rest/v1/{table}", headers,
                    {"owner_id": f"eq.{user_id}", "select": ",".join(columns)})
            from app.services import despacho_signing_v5, despacho_connections, despacho_rooms_v5
            result["despacho"]["firmas_verificadas"] = await despacho_signing_v5.export_owner(user_id, token)
            result["despacho"]["conexiones"] = await despacho_connections.export_owner(user_id, token)
            result["despacho"]["salas"] = await despacho_rooms_v5.export_owner(user_id, token)
        return result
    except HTTPException as exc:
        raise ErrorSupabase("La exportación no pudo completarse: " + str(exc.detail) + " Ningún archivo parcial se presenta como completo.") from None
    except httpx.HTTPError:
        raise ErrorSupabase("La exportación se interrumpió al consultar tus datos. Puedes volver a intentarlo.") from None
    except (ValueError, TypeError):
        raise ErrorSupabase("No se pudo interpretar la respuesta de la base de datos.") from None


async def _borrar_archivos_usuario(client, base: str, headers: dict, user_id: str) -> None:
    """Solo directorios personales usados por la aplicación; no archivos de otros miembros."""
    bucket = quote(get_settings().SUPABASE_STORAGE_BUCKET, safe="")
    for categoria in ("logo", "firma", "plantilla"):
        pendientes = [f"{categoria}/{user_id}/"]
        carpetas = 0
        while pendientes:
            prefijo = pendientes.pop()
            carpetas += 1
            if carpetas > 100:
                raise ErrorSupabase("No se completó el borrado de archivos. Contacta con el administrador.")
            offset, archivos = 0, []
            while True:
                r = await client.post(f"{base}/storage/v1/object/list/{bucket}", headers=headers,
                                      json={"prefix": prefijo, "limit": 1000, "offset": offset, "sortBy": {"column": "name", "order": "asc"}})
                if r.status_code != 200:
                    raise ErrorSupabase("No se pudo comprobar el borrado de tus archivos. La cuenta no se ha eliminado.")
                lista = r.json()
                if not isinstance(lista, list):
                    raise ErrorSupabase("El almacenamiento devolvió una respuesta inesperada.")
                for obj in lista:
                    name = obj.get("name", "")
                    if not isinstance(name, str) or not name or "/" in name or name in (".", ".."):
                        raise ErrorSupabase("Se encontró una ruta de archivo no válida; se detuvo el borrado.")
                    ruta = prefijo + name
                    if obj.get("id") is None:
                        pendientes.append(ruta + "/")
                    else:
                        archivos.append(ruta)
                if len(lista) < 1000:
                    break
                offset += len(lista)
            for i in range(0, len(archivos), 100):
                r = await client.request("DELETE", f"{base}/storage/v1/object/{bucket}", headers=headers,
                                         json={"prefixes": archivos[i:i + 100]})
                if r.status_code not in (200, 204):
                    raise ErrorSupabase("No se completó el borrado de archivos. La cuenta no se ha eliminado.")


async def _comprobar_baja_sin_trabajo_ajeno(client, base, headers, user_id):
    """Evita que un ON DELETE CASCADE destruya aportes de otros integrantes."""
    casos = await _filas(client, f"{base}/rest/v1/casos", headers, {"user_id": f"eq.{user_id}", "select": "id"})
    documentos = await _filas(client, f"{base}/rest/v1/documentos", headers, {"creado_por": f"eq.{user_id}", "select": "id"})
    relaciones = [(casos, "documentos", "caso_id"), (documentos, "versiones", "documento_id")]
    for padres, tabla, campo in relaciones:
        for i in range(0, len(padres), 100):
            ids = ",".join(str(row["id"]) for row in padres[i:i + 100])
            hijos = await _filas(client, f"{base}/rest/v1/{tabla}", headers, {campo: f"in.({ids})", "select": "id,creado_por"})
            if any(row.get("creado_por") != user_id for row in hijos):
                raise ErrorSupabase(
                    "Tu cuenta tiene expedientes o documentos con aportes de otras personas. "
                    "Solicita al administrador transferir esos registros antes de eliminar la cuenta. "
                    "No se ha borrado ningún dato."
                )


async def eliminar_cuenta_usuario(user_id: str, token: str) -> bool:
    """El éxito exige respuestas satisfactorias de cada sistema; puede haber borrado parcial si una API falla."""
    s = get_settings()
    # Comprobar antes de la primera escritura: con la clave pública no se puede
    # borrar Auth. Nunca eliminar los datos primero y luego fingir la baja.
    if not s.SUPABASE_URL or not s.SUPABASE_SERVICE_ROLE_KEY:
        raise ErrorSupabase("La eliminación de cuentas no está habilitada. El administrador debe configurar el servicio de cuentas; no se ha borrado ningún dato.")
    base = s.SUPABASE_URL.rstrip("/")
    headers = {"Authorization": f"Bearer {s.SUPABASE_SERVICE_ROLE_KEY}",
               "apikey": s.SUPABASE_SERVICE_ROLE_KEY, "Content-Type": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Todos estos controles ocurren ANTES de la primera escritura.
            await _comprobar_baja_sin_trabajo_ajeno(client, base, headers, user_id)
            # No borrar firmas compartidas ni perfiles de otros miembros.
            firmas = await _filas(client, f"{base}/rest/v1/firmas", headers, {"creado_por": f"eq.{user_id}"})
            firmas_personales = []
            for firma in firmas:
                miembros = await _filas(client, f"{base}/rest/v1/perfiles", headers, {"firma_id": f"eq.{firma['id']}"})
                if all(p.get("id") == user_id for p in miembros):
                    ajenos = False
                    for tabla, campo in [("clientes", "user_id"), ("casos", "user_id"), ("documentos", "creado_por")]:
                        registros = await _filas(client, f"{base}/rest/v1/{tabla}", headers,
                                                {"firma_id": f"eq.{firma['id']}", "select": f"id,{campo}"})
                        ajenos = ajenos or any(row.get(campo) != user_id for row in registros)
                    if not ajenos:
                        firmas_personales.append(firma["id"])
            from app.services.despacho_store import borrar_archivos_despacho
            await borrar_archivos_despacho(client, base, headers, user_id)
            from app.services import despacho_signing_v5, despacho_connections, despacho_browser, despacho_rooms_v5
            await despacho_browser.close_owner(user_id)
            await despacho_signing_v5.purge_owner_storage(user_id)
            await despacho_rooms_v5.purge_owner_storage(user_id)
            await despacho_connections.cleanup_owner_connections(user_id)
            await _borrar_archivos_usuario(client, base, headers, user_id)
            for tabla, campo in [("versiones", "creado_por"), ("documentos", "creado_por"), ("casos", "user_id"), ("clientes", "user_id")]:
                r = await client.delete(f"{base}/rest/v1/{tabla}", headers=headers, params={campo: f"eq.{user_id}"})
                if r.status_code not in (200, 204):
                    raise ErrorSupabase("La eliminación quedó incompleta y puede haber datos ya borrados. Contacta con el administrador antes de reintentar.")
            for firma_id in firmas_personales:
                r = await client.delete(f"{base}/rest/v1/firmas", headers=headers, params={"id": f"eq.{firma_id}", "creado_por": f"eq.{user_id}"})
                if r.status_code not in (200, 204):
                    raise ErrorSupabase("No se completó el borrado del despacho personal. Contacta con el administrador.")
            r = await client.delete(f"{base}/auth/v1/admin/users/{quote(user_id, safe='')}", headers=headers)
            if r.status_code not in (200, 204):
                raise ErrorSupabase("Los registros se procesaron, pero la cuenta no pudo eliminarse. Contacta con el administrador.")
        _TOKEN_CACHE.clear()
        return True
    except HTTPException as exc:
        raise ErrorSupabase("La eliminación se detuvo antes de cerrar la cuenta: " + str(exc.detail) + " Puede haber cambios parciales; revisa el estado antes de reintentar.") from None
    except httpx.HTTPError:
        raise ErrorSupabase("La eliminación se interrumpió y puede ser parcial. Contacta con el administrador para completarla.") from None
    except (ValueError, TypeError, KeyError):
        raise ErrorSupabase("No se pudo comprobar toda la eliminación. Contacta con el administrador.") from None
