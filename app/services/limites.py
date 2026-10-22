"""
El Memorialista · control de acceso y límites de uso (v2.3)
Autenticación con Supabase Auth (Bearer tokens y Enlace Mágico) y límites por usuario.
"""
import hmac
import time
from collections import defaultdict, deque
from typing import Any, Optional

from fastapi import HTTPException, Request

from app.config import get_settings
from app.services.supabase_service import validar_token_supabase


def ip_cliente(request: Request) -> str:
    reenviada = request.headers.get("x-forwarded-for", "")
    if reenviada:
        primera = reenviada.split(",")[0].strip()
        if primera:
            return primera[:64]
    return request.client.host if request.client else "desconocida"


async def verificar_acceso(request: Request) -> Optional[dict[str, Any]]:
    """Verifica la sesión activa de Supabase (Bearer token) o código de acceso de respaldo."""
    settings = get_settings()
    auth_header = request.headers.get("authorization", "").strip()
    token = ""
    if auth_header.lower().startswith("bearer "):
        token = auth_header[7:].strip()

    # Si se envía un token Bearer o si Supabase está activo
    if token or settings.SUPABASE_URL:
        if not token:
            raise HTTPException(
                status_code=401,
                detail="Se requiere iniciar sesión con tu enlace mágico para acceder a El Memorialista.",
            )
        usuario = await validar_token_supabase(token)
        if not usuario:
            raise HTTPException(
                status_code=401,
                detail="Tu sesión de Supabase ha expirado o no es válida. Inicia sesión nuevamente.",
            )
        request.state.usuario = usuario
        request.state.user_id = usuario.get("id") or usuario.get("sub")
        return usuario

    # Respaldo de código de acceso legado si no hay Supabase configurado
    codigo = settings.APP_ACCESS_CODE.strip()
    if codigo:
        enviado = request.headers.get("x-codigo-acceso", "").strip()
        if not enviado or not hmac.compare_digest(enviado.encode("utf-8"), codigo.encode("utf-8")):
            raise HTTPException(
                status_code=401,
                detail="Esta versión de El Memorialista requiere autenticación válida.",
            )
    return None


class Limitador:
    """Ventanas deslizantes en memoria aplicadas por usuario y por IP."""

    def __init__(self) -> None:
        self._eventos = defaultdict(deque)
        self._ultima_limpieza = time.monotonic()

    def _reglas(self, accion: str, ip: str, user_id: Optional[str] = None) -> list:
        s = get_settings()
        id_clave = f"u:{user_id}" if user_id else f"ip:{ip}"
        limite_dia = s.LIMITE_DIA_USUARIO if user_id else s.LIMITE_DIA_IP

        if accion == "redactar":
            return [
                (f"r:{id_clave}:v", s.VENTANA_MINUTOS * 60, s.LIMITE_POR_VENTANA,
                 "Hiciste muchas redacciones seguidas. Espera unos {min} min y vuelve a intentarlo."),
                (f"r:{id_clave}:d", 86400, limite_dia,
                 "Alcanzaste tu límite diario de redacciones ({limite} al día). Vuelve a intentarlo mañana."),
                ("r:global:d", 86400, s.LIMITE_DIA_GLOBAL,
                 "El servicio alcanzó su límite diario de redacciones. Intenta de nuevo mañana."),
            ]
        if accion in ("citas", "revisar"):
            return [
                (f"{accion[0]}:{id_clave}:h", 3600, max(100, s.LIMITE_ESTILO_HORA * 6),
                 "Revisaste muchos escritos seguidos. Espera unos {min} min."),
            ]
        return [
            (f"e:{id_clave}:h", 3600, s.LIMITE_ESTILO_HORA,
             "Analizaste muchas muestras seguidas. Espera unos {min} min."),
        ]

    def verificar(self, request: Request, accion: str, user_id: Optional[str] = None) -> None:
        ahora = time.monotonic()
        u_id = user_id or getattr(request.state, "user_id", None)
        reglas = self._reglas(accion, ip_cliente(request), user_id=u_id)
        for clave, ventana, limite, mensaje in reglas:
            if limite <= 0:
                continue
            cola = self._eventos[clave]
            while cola and ahora - cola[0] > ventana:
                cola.popleft()
            if len(cola) >= limite:
                espera = max(1, int(ventana - (ahora - cola[0])))
                raise HTTPException(
                    status_code=429,
                    detail=mensaje.format(min=max(1, round(espera / 60)), limite=limite),
                    headers={"Retry-After": str(espera)},
                )
        for clave, _ventana, limite, _mensaje in reglas:
            if limite > 0:
                self._eventos[clave].append(ahora)
        self._limpiar(ahora)

    def _limpiar(self, ahora: float) -> None:
        if ahora - self._ultima_limpieza < 600:
            return
        self._ultima_limpieza = ahora
        viejas = [k for k, cola in self._eventos.items() if not cola or ahora - cola[-1] > 86400]
        for k in viejas:
            del self._eventos[k]

    def reiniciar(self) -> None:
        self._eventos.clear()


limitador = Limitador()
