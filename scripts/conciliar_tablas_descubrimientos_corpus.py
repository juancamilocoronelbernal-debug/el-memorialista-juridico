# -*- coding: utf-8 -*-
"""
Script de conciliación y sincronización bidireccional entre:
- despacho_corpus_documentos
- despacho_conector_descubrimientos

Sincroniza las 13 providencias C y SU procesadas para el lote de 25 en triage hacia
despacho_conector_descubrimientos con su document_id permanente y source_status='technically_validated'.
"""

import asyncio
import json
import logging
import re
from app.config import get_settings
from app.services import despacho_store as store

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("memorialista.conciliacion")

def norm(s):
    s = (s or "").strip().upper()
    m = re.search(r'(T|C|SU|A)[-\s]?(\d{1,5})[\s\/\-](\d{2,4})', s)
    if m:
        t, n, y = m.group(1), m.group(2), m.group(3)
        if len(y) == 4: y = y[2:]
        return f'{t}-{n}/{y}'
    return s

async def main():
    settings = get_settings()
    key = settings.SUPABASE_SERVICE_ROLE_KEY
    if not key:
        raise ValueError("Se requiere SUPABASE_SERVICE_ROLE_KEY")

    # 1. Consultar estado actual
    desc_rows = await store.db_request("GET", "despacho_conector_descubrimientos?select=id,sentencia,source_status,document_id", key, service=True) or []
    corpus_rows = await store.db_request("GET", "despacho_corpus_documentos?select=id,title,source_url,metadata,workflow_status,published,first_seen_at", key, service=True) or []

    desc_map = {norm(d["sentencia"]): d for d in desc_rows if d.get("sentencia")}
    
    missing_in_desc = []
    for c in corpus_rows:
        meta = c.get("metadata") or {}
        if isinstance(meta, str):
            try: meta = json.loads(meta)
            except: meta = {}
        s = norm(meta.get("sentencia") or c.get("title") or "")
        if s and s not in desc_map:
            missing_in_desc.append((s, c, meta))

    log.info("Providencias presentes en corpus_documentos pero faltantes en descubrimientos: %d", len(missing_in_desc))

    for s, c, meta in missing_in_desc:
        tipo = "T" if s.startswith("T-") else ("C" if s.startswith("C-") else ("SU" if s.startswith("SU-") else "A"))
        fecha = meta.get("fecha") or meta.get("decision_date") or ""
        anio = meta.get("anio") or (int(fecha[:4]) if (fecha and len(fecha) >= 4 and fecha[:4].isdigit()) else None)
        
        doc_id = c["id"]
        is_published = bool(c.get("published"))
        target_status = "published" if is_published else "technically_validated"
        
        payload = {
            "sentencia": s,
            "tipo": tipo,
            "anio": anio,
            "fecha": fecha,
            "magistrado": meta.get("magistrado"),
            "sala": meta.get("sala"),
            "expediente": meta.get("expediente") or meta.get("radicado"),
            "proceso": meta.get("proceso") or "Control de constitucionalidad / Tutela",
            "tema": meta.get("tema") or meta.get("materia"),
            "source_dataset": "relatoria_oficial",
            "source_url": c.get("source_url"),
            "source_status": target_status,
            "document_id": doc_id,
            "metadata": meta,
            "first_discovered_at": c.get("first_seen_at"),
            "last_checked_at": c.get("first_seen_at"),
        }

        log.info("Sincronizando atómicamente en despacho_conector_descubrimientos: %s (doc_id=%s, status=%s)", s, doc_id, target_status)
        await store.db_request("POST", "rpc/despacho_upsert_descubrimiento", key, service=True, json={"p_data": payload})

    # Verificación posterior
    desc_after = await store.db_request("GET", "despacho_conector_descubrimientos?select=id,sentencia,source_status,document_id", key, service=True) or []
    corpus_after = await store.db_request("GET", "despacho_corpus_documentos?select=id,title,published,workflow_status", key, service=True) or []
    
    desc_published = [d for d in desc_after if d.get("source_status") == "published"]
    desc_triage = [d for d in desc_after if d.get("source_status") in ("technically_validated", "pending_legal_review")]
    desc_pending_source = [d for d in desc_after if d.get("source_status") in ("pending_source", "temporarily_unavailable")]
    
    corpus_published = [c for c in corpus_after if c.get("published")]
    corpus_triage = [c for c in corpus_after if not c.get("published")]

    log.info("=== RESULTADO POST-CONCILIACIÓN ===")
    log.info("Total descubrimientos: %d", len(desc_after))
    log.info("  - Publicadas en descubrimientos: %d (esperadas: %d)", len(desc_published), len(corpus_published))
    log.info("  - Validadas en triage descubrimientos: %d (esperadas: %d)", len(desc_triage), len(corpus_triage))
    log.info("  - Pendientes de fuente oficial: %d", len(desc_pending_source))
    log.info("Total documentos en corpus: %d", len(corpus_after))
    log.info("  - Publicadas en corpus: %d", len(corpus_published))
    log.info("  - En triage en corpus: %d", len(corpus_triage))

if __name__ == "__main__":
    asyncio.run(main())
