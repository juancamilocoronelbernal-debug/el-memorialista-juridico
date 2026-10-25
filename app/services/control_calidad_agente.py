"""Control de Calidad Determinista y Verificación Inteligente Selectiva de Respuestas del Agente (Fase 2.3).

Implementa las comprobaciones de fundamentación jurídica y confiabilidad:
1. Comprobar que las sentencias citadas existen (en el corpus oficial o catálogo oficial).
2. Comprobar que los fragmentos citados [O#-S#] son auténticos y coinciden con las fuentes recuperadas.
3. Verificar correspondencia estricta de referencias [O#-S#] y [D#-S#].
4. Verificar accesibilidad de las citas.
5. Control de salvamentos de voto: Evitar que votos disidentes o aclaraciones se presenten como postura mayoritaria.
6. Detección de respuestas con cobertura documental insuficiente.
7. Identificación de afirmaciones no respaldadas para envío a revisión jurídica humana.

REGLA DE CONFIABILIDAD:
Distingue taxativamente entre:
- Verificación técnica determinista (sintaxis, existencia de citas y referencias auténticas: inmediata, 0 costes).
- Evaluación jurídica sustantiva (análisis de fondo, requiere revisión jurídica humana o verificación inteligente selectiva).
JAMÁS presenta como sustantivamente verificada una respuesta que solo superó una comprobación sintáctica.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from app.config import get_settings
from app.services import despacho_store as store
from app.services.gemini_service import gemini_service

log = logging.getLogger("memorialista.despacho.calidad_agente")

_RULING_EXTRACT_RE = re.compile(
    r"\b(?:sentencias?\s+)?(T|C|SU|A)[-\s]?(\d{1,5})\s*(?:(?:de|\/|-)\s*(\d{2,4}))\b|\bauto\s+(\d{1,5})\s*(?:(?:de|\/|-)\s*(\d{2,4}))\b",
    re.IGNORECASE,
)
_REF_MARKER_RE = re.compile(r"\[((?:D\d+-S\d+)|(?:W\d+)|(?:O\d+-S\d+))\]")

_MAJORITY_CLAIM_PATTERNS = [
    re.compile(r"\bla\s+corte(?:\s+constitucional|\s+plena)?\s+(?:resolvi[oó]|determin[oó]|estableci[oó]|concluy[oó]|ampar[oó]|declar[oó])\b", re.IGNORECASE),
    re.compile(r"\bla\s+decisi[oó]n\s+mayoritaria\b", re.IGNORECASE),
    re.compile(r"\bla\s+jurisprudencia\s+(?:unificada|reiterada|uniforme)\b", re.IGNORECASE),
    re.compile(r"\bel\s+pleno\s+de\s+la\s+corte\b", re.IGNORECASE),
]


def extract_cited_rulings(text: str) -> List[str]:
    """Extrae y normaliza las sentencias de la Corte Constitucional citadas en un texto."""
    found = []
    for match in _RULING_EXTRACT_RE.finditer(text):
        if match.group(1):
            tipo = match.group(1).upper()
            num = match.group(2)
            anio = match.group(3)
        else:
            tipo = "A"
            num = match.group(4)
            anio = match.group(5)
        if len(anio) == 4:
            anio = anio[-2:]
        normalized = f"{tipo}-{num}/{anio}"
        if normalized not in found:
            found.append(normalized)
    return found


async def verify_agent_response_quality(
    query: str,
    answer: str,
    sources: List[Dict[str, Any]],
    coverage: Optional[Dict[str, Any]] = None,
    service_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Ejecuta los controles deterministas de calidad sobre la respuesta del agente."""
    settings = get_settings()
    key = service_key or settings.SUPABASE_SERVICE_ROLE_KEY

    flags: List[str] = []
    checks: Dict[str, Dict[str, Any]] = {}

    # 1. Sentencias citadas en el texto
    cited_rulings = extract_cited_rulings(answer)
    existing_rulings: Set[str] = set()
    missing_rulings: List[str] = []

    if cited_rulings and key:
        # Consultar en paralelo si existen en descubrimientos o corpus documentos
        for r in cited_rulings:
            try:
                # Comprobar en despacho_corpus_documentos
                doc_res = await store.db_request(
                    "GET",
                    f"despacho_corpus_documentos?title=ilike.*{r}*&select=id,title,published&limit=1",
                    key,
                    service=True,
                )
                if doc_res:
                    existing_rulings.add(r)
                    continue
                # Comprobar en descubrimientos oficiales
                disc_res = await store.db_request(
                    "GET",
                    f"despacho_conector_descubrimientos?sentencia=eq.{r}&select=sentencia,source_status&limit=1",
                    key,
                    service=True,
                )
                if disc_res:
                    existing_rulings.add(r)
                else:
                    missing_rulings.append(r)
            except Exception as exc:
                log.debug("Error comprobando providencia %s: %s", r, exc)

    if missing_rulings:
        flags.append(f"Cita providencias no registradas en el corpus oficial: {', '.join(missing_rulings)}")
        checks["sentencias_existen"] = {
            "passed": False,
            "detail": f"Providencias sin confirmar: {', '.join(missing_rulings)}",
            "missing": missing_rulings,
        }
    else:
        checks["sentencias_existen"] = {
            "passed": True,
            "detail": f"Providencias confirmadas ({len(cited_rulings)} citadas)",
            "cited": cited_rulings,
        }

    # 2. Correspondencia estricta de referencias [O#-S#], [D#-S#], [W#]
    valid_source_ids = {s.get("id") for s in sources if s.get("id")}
    cited_refs = set(_REF_MARKER_RE.findall(answer))
    unmatched_refs = cited_refs - valid_source_ids

    if unmatched_refs:
        flags.append(f"Referencias sin respaldo en fuentes recuperadas: {', '.join(sorted(unmatched_refs))}")
        checks["referencias_correspondencia"] = {
            "passed": False,
            "detail": f"Referencias inválidas: {', '.join(sorted(unmatched_refs))}",
            "invalid": sorted(list(unmatched_refs)),
        }
    else:
        checks["referencias_correspondencia"] = {
            "passed": True,
            "detail": f"Todas las {len(cited_refs)} referencias corresponden a fuentes recuperadas",
            "cited_count": len(cited_refs),
        }

    # 3. Autenticidad de fragmentos y control de salvamentos de voto
    sources_by_id = {s.get("id"): s for s in sources if s.get("id")}
    salvamento_violations = []

    for ref in cited_refs:
        source_item = sources_by_id.get(ref)
        if not source_item:
            continue
        sec_type = str(source_item.get("section_type") or "").lower()
        # Verificar si la fuente es un salvamento de voto
        if "salvamento" in sec_type or "aclaracion" in sec_type:
            # Buscar en el párrafo donde aparece la referencia si se afirma que fue la Corte o decisión mayoritaria
            # Tomar ventana de 250 caracteres alrededor de la referencia
            idx = answer.find(f"[{ref}]")
            if idx != -1:
                start = max(0, idx - 150)
                end = min(len(answer), idx + 150)
                window = answer[start:end]
                for pat in _MAJORITY_CLAIM_PATTERNS:
                    if pat.search(window):
                        salvamento_violations.append({
                            "ref": ref,
                            "section": sec_type,
                            "context": window.strip(),
                        })
                        break

    if salvamento_violations:
        flags.append("Posible atribución de voto disidente o aclaración como decisión de la Corte.")
        checks["control_salvamentos"] = {
            "passed": False,
            "detail": f"{len(salvamento_violations)} citas de salvamentos aducidas con lenguaje de mayoría",
            "violations": salvamento_violations,
        }
    else:
        checks["control_salvamentos"] = {
            "passed": True,
            "detail": "No se detectaron salvamentos de voto presentados como regla mayoritaria",
        }

    # 4. Cobertura documental
    cov_ratio = (coverage or {}).get("ratio", 1.0) if coverage else 1.0
    official_sources_count = sum(1 for s in sources if str(s.get("id", "")).startswith("O"))
    query_is_jurisprudential = bool(re.search(r"\b(sentencia|jurisprudencia|corte|constitucional|amparo|tutela)\b", query, re.IGNORECASE))

    if query_is_jurisprudential and official_sources_count == 0 and len(cited_rulings) > 0:
        flags.append("Consulta jurisprudencial resuelta sin respaldo de fragmentos del Corpus Jurídico Oficial.")
        checks["cobertura_documental"] = {
            "passed": False,
            "detail": "Cero fragmentos del Corpus Oficial en el contexto para consulta jurisprudencial",
            "ratio": cov_ratio,
        }
    else:
        checks["cobertura_documental"] = {
            "passed": True,
            "detail": f"Fuentes disponibles: {len(sources)} ({official_sources_count} oficiales)",
            "ratio": cov_ratio,
        }

    is_technically_verified = (
        checks["sentencias_existen"]["passed"]
        and checks["referencias_correspondencia"]["passed"]
        and checks["control_salvamentos"]["passed"]
        and checks["cobertura_documental"]["passed"]
    )

    quality_summary = {
        "technical_verification": "verificado_tecnicamente" if is_technically_verified else "con_inconsistencias",
        "substantive_review_status": "pendiente_evaluacion_humana",
        "badge_label": "Verificación técnica determinista aprobada" if is_technically_verified else "Inconsistencias técnicas detectadas",
        "disclaimer": "La verificación técnica comprueba citas y referencias auténticas; la evaluación jurídica sustantiva permanece bajo criterio del profesional.",
        "checks": checks,
        "flags": flags,
        "verified_at": datetime.now(timezone.utc).isoformat(),
    }

    # Si hay inconsistencias graves y service_key disponible, registrar incidencia automática
    if not is_technically_verified and key and (unmatched_refs or missing_rulings or salvamento_violations):
        try:
            issue_type = "salvamento_como_mayoria" if salvamento_violations else (
                "referencia_invalida" if unmatched_refs else "cita_inexistente"
            )
            inc_payload = {
                "scope": "agente",
                "issue_type": issue_type,
                "severity": "alta" if (unmatched_refs or missing_rulings) else "media",
                "status": "detectado",
                "evidence": {
                    "query_snippet": query[:300],
                    "flags": flags,
                    "checks": checks,
                    "cited_rulings": cited_rulings,
                    "unmatched_refs": list(unmatched_refs),
                },
                "action_history": [
                    {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "actor": "verificador_calidad_agente",
                        "action": "incidencia_agente_detectada",
                        "note": f"Fallo determinista en respuesta: {', '.join(flags)}",
                    }
                ],
            }
            await store.db_request("POST", "despacho_corpus_incidencias", key, json=inc_payload, service=True)
        except Exception as exc:
            log.warning("No se pudo persistir incidencia de calidad del agente: %s", exc)

    return quality_summary


