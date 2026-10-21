import asyncio
import httpx
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from app.config import get_settings
from app.routers import documents

settings = get_settings()

async def keep_alive_worker():
    """
    Heartbeat autónomo para evitar que el contenedor de Render se duerma.
    Envía un ping periódico cada 9 minutos (540s), garantizando que nunca
    se alcancen los 15 minutos de inactividad que provocan la hibernación.
    """
    # Espera inicial para permitir arranque completo del servidor
    await asyncio.sleep(45)
    target_url = settings.RENDER_EXTERNAL_URL.rstrip("/") + "/api/health"

    while True:
        try:
            if "onrender.com" in target_url:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.get(target_url)
                    print(f"[Keep-Alive] 💓 Heartbeat exitoso ({target_url}) -> HTTP {resp.status_code}")
        except Exception as e:
            print(f"[Keep-Alive] Aviso en heartbeat: {e}")

        # 9 minutos de espera (Render duerme a los 15 minutos)
        await asyncio.sleep(540)

@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(keep_alive_worker())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

app = FastAPI(
    title="El Memorialista - Generador Jurídico de Colombia",
    description="Redacción autónoma de demandas, tutelas, memoriales y derechos de petición con Google Gemini",
    version="2.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir rutas de API
app.include_router(documents.router)

# Ruta estática
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/")
async def root_index():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {
        "app": "El Memorialista API",
        "status": "online",
        "docs": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.PORT, reload=settings.DEBUG)
