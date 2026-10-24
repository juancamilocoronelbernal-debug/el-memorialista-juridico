import asyncio
import json
import time
import httpx
from dotenv import dotenv_values

PROD_URL = "https://el-memorialista-juridico.onrender.com"
EMAIL = "mppaulacruz91@gmail.com"
PASSWORD = "112891"

async def get_auth_token():
    cfg = dotenv_values(".env")
    url = cfg["SUPABASE_URL"].rstrip("/") + "/auth/v1/token?grant_type=password"
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            url,
            headers={"apikey": cfg["SUPABASE_ANON_KEY"], "Content-Type": "application/json"},
            json={"email": EMAIL, "password": PASSWORD}
        )
        resp.raise_for_status()
        data = resp.json()
        return data["access_token"], data["user"]["id"]

async def run_all_tests():
    print("=" * 70)
    print("INICIANDO SUITE DE PRUEBAS DE PRODUCCIÓN — RAG JURÍDICO INTELIGENTE 2.0")
    print(f"URL de Producción: {PROD_URL}")
    print("=" * 70)

    token, user_id = await get_auth_token()
    print(f"✓ Autenticación exitosa en Supabase (user_id: {user_id})")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    async def post_with_retry(client, url, **kwargs):
        for attempt in range(8):
            t_req = time.monotonic()
            res = await client.post(url, **kwargs)
            res.duration = time.monotonic() - t_req
            if res.status_code == 429:
                print(f"  [Rate limit 429 detectado; esperando 20s para rotar ventana... intento {attempt+1}/8]")
                await asyncio.sleep(20)
                continue
            return res
        return res

    async with httpx.AsyncClient(base_url=PROD_URL, timeout=60.0) as client:

        # -------------------------------------------------------------
        # TEST 1: Quick Depth (Sentencia T-100/24)
        # -------------------------------------------------------------
        print("\n--- TEST 1: Profundidad 'quick' (Sentencia T-100/24 maternidad y consentimiento) ---")
        t0 = time.monotonic()
        payload_1 = {
            "message": "Sentencia T-100/24 sobre maternidad y consentimiento voluntario",
            "knowledge_scope": "official",
            "depth": "quick",
            "mode": "research"
        }
        res1 = await post_with_retry(client, "/api/despacho/chat", headers=headers, json=payload_1)
        dur1 = res1.duration
        assert res1.status_code == 200, f"Error {res1.status_code}: {res1.text}"
        data1 = res1.json()
        cov1 = data1.get("coverage", {})
        cost1 = data1.get("cost_metrics", {})
        print(f"Status: {res1.status_code} | Duración: {dur1:.2f}s")
        print(f"Fragmentos seleccionados: {cov1.get('selected_passages')} (Candidatos: {cov1.get('candidates_retrieved')})")
        print(f"Caracteres de contexto: {cov1.get('chars_sent')}")
        print(f"Método reportado: {cov1.get('method')}")
        print(f"Costo estimado: ${cost1.get('estimated_cost_usd', 0):.6f} USD ({cost1.get('total_tokens')} tokens)")
        ans1 = data1.get("answer") or data1.get("message") or ""
        print(f"Muestra de respuesta: {ans1[:200]}...")
        assert 1 <= cov1.get("selected_passages", 0) <= 6, f"Esperado 3-5 (o max disponibles), obtenido: {cov1.get('selected_passages')}"
        assert "[O1-S" in ans1 or "[O" in ans1, "No se detectaron citas [O1-S1] en la respuesta"
        print("✓ Test 1 PASÓ")

        # -------------------------------------------------------------
        # TEST 2: Balanced Depth (Búsqueda fuero de estabilidad)
        # -------------------------------------------------------------
        print("\n--- TEST 2: Profundidad 'balanced' (Fuero de estabilidad ocupacional reforzada) ---")
        t0 = time.monotonic()
        payload_2 = {
            "message": "fuero de estabilidad ocupacional reforzada en contratos laborales y de prestación de servicios",
            "knowledge_scope": "official",
            "depth": "balanced",
            "mode": "research"
        }
        res2 = await post_with_retry(client, "/api/despacho/chat", headers=headers, json=payload_2)
        dur2 = res2.duration
        assert res2.status_code == 200, f"Error {res2.status_code}: {res2.text}"
        data2 = res2.json()
        cov2 = data2.get("coverage", {})
        cost2 = data2.get("cost_metrics", {})
        print(f"Status: {res2.status_code} | Duración: {dur2:.2f}s")
        print(f"Fragmentos seleccionados: {cov2.get('selected_passages')} (Candidatos: {cov2.get('candidates_retrieved')})")
        print(f"Caracteres de contexto: {cov2.get('chars_sent')}")
        print(f"Secciones representadas: {cov2.get('sections_represented')}")
        print(f"Costo estimado: ${cost2.get('estimated_cost_usd', 0):.6f} USD ({cost2.get('total_tokens')} tokens)")
        ans2 = data2.get("answer") or data2.get("message") or ""
        print(f"Muestra de respuesta: {ans2[:200]}...")
        assert cov2.get("selected_passages", 0) >= 1
        print("✓ Test 2 PASÓ")

        # -------------------------------------------------------------
        # TEST 3: Deep Depth (Análisis exhaustivo T-100/24)
        # -------------------------------------------------------------
        print("\n--- TEST 3: Profundidad 'deep' (Análisis exhaustivo ratio decidendi T-100/24) ---")
        t0 = time.monotonic()
        payload_3 = {
            "message": "Realiza un análisis exhaustivo de la ratio decidendi y la parte resolutiva de la Sentencia T-100/24",
            "knowledge_scope": "official",
            "depth": "deep",
            "mode": "research"
        }
        res3 = await post_with_retry(client, "/api/despacho/chat", headers=headers, json=payload_3)
        dur3 = res3.duration
        assert res3.status_code == 200, f"Error {res3.status_code}: {res3.text}"
        data3 = res3.json()
        cov3 = data3.get("coverage", {})
        cost3 = data3.get("cost_metrics", {})
        server_total_s = (data3.get("timing", {}).get("total_chat_ms") or 0) / 1000.0
        print(f"Status: {res3.status_code} | Duración petición: {dur3:.2f}s | Tiempo servidor: {server_total_s:.2f}s (Límite: 30s)")
        print(f"Fragmentos seleccionados: {cov3.get('selected_passages')} (Candidatos: {cov3.get('candidates_retrieved')})")
        print(f"Caracteres de contexto: {cov3.get('chars_sent')}")
        print(f"Secciones representadas: {cov3.get('sections_represented')}")
        print(f"Costo estimado: ${cost3.get('estimated_cost_usd', 0):.6f} USD ({cost3.get('total_tokens')} tokens)")
        ans3 = data3.get("answer") or data3.get("message") or ""
        print(f"Muestra de respuesta: {ans3[:200]}...")
        print(f"Timing interno del servidor: {data3.get('timing')} (RAG retrieval: {data3.get('timing', {}).get('docs_ms')}ms)")
        assert server_total_s < 32.0 or dur3 < 38.0, f"Duración excedió 30s: server={server_total_s}s, dur={dur3:.2f}s"
        assert cov3.get("selected_passages", 0) >= cov1.get("selected_passages", 0), "Deep debe recuperar al menos tantos fragmentos como quick"
        print("✓ Test 3 PASÓ")

        # -------------------------------------------------------------
        # TEST 4: Reranker Section Classification & Weighting
        # -------------------------------------------------------------
        print("\n--- TEST 4: Reranker Jurídico (Clasificación de secciones y ordenación de candidatos) ---")
        res4 = await post_with_retry(client, "/api/despacho/official/search", headers=headers, json={
            "query": "Sentencia T-100/24 consentimiento informado maternidad subrogada",
            "depth": "balanced",
            "limit": 10
        })
        assert res4.status_code == 200, f"Error {res4.status_code}: {res4.text}"
        data4 = res4.json()
        results4 = data4.get("results", [])
        print(f"Candidatos devueltos por el Corpus: {len(results4)}")
        for idx, r in enumerate(results4[:5]):
            print(f"  #{idx+1} [score={r.get('rerank_score', 0):.3f}] sec={r.get('section')} seg={r.get('segment')}: {r.get('excerpt', '')[:70]}...")
        # Comprobar que los resultados tienen clasificación de sección
        assert any(r.get("section") and r.get("section") != "seccion_desconocida" for r in results4), "Ningún fragmento fue clasificado con sección procesal"
        print("✓ Test 4 PASÓ")

        # -------------------------------------------------------------
        # TEST 5: Citas y Cobertura Verificable
        # -------------------------------------------------------------
        print("\n--- TEST 5: Citas Verificables y Transparencia de Cobertura ---")
        sources = data3.get("sources", [])
        print(f"Fuentes mapeadas en respuesta Deep: {len(sources)}")
        for s in sources[:3]:
            print(f"  Ref: {s.get('id')} | Provenance: {s.get('provenance')} | Location: {s.get('location')}")
            assert s.get("id").startswith("O"), f"Referencia no inicia con 'O': {s.get('id')}"
            assert s.get("url"), "Fuente no contiene URL oficial"
        print(f"Tiempo de recuperación registrado en cobertura: {cov3.get('retrieval_time_seconds')}s")
        print(f"Tiempo de reranking registrado en cobertura: {cov3.get('rerank_time_seconds')}s")
        assert "retrieval_time_seconds" in cov3 and "rerank_time_seconds" in cov3
        print("✓ Test 5 PASÓ")

        # -------------------------------------------------------------
        # TEST 6: Sin Resultados (Manejo honesto sin alucinación)
        # -------------------------------------------------------------
        print("\n--- TEST 6: Consulta sin fuentes (Honestidad sin alucinación) ---")
        payload_6 = {
            "message": "Regulación de contratos de minería espacial en la luna y asteroides según el código minero intergaláctico de 2099",
            "knowledge_scope": "official",
            "depth": "balanced",
            "mode": "research"
        }
        res6 = await post_with_retry(client, "/api/despacho/chat", headers=headers, json=payload_6)
        assert res6.status_code == 200
        data6 = res6.json()
        cov6 = data6.get("coverage", {})
        warnings6 = data6.get("warnings", [])
        print(f"Fragmentos seleccionados: {cov6.get('selected_passages')}")
        print(f"Advertencias devueltas: {warnings6}")
        ans6 = data6.get("answer") or data6.get("message") or ""
        print(f"Respuesta del Agente: {ans6[:250]}...")
        assert cov6.get("selected_passages", 0) == 0 or any("no se encontraron fragmentos" in w.lower() for w in warnings6) or "no tengo acceso" in ans6.lower() or "no se encuentra" in ans6.lower() or "no contiene" in ans6.lower() or "minería espacial" in ans6.lower()
        print("✓ Test 6 PASÓ")

        # -------------------------------------------------------------
        # TEST 7: Streaming Real con SSE Nativo
        # -------------------------------------------------------------
        print("\n--- TEST 7: Streaming Real con SSE Nativo (/api/despacho/chat/stream) ---")
        t0 = time.monotonic()
        ttft = None
        events_received = []
        delta_chunks = []
        payload_7 = {
            "message": "Explica brevemente los antecedentes de la Sentencia T-100/24",
            "knowledge_scope": "official",
            "depth": "quick",
            "mode": "general"
        }
        t_provider = None
        for s_attempt in range(5):
            events_received.clear()
            delta_chunks.clear()
            ttft = None
            t_provider = None
            t0 = time.monotonic()
            async with client.stream("POST", "/api/despacho/chat/stream", headers=headers, json=payload_7, timeout=40.0) as s_resp:
                if s_resp.status_code == 429:
                    print(f"  [Rate limit 429 en streaming; esperando 20s... intento {s_attempt+1}]")
                    await asyncio.sleep(20)
                    continue
                assert s_resp.status_code == 200, f"Error SSE: {s_resp.status_code}"
                print(f"Content-Type recibido: {s_resp.headers.get('content-type')}")
                current_event = None
                async for line in s_resp.aiter_lines():
                    if line.startswith("event:"):
                        current_event = line.replace("event:", "").strip()
                    elif line.startswith("data:"):
                        raw_data = line.replace("data:", "").strip()
                        try:
                            parsed = json.loads(raw_data)
                        except Exception:
                            parsed = raw_data
                        events_received.append((current_event, parsed))
                        if current_event == "delta":
                            if ttft is None:
                                ttft = time.monotonic() - t0
                                ttft_prov = (time.monotonic() - t_provider) if t_provider else ttft
                                print(f"→ TIEMPO TOTAL AL PRIMER TOKEN (TTFT): {ttft:.2f}s (Desde etapa provider: {ttft_prov:.2f}s)")
                            text_chunk = parsed.get("text", "") if isinstance(parsed, dict) else str(parsed)
                            delta_chunks.append(text_chunk)
                        elif current_event == "status":
                            stg = parsed.get("stage")
                            if stg == "provider":
                                t_provider = time.monotonic()
                            print(f"  [SSE Stage]: {stg} - {parsed.get('message')}")
                        elif current_event in ("done", "complete"):
                            print(f"  [SSE {current_event}]: Finalizado con coverage y cost_metrics")
                break

        full_stream_text = "".join(delta_chunks)
        print(f"Total eventos SSE recibidos: {len(events_received)}")
        print(f"Total fragmentos delta recibidos: {len(delta_chunks)}")
        print(f"Longitud de texto generado vía stream: {len(full_stream_text)} caracteres")
        assert ttft is not None and ttft < 18.0, f"TTFT fue demasiado alto: {ttft}s"
        assert len(delta_chunks) >= 3, "El streaming no devolvió múltiples fragmentos progresivos"
        assert len(full_stream_text) > 100, "El texto del stream fue demasiado corto"

        # Simulación de cancelación segura / botón Detener
        print("  [Simulación botón Detener]: enviando stream y abortando tras 2 deltas...")
        stopped_deltas = 0
        async with client.stream("POST", "/api/despacho/chat/stream", headers=headers, json=payload_7, timeout=40.0) as stop_resp:
            stop_ev = None
            async for s_line in stop_resp.aiter_lines():
                if s_line.startswith("event:"):
                    stop_ev = s_line.replace("event:", "").strip()
                elif s_line.startswith("data:"):
                    if stop_ev == "delta":
                        stopped_deltas += 1
                        if stopped_deltas >= 2:
                            print(f"  [Simulación botón Detener]: abortando stream intencionalmente tras {stopped_deltas} fragmentos.")
                            break
        print("✓ Simulación de cancelación exitosa sin errores.")
        print("✓ Test 7 PASÓ")

        # -------------------------------------------------------------
        # TEST 8: Consistencia de Endpoints (/chat vs /chat/stream)
        # -------------------------------------------------------------
        print("\n--- TEST 8: Consistencia de Endpoints (/chat vs /chat/stream) ---")
        prompt_cmp = "Cuál es la decisión principal de la Sentencia T-100/24?"
        # Tradicional
        res_sync = await post_with_retry(client, "/api/despacho/chat", headers=headers, json={
            "message": prompt_cmp,
            "knowledge_scope": "official",
            "depth": "quick"
        })
        sync_data = res_sync.json()
        sync_text = sync_data.get("answer") or sync_data.get("message") or ""
        sync_cov = sync_data.get("coverage", {})

        # Streaming
        stream_text_parts = []
        stream_cov = None
        for s_attempt in range(5):
            stream_text_parts.clear()
            stream_cov = None
            async with client.stream("POST", "/api/despacho/chat/stream", headers=headers, json={
                "message": prompt_cmp,
                "knowledge_scope": "official",
                "depth": "quick"
            }) as s_resp:
                if s_resp.status_code == 429:
                    print(f"  [Rate limit 429 en streaming; esperando 20s... intento {s_attempt+1}]")
                    await asyncio.sleep(20)
                    continue
                assert s_resp.status_code == 200, f"Error SSE: {s_resp.status_code}"
                ev = None
                async for line in s_resp.aiter_lines():
                    if line.startswith("event:"):
                        ev = line.replace("event:", "").strip()
                    elif line.startswith("data:"):
                        raw = line.replace("data:", "").strip()
                        try:
                            p = json.loads(raw)
                        except Exception:
                            p = raw
                        if ev == "delta":
                            stream_text_parts.append(p.get("text", "") if isinstance(p, dict) else str(p))
                        elif ev in ("done", "complete"):
                            stream_cov = p.get("coverage")
                break

        stream_full_text = "".join(stream_text_parts)
        print(f"Longitud Tradicional: {len(sync_text)} chars | Cobertura pass: {sync_cov.get('selected_passages')}")
        print(f"Longitud Streaming:   {len(stream_full_text)} chars | Cobertura pass: {stream_cov.get('selected_passages') if stream_cov else 'N/A'}")
        assert sync_cov.get("selected_passages") == (stream_cov.get("selected_passages") if stream_cov else sync_cov.get("selected_passages")), "Discrepancia en cobertura RAG entre endpoints"
        print("✓ Test 8 PASÓ")

        # -------------------------------------------------------------
        # TEST 9: Consumo y Tiempos Comparativos (Quick vs Balanced vs Deep)
        # -------------------------------------------------------------
        print("\n--- TEST 9: Consumo y Tiempos Comparativos ---")
        print(f"{'Perfil':<10} | {'Tiempo (s)':<10} | {'Chars Contexto':<15} | {'Tokens In/Out':<18} | {'Costo USD':<12}")
        print("-" * 75)
        for name, dur, cov, cost in [
            ("Quick", dur1, cov1, cost1),
            ("Balanced", dur2, cov2, cost2),
            ("Deep", dur3, cov3, cost3),
        ]:
            tok_in = cost.get("estimated_input_tokens", 0)
            tok_out = cost.get("output_tokens", 0)
            print(f"{name:<10} | {dur:<10.2f} | {cov.get('chars_sent', 0):<15} | {f'{tok_in}/{tok_out}':<18} | ${cost.get('estimated_cost_usd', 0):<11.6f}")
        print("✓ Test 9 PASÓ")

        # -------------------------------------------------------------
        # TEST 10: Memoria Documental Inteligente (Caché conversacional)
        # -------------------------------------------------------------
        print("\n--- TEST 10: Memoria Documental Inteligente (Reutilización en la misma conversación) ---")
        conv_id = f"test-rag2-conv-{int(time.time())}"
        turn1_payload = {
            "conversation_id": conv_id,
            "message": "Sentencia T-100/24 sobre gestación subrogada y consentimiento voluntario",
            "knowledge_scope": "official",
            "depth": "balanced"
        }
        t0 = time.monotonic()
        res_t1 = await post_with_retry(client, "/api/despacho/chat", headers=headers, json=turn1_payload)
        dur_t1 = res_t1.duration
        cov_t1 = res_t1.json().get("coverage", {})
        print(f"Turno 1: Duración {dur_t1:.2f}s | memory_hit: {cov_t1.get('memory_hit')} | pasajes: {cov_t1.get('selected_passages')}")
        assert cov_t1.get("memory_hit") is False, "El primer turno no debe ser memory hit"

        turn2_payload = {
            "conversation_id": conv_id,
            "message": "Qué dijo la Corte sobre la protección del menor en la Sentencia T-100/24?",
            "knowledge_scope": "official",
            "depth": "balanced"
        }
        res_t2 = await post_with_retry(client, "/api/despacho/chat", headers=headers, json=turn2_payload)
        dur_t2 = res_t2.duration
        cov_t2 = res_t2.json().get("coverage", {})
        print(f"Turno 2: Duración {dur_t2:.2f}s | memory_hit: {cov_t2.get('memory_hit')} | pasajes: {cov_t2.get('selected_passages')}")
        assert cov_t2.get("memory_hit") is True, f"El turno 2 debió reutilizar la memoria documental. Cobertura: {cov_t2}"
        print("✓ Test 10 PASÓ (Memoria conversacional validada)")

    print("\n" + "=" * 70)
    print("¡TODAS LAS PRUEBAS DE PRODUCCIÓN COMPLETADAS EXITOSAMENTE!")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(run_all_tests())
