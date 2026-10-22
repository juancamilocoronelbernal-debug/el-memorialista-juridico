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
    GEMINI_MODEL: str = "gemini-3.5-flash"        # Máximo razonamiento con thinkingBudget
    GEMINI_MODEL_PRO: str = "gemini-3.1-pro-preview"      # Calidad Pro (máximo razonamiento)
    GEMINI_FALLBACK_MODELS: str = "gemini-3.6-flash,gemini-3-flash-preview,gemini-3.8-flash,gemini-4-argon"
    GEMINI_MAX_OUTPUT_TOKENS: int = 65536         # incluye los tokens de "pensamiento"
    GEMINI_THINKING_DEFAULT: str = "8192"         # 8.192 tokens de razonamiento profundo paso a paso
    GEMINI_THINKING_COMPLEX: str = "16384"        # 16.384 tokens para demandas complejas
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

    # Supabase (Auth Magic Link, Postgres RLS, Storage privado)
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_JWT_SECRET: str = ""
    SUPABASE_STORAGE_BUCKET: str = "archivos-privados"

    # Acceso y límites de uso (por usuario y por IP)
    APP_ACCESS_CODE: str = ""        # respaldo legado si no se usa Supabase
    ALLOWED_ORIGINS: str = ""        # vacío = solo el mismo dominio (recomendado)
    LIMITE_POR_VENTANA: int = 15     # redacciones y ajustes por usuario/IP dentro de la ventana
    VENTANA_MINUTOS: int = 10
    LIMITE_DIA_USUARIO: int = 50     # tope diario de redacciones por usuario autenticado
    LIMITE_DIA_IP: int = 150         # una oficina con varios abogados comparte la misma IP
    LIMITE_DIA_GLOBAL: int = 500     # tope diario de todo el servidor (controla el gasto)
    LIMITE_ESTILO_HORA: int = 10


@lru_cache
def get_settings() -> Settings:
    return Settings()
