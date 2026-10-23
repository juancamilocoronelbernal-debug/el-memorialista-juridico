"""
El Memorialista · control de acceso y límites de uso (v2.3)
Autenticación con Supabase Auth (Bearer tokens y Enlace Mágico) y límites por usuario.
"""
import time
from collections import defaultdict, deque
from functools import lru_cache
from ipaddress import ip_address, ip_network
from typing import Any, Optional

from fastapi import HTTPException, Request

from app.config import get_settings
from app.services import supabase_service


def _direccion_ip(value: str):
    """Solo direcciones numéricas, normalizadas; nunca puertos, listas ni zone IDs."""
    if not isinstance(value, str) or not value or len(value) > 64 or "%" in value:
        return None
    try:
        direccion = ip_address(value.strip())
        # La misma IPv4 no debe obtener dos cuotas usando la notación IPv6 mapeada.
        return getattr(direccion, "ipv4_mapped", None) or direccion
    except ValueError:
        return None


@lru_cache(maxsize=32)
def _redes_proxy(configuracion: str) -> tuple:
    try:
        redes = tuple(ip_network(value.strip(), strict=False) for value in configuracion.split(",") if value.strip())
        return redes if all(red.prefixlen > 0 for red in redes) else ()
    except ValueError:
        return ()


def ip_cliente(request: Request) -> str:
    """Solo un peer declarado puede aportar la IP del cliente.

    El servidor ASGI también debe tener una configuración segura de proxies: no
    puede recuperar aquí el peer original si otro middleware ya lo sustituyó.
    No hay autodetección por proveedor ni confianza implícita en encabezados.
    """
    directa = _direccion_ip(request.client.host) if request.client else None
    resultado_directo = str(directa) if directa else "desconocida"
    s = get_settings()
    redes = _redes_proxy(s.PROXY_IPS_CONFIABLES)

    def confiable(ip) -> bool:
        return ip is not None and any(ip.version == red.version and ip in red for red in redes)

    if not confiable(directa):
        return resultado_directo
    cabecera = s.IP_CABECERA_CONFIABLE
    if cabecera:
        valores = request.headers.getlist(cabecera)
        # Las cabeceras dedicadas deben ser reemplazadas por el proxy, no anexadas.
        ip = _direccion_ip(valores[0]) if len(valores) == 1 else None
        return str(ip) if ip else resultado_directo

    saltos = s.PROXIES_CONFIABLES
    if not saltos:
        return resultado_directo
    valores = request.headers.getlist("x-forwarded-for")
    if len(valores) != 1 or len(valores[0]) > 4096:
        return resultado_directo
    partes = valores[0].split(",")
    if len(partes) < saltos or len(partes) > 32:
        return resultado_directo
    cadena = [_direccion_ip(parte) for parte in partes]
    if any(ip is None for ip in cadena):
        return resultado_directo
    # Contar desde la derecha descarta los prefijos que puede aportar el cliente.
    # Cada salto a la derecha del cliente elegido debe ser además un proxy declarado.
    if any(not confiable(ip) for ip in cadena[len(cadena) - saltos + 1:]):
        return resultado_directo
    return str(cadena[-saltos])


async def verificar_acceso(request: Request) -> dict[str, Any]:
    """Toda API profesional exige un JWT real; una cookie sola no la autoriza."""
    if getattr(request.state, "usuario_verificado_bearer", False):
        return request.state.usuario
    auth_header = request.headers.get("authorization", "").strip()
    esquema, _, token = auth_header.partition(" ")
    token = token.strip() if esquema.lower() == "bearer" else ""
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Inicia sesión para acceder al espacio profesional.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        usuario = await supabase_service.validar_token_supabase(token)
    except supabase_service.ErrorSupabase as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None
    if not usuario:
        raise HTTPException(
            status_code=401,
            detail="Tu sesión ha expirado o no es válida. Inicia sesión nuevamente.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    request.state.usuario = usuario
    request.state.user_id = usuario["id"]
    request.state.usuario_verificado_bearer = True
    return usuario


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
