"""
El Memorialista · configuración (v2.2)
Todo se controla con variables de entorno (Render > Environment) o con el archivo .env en local.
"""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # General
    ENVIRONMENT: str = "development"
    PORT: int = 8000
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    VERSION: str = "2.2.1"

    # Render (Render define RENDER_EXTERNAL_URL automáticamente)
    RENDER_EXTERNAL_URL: str = ""
    KEEP_ALIVE: bool = True

    # Google Gemini (modelos vigentes a octubre de 2026)
    GEMINI_API_KEY: str = ""
    GEMINI_API_BASE: str = "https://generativelanguage.googleapis.com"
    GEMINI_MODEL: str = "gemini-3.8-flash"        # calidad "Equilibrada"
    GEMINI_MODEL_PRO: str = "gemini-4-argon"      # calidad "Máxima" (solo plan pago)
    GEMINI_FALLBACK_MODELS: str = "gemini-3.6-flash,gemini-3.5-flash-lite,gemini-2.5-flash"
    GEMINI_MAX_OUTPUT_TOKENS: int = 65536         # incluye los tokens de "pensamiento"
    GEMINI_THINKING_DEFAULT: str = ""             # "", "low", "medium" o "high" ("" = el del modelo)
    GEMINI_THINKING_COMPLEX: str = ""
    GEMINI_SAFETY: str = ""                       # "" = filtros por defecto del modelo

    # Groq (respaldo opcional)
    GROQ_API_KEY: str = ""
    GROQ_API_BASE: str = "https://api.groq.com/openai/v1"
    GROQ_MODEL: str = "openai/gpt-oss-120b"
    GROQ_MAX_TOKENS: int = 16384

    # Robustez
    MAX_CONTINUACIONES: int = 3
    INTENTOS_POR_MODELO: int = 2
    ESPERA_REINTENTO_S: float = 1.5
    TIMEOUT_CONEXION_S: float = 15.0
    TIMEOUT_LECTURA_S: float = 300.0
    PING_NDJSON_S: float = 15.0

    # Acceso y límites de uso (mientras no haya cuentas de usuario)
    APP_ACCESS_CODE: str = ""        # si se define, la app pide este código
    ALLOWED_ORIGINS: str = ""        # vacío = solo el mismo dominio (recomendado)
    LIMITE_POR_VENTANA: int = 15     # redacciones y ajustes por IP dentro de la ventana
    VENTANA_MINUTOS: int = 10
    LIMITE_DIA_IP: int = 150         # una oficina con varios abogados comparte la misma IP
    LIMITE_DIA_GLOBAL: int = 500     # tope diario de todo el servidor (controla el gasto)
    LIMITE_ESTILO_HORA: int = 10


@lru_cache
def get_settings() -> Settings:
    return Settings()
