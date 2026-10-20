from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional
from app.services.gemini_service import gemini_service
from app.config import get_settings

router = APIRouter(prefix="/api", tags=["Documentos"])

class RedactarRequest(BaseModel):
    prompt: str = Field(..., description="Prompt completo con contexto normativo, hechos y estilo")
    modo: Optional[str] = Field("nuevo", description="nuevo | regenerar | ajuste")
    instruccion: Optional[str] = Field("", description="Instrucción de ajuste solicitada por el usuario")
    texto_previo: Optional[str] = Field("", description="Texto previo para ajustes")
    calidad: Optional[str] = Field("default", description="default | complex")

class AnalizarEstiloRequest(BaseModel):
    muestra: str = Field(..., min_length=20, description="Texto de muestra jurídica del abogado")

@router.get("/health")
async def health_check():
    settings = get_settings()
    has_key = bool(settings.GEMINI_API_KEY and len(settings.GEMINI_API_KEY.strip()) > 5)
    return {
        "status": "online",
        "app": "El Memorialista",
        "gemini_configured": has_key,
        "model": settings.GEMINI_MODEL
    }

@router.post("/redactar")
async def redactar_documento(req: RedactarRequest):
    if not req.prompt:
        raise HTTPException(status_code=400, detail="El prompt es obligatorio.")
    
    stream_gen = gemini_service.stream_document_generation(
        prompt=req.prompt,
        modo=req.modo or "nuevo",
        instruccion=req.instruccion or "",
        texto_previo=req.texto_previo or "",
        calidad=req.calidad or "default"
    )

    return StreamingResponse(
        stream_gen,
        media_type="text/plain; charset=utf-8"
    )

@router.post("/analizar-estilo")
async def analizar_estilo(req: AnalizarEstiloRequest):
    res = await gemini_service.analyze_style(req.muestra)
    if not res.get("ok"):
        raise HTTPException(status_code=500, detail=res.get("error", "Error al analizar muestra"))
    return res
