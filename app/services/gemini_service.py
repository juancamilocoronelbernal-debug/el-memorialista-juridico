import json
import re
import httpx
from typing import AsyncGenerator, Dict, Any, Optional
from app.config import get_settings

def clean_gemini_text(text: str) -> str:
    """Elimina etiquetas de razonamiento o markdown innecesario."""
    if not text:
        return ""
    text = re.sub(r"<think>[\s\S]*?</think>", "", text, flags=re.IGNORECASE).strip()
    return text

class GeminiService:
    def __init__(self):
        self.settings = get_settings()

    def get_candidate_models(self) -> list:
        preferred = self.settings.GEMINI_MODEL.strip()
        fallback_str = self.settings.GEMINI_FALLBACK_MODELS
        fallbacks = [m.strip() for m in fallback_str.split(",") if m.strip()]
        candidates = [preferred] + [m for m in fallbacks if m != preferred]
        return candidates

    async def stream_document_generation(
        self,
        prompt: str,
        modo: str = "nuevo",
        instruccion: str = "",
        texto_previo: str = "",
        calidad: str = "default"
    ) -> AsyncGenerator[str, None]:
        api_key = self.settings.GEMINI_API_KEY.strip()
        if not api_key:
            yield (
                "⚠️ **Configuración requerida:** No se ha configurado la clave `GEMINI_API_KEY`.\n\n"
                "Para redactar con Inteligencia Artificial, agrega tu clave en el archivo `.env` del proyecto:\n"
                "```bash\nGEMINI_API_KEY=tu_clave_de_gemini_aqui\n```\n"
                "Luego reinicia el servidor o despliega en Render/Vercel con esa variable de entorno."
            )
            return

        # Construir estructura de mensajes según el modo
        if modo == "ajuste" and texto_previo:
            contents = [
                {"role": "user", "parts": [{"text": prompt}]},
                {"role": "model", "parts": [{"text": texto_previo}]},
                {"role": "user", "parts": [{
                    "text": (
                        f"AJUSTE PEDIDO POR EL ABOGADO: {instruccion}\n\n"
                        "Aplica el ajuste al documento anterior y devuelve el documento COMPLETO actualizado, "
                        "con el mismo formato de marcas. Conserva lo que el ajuste no pide cambiar. Sigue las reglas: "
                        "no inventes hechos y usa [COMPLETAR] y [VERIFICAR] cuando corresponda. Escribe solo el documento."
                    )
                }]}
            ]
        else:
            contents = [
                {"role": "user", "parts": [{"text": prompt}]}
            ]

        # Parámetros de generación
        max_tokens = 8192
        temp = 0.2 if calidad == "complex" else 0.35
        gen_config: Dict[str, Any] = {
            "temperature": temp,
            "maxOutputTokens": max_tokens,
            "topP": 0.95,
        }

        candidates = self.get_candidate_models()
        exito = False
        ultimo_error = ""

        for model_name in candidates:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:streamGenerateContent?key={api_key}&alt=sse"
            payload = {
                "contents": contents,
                "generationConfig": gen_config
            }

            try:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    async with client.stream("POST", url, json=payload) as response:
                        if response.status_code == 200:
                            exito = True
                            async for raw_line in response.aiter_lines():
                                if not raw_line or not raw_line.startswith("data:"):
                                    continue
                                data_str = raw_line[len("data:"):].strip()
                                if data_str == "[DONE]":
                                    break
                                try:
                                    chunk_json = json.loads(data_str)
                                    cand = chunk_json.get("candidates", [])
                                    if cand:
                                        parts = cand[0].get("content", {}).get("parts", [])
                                        for p in parts:
                                            # Descartar partes de pensamiento interno si existen
                                            if not p.get("thought", False):
                                                t = p.get("text", "")
                                                if t:
                                                    yield t
                                except json.JSONDecodeError:
                                    continue
                            break
                        else:
                            error_body = await response.aread()
                            ultimo_error = f"Modelo {model_name} respondió con código HTTP {response.status_code}: {error_body.decode('utf-8', errors='ignore')[:200]}"
                            print(f"[Gemini Error] {ultimo_error}")
            except Exception as e:
                ultimo_error = f"Error al conectar con {model_name}: {str(e)}"
                print(f"[Gemini Exception] {ultimo_error}")

        if not exito:
            yield f"\n\n❌ **Error al generar el escrito:** No fue posible conectar con Google Gemini.\nDetalle: {ultimo_error}"

    async def analyze_style(self, muestra: str) -> Dict[str, Any]:
        api_key = self.settings.GEMINI_API_KEY.strip()
        if not api_key:
            return {
                "ok": False,
                "error": "No se ha configurado la variable GEMINI_API_KEY en el servidor.",
                "ficha": ""
            }

        prompt = (
            "Analiza el estilo de redacción del siguiente escrito jurídico de un abogado colombiano "
            "para que otro redactor pueda imitarlo fielmente. Responde ÚNICAMENTE con un objeto JSON válido "
            "con las siguientes claves en español y valores breves (cita entre comillas fórmulas exactas):\n"
            "{\n"
            '  "encabezado": "cómo escribe el destinatario y la referencia",\n'
            '  "presentacion": "fórmula con la que se presenta",\n'
            '  "tratamiento": "cómo se dirige al despacho",\n'
            '  "persona": "primera o tercera persona",\n'
            '  "capitulos": "orden y nombres de sus capítulos",\n'
            '  "numeracion": "cómo numera hechos y pretensiones",\n'
            '  "titulos": "cómo escribe los títulos",\n'
            '  "conectores": "conectores y fórmulas frecuentes",\n'
            '  "citas": "cómo cita normas y jurisprudencia",\n'
            '  "cierre": "fórmula de despedida y firma",\n'
            '  "rasgos": "otros rasgos distintivos"\n'
            "}\n\n"
            f"ESCRITO:\n<<<\n{muestra[:12000]}\n>>>"
        )

        candidates = self.get_candidate_models()
        for model_name in candidates:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.2,
                    "maxOutputTokens": 2048,
                    "responseMimeType": "application/json"
                }
            }
            try:
                async with httpx.AsyncClient(timeout=45.0) as client:
                    r = await client.post(url, json=payload)
                    # Si falla por responseMimeType json en algún modelo, reintentar sin él
                    if r.status_code == 400:
                        del payload["generationConfig"]["responseMimeType"]
                        r = await client.post(url, json=payload)

                    if r.status_code == 200:
                        data = r.json()
                        cand = data.get("candidates", [])
                        if cand:
                            parts = cand[0].get("content", {}).get("parts", [])
                            raw_text = "".join(p.get("text", "") for p in parts if not p.get("thought", False)).strip()
                            raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
                            raw_text = re.sub(r"\s*```$", "", raw_text)
                            parsed = json.loads(raw_text)

                            etiquetas = {
                                "encabezado": "Encabezado",
                                "presentacion": "Presentación",
                                "tratamiento": "Tratamiento",
                                "persona": "Persona",
                                "capitulos": "Capítulos",
                                "numeracion": "Numeración",
                                "titulos": "Títulos",
                                "conectores": "Conectores",
                                "citas": "Citas",
                                "cierre": "Cierre",
                                "rasgos": "Rasgos"
                            }
                            lineas = []
                            for k, nom in etiquetas.items():
                                val = parsed.get(k)
                                if val:
                                    lineas.append(f"{nom}: {str(val).strip()}")
                            ficha = "\n".join(lineas)
                            return {"ok": True, "ficha": ficha, "raw": parsed}
            except Exception as e:
                print(f"[Analyze Style Error] {model_name}: {e}")
                continue

        return {
            "ok": False,
            "error": "No se pudo generar la ficha de estilo con Gemini.",
            "ficha": ""
        }

gemini_service = GeminiService()
