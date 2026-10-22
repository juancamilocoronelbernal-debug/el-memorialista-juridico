"""
El Memorialista · control de acceso y límites de uso (v2.2)
Mientras no existan cuentas de usuario, esto evita que cualquiera use tu clave de IA gratis.
"""
import hmac
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

from app.config import get_settings


def ip_cliente(request: Request) -> str:
    reenviada = request.headers.get("x-forwarded-for", "")
    if reenviada:
        primera = reenviada.split(",")[0].strip()
        if primera:
            return primera[:64]
    return request.client.host if request.client else "desconocida"


def verificar_acceso(request: Request) -> None:
    codigo = get_settings().APP_ACCESS_CODE.strip()
    if not codigo:
        return
    enviado = request.headers.get("x-codigo-acceso", "").strip()
    if not enviado or not hmac.compare_digest(enviado.encode("utf-8"), codigo.encode("utf-8")):
        raise HTTPException(
            status_code=401,
            detail="Esta versión de El Memorialista requiere un código de acceso válido.",
        )


class Limitador:
    """Ventanas deslizantes en memoria. Suficiente para una sola instancia en Render."""

    def __init__(self) -> None:
        self._eventos = defaultdict(deque)
        self._ultima_limpieza = time.monotonic()

    def _reglas(self, accion: str, ip: str) -> list:
        s = get_settings()
        if accion == "redactar":
            return [
                (f"r:{ip}:v", s.VENTANA_MINUTOS * 60, s.LIMITE_POR_VENTANA,
                 "Hiciste muchas redacciones seguidas. Espera unos {min} min y vuelve a intentarlo."),
                (f"r:{ip}:d", 86400, s.LIMITE_DIA_IP,
                 "Llegaste al límite diario de redacciones de esta versión. Vuelve a intentarlo mañana."),
                ("r:global:d", 86400, s.LIMITE_DIA_GLOBAL,
                 "El servicio alcanzó su límite diario de redacciones. Intenta de nuevo mañana."),
            ]
        if accion in ("citas", "revisar"):
            return [
                (f"{accion[0]}:{ip}:h", 3600, max(100, s.LIMITE_ESTILO_HORA * 6),
                 "Revisaste muchos escritos seguidos. Espera unos {min} min."),
            ]
        return [
            (f"e:{ip}:h", 3600, s.LIMITE_ESTILO_HORA,
             "Analizaste muchas muestras seguidas. Espera unos {min} min."),
        ]

    def verificar(self, request: Request, accion: str) -> None:
        ahora = time.monotonic()
        reglas = self._reglas(accion, ip_cliente(request))
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
                    detail=mensaje.format(min=max(1, round(espera / 60))),
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
