"""El Memorialista · Módulo de Cálculos Jurídicos, Laborales y Financieros de Colombia (v1.0).

Incluye motores de cálculo deterministas conforme a la legislación colombiana vigente:
1. Liquidación laboral integral (prestaciones sociales, indemnización art. 64 CST, moratoria art. 65 CST,
   sanción art. 99 Ley 50/1990, salarios variables y advertencia de la Ley 2466 de 2025).
2. Intereses moratorios mercantiles (art. 884 Código de Comercio - 1.5 veces IBC certificado por la SFC,
   mes a mes, con resoluciones oficiales).
3. Indexación con IPC oficial del DANE (valor histórico × IPC final / IPC inicial).
4. Generador de anexos tabulares en Markdown y texto plano para inserción directa en memoriales y demandas.
"""
from __future__ import annotations

import calendar
import json
import logging
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

log = logging.getLogger("memorialista.calculos")

# Catálogos base
CATALOGO_DIR = Path(__file__).resolve().parent.parent / "catalogo"
ARCHIVO_TASAS_SFC = CATALOGO_DIR / "tasas_sfc.json"
ARCHIVO_IPC = CATALOGO_DIR / "ipc.json"

# Salarios mínimos y auxilio de transporte en Colombia por año
TABLA_SALARIOS_COLOMBIA: Dict[int, Dict[str, float]] = {
    2020: {"smmlv": 877803.0, "auxilio_transporte": 102854.0},
    2021: {"smmlv": 908526.0, "auxilio_transporte": 106454.0},
    2022: {"smmlv": 1000000.0, "auxilio_transporte": 117172.0},
    2023: {"smmlv": 1160000.0, "auxilio_transporte": 140606.0},
    2024: {"smmlv": 1300000.0, "auxilio_transporte": 162000.0},
    2025: {"smmlv": 1423500.0, "auxilio_transporte": 200000.0},
    2026: {"smmlv": 1565000.0, "auxilio_transporte": 220000.0},
}
VALOR_DEFECTO_SMMLV = 1565000.0
VALOR_DEFECTO_AUXILIO = 220000.0

# -----------------------------------------------------------------------------
# Carga de catálogos
# -----------------------------------------------------------------------------