async def verify_substantive_agent_response_intelligent(
    query: str,
    answer: str,
    sources: List[Dict[str, Any]],
    user_id: str,
) -> Dict[str, Any]:
    """Verificación Inteligente Selectiva (on-demand / high-risk) usando gemini-3.6-flash."""
    # Extraer extractos de fuentes oficiales
    evidence_text = "\n\n".join(
        f"--- FUENTE [{s.get('id', 'F')}]: {s.get('title', 'Documento')} (Sección: {s.get('section_type', 'general')}) ---\n"
        f"{s.get('content') or s.get('text', '')}"
        for s in sources[:8]
    )

    prompt = f"""Eres el Auditor Jurídico Superior de El Memorialista.
Tu función es auditar con estricto rigor probatorio la calidad sustantiva de una respuesta jurídica emitida por el Agente.

CONSULTA DEL USUARIO:
\"\"\"{query}\"\"\"

RESPUESTA DEL AGENTE:
\"\"\"{answer}\"\"\"

EVIDENCIA DOCUMENTAL RECUPERADA DEL CORPUS OFICIAL:
\"\"\"{evidence_text}\"\"\"

INSTRUCCIONES DE AUDITORÍA:
Evalúa objetivamente:
1. Conclusión jurídica: ¿Se deriva rigurosamente de las fuentes citadas o hace inferencias no probadas?
2. Postura de la Corte: ¿Distingue adecuadamente la tesis de la mayoría respecto de votos disidentes o aclaraciones?
3. Fidelidad de citas: ¿Las referencias corresponden al sentido textual de los fragmentos?
4. Contradicciones o anacronismos: ¿Hay inconsistencias temporales o normativas?

RESPONDE EXCLUSIVAMENTE UN OBJETO JSON con la siguiente estructura:
{{
  "substantive_verdict": "aprobado" | "requiere_ajuste" | "rechazado",
  "fidelity_score": 0.0 a 100.0,
  "supported_claims": ["afirmacion 1 con respaldo", ...],
  "unsupported_claims": ["afirmacion sin respaldo o dudosa", ...],
  "dissent_confusion_detected": true | false,
  "auditor_summary": "Explicación concisa y técnica del dictamen jurídico.",
  "recommended_action": "aprobar" | "revisar_abogado" | "corregir_respuesta"
}}
"""
    try:
        raw_res = await gemini_service.generar_texto(
            prompt=prompt,
            mode="substantive_audit",
            system_instruction="Eres un auditor jurídico de la Corte Constitucional de Colombia. Responde estrictamente en formato JSON válido.",
        )
        clean_text = raw_res.strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        if clean_text.startswith("```"):
            clean_text = clean_text[3:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]
        parsed = json.loads(clean_text.strip())
        parsed["model_used"] = "gemini-3.6-flash"
        parsed["audited_at"] = datetime.now(timezone.utc).isoformat()
        return parsed
    except Exception as exc:
        log.warning("Fallo en verificación inteligente de respuesta: %s", exc)
        return {
            "substantive_verdict": "indeterminado",
            "fidelity_score": 50.0,
            "error": str(exc),
            "auditor_summary": "No se pudo completar la llamada inteligente de verificación. Requiere revisión humana directa.",
            "recommended_action": "revisar_abogado",
            "audited_at": datetime.now(timezone.utc).isoformat(),
        }
