"""
El Memorialista · configuración (v3.0)
Todo se controla con variables de entorno (Render > Environment) o con el archivo .env en local.
"""
from functools import lru_cache
from ipaddress import ip_network
from pathlib import Path
import re

from pydantic import Field, field_validator, model_validator
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
    VERSION: str = "5.0.1"

    # Render (Render define RENDER_EXTERNAL_URL automáticamente)
    RENDER_EXTERNAL_URL: str = ""
    KEEP_ALIVE: bool = True

    # Google Gemini (modelos vigentes a octubre de 2026)
    GEMINI_API_KEY: str = ""
    GEMINI_API_BASE: str = "https://generativelanguage.googleapis.com"
    GEMINI_MODEL: str = "gemini-3.5-flash"        # Calidad principal: Gemini 3.5 Flash de alta disponibilidad
    GEMINI_MODEL_PRO: str = "gemini-4-argon"      # Calidad avanzada: Gemini 4 Argon con thinkingLevel medium
    GEMINI_FALLBACK_MODELS: str = "gemini-4-argon,gemini-3.6-flash,gemini-3.5-flash"
    GEMINI_MAX_OUTPUT_TOKENS: int = 65536         # incluye los tokens de "pensamiento"
    GEMINI_THINKING_DEFAULT: str = "high"         # Nivel de pensamiento "high" para Gemini 3.8 Flash
    GEMINI_THINKING_COMPLEX: str = "medium"       # Nivel de pensamiento "medium" para Gemini 4 Argon
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

    # Autenticación obligatoria. No existen sesiones simuladas ni códigos de acceso.
    APP_BASE_URL: str = ""           # URL pública canónica (opcional; sin barra final)
    AUTH_ALLOW_SIGNUP: bool = False # usuarios nuevos: habilitar explícitamente en Supabase
    AUTH_COOKIE_MAX_AGE_SECONDS: int = Field(3600, ge=60, le=86400)

    # Despacho profesional: mismo Auth y base existente, migraciones adicionales.
    DESPACHO_MONITORS_ENABLED: bool = False
    DESPACHO_MONITOR_POLL_SECONDS: int = Field(60, ge=30, le=3600)
    DESPACHO_MONITOR_ALLOWED_HOSTS: str = (
        "corteconstitucional.gov.co,cortesuprema.gov.co,consejodeestado.gov.co,"
        "ramajudicial.gov.co,suin-juriscol.gov.co,funcionpublica.gov.co,"
        "secretariasenado.gov.co,diariooficial.imprenta.gov.co,sic.gov.co,"
        "dian.gov.co,mintrabajo.gov.co"
    )
    DESPACHO_SIGNING_ENABLED: bool = True  # además requiere service_role y migración

    # Biblioteca documental, OCR y búsqueda conceptual (migración V5).
    DESPACHO_EMBEDDINGS_ENABLED: bool = False
    DESPACHO_EMBEDDING_MODEL: str = "gemini-embedding-001"
    DESPACHO_OCR_ENABLED: bool = True
    DESPACHO_OCR_LANGUAGES: str = "spa+eng"
    DESPACHO_OCR_MAX_PAGES: int = Field(30, ge=1, le=100)
    DESPACHO_OCR_PAGE_TIMEOUT_SECONDS: int = Field(25, ge=5, le=90)
    DESPACHO_MONITOR_AI_ENABLED: bool = True

    # Encargos persistidos, programación y navegador supervisado.
    DESPACHO_AGENT_WORKER_ENABLED: bool = False
    DESPACHO_AGENT_POLL_SECONDS: int = Field(30, ge=10, le=600)
    DESPACHO_AUTOMATION_DAILY_USER_CALLS: int = Field(100, ge=0, le=100000)
    DESPACHO_AUTOMATION_DAILY_GLOBAL_CALLS: int = Field(1000, ge=0, le=1000000)
    DESPACHO_BROWSER_ENABLED: bool = False
    DESPACHO_BROWSER_PROVIDER: str = "local"
    BROWSERBASE_API_KEY: str = ""
    BROWSERBASE_PROJECT_ID: str = ""
    DESPACHO_BROWSER_EXECUTABLE: str = ""
    DESPACHO_BROWSER_ALLOWED_HOSTS: str = (
        "corteconstitucional.gov.co,cortesuprema.gov.co,consejodeestado.gov.co,"
        "ramajudicial.gov.co,suin-juriscol.gov.co,funcionpublica.gov.co,"
        "secretariasenado.gov.co,sic.gov.co,dian.gov.co,mintrabajo.gov.co"
    )
    DESPACHO_BROWSER_SESSION_TTL_SECONDS: int = Field(900, ge=60, le=3600)

    # OAuth: secretos exclusivamente en el servidor; tokens cifrados en reposo.
    DESPACHO_CONNECTIONS_ENABLED: bool = False
    DESPACHO_TOKEN_ENCRYPTION_KEY: str = ""
    GOOGLE_OAUTH_CLIENT_ID: str = ""
    GOOGLE_OAUTH_CLIENT_SECRET: str = ""
    MICROSOFT_OAUTH_CLIENT_ID: str = ""
    MICROSOFT_OAUTH_CLIENT_SECRET: str = ""
    MICROSOFT_OAUTH_TENANT: str = "common"
    SMTP_HOST: str = ""
    SMTP_PORT: int = Field(587, ge=1, le=65535)
    SMTP_TLS_MODE: str = "starttls"
    SMTP_FROM_EMAIL: str = ""
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    DESPACHO_SIGNING_OTP_SECRET: str = ""

    # Acceso y límites de uso (por usuario y por IP)
    APP_ACCESS_CODE: str = ""        # obsoleto: ignorado; conservado solo para migración
    ALLOWED_ORIGINS: str = ""        # vacío = solo el mismo dominio (recomendado)
    # Ninguna cabecera de IP es confiable sin declarar también quién la envía.
    PROXY_IPS_CONFIABLES: str = ""   # IPs/CIDR del peer y los proxies internos, separados por coma
    PROXIES_CONFIABLES: int = Field(0, ge=0, le=16)  # saltos en X-Forwarded-For; 0 = conexión directa
    IP_CABECERA_CONFIABLE: str = ""  # alternativa a X-Forwarded-For, reescrita por el proxy
    LIMITE_POR_VENTANA: int = 15     # redacciones y ajustes por usuario/IP dentro de la ventana
    VENTANA_MINUTOS: int = 10
    LIMITE_DIA_USUARIO: int = 50     # tope diario de redacciones por usuario autenticado
    LIMITE_DIA_IP: int = 150         # una oficina con varios abogados comparte la misma IP
    LIMITE_DIA_GLOBAL: int = 500     # tope diario de todo el servidor (controla el gasto)
    LIMITE_ESTILO_HORA: int = 10

    @field_validator("PROXY_IPS_CONFIABLES")
    @classmethod
    def validar_redes_proxy(cls, value: str) -> str:
        redes = []
        for parte in value.split(","):
            parte = parte.strip()
            if not parte:
                continue
            if "%" in parte:
                raise ValueError("Las redes de proxies no admiten identificadores de interfaz.")
            red = ip_network(parte, strict=False)
            if red.prefixlen == 0:
                raise ValueError("Declara las IPs o redes del proxy; no se admite confiar en todo Internet.")
            if str(red) not in redes:
                redes.append(str(red))
        return ",".join(redes)

    @field_validator("IP_CABECERA_CONFIABLE")
    @classmethod
    def validar_nombre_cabecera_ip(cls, value: str) -> str:
        nombre = value.strip().lower()
        if nombre and not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", nombre):
            raise ValueError("El nombre de la cabecera de IP no es válido.")
        if nombre in {"x-forwarded-for", "forwarded", "authorization", "cookie", "host"}:
            raise ValueError("Usa PROXIES_CONFIABLES para X-Forwarded-For o una cabecera exclusiva de IP.")
        return nombre

    @model_validator(mode="after")
    def validar_confianza_proxy(self):
        if self.PROXIES_CONFIABLES and self.IP_CABECERA_CONFIABLE:
            raise ValueError("Elige X-Forwarded-For o una cabecera exclusiva de IP; no ambos modos.")
        if (self.PROXIES_CONFIABLES or self.IP_CABECERA_CONFIABLE) and not self.PROXY_IPS_CONFIABLES:
            raise ValueError("Declara PROXY_IPS_CONFIABLES antes de confiar en cabeceras de IP.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