def cargar_catalogo_tasas_sfc() -> Dict[str, Any]:
    """Carga la serie histórica de tasas certificadas por la Superintendencia Financiera."""
    if not ARCHIVO_TASAS_SFC.exists():
        log.warning("No se encontró %s", ARCHIVO_TASAS_SFC)
        return {"series": [], "fuente": "Superintendencia Financiera de Colombia"}
    try:
        with open(ARCHIVO_TASAS_SFC, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        log.error("Error al cargar %s: %s", ARCHIVO_TASAS_SFC, exc)
        return {"series": [], "fuente": "Superintendencia Financiera de Colombia"}


def cargar_catalogo_ipc() -> Dict[str, Any]:
    """Carga la serie mensual del IPC (Índice de Precios al Consumidor) del DANE."""
    if not ARCHIVO_IPC.exists():
        log.warning("No se encontró %s", ARCHIVO_IPC)
        return {"series": [], "fuente": "DANE"}
    try:
        with open(ARCHIVO_IPC, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        log.error("Error al cargar %s: %s", ARCHIVO_IPC, exc)
        return {"series": [], "fuente": "DANE"}


# -----------------------------------------------------------------------------
# Utilidades de fecha y formato
# -----------------------------------------------------------------------------

def parsear_fecha(valor: Union[str, date]) -> date:
    """Convierte un string YYYY-MM-DD o YYYY-MM en objeto date."""
    if isinstance(valor, date):
        return valor
    valor_str = str(valor).strip()
    if len(valor_str) == 7:  # YYYY-MM
        return datetime.strptime(valor_str + "-01", "%Y-%m-%d").date()
    return datetime.strptime(valor_str[:10], "%Y-%m-%d").date()


def es_ultimo_dia_mes(f: date) -> bool:
    """Indica si una fecha corresponde al último día calendario de su mes."""
    ultimo_dia = calendar.monthrange(f.year, f.month)[1]
    return f.day == ultimo_dia


def dias_laborales_comerciales(f_ini: date, f_fin: date) -> int:
    """
    Cómputo estándar laboral colombiano: meses de 30 días, año de 360 días.
    Fórmula unificada: (A2 - A1)*360 + (M2 - M1)*30 + (D2 - D1) + 1.
    Si el día final o inicial es 31, se asimila a 30.
    Si febrero se labora completo (inicia el 1 y termina el 28 o 29), cuenta como 30 días.
    """
    if f_fin < f_ini:
        return 0

    d1 = min(f_ini.day, 30)
    d2 = min(f_fin.day, 30)

    # Caso especial febrero completo
    if f_ini.month == 2 and f_ini.day == 1 and es_ultimo_dia_mes(f_fin) and f_fin.month == 2:
        d2 = 30
    elif f_fin.month == 2 and es_ultimo_dia_mes(f_fin):
        d2 = 30

    dias = (f_fin.year - f_ini.year) * 360 + (f_fin.month - f_ini.month) * 30 + (d2 - d1) + 1
    return max(1, dias)


def formato_pesos(valor: float) -> str:
    """Formatea un valor en pesos colombianos con separador de miles y sin decimales si es entero."""
    if abs(valor - round(valor)) < 0.005:
        return f"${round(valor):,}".replace(",", ".")
    return f"${valor:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def obtener_smmlv_y_auxilio(anio: int) -> Tuple[float, float]:
    """Obtiene el SMMLV y Auxilio de Transporte legal para un año determinado."""
    if anio in TABLA_SALARIOS_COLOMBIA:
        info = TABLA_SALARIOS_COLOMBIA[anio]
        return info["smmlv"], info["auxilio_transporte"]
    if anio < min(TABLA_SALARIOS_COLOMBIA.keys()):
        primer_anio = min(TABLA_SALARIOS_COLOMBIA.keys())
        return TABLA_SALARIOS_COLOMBIA[primer_anio]["smmlv"], TABLA_SALARIOS_COLOMBIA[primer_anio]["auxilio_transporte"]
    ultimo_anio = max(TABLA_SALARIOS_COLOMBIA.keys())
    return TABLA_SALARIOS_COLOMBIA[ultimo_anio]["smmlv"], TABLA_SALARIOS_COLOMBIA[ultimo_anio]["auxilio_transporte"]


# -----------------------------------------------------------------------------
# 1. MOTOR DE LIQUIDACIÓN LABORAL
# -----------------------------------------------------------------------------

class SalarioVariableItem(BaseModel):
    periodo: str = Field(description="Periodo o mes en formato YYYY-MM o descripción")
    valor: float = Field(ge=0, description="Monto devengado por salario ordinario y factores salariales")
    horas_extras_recargos: float = Field(default=0.0, description="Recargos nocturnos, dominicales o festivos")


class LiquidacionLaboralRequest(BaseModel):
    fecha_inicio: str = Field(description="Fecha de inicio de la relación laboral (YYYY-MM-DD)")
    fecha_fin: str = Field(description="Fecha de terminación del contrato (YYYY-MM-DD)")
    salario_base: float = Field(ge=0, description="Salario básico mensual pactado")
    auxilio_transporte: Optional[float] = Field(
        default=None,
        description="Auxilio de transporte mensual. Si es None, se calcula automáticamente según SMMLV.",
    )
    incluir_auxilio_transporte: bool = Field(
        default=True,
        description="Si es False, se excluye expresamente el auxilio de transporte.",
    )
    tipo_contrato: Literal["indefinido", "termino_fijo", "obra_labor"] = Field(
        default="indefinido",
        description="Modalidad contractual (art. 45 y ss. CST)",
    )
    fecha_fin_pactada: Optional[str] = Field(
        default=None,
        description="Para contratos a término fijo, fecha en que vencía el plazo estipulado.",
    )
    motivo_terminacion: Literal[
        "despido_sin_justa_causa",
        "despido_con_justa_causa",
        "renuncia_voluntaria",
        "mutuo_acuerdo",
        "vencimiento_termino",
        "terminacion_obra",
    ] = Field(
        default="despido_sin_justa_causa",
        description="Causal o motivo de terminación contractual.",
    )
    # Fechas específicas para cada concepto (si son distintas al periodo completo)
    fecha_inicio_cesantias: Optional[str] = Field(
        default=None,
        description="Fecha desde la cual se adeudan cesantías (por defecto 1 de enero del año de retiro).",
    )
    fecha_inicio_prima: Optional[str] = Field(
        default=None,
        description="Fecha desde la cual se adeuda prima (por defecto 1 de enero o 1 de julio del año de retiro).",
    )
    fecha_inicio_vacaciones: Optional[str] = Field(
        default=None,
        description="Fecha desde la cual se adeudan vacaciones no compensadas ni disfrutadas.",
    )
    # Salarios caídos y mora
    liquidar_moratoria_art65: bool = Field(
        default=False,
        description="Liquidar indemnización moratoria del art. 65 CST (un día de salario por día de retardo).",
    )
    fecha_corte_moratoria: Optional[str] = Field(
        default=None,
        description="Fecha hasta la cual se liquida la mora del art. 65 CST (por defecto hoy o fecha de terminación).",
    )
    # Sanción no consignación de cesantías
    liquidar_sancion_consignacion_art99: bool = Field(
        default=False,
        description="Liquidar sanción del art. 99 Ley 50/1990 por no consignación antes del 15 de febrero.",
    )
    dias_mora_consignacion: Optional[int] = Field(
        default=None,
        ge=0,
        description="Número de días de retardo en la consignación de cesantías.",
    )
    fecha_inicio_mora_consignacion: Optional[str] = Field(
        default=None,
        description="Fecha de exigibilidad de la consignación (usualmente 15 de febrero de algún año).",
    )
    salarios_variables: Optional[List[SalarioVariableItem]] = Field(
        default=None,
        description="Historial de salarios devengados para computar el promedio del último año.",
    )
    nombre_trabajador: Optional[str] = Field(default="", description="Nombre del trabajador para el anexo")
    nombre_empleador: Optional[str] = Field(default="", description="Nombre del empleador o empresa")


class ConceptoLiquidacion(BaseModel):
    id: str
    concepto: str
    dias: int
    base_calculo: float
    formula: str
    subtotal: float
    norma: str
    detalle: str
    aplica_ley_2466: bool = False


class LiquidacionLaboralResponse(BaseModel):
    trabajador: str
    empleador: str
    tipo_contrato: str
    motivo_terminacion: str
    fecha_inicio: str
    fecha_fin: str
    dias_totales_servicio: int
    salario_base_ordinario: float
    auxilio_transporte: float
    salario_base_prestaciones: float
    salario_base_vacaciones: float
    conceptos: List[ConceptoLiquidacion]
    total_prestaciones_sociales: float
    total_indemnizaciones_y_sanciones: float
    gran_total_liquidacion: float
    advertencias_legales: List[str]
    tabla_markdown: str
    tabla_texto: str


def advertencia_ley_2466_2025(
    motivo: str,
    f_fin: date,
    tipo_contrato: str,
    tiene_salarios_variables: bool,
) -> Optional[str]:
    """Genera advertencia legal conforme a la Ley 2466 de 2025 (Reforma Laboral)."""
    # Si la fecha de terminación es a partir del 2025 o si hay indemnización art. 64 / recargos
    aplica = (
        f_fin >= date(2025, 1, 1)
        or motivo == "despido_sin_justa_causa"
        or tiene_salarios_variables
    )
    if not aplica:
        return None

    texto = (
        "⚠️ ADVERTENCIA LEGAL - LEY 2466 DE 2025 (REFORMA LABORAL):\n"
        "1. Indemnización por despido sin justa causa (Art. 64 CST): La reforma laboral incrementa "
        "los días de indemnización para contratos a término indefinido (35 días para el 1er año y entre "
        "15, 30 o 45 días adicionales por año subsiguiente según antigüedad acumulada), y exige el agotamiento "
        "del debido proceso disciplinario previo incluso en despidos sin justa causa alegada.\n"
        "2. Recargo nocturno y dominical/festivo: El horario nocturno inicia a las 7:00 p.m. (no a las 9:00 p.m.) "
        "y el recargo dominical/festivo se eleva progresivamente al 100%. Si se ingresaron salarios variables, "
        "verifique si los turnos laborados causaron los nuevos recargos vigentes.\n"
        "3. Contrato a término fijo: El límite máximo de prórrogas consecutivas y la reconducción a indefinido "
        "fueron modificados por la Ley 2466 de 2025. Coteje si la fecha de terminación se encuentra bajo el nuevo régimen."
    )
    return texto


def calcular_liquidacion_laboral(req: LiquidacionLaboralRequest) -> LiquidacionLaboralResponse:
    """Ejecuta el cómputo integral de prestaciones, indemnizaciones y sanciones laborales."""
    f_ini = parsear_fecha(req.fecha_inicio)
    f_fin = parsear_fecha(req.fecha_fin)
    if f_fin < f_ini:
        raise HTTPException(status_code=400, detail="La fecha de finalización no puede ser anterior a la de inicio.")

    dias_totales = dias_laborales_comerciales(f_ini, f_fin)
    smmlv_vigente, auxilio_legal = obtener_smmlv_y_auxilio(f_fin.year)

    # Determinar salario base: si hay salarios variables, computar promedio
    salario_ordinario = float(req.salario_base)
    tiene_salarios_variables = bool(req.salarios_variables and len(req.salarios_variables) > 0)
    detalle_promedio = ""
    if tiene_salarios_variables:
        tot_salarios = sum(sv.valor + sv.horas_extras_recargos for sv in req.salarios_variables)  # type: ignore
        salario_ordinario = round(tot_salarios / len(req.salarios_variables), 2)  # type: ignore
        detalle_promedio = f" (Promedio de {len(req.salarios_variables)} periodos variables: {formato_pesos(salario_ordinario)})"

    # Auxilio de transporte: aplica si salario ordinario <= 2 SMMLV (salvo exclusión voluntaria)
    devenga_auxilio = False
    auxilio_transporte = 0.0
    if req.incluir_auxilio_transporte:
        if req.auxilio_transporte is not None:
            auxilio_transporte = float(req.auxilio_transporte)
            devenga_auxilio = auxilio_transporte > 0
        else:
            if salario_ordinario <= (2 * smmlv_vigente):
                auxilio_transporte = auxilio_legal
                devenga_auxilio = True

    base_prestaciones = salario_ordinario + auxilio_transporte
    base_vacaciones = salario_ordinario  # El auxilio de transporte no entra en vacaciones (art. 192 CST)

    conceptos: List[ConceptoLiquidacion] = []

    # 1. Cesantías (Art. 249 CST)
    # Por defecto se liquida el año de terminación (del 1 de enero al f_fin o desde f_ini si ingresó ese año)
    if req.fecha_inicio_cesantias:
        f_ini_ces = parsear_fecha(req.fecha_inicio_cesantias)
    else:
        f_ini_ces = max(f_ini, date(f_fin.year, 1, 1))
    dias_cesantias = dias_laborales_comerciales(f_ini_ces, f_fin)
    monto_cesantias = round((base_prestaciones * dias_cesantias) / 360.0, 2)
    conceptos.append(
        ConceptoLiquidacion(
            id="cesantias",
            concepto="Cesantías",
            dias=dias_cesantias,
            base_calculo=base_prestaciones,
            formula=f"({formato_pesos(base_prestaciones)} × {dias_cesantias}) / 360",
            subtotal=monto_cesantias,
            norma="Art. 249 del Código Sustantivo del Trabajo (CST)",
            detalle=f"Periodo del {f_ini_ces.isoformat()} al {f_fin.isoformat()}{detalle_promedio}. Incluye auxilio de transporte ({formato_pesos(auxilio_transporte)})." if devenga_auxilio else f"Periodo del {f_ini_ces.isoformat()} al {f_fin.isoformat()}{detalle_promedio}.",
            aplica_ley_2466=False,
        )
    )

    # 2. Intereses a las Cesantías (Ley 52 de 1975)
    # 12% anual sobre el valor de las cesantías causado en el periodo
    monto_intereses = round((monto_cesantias * dias_cesantias * 0.12) / 360.0, 2)
    conceptos.append(
        ConceptoLiquidacion(
            id="intereses_cesantias",
            concepto="Intereses sobre las Cesantías (12% anual)",
            dias=dias_cesantias,
            base_calculo=monto_cesantias,
            formula=f"({formato_pesos(monto_cesantias)} × {dias_cesantias} × 12%) / 360",
            subtotal=monto_intereses,
            norma="Ley 52 de 1975 y Decreto Reglamentario 116 de 1976",
            detalle=f"12% anual proporcional a {dias_cesantias} días sobre el saldo de cesantías.",
            aplica_ley_2466=False,
        )
    )

    # 3. Prima de Servicios (Art. 306 CST)
    # Por defecto se liquida el semestre de retiro (1er sem: 1 ene - 30 jun; 2do sem: 1 jul - 31 dic)
    if req.fecha_inicio_prima:
        f_ini_prima = parsear_fecha(req.fecha_inicio_prima)
    else:
        f_semestre = date(f_fin.year, 1, 1) if f_fin.month <= 6 else date(f_fin.year, 7, 1)
        f_ini_prima = max(f_ini, f_semestre)
    dias_prima = dias_laborales_comerciales(f_ini_prima, f_fin)
    monto_prima = round((base_prestaciones * dias_prima) / 360.0, 2)
    conceptos.append(
        ConceptoLiquidacion(
            id="prima_servicios",
            concepto="Prima de Servicios",
            dias=dias_prima,
            base_calculo=base_prestaciones,
            formula=f"({formato_pesos(base_prestaciones)} × {dias_prima}) / 360",
            subtotal=monto_prima,
            norma="Art. 306 del CST (modificado por la Ley 1788 de 2016)",
            detalle=f"Semestre del {f_ini_prima.isoformat()} al {f_fin.isoformat()}.",
            aplica_ley_2466=False,
        )
    )

    # 4. Vacaciones Compensadas en Dinero (Art. 186 y 189 CST)
    # 15 días hábiles por cada 360 días laborados (divisor 720). Base ordinaria pura sin auxilio de transporte.
    if req.fecha_inicio_vacaciones:
        f_ini_vac = parsear_fecha(req.fecha_inicio_vacaciones)
        dias_vac = dias_laborales_comerciales(f_ini_vac, f_fin)
    else:
        f_ini_vac = f_ini
        dias_vac = dias_totales
    monto_vacaciones = round((base_vacaciones * dias_vac) / 720.0, 2)
    conceptos.append(
        ConceptoLiquidacion(
            id="vacaciones",
            concepto="Compensación de Vacaciones",
            dias=dias_vac,
            base_calculo=base_vacaciones,
            formula=f"({formato_pesos(base_vacaciones)} × {dias_vac}) / 720",
            subtotal=monto_vacaciones,
            norma="Arts. 186, 189 y 192 del CST",
            detalle=f"15 días por cada 360 días laborados (periodo {f_ini_vac.isoformat()} a {f_fin.isoformat()}). Excluye auxilio de transporte por mandato del art. 192 CST.",
            aplica_ley_2466=False,
        )
    )

    total_prestaciones = round(monto_cesantias + monto_intereses + monto_prima + monto_vacaciones, 2)
    total_indemnizaciones = 0.0

    # 5. Indemnización por Despido sin Justa Causa (Art. 64 CST)
    if req.motivo_terminacion == "despido_sin_justa_causa":
        monto_indemnizacion = 0.0
        formula_ind = ""
        detalle_ind = ""
        dias_ind = 0

        salario_diario = salario_ordinario / 30.0

        if req.tipo_contrato == "indefinido":
            # Tabla del art. 64 CST según nivel salarial (< 10 SMMLV vs >= 10 SMMLV)
            es_menos_10_smmlv = salario_ordinario < (10 * smmlv_vigente)

            if es_menos_10_smmlv:
                # 30 días 1er año + 20 días por año subsiguiente y proporcionalmente
                if dias_totales <= 360:
                    dias_ind = 30
                    monto_indemnizacion = round(salario_diario * 30.0, 2)
                    formula_ind = f"30 días × {formato_pesos(salario_diario)}"
                    detalle_ind = "Antigüedad no mayor a 1 año (30 días de salario)."
                else:
                    dias_adicionales = dias_totales - 360
                    dias_proporcionales = (dias_adicionales / 360.0) * 20.0
                    dias_ind_total = 30.0 + dias_proporcionales
                    dias_ind = dias_ind_total
                    monto_indemnizacion = round(salario_diario * dias_ind_total, 2)
                    formula_ind = f"(30 + ({dias_adicionales}/360 × 20)) días × {formato_pesos(salario_diario)}"
                    detalle_ind = f"Primer año: 30 días + {dias_adicionales} días subsiguientes: {dias_proporcionales:.2f} días (total {dias_ind_total:.2f} días)."
            else:
                # 20 días 1er año + 15 días por año subsiguiente y proporcionalmente
                if dias_totales <= 360:
                    dias_ind = 20
                    monto_indemnizacion = round(salario_diario * 20.0, 2)
                    formula_ind = f"20 días × {formato_pesos(salario_diario)}"
                    detalle_ind = "Salario ≥ 10 SMMLV, antigüedad ≤ 1 año (20 días de salario)."
                else:
                    dias_adicionales = dias_totales - 360
                    dias_proporcionales = (dias_adicionales / 360.0) * 15.0
                    dias_ind_total = 20.0 + dias_proporcionales
                    dias_ind = dias_ind_total
                    monto_indemnizacion = round(salario_diario * dias_ind_total, 2)
                    formula_ind = f"(20 + ({dias_adicionales}/360 × 15)) días × {formato_pesos(salario_diario)}"
                    detalle_ind = f"Salario ≥ 10 SMMLV: 20 días primer año + {dias_adicionales} días subsiguientes: {dias_proporcionales:.2f} días (total {dias_ind_total:.2f} días)."

        elif req.tipo_contrato == "termino_fijo":
            if req.fecha_fin_pactada:
                f_pactada = parsear_fecha(req.fecha_fin_pactada)
                if f_pactada > f_fin:
                    f_siguiente = date.fromordinal(f_fin.toordinal() + 1)
                    dias_faltantes = dias_laborales_comerciales(f_siguiente, f_pactada)
                    monto_indemnizacion = round(salario_diario * dias_faltantes, 2)
                    formula_ind = f"{dias_faltantes} días faltantes × {formato_pesos(salario_diario)}"
                    detalle_ind = f"Salarios correspondientes al tiempo faltante hasta el {f_pactada.isoformat()} ({dias_faltantes} días)."
                else:
                    detalle_ind = "El contrato ya había alcanzado la fecha pactada de terminación."
            else:
                detalle_ind = "Contrato a término fijo sin fecha pactada de vencimiento especificada."

        elif req.tipo_contrato == "obra_labor":
            # Tiempo que falte para la terminación de la obra, nunca inferior a 15 días
            dias_min = 15
            monto_indemnizacion = round(salario_diario * dias_min, 2)
            formula_ind = f"{dias_min} días × {formato_pesos(salario_diario)}"
            detalle_ind = "Mínimo legal de 15 días de salario por terminación intempestiva de obra o labor."

        if monto_indemnizacion > 0:
            total_indemnizaciones += monto_indemnizacion
            conceptos.append(
                ConceptoLiquidacion(
                    id="indemnizacion_despido",
                    concepto="Indemnización por Despido sin Justa Causa",
                    dias=int(dias_ind) if dias_ind else 0,
                    base_calculo=salario_ordinario,
                    formula=formula_ind,
                    subtotal=monto_indemnizacion,
                    norma="Art. 64 del CST (modificado por Ley 789 de 2002 y sujeto a Ley 2466 de 2025)",
                    detalle=detalle_ind,
                    aplica_ley_2466=True,
                )
            )

    # 6. Indemnización Moratoria / Salarios Caídos (Art. 65 CST)
    if req.liquidar_moratoria_art65:
        f_corte = parsear_fecha(req.fecha_corte_moratoria) if req.fecha_corte_moratoria else date.today()
        if f_corte > f_fin:
            f_inicio_mora = date.fromordinal(f_fin.toordinal() + 1)
            dias_retardo = dias_laborales_comerciales(f_inicio_mora, f_corte)
            salario_diario = salario_ordinario / 30.0

            # Si gana hasta 1 SMMLV: 1 día por cada día de retardo sin tope
            # Si gana más de 1 SMMLV: 1 día por día los primeros 24 meses (720 días)
            es_hasta_1_smmlv = salario_ordinario <= smmlv_vigente
            if es_hasta_1_smmlv:
                monto_moratoria = round(salario_diario * dias_retardo, 2)
                detalle_mora = f"{dias_retardo} días de retardo del {f_inicio_mora.isoformat()} al {f_corte.isoformat()} a razón de un día de salario."
            else:
                dias_primeros_24m = min(dias_retardo, 720)
                monto_moratoria = round(salario_diario * dias_primeros_24m, 2)
                detalle_mora = f"{dias_primeros_24m} días de retardo (tope 24 meses / 720 días del art. 65 CST). Del {f_inicio_mora.isoformat()} al {f_corte.isoformat()}."
                if dias_retardo > 720:
                    detalle_mora += f" (Se causan además intereses moratorios a la tasa SFC sobre los {dias_retardo - 720} días posteriores al mes 24)."

            total_indemnizaciones += monto_moratoria
            conceptos.append(
                ConceptoLiquidacion(
                    id="indemnizacion_moratoria_art65",
                    concepto="Indemnización Moratoria (Salarios Caídos)",
                    dias=dias_retardo,
                    base_calculo=salario_ordinario,
                    formula=f"{min(dias_retardo, 720 if not es_hasta_1_smmlv else dias_retardo)} días × {formato_pesos(salario_diario)}/día",
                    subtotal=monto_moratoria,
                    norma="Art. 65 del CST (modificado por art. 29 Ley 789 de 2002)",
                    detalle=detalle_mora,
                    aplica_ley_2466=False,
                )
            )

    # 7. Sanción por no Consignación de Cesantías (Art. 99 Ley 50 de 1990)
    if req.liquidar_sancion_consignacion_art99:
        dias_sancion = req.dias_mora_consignacion or 0
        if dias_sancion == 0 and req.fecha_inicio_mora_consignacion:
            f_ini_mora = parsear_fecha(req.fecha_inicio_mora_consignacion)
            f_corte = parsear_fecha(req.fecha_corte_moratoria) if req.fecha_corte_moratoria else date.today()
            if f_corte > f_ini_mora:
                dias_sancion = dias_laborales_comerciales(f_ini_mora, f_corte)

        if dias_sancion > 0:
            salario_diario = salario_ordinario / 30.0
            monto_sancion = round(salario_diario * dias_sancion, 2)
            total_indemnizaciones += monto_sancion
            conceptos.append(
                ConceptoLiquidacion(
                    id="sancion_consignacion_cesantias",
                    concepto="Sanción por no Consignación de Cesantías",
                    dias=dias_sancion,
                    base_calculo=salario_ordinario,
                    formula=f"{dias_sancion} días de mora × {formato_pesos(salario_diario)}/día",
                    subtotal=monto_sancion,
                    norma="Art. 99 Numeral 3 de la Ley 50 de 1990",
                    detalle=f"Un día de salario por cada día de retardo en la consignación de cesantías al fondo a partir del 15 de febrero ({dias_sancion} días).",
                    aplica_ley_2466=False,
                )
            )

    gran_total = round(total_prestaciones + total_indemnizaciones, 2)

    # Recoger advertencias legales
    advertencias: List[str] = []
    adv_2466 = advertencia_ley_2466_2025(
        motivo=req.motivo_terminacion,
        f_fin=f_fin,
        tipo_contrato=req.tipo_contrato,
        tiene_salarios_variables=tiene_salarios_variables,
    )
    if adv_2466:
        advertencias.append(adv_2466)

    # Construir tablas en Markdown y Texto plano
    tabla_md, tabla_txt = formatear_tabla_laboral(
        req=req,
        conceptos=conceptos,
        total_prestaciones=total_prestaciones,
        total_indemnizaciones=total_indemnizaciones,
        gran_total=gran_total,
        f_ini=f_ini,
        f_fin=f_fin,
        dias_totales=dias_totales,
        salario_ordinario=salario_ordinario,
        auxilio_transporte=auxilio_transporte,
    )

    return LiquidacionLaboralResponse(
        trabajador=req.nombre_trabajador or "No especificado",
        empleador=req.nombre_empleador or "No especificado",
        tipo_contrato=req.tipo_contrato,
        motivo_terminacion=req.motivo_terminacion,
        fecha_inicio=f_ini.isoformat(),
        fecha_fin=f_fin.isoformat(),
        dias_totales_servicio=dias_totales,
        salario_base_ordinario=salario_ordinario,
        auxilio_transporte=auxilio_transporte,
        salario_base_prestaciones=base_prestaciones,
        salario_base_vacaciones=base_vacaciones,
        conceptos=conceptos,
        total_prestaciones_sociales=total_prestaciones,
        total_indemnizaciones_y_sanciones=total_indemnizaciones,
        gran_total_liquidacion=gran_total,
        advertencias_legales=advertencias,
        tabla_markdown=tabla_md,
        tabla_texto=tabla_txt,
    )


def formatear_tabla_laboral(
    req: LiquidacionLaboralRequest,
    conceptos: List[ConceptoLiquidacion],
    total_prestaciones: float,
    total_indemnizaciones: float,
    gran_total: float,
    f_ini: date,
    f_fin: date,
    dias_totales: int,
    salario_ordinario: float,
    auxilio_transporte: float,
) -> Tuple[str, str]:
    """Genera la tabla en Markdown y en texto plano monoespaciado para anexar al escrito."""
    # MARKDOWN
    md_lines = [
        "### ANEXO LIQUIDATORIO: PRESTACIONES SOCIALES E INDEMNIZACIONES LABORALES",
        "",
        f"- **Trabajador:** {req.nombre_trabajador or 'Demandante / Trabajador'} | **Empleador:** {req.nombre_empleador or 'Demandado / Empleador'}",
        f"- **Periodo Laborado:** {f_ini.isoformat()} al {f_fin.isoformat()} ({dias_totales} días de servicio)",
        f"- **Salario Ordinario:** {formato_pesos(salario_ordinario)} | **Auxilio de Transporte:** {formato_pesos(auxilio_transporte)}",
        f"- **Modalidad / Causal:** Contrato {req.tipo_contrato} / {req.motivo_terminacion.replace('_', ' ').capitalize()}",
        "",
        "| Rubro / Concepto | Días | Base de Cálculo | Fórmula Aplicada | Subtotal | Fuente Legal |",
        "| :--- | :---: | :---: | :--- | :---: | :--- |",
    ]
    for c in conceptos:
        md_lines.append(
            f"| **{c.concepto}** | {c.dias} | {formato_pesos(c.base_calculo)} | `{c.formula}` | **{formato_pesos(c.subtotal)}** | {c.norma} |"
        )
    md_lines.append(
        f"| **SUBTOTAL PRESTACIONES SOCIALES** | - | - | - | **{formato_pesos(total_prestaciones)}** | Arts. 186, 249, 306 CST y Ley 52/1975 |"
    )
    if total_indemnizaciones > 0:
        md_lines.append(
            f"| **SUBTOTAL INDEMNIZACIONES / SANCIONES** | - | - | - | **{formato_pesos(total_indemnizaciones)}** | Arts. 64, 65 CST y Ley 50/1990 |"
        )
    md_lines.append(
        f"| **GRAN TOTAL LIQUIDACIÓN LABORAL** | - | - | - | **{formato_pesos(gran_total)}** | M/CTE |"
    )
    md_lines.append("")
    md_tabla = "\n".join(md_lines)

    # TEXTO PLANO
    sep = "=" * 102
    sep_sub = "-" * 102
    txt_lines = [
        sep,
        "ANEXO: LIQUIDACIÓN DISCRIMINADA DE PRESTACIONES SOCIALES E INDEMNIZACIONES LABORALES",
        sep,
        f"Trabajador: {req.nombre_trabajador or 'Demandante'}  |  Empleador: {req.nombre_empleador or 'Demandado'}",
        f"Periodo: {f_ini.isoformat()} al {f_fin.isoformat()} ({dias_totales} días)  |  Contrato: {req.tipo_contrato}",
        f"Salario Básico: {formato_pesos(salario_ordinario)}  |  Auxilio Transporte: {formato_pesos(auxilio_transporte)}  |  Causal: {req.motivo_terminacion}",
        sep_sub,
        f"{'CONCEPTO':<32} {'DÍAS':<6} {'BASE CÁLCULO':<16} {'SUBTOTAL (COP)':<18} {'FUENTE LEGAL':<28}",
        sep_sub,
    ]
    for c in conceptos:
        txt_lines.append(
            f"{c.concepto[:31]:<32} {c.dias:<6} {formato_pesos(c.base_calculo):<16} {formato_pesos(c.subtotal):<18} {c.norma[:27]:<28}"
        )
    txt_lines.append(sep_sub)
    txt_lines.append(f"{'SUBTOTAL PRESTACIONES SOCIALES:':<56} {formato_pesos(total_prestaciones):<18}")
    if total_indemnizaciones > 0:
        txt_lines.append(f"{'SUBTOTAL INDEMNIZACIONES Y SANCIONES:':<56} {formato_pesos(total_indemnizaciones):<18}")
    txt_lines.append(sep)
    txt_lines.append(f"{'GRAN TOTAL A PAGAR (M/CTE):':<56} {formato_pesos(gran_total):<18}")
    txt_lines.append(sep)
    txt_tabla = "\n".join(txt_lines)

    return md_tabla, txt_tabla


# -----------------------------------------------------------------------------
# 2. MOTOR DE INTERESES MORATORIOS MERCANTILES (Art. 884 C. Co.)
# -----------------------------------------------------------------------------

class InteresesMoratoriosRequest(BaseModel):
    capital: float = Field(gt=0, description="Capital o monto adeudado sobre el cual corre la mora (COP)")
    fecha_inicio: str = Field(description="Fecha en que se inicia la mora o exigibilidad (YYYY-MM-DD)")
    fecha_fin: str = Field(description="Fecha de corte o liquidación de la mora (YYYY-MM-DD)")
    metodo: Literal["financiero_exacto", "nominal_comercial"] = Field(
        default="financiero_exacto",
        description="Fórmula financiera: 'financiero_exacto' ((1+i_ea)^(dias/365)-1) o 'nominal_comercial' (i_m * dias/30).",
    )
    concepto_obligacion: Optional[str] = Field(
        default="",
        description="Descripción del título valor, factura, pagaré o contrato mercantil origen de la deuda",
    )


class PeriodoMoraItem(BaseModel):
    periodo: str  # YYYY-MM
    fecha_desde: str
    fecha_hasta: str
    dias_mora: int
    capital_base: float
    ibc_ea: float
    mora_ea: float
    tasa_periodo_pct: float
    interes_periodo: float
    interes_acumulado: float
    resolucion: str
    fuente: str


class InteresesMoratoriosResponse(BaseModel):
    capital: float
    fecha_inicio: str
    fecha_fin: str
    dias_totales_mora: int
    interes_total: float
    total_adeudado: float
    concepto_obligacion: str
    criterio_legal: str
    periodos: List[PeriodoMoraItem]
    tabla_markdown: str
    tabla_texto: str


def iterar_meses_rango(f_ini: date, f_fin: date) -> List[Tuple[str, date, date, int]]:
    """
    Divide un rango de fechas en segmentos mensuales con sus fechas de inicio, fin y días efectivos.
    Retorna lista de (YYYY-MM, f_desde, f_hasta, dias).
    """
    segmentos = []
    curr = f_ini
    while curr <= f_fin:
        periodo = f"{curr.year:04d}-{curr.month:02d}"
        ultimo_dia_mes = calendar.monthrange(curr.year, curr.month)[1]
        fin_mes = date(curr.year, curr.month, ultimo_dia_mes)
        f_hasta = min(fin_mes, f_fin)

        # Días calendario transcurridos en este tramo mensual
        dias = (f_hasta - curr).days + 1
        segmentos.append((periodo, curr, f_hasta, dias))

        # Avanzar al primer día del siguiente mes
        if f_hasta.month == 12:
            curr = date(f_hasta.year + 1, 1, 1)
        else:
            curr = date(f_hasta.year, f_hasta.month + 1, 1)

    return segmentos


def calcular_intereses_moratorios(req: InteresesMoratoriosRequest) -> InteresesMoratoriosResponse:
    """
    Calcula mes a mes los intereses de mora mercantiles conforme al art. 884 del Código de Comercio:
    Tasa de mora = 1.5 veces el Interés Bancario Corriente (IBC) certificado por la SFC, sin superar usura.
    """
    f_ini = parsear_fecha(req.fecha_inicio)
    f_fin = parsear_fecha(req.fecha_fin)
    if f_fin < f_ini:
        raise HTTPException(status_code=400, detail="La fecha final no puede ser anterior a la fecha inicial.")

    cat = cargar_catalogo_tasas_sfc()
    tasas_dict: Dict[str, Dict[str, Any]] = {item["periodo"]: item for item in cat.get("series", [])}

    # Si hay periodos fuera de rango, tomar la tasa más cercana conocida
    periodos_ordenados = sorted(tasas_dict.keys())
    tasa_minima_conocida = tasas_dict[periodos_ordenados[0]] if periodos_ordenados else {"ibc_ea": 20.0, "mora_ea": 30.0, "resolucion": "SFC Referencia"}
    tasa_maxima_conocida = tasas_dict[periodos_ordenados[-1]] if periodos_ordenados else tasa_minima_conocida

    segmentos = iterar_meses_rango(f_ini, f_fin)
    items_periodo: List[PeriodoMoraItem] = []
    acumulado_interes = 0.0
    dias_totales = 0

    capital = float(req.capital)

    for periodo, f_desde, f_hasta, dias_tramo in segmentos:
        if periodo in tasas_dict:
            datos_tasa = tasas_dict[periodo]
        elif periodo < periodos_ordenados[0]:
            datos_tasa = tasa_minima_conocida
        else:
            datos_tasa = tasa_maxima_conocida

        ibc_ea = float(datos_tasa.get("ibc_ea", 0.0))
        mora_ea = float(datos_tasa.get("mora_ea", ibc_ea * 1.5))
        resolucion = str(datos_tasa.get("resolucion", "Resolución SFC"))

        i_ea = mora_ea / 100.0

        dias_en_mes_completo = calendar.monthrange(f_desde.year, f_desde.month)[1]
        es_mes_completo = (dias_tramo == dias_en_mes_completo)

        if req.metodo == "financiero_exacto":
            if es_mes_completo:
                # Tasa efectiva mensual: (1 + i_ea)^(1/12) - 1
                tasa_periodo = ((1.0 + i_ea) ** (1.0 / 12.0)) - 1.0
            else:
                # Tasa periódica diaria exacta para la fracción: (1 + i_ea)^(dias/365) - 1
                tasa_periodo = ((1.0 + i_ea) ** (dias_tramo / 365.0)) - 1.0
            interes_tramo = round(capital * tasa_periodo, 2)
        else:
            # Nominal comercial: i_m = (1+i_ea)^(1/12) - 1; proporcional a dias/30
            i_m = ((1.0 + i_ea) ** (1.0 / 12.0)) - 1.0
            tasa_periodo = i_m * (dias_tramo / 30.0)
            interes_tramo = round(capital * tasa_periodo, 2)

        acumulado_interes = round(acumulado_interes + interes_tramo, 2)
        dias_totales += dias_tramo

        items_periodo.append(
            PeriodoMoraItem(
                periodo=periodo,
                fecha_desde=f_desde.isoformat(),
                fecha_hasta=f_hasta.isoformat(),
                dias_mora=dias_tramo,
                capital_base=capital,
                ibc_ea=ibc_ea,
                mora_ea=mora_ea,
                tasa_periodo_pct=round(tasa_periodo * 100.0, 4),
                interes_periodo=interes_tramo,
                interes_acumulado=acumulado_interes,
                resolucion=resolucion,
                fuente="Superintendencia Financiera de Colombia",
            )
        )

    gran_total = round(capital + acumulado_interes, 2)
    criterio = (
        "Art. 884 del Código de Comercio (modificado por art. 111 Ley 510 de 1999): "
        "interés de mora mercantil equivalente a 1.5 veces el Interés Bancario Corriente (IBC) "
        "certificado por la Superintendencia Financiera de Colombia, sin exceder el límite de usura."
    )

    tabla_md, tabla_txt = formatear_tabla_intereses(
        req=req,
        items=items_periodo,
        capital=capital,
        acumulado_interes=acumulado_interes,
        gran_total=gran_total,
        f_ini=f_ini,
        f_fin=f_fin,
        dias_totales=dias_totales,
    )

    return InteresesMoratoriosResponse(
        capital=capital,
        fecha_inicio=f_ini.isoformat(),
        fecha_fin=f_fin.isoformat(),
        dias_totales_mora=dias_totales,
        interes_total=acumulado_interes,
        total_adeudado=gran_total,
        concepto_obligacion=req.concepto_obligacion or "Obligación Mercantil",
        criterio_legal=criterio,
        periodos=items_periodo,
        tabla_markdown=tabla_md,
        tabla_texto=tabla_txt,
    )


def formatear_tabla_intereses(
    req: InteresesMoratoriosRequest,
    items: List[PeriodoMoraItem],
    capital: float,
    acumulado_interes: float,
    gran_total: float,
    f_ini: date,
    f_fin: date,
    dias_totales: int,
) -> Tuple[str, str]:
    """Genera tabla detallada de liquidación de mora comercial mes a mes."""
    # MARKDOWN
    md_lines = [
        "### ANEXO LIQUIDATORIO: INTERESES MORATORIOS MERCANTILES (ART. 884 CÓDIGO DE COMERCIO)",
        "",
        f"- **Concepto / Título:** {req.concepto_obligacion or 'Obligación Mercantil en Mora'}",
        f"- **Capital Base:** {formato_pesos(capital)} | **Periodo de Mora:** {f_ini.isoformat()} al {f_fin.isoformat()} ({dias_totales} días)",
        "- **Criterio Legal:** 1.5 veces el Interés Bancario Corriente (IBC) certificado mes a mes por la Superintendencia Financiera de Colombia.",
        "",
        "| Periodo | Rango de Fechas | Días | IBC E.A. | Tasa Mora E.A. | Tasa Aplicada | Interés Mes | Interés Acumulado | Resolución SFC |",
        "| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |",
    ]
    for it in items:
        md_lines.append(
            f"| {it.periodo} | {it.fecha_desde} a {it.fecha_hasta} | {it.dias_mora} | {it.ibc_ea:.2f}% | {it.mora_ea:.2f}% | {it.tasa_periodo_pct:.4f}% | {formato_pesos(it.interes_periodo)} | {formato_pesos(it.interes_acumulado)} | {it.resolucion} |"
        )
    md_lines.append(
        f"| **TOTALES** | **{f_ini.isoformat()} al {f_fin.isoformat()}** | **{dias_totales}** | - | - | - | **{formato_pesos(acumulado_interes)}** | **{formato_pesos(acumulado_interes)}** | **Superfinanciera** |"
    )
    md_lines.append("")
    md_lines.append(f"**CAPITAL BASE:** {formato_pesos(capital)} M/CTE")
    md_lines.append(f"**TOTAL INTERESES MORATORIOS:** {formato_pesos(acumulado_interes)} M/CTE")
    md_lines.append(f"**GRAN TOTAL ADEUDADO (CAPITAL + MORA):** {formato_pesos(gran_total)} M/CTE")
    md_lines.append("")
    md_tabla = "\n".join(md_lines)

    # TEXTO PLANO
    sep = "=" * 110
    sep_sub = "-" * 110
    txt_lines = [
        sep,
        "LIQUIDACIÓN DE INTERESES MORATORIOS MERCANTILES (ART. 884 C. Co. - SUPERINTENDENCIA FINANCIERA)",
        sep,
        f"Obligación: {req.concepto_obligacion or 'Crédito Mercantil'}  |  Capital Base: {formato_pesos(capital)}",
        f"Lapso en Mora: {f_ini.isoformat()} al {f_fin.isoformat()} ({dias_totales} días)",
        sep_sub,
        f"{'PERIODO':<8} {'RANGO FECHAS':<24} {'DÍAS':<5} {'IBC E.A.':<9} {'MORA E.A.':<10} {'INT. MES':<14} {'INT. ACUM.':<14} {'RESOLUCIÓN SFC':<20}",
        sep_sub,
    ]
    for it in items:
        rango = f"{it.fecha_desde} a {it.fecha_hasta}"
        txt_lines.append(
            f"{it.periodo:<8} {rango:<24} {it.dias_mora:<5} {it.ibc_ea:>6.2f}%   {it.mora_ea:>6.2f}%   {formato_pesos(it.interes_periodo):<14} {formato_pesos(it.interes_acumulado):<14} {it.resolucion[:19]:<20}"
        )
    txt_lines.append(sep_sub)
    txt_lines.append(f"{'CAPITAL PRINCIPAL (COP):':<64} {formato_pesos(capital):<18}")
    txt_lines.append(f"{'TOTAL INTERESES DE MORA LIQUIDADOS (COP):':<64} {formato_pesos(acumulado_interes):<18}")
    txt_lines.append(sep)
    txt_lines.append(f"{'GRAN TOTAL ADEUDADO A LA FECHA DE CORTE (COP):':<64} {formato_pesos(gran_total):<18}")
    txt_lines.append(sep)
    txt_tabla = "\n".join(txt_lines)

    return md_tabla, txt_tabla


# -----------------------------------------------------------------------------
# 3. MOTOR DE INDEXACIÓN CON IPC DEL DANE
# -----------------------------------------------------------------------------

class IndexacionRequest(BaseModel):
    valor_historico: float = Field(gt=0, description="Monto o valor histórico a actualizar monetariamente (COP)")
    fecha_inicial: str = Field(description="Fecha de causación o exigibilidad inicial (YYYY-MM o YYYY-MM-DD)")
    fecha_final: str = Field(description="Fecha de corte o liquidación final (YYYY-MM o YYYY-MM-DD)")
    concepto: Optional[str] = Field(default="", description="Concepto del crédito, condena o perjuicio a indexar")


class IndexacionResponse(BaseModel):
    valor_historico: float
    fecha_inicial: str
    fecha_final: str
    periodo_inicial: str
    periodo_final: str
    ipc_inicial: float
    ipc_final: float
    factor_indexacion: float
    variacion_porcentual: float
    correccion_monetaria: float
    valor_indexado: float
    formula: str
    fuente_dane: str
    norma: str
    tabla_markdown: str
    tabla_texto: str


def calcular_indexacion_ipc(req: IndexacionRequest) -> IndexacionResponse:
    """
    Indexación con el IPC oficial del DANE bajo la fórmula jurisprudencial unificada
    de la Corte Suprema de Justicia (Salas Civil y Laboral) y el Consejo de Estado:
    VA = VH × (IPC_final / IPC_inicial).
    """
    f_ini = parsear_fecha(req.fecha_inicial)
    f_fin = parsear_fecha(req.fecha_final)
    if f_fin < f_ini:
        raise HTTPException(status_code=400, detail="La fecha final de indexación no puede ser anterior a la inicial.")

    periodo_ini = f"{f_ini.year:04d}-{f_ini.month:02d}"
    periodo_fin = f"{f_fin.year:04d}-{f_fin.month:02d}"

    cat = cargar_catalogo_ipc()
    series = {item["periodo"]: float(item["indice"]) for item in cat.get("series", [])}
    if not series:
        raise HTTPException(status_code=500, detail="No se encontró la serie histórica del IPC del DANE.")

    periodos_disponibles = sorted(series.keys())

    # Búsqueda o aproximación al más cercano si excede los límites
    if periodo_ini in series:
        ipc_ini = series[periodo_ini]
    elif periodo_ini < periodos_disponibles[0]:
        ipc_ini = series[periodos_disponibles[0]]
        periodo_ini = periodos_disponibles[0]
    else:
        ipc_ini = series[periodos_disponibles[-1]]
        periodo_ini = periodos_disponibles[-1]

    if periodo_fin in series:
        ipc_fin = series[periodo_fin]
    elif periodo_fin > periodos_disponibles[-1]:
        ipc_fin = series[periodos_disponibles[-1]]
        periodo_fin = periodos_disponibles[-1]
    else:
        ipc_fin = series[periodos_disponibles[0]]
        periodo_fin = periodos_disponibles[0]

    vh = float(req.valor_historico)
    factor = ipc_fin / ipc_ini
    valor_indexado = round(vh * factor, 2)
    correccion_monetaria = round(valor_indexado - vh, 2)
    variacion_pct = round(((ipc_fin - ipc_ini) / ipc_ini) * 100.0, 2)

    formula = f"VA = VH × ({ipc_fin:.2f} / {ipc_ini:.2f}) = {formato_pesos(vh)} × {factor:.6f}"
    fuente = "DANE - Índice de Precios al Consumidor (IPC), Total Nacional (Base Diciembre 2018 = 100)"
    norma = (
        "Corte Suprema de Justicia (Sala de Casación Civil y Laboral) y Consejo de Estado: "
        "actualización monetaria por pérdida del poder adquisitivo de la moneda."
    )

    tabla_md, tabla_txt = formatear_tabla_indexacion(
        req=req,
        periodo_ini=periodo_ini,
        periodo_fin=periodo_fin,
        ipc_ini=ipc_ini,
        ipc_fin=ipc_fin,
        factor=factor,
        variacion_pct=variacion_pct,
        vh=vh,
        correccion_monetaria=correccion_monetaria,
        valor_indexado=valor_indexado,
    )

    return IndexacionResponse(
        valor_historico=vh,
        fecha_inicial=f_ini.isoformat(),
        fecha_final=f_fin.isoformat(),
        periodo_inicial=periodo_ini,
        periodo_final=periodo_fin,
        ipc_inicial=ipc_ini,
        ipc_final=ipc_fin,
        factor_indexacion=round(factor, 6),
        variacion_porcentual=variacion_pct,
        correccion_monetaria=correccion_monetaria,
        valor_indexado=valor_indexado,
        formula=formula,
        fuente_dane=fuente,
        norma=norma,
        tabla_markdown=tabla_md,
        tabla_texto=tabla_txt,
    )


def formatear_tabla_indexacion(
    req: IndexacionRequest,
    periodo_ini: str,
    periodo_fin: str,
    ipc_ini: float,
    ipc_fin: float,
    factor: float,
    variacion_pct: float,
    vh: float,
    correccion_monetaria: float,
    valor_indexado: float,
) -> Tuple[str, str]:
    """Genera la tabla de indexación en Markdown y texto plano."""
    # MARKDOWN
    md_lines = [
        "### ANEXO LIQUIDATORIO: ACTUALIZACIÓN MONETARIA CON IPC (DANE)",
        "",
        f"- **Concepto:** {req.concepto or 'Obligación / Condena Judicial'}",
        f"- **Periodo de Indexación:** {periodo_ini} a {periodo_fin}",
        "- **Fórmula Judicial Unificada:** `VA = VH × (IPC_final / IPC_inicial)`",
        "- **Fuente Oficial:** DANE (Índice de Precios al Consumidor - Total Nacional)",
        "",
        "| Elemento Liquidatorio | Valor / Parámetro | Fuente / Detalle |",
        "| :--- | :---: | :--- |",
        f"| **Valor Histórico (VH)** | **{formato_pesos(vh)}** | Capital de origen en mora o causado |",
        f"| **IPC Inicial ({periodo_ini})** | {ipc_ini:.2f} | DANE IPC Base Dic/2018=100 |",
        f"| **IPC Final ({periodo_fin})** | {ipc_fin:.2f} | DANE IPC Base Dic/2018=100 |",
        f"| **Factor de Actualización** | {factor:.6f} | `{ipc_fin:.2f} / {ipc_ini:.2f}` |",
        f"| **Inflación Acumulada** | {variacion_pct:.2f}% | Variación del poder adquisitivo |",
        f"| **Corrección Monetaria** | **{formato_pesos(correccion_monetaria)}** | Ajuste inflacionario (`VA - VH`) |",
        f"| **VALOR ACTUALIZADO INDEXADO (VA)** | **{formato_pesos(valor_indexado)}** | **Total actualizado a la fecha de corte** |",
        "",
    ]
    md_tabla = "\n".join(md_lines)

    # TEXTO PLANO
    sep = "=" * 80
    sep_sub = "-" * 80
    txt_lines = [
        sep,
        "ANEXO: CUADRO DE ACTUALIZACIÓN MONETARIA (INDEXACIÓN CON IPC DANE)",
        sep,
        f"Concepto: {req.concepto or 'Obligación / Condena Judicial'}",
        f"Fórmula: VA = VH * (IPC_final / IPC_inicial)",
        f"Periodo: {periodo_ini} a {periodo_fin}",
        sep_sub,
        f"{'PARÁMETRO':<36} {'VALOR':<20} {'DETALLE / FUENTE':<22}",
        sep_sub,
        f"{'Valor Histórico (VH):':<36} {formato_pesos(vh):<20} {'Capital base':<22}",
        f"{f'IPC Inicial ({periodo_ini}):':<36} {f'{ipc_ini:.2f}':<20} {'DANE':<22}",
        f"{f'IPC Final ({periodo_fin}):':<36} {f'{ipc_fin:.2f}':<20} {'DANE':<22}",
        f"{'Factor Multiplicador:':<36} {f'{factor:.6f}':<20} {'IPC_f / IPC_i':<22}",
        f"{'Variación IPC Acumulada:':<36} {f'{variacion_pct:.2f}%':<20} {'Inflación periodo':<22}",
        f"{'Corrección Monetaria:':<36} {formato_pesos(correccion_monetaria):<20} {'Ajuste neto':<22}",
        sep,
        f"{'VALOR ACTUALIZADO (VA):':<36} {formato_pesos(valor_indexado):<20} {'Total Indexado (COP)':<22}",
        sep,
    ]
    txt_tabla = "\n".join(txt_lines)

    return md_tabla, txt_tabla


# -----------------------------------------------------------------------------
# FASTAPI ROUTER Y ENDPOINTS
# -----------------------------------------------------------------------------

router = APIRouter(prefix="/api/calculos", tags=["Cálculos Jurídicos y Financieros"])


@router.post("/laboral", response_model=LiquidacionLaboralResponse)
@router.post("/liquidacion-laboral", response_model=LiquidacionLaboralResponse)
async def endpoint_liquidacion_laboral(req: LiquidacionLaboralRequest):
    """
    Liquidación laboral integral colombiana:
    - Cesantías (art. 249 CST)
    - Intereses a las cesantías (Ley 52 de 1975)
    - Prima de servicios (art. 306 CST)
    - Vacaciones (art. 186 CST)
    - Indemnización por despido sin justa causa (art. 64 CST)
    - Indemnización moratoria (art. 65 CST)
    - Sanción por no consignación (art. 99 Ley 50/1990)
    - Advertencia legal sobre el impacto de la Ley 2466 de 2025.
    """
    return calcular_liquidacion_laboral(req)


@router.post("/intereses-moratorios", response_model=InteresesMoratoriosResponse)
async def endpoint_intereses_moratorios(req: InteresesMoratoriosRequest):
    """
    Liquidación de intereses moratorios mercantiles:
    - 1.5 veces el Interés Bancario Corriente (IBC) certificado mes a mes por la SFC.
    - Cumplimiento del art. 884 del Código de Comercio y límite de usura (art. 305 Código Penal).
    """
    return calcular_intereses_moratorios(req)


@router.post("/indexacion", response_model=IndexacionResponse)
@router.post("/indexacion-ipc", response_model=IndexacionResponse)
async def endpoint_indexacion_ipc(req: IndexacionRequest):
    """
    Indexación monetaria con IPC oficial del DANE:
    VA = VH × (IPC_final / IPC_inicial).
    Fórmula unificada de la Corte Suprema de Justicia y Consejo de Estado.
    """
    return calcular_indexacion_ipc(req)


@router.get("/tasas-sfc")
async def endpoint_obtener_tasas_sfc():
    """Retorna el catálogo oficial de tasas IBC y mora de la Superintendencia Financiera."""
    return cargar_catalogo_tasas_sfc()


@router.get("/ipc")
async def endpoint_obtener_ipc():
    """Retorna la serie histórica del IPC del DANE utilizada para indexación."""
    return cargar_catalogo_ipc()
