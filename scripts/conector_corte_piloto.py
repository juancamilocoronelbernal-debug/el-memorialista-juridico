"""Script administrativo para ejecución y verificación del Conector Oficial de la Corte Constitucional (Fase 2).

Uso:
  python scripts/conector_corte_piloto.py --status
  python scripts/conector_corte_piloto.py --pilot --limit 20
  python scripts/conector_corte_piloto.py --idempotency-check
"""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services import conector_corte_constitucional as conector


async def main():
    parser = argparse.ArgumentParser(description="Conector Oficial Corte Constitucional - Fase 2")
    parser.add_argument("--status", action="store_true", help="Muestra el estado actual del conector")
    parser.add_argument("--pilot", action="store_true", help="Ejecuta el piloto controlado de hasta 20 providencias")
    parser.add_argument("--limit", type=int, default=20, help="Límite máximo de providencias en el piloto (máx 20)")
    parser.add_argument("--no-semantic", action="store_true", help="Ejecuta sin generar embeddings vectoriales")
    parser.add_argument("--idempotency-check", action="store_true", help="Ejecuta una segunda pasada para verificar idempotencia absoluta")

    args = parser.parse_args()

    if args.status:
        st = await conector.get_connector_status()
        print(json.dumps(st, indent=2, ensure_ascii=False))
        return

    if args.pilot:
        lim = min(args.limit, 20)
        print(f"=== INICIANDO PILOTO CONTROLADO: MÁXIMO {lim} PROVIDENCIAS OFICIALES ===")
        t0 = time.monotonic()
        rep = await conector.run_controlled_pilot(max_rulings=lim, semantic=not args.no_semantic)
        dur = round(time.monotonic() - t0, 2)
        print(f"\n--- REPORTE DEL PILOTO ({dur}s) ---")
        print(f"Estado final: {rep['status']}")
        print(f"Descubiertos: {rep['discovered_count']}")
        print(f"Recuperados: {rep['retrieved_count']}")
        print(f"Publicados: {rep['published_count']}")
        print(f"Sin cambios (ya publicados): {rep['unchanged_count']}")
        print(f"Rechazados: {rep['rejected_count']}")
        print(f"Fragmentos indexados: {rep['fragments_count']}")
        print(f"Embeddings generados: {rep['embeddings_count']}")
        print(f"Tokens consumidos: {rep['total_tokens_consumed']}")
        print(f"Coste estimado: ${rep['estimated_cost_usd']} USD")
        if rep['errors']:
            print(f"Errores: {rep['errors']}")

        if args.idempotency_check:
            print("\n=== VERIFICACIÓN OBLIGATORIA DE IDEMPOTENCIA (SEGUNDA EJECUCIÓN) ===")
            t1 = time.monotonic()
            rep2 = await conector.run_controlled_pilot(max_rulings=lim, semantic=not args.no_semantic)
            dur2 = round(time.monotonic() - t1, 2)
            print(f"Segunda ejecución completada en {dur2}s")
            print(f"Publicados nuevos: {rep2['published_count']} (debe ser 0)")
            print(f"Sin cambios detectados: {rep2['unchanged_count']} (debe ser {rep['retrieved_count']})")
            print(f"Embeddings generados: {rep2['embeddings_count']} (debe ser 0)")
            print(f"Coste de segunda ejecución: ${rep2['estimated_cost_usd']} USD (debe ser $0.0)")
            assert rep2['published_count'] == 0, "Fallo: la segunda ejecución intentó volver a publicar documentos"
            assert rep2['embeddings_count'] == 0, "Fallo: la segunda ejecución consumió embeddings en documentos idénticos"
            print("✓ IDEMPOTENCIA TOTAL VERIFICADA: Cero reindexaciones, cero consumo innecesario.")

        return

    # Si no se pasó argumento, mostrar ayuda
    parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())
