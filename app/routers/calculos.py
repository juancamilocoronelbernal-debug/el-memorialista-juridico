"""El Memorialista · Router de Cálculos Jurídicos, Laborales y Financieros."""
from app.services.calculos import (
    router,
    calcular_liquidacion_laboral,
    calcular_intereses_moratorios,
    calcular_indexacion_ipc,
    cargar_catalogo_tasas_sfc,
    cargar_catalogo_ipc,
    LiquidacionLaboralRequest,
    LiquidacionLaboralResponse,
    InteresesMoratoriosRequest,
    InteresesMoratoriosResponse,
    IndexacionRequest,
    IndexacionResponse,
)

__all__ = [
    "router",
    "calcular_liquidacion_laboral",
    "calcular_intereses_moratorios",
    "calcular_indexacion_ipc",
    "cargar_catalogo_tasas_sfc",
    "cargar_catalogo_ipc",
    "LiquidacionLaboralRequest",
    "LiquidacionLaboralResponse",
    "InteresesMoratoriosRequest",
    "InteresesMoratoriosResponse",
    "IndexacionRequest",
    "IndexacionResponse",
]
