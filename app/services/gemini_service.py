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
        groq_key = self.settings.GROQ_API_KEY.strip()
        groq_model = self.settings.GROQ_MODEL.strip() or "openai/gpt-oss-120b"

        # Mensajes base
        if modo == "ajuste" and texto_previo:
            ajuste_msg = (
                f"AJUSTE PEDIDO POR EL ABOGADO: {instruccion}\n\n"
                "Aplica el ajuste al documento anterior y devuelve el documento COMPLETO actualizado, "
                "con el mismo formato de marcas. Conserva lo que el ajuste no pide cambiar. Sigue las reglas: "
                "no inventes hechos y usa [COMPLETAR] y [VERIFICAR] cuando corresponda. Escribe solo el documento."
            )
            gemini_contents = [
                {"role": "user", "parts": [{"text": prompt}]},
                {"role": "model", "parts": [{"text": texto_previo}]},
                {"role": "user", "parts": [{"text": ajuste_msg}]}
            ]
            openai_messages = [
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": texto_previo},
                {"role": "user", "content": ajuste_msg}
            ]
        else:
            gemini_contents = [
                {"role": "user", "parts": [{"text": prompt}]}
            ]
            openai_messages = [
                {"role": "user", "content": prompt}
            ]

        # ---------------------------------------------------------------------
        # 1. INTENTAR CON GOOGLE GEMINI (Si hay clave configurada)
        # ---------------------------------------------------------------------
        if api_key and len(api_key) > 10:
            candidates = self.get_candidate_models()
            temp = 0.2 if calidad == "complex" else 0.35
            gen_config: Dict[str, Any] = {
                "temperature": temp,
                "maxOutputTokens": 8192,
                "topP": 0.95,
            }

            for model_name in candidates:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:streamGenerateContent?key={api_key}&alt=sse"
                payload = {
                    "contents": gemini_contents,
                    "generationConfig": gen_config
                }
                try:
                    async with httpx.AsyncClient(timeout=120.0) as client:
                        async with client.stream("POST", url, json=payload) as response:
                            if response.status_code == 200:
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
                                                if not p.get("thought", False):
                                                    t = p.get("text", "")
                                                    if t:
                                                        yield t
                                    except json.JSONDecodeError:
                                        continue
                                return
                except Exception as e:
                    print(f"[Gemini Exception] {model_name}: {e}")
                    continue

        # ---------------------------------------------------------------------
        # 2. MOTOR DE RESPALDO: GROQ (120B Razonamiento)
        # ---------------------------------------------------------------------
        if groq_key and len(groq_key) > 10:
            url = "https://api.groq.com/openai/v1/chat/completions"
            payload = {
                "model": groq_model,
                "messages": openai_messages,
                "temperature": 0.25,
                "max_tokens": 8192,
                "stream": True
            }
            headers = {
                "Authorization": f"Bearer {groq_key}",
                "Content-Type": "application/json"
            }
            try:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    async with client.stream("POST", url, json=payload, headers=headers) as response:
                        if response.status_code == 200:
                            async for raw_line in response.aiter_lines():
                                if not raw_line or not raw_line.startswith("data:"):
                                    continue
                                data_str = raw_line[len("data:"):].strip()
                                if data_str == "[DONE]":
                                    break
                                try:
                                    chunk_json = json.loads(data_str)
                                    choices = chunk_json.get("choices", [])
                                    if choices:
                                        delta = choices[0].get("delta", {})
                                        content = delta.get("content", "")
                                        if content:
                                            yield content
                                except json.JSONDecodeError:
                                    continue
                            return
                        else:
                            err_body = await response.aread()
                            print(f"[Groq Error] HTTP {response.status_code}: {err_body.decode('utf-8', errors='ignore')[:150]}")
            except Exception as e:
                print(f"[Groq Exception]: {e}")

        # Si ninguno funcionó
        yield (
            "⚠️ **Configuración requerida:** No se pudo conectar con el motor de Inteligencia Artificial.\n\n"
            "Por favor, revisa que tu `GEMINI_API_KEY` o `GROQ_API_KEY` esté configurada correctamente en `.env`."
        )

    async def analyze_style(self, muestra: str) -> Dict[str, Any]:
        api_key = self.settings.GEMINI_API_KEY.strip()
        groq_key = self.settings.GROQ_API_KEY.strip()
        groq_model = self.settings.GROQ_MODEL.strip() or "openai/gpt-oss-120b"

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

        # Intentar con Groq si está disponible
        if groq_key:
            try:
                url = "https://api.groq.com/openai/v1/chat/completions"
                headers = {"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"}
                payload = {
                    "model": groq_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.2,
                    "response_format": {"type": "json_object"}
                }
                async with httpx.AsyncClient(timeout=45.0) as client:
                    r = await client.post(url, json=payload, headers=headers)
                    if r.status_code == 200:
                        data = r.json()
                        raw_text = data["choices"][0]["message"]["content"]
                        parsed = json.loads(raw_text)
                        lineas = [f"{nom}: {str(parsed.get(k, '')).strip()}" for k, nom in etiquetas.items() if parsed.get(k)]
                        return {"ok": True, "ficha": "\n".join(lineas), "raw": parsed}
            except Exception as e:
                print(f"[Style Groq Exception]: {e}")

        # Intentar con Gemini
        if api_key:
            for model_name in self.get_candidate_models():
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.2, "maxOutputTokens": 2048}
                }
                try:
                    async with httpx.AsyncClient(timeout=45.0) as client:
                        r = await client.post(url, json=payload)
                        if r.status_code == 200:
                            data = r.json()
                            cand = data.get("candidates", [])
                            if cand:
                                raw_text = "".join(p.get("text", "") for p in cand[0]["content"]["parts"] if not p.get("thought", False)).strip()
                                raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
                                raw_text = re.sub(r"\s*```$", "", raw_text)
                                parsed = json.loads(raw_text)
                                lineas = [f"{nom}: {str(parsed.get(k, '')).strip()}" for k, nom in etiquetas.items() if parsed.get(k)]
                                return {"ok": True, "ficha": "\n".join(lineas), "raw": parsed}
                except Exception:
                    continue

        return {"ok": False, "error": "No se pudo generar la ficha de estilo.", "ficha": ""}

gemini_service = GeminiService()
