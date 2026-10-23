import asyncio
import json
import subprocess
import time
import httpx
import websockets

async def run_browser_test():
    # 1. Start uvicorn server
    app_proc = subprocess.Popen(
        ['./venv/bin/python', '-m', 'uvicorn', 'app.main:app', '--port', '8765', '--host', '127.0.0.1'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    chrome_proc = None
    try:
        # Wait for app server
        for _ in range(30):
            try:
                r = httpx.get('http://127.0.0.1:8765/', timeout=1.0)
                if r.status_code == 200:
                    break
            except Exception:
                time.sleep(0.2)
        else:
            raise RuntimeError("Uvicorn app server did not start in time")
            
        print("✓ Uvicorn app server running on http://127.0.0.1:8765")

        # 2. Start Chrome
        chrome_bin = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
        chrome_proc = subprocess.Popen([
            chrome_bin,
            '--headless=new',
            '--remote-debugging-port=9225',
            '--no-first-run',
            '--no-default-browser-check',
            'about:blank'
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Wait for Chrome CDP
        for _ in range(30):
            try:
                v = httpx.get('http://127.0.0.1:9225/json/version', timeout=1.0).json()
                if 'webSocketDebuggerUrl' in v:
                    break
            except Exception:
                time.sleep(0.2)
        else:
            raise RuntimeError("Chrome CDP did not start in time")

        tabs = httpx.get('http://127.0.0.1:9225/json/list').json()
        page_tab = next(t for t in tabs if t.get('type') == 'page')
        ws_url = page_tab['webSocketDebuggerUrl']
        print(f"✓ Chrome CDP connected to page tab: {ws_url}")

        async with websockets.connect(ws_url) as ws:
            msg_id = 0
            async def send(method, params=None):
                nonlocal msg_id
                msg_id += 1
                req = {"id": msg_id, "method": method, "params": params or {}}
                await ws.send(json.dumps(req))
                while True:
                    res = json.loads(await ws.recv())
                    if res.get("id") == req["id"]:
                        return res.get("result", {})

            await send("Page.enable")
            await send("Runtime.enable")

            # Navigate to the app and wait until page load event fires
            await send("Page.navigate", {"url": "http://127.0.0.1:8765/"})
            while True:
                ev = json.loads(await ws.recv())
                if ev.get("method") == "Page.loadEventFired":
                    break

            await asyncio.sleep(0.5)

            # Test 1: Check Mock SpeechRecognition behavior and button visibility
            eval_res = await send("Runtime.evaluate", {
                "expression": """
                (() => {
                    // Inject Mock SpeechRecognition
                    class MockSpeechRecognition {
                        constructor() {
                            this.lang = '';
                            this.continuous = false;
                            this.interimResults = false;
                            MockSpeechRecognition.instance = this;
                        }
                        start() {
                            this._started = true;
                            if (this.onstart) this.onstart();
                        }
                        stop() {
                            this._started = false;
                            if (this.onend) this.onend();
                        }
                    }
                    window.SpeechRecognition = MockSpeechRecognition;
                    window.webkitSpeechRecognition = MockSpeechRecognition;

                    // Switch to tutela
                    state.tipo = 'tutela';
                    renderFormulario();

                    const btnHechos = document.getElementById('btnMic_hechos');
                    const btnPret = document.getElementById('btnMic_pretensiones');
                    const btnAccionante = document.getElementById('btnMic_accionante');

                    return {
                        soportaVoz: soportaVoz(),
                        hasBtnHechos: !!btnHechos,
                        btnHechosVisible: btnHechos && !btnHechos.hidden && getComputedStyle(btnHechos).display !== 'none',
                        hasBtnPret: !!btnPret,
                        btnPretVisible: btnPret && !btnPret.hidden && getComputedStyle(btnPret).display !== 'none',
                        hasBtnAccionante: !!btnAccionante
                    };
                })()
                """,
                "returnByValue": True
            })
            print("Full eval_res:", eval_res)
            val1 = eval_res.get("result", {}).get("value", {})
            print("Test 1 Result (Support & Visibility):", val1)
            assert val1["soportaVoz"] is True, "soportaVoz should be true"
            assert val1["hasBtnHechos"] is True, "btnMic_hechos should exist"
            assert val1["btnHechosVisible"] is True, "btnMic_hechos should be visible"
            assert val1["hasBtnPret"] is True, "btnMic_pretensiones should exist"
            assert val1["btnPretVisible"] is True, "btnMic_pretensiones should be visible"
            assert val1["hasBtnAccionante"] is False, "accuser field should NOT have microphone button"

            # Test 2: Click to record, check es-CO lang and .grabando class
            eval_res2 = await send("Runtime.evaluate", {
                "expression": """
                (() => {
                    const btnHechos = document.getElementById('btnMic_hechos');
                    const inpHechos = document.getElementById('f_hechos');
                    inpHechos.value = '';

                    // Click to start recording
                    btnHechos.click();

                    const rec = window.SpeechRecognition.instance;
                    const isRecording = btnHechos.classList.contains('grabando');
                    const lang = rec ? rec.lang : null;

                    return {
                        isRecording,
                        lang,
                        buttonText: btnHechos.innerText.trim()
                    };
                })()
                """,
                "returnByValue": True
            })
            val2 = eval_res2.get("result", {}).get("value", {})
            print("Test 2 Result (Start recording):", val2)
            assert val2["isRecording"] is True, "Button should have .grabando class"
            assert val2["lang"] == "es-CO", f"SpeechRecognition.lang must be 'es-CO', got {val2['lang']}"

            # Test 3: Simulate speech input appending to empty field
            eval_res3 = await send("Runtime.evaluate", {
                "expression": """
                (() => {
                    const rec = window.SpeechRecognition.instance;
                    const inpHechos = document.getElementById('f_hechos');

                    // Helper to build speech event
                    const makeEvent = (text) => {
                        const item = [{ transcript: text }];
                        item.isFinal = true;
                        return { resultIndex: 0, results: [item] };
                    };

                    rec.onresult(makeEvent('el accionante requiere medicamento no pos'));
                    const valPaso1 = inpHechos.value;

                    // Simulate second speech result (should append at end)
                    rec.onresult(makeEvent('la eps negó la entrega inmediata.'));
                    const valPaso2 = inpHechos.value;

                    // Simulate third speech result after a period (should start on newline capitalized)
                    rec.onresult(makeEvent('se configuró vulneración al derecho fundamental a la salud.'));
                    const valPaso3 = inpHechos.value;

                    // Click to stop
                    const btnHechos = document.getElementById('btnMic_hechos');
                    btnHechos.click();
                    const isRecordingAfterStop = btnHechos.classList.contains('grabando');

                    return {
                        valPaso1,
                        valPaso2,
                        valPaso3,
                        isRecordingAfterStop,
                        stateDatosHechos: state.datos.hechos
                    };
                })()
                """,
                "returnByValue": True
            })
            val3 = eval_res3.get("result", {}).get("value", {})
            print("Test 3 Result (Speech transcription appending):", val3)
            assert val3["valPaso1"] == "El accionante requiere medicamento no pos", "Should capitalize first letter on empty field"
            assert "la eps negó la entrega inmediata." in val3["valPaso2"], "Should append second phrase with space"
            assert "\nSe configuró vulneración" in val3["valPaso3"], "Should append after period on a new line with capital letter"
            assert val3["isRecordingAfterStop"] is False, "Should stop recording on second click"
            assert val3["stateDatosHechos"] == val3["valPaso3"], "state.datos.hechos must update synchronously"

            # Test 4: Contestación assistant fact cards and consolidated facts
            eval_res4 = await send("Runtime.evaluate", {
                "expression": """
                (() => {
                    state.tipo = 'contestacion';
                    state.hechosContestacion = [
                        { numero: 1, texto: 'El contrato inició en 2020.', pronunciamiento: 'No es cierto', razon: '' }
                    ];
                    renderFormulario();

                    const btnMicRazon1 = document.getElementById('btnMic_razon_1');
                    const btnMicConsolidado = document.getElementById('btnMic_respuesta_hechos');

                    const hasBtnRazon1 = !!btnMicRazon1 && !btnMicRazon1.hidden;
                    const hasBtnConsolidado = !!btnMicConsolidado && !btnMicConsolidado.hidden;

                    // Dictate into razon 1
                    btnMicRazon1.click();
                    const rec = window.SpeechRecognition.instance;
                    const item = [{ transcript: 'el contrato inició el 15 de enero de 2021' }];
                    item.isFinal = true;
                    rec.onresult({
                        resultIndex: 0,
                        results: [item]
                    });
                    btnMicRazon1.click();

                    const inpRazon1 = document.querySelector('.asistente-hecho-razon');

                    return {
                        hasBtnRazon1,
                        hasBtnConsolidado,
                        razonVal: inpRazon1 ? inpRazon1.value : null,
                        hechoRazonState: state.hechosContestacion[0].razon
                    };
                })()
                """,
                "returnByValue": True
            })
            val4 = eval_res4.get("result", {}).get("value", {})
            print("Test 4 Result (Contestación facts assistant):", val4)
            assert val4["hasBtnRazon1"] is True, "btnMic_razon_1 must exist in contestación fact card"
            assert val4["hasBtnConsolidado"] is True, "btnMic_respuesta_hechos must exist for consolidated facts"
            assert "El contrato inició el 15 de enero de 2021" in val4["razonVal"], "Dictation into fact reason must succeed"
            assert val4["hechoRazonState"] == val4["razonVal"], "State must reflect dictated reason"

            # Test 5: Verify button is HIDDEN when browser does NOT support SpeechRecognition
            eval_res5 = await send("Runtime.evaluate", {
                "expression": """
                (() => {
                    // Remove SpeechRecognition support
                    delete window.SpeechRecognition;
                    delete window.webkitSpeechRecognition;

                    state.tipo = 'tutela';
                    renderFormulario();

                    const btnHechos = document.getElementById('btnMic_hechos');
                    const btnPret = document.getElementById('btnMic_pretensiones');

                    const isHechosHidden = !btnHechos || btnHechos.hidden || getComputedStyle(btnHechos).display === 'none';
                    const isPretHidden = !btnPret || btnPret.hidden || getComputedStyle(btnPret).display === 'none';

                    return {
                        soportaVoz: soportaVoz(),
                        isHechosHidden,
                        isPretHidden
                    };
                })()
                """,
                "returnByValue": True
            })
            val5 = eval_res5.get("result", {}).get("value", {})
            print("Test 5 Result (Unsupported browser - button hidden):", val5)
            assert val5["soportaVoz"] is False, "soportaVoz should be false when API not present"
            assert val5["isHechosHidden"] is True, "Microphone button must be hidden when unsupported"
            assert val5["isPretHidden"] is True, "Microphone button for pretensiones must be hidden when unsupported"

        print("\n🎉 ALL 5 BROWSER TESTS PASSED PERFECTLY!")
    finally:
        if chrome_proc:
            chrome_proc.terminate()
        if app_proc:
            app_proc.terminate()

import os
import sys
import pytest

@pytest.mark.skipif(
    os.environ.get("MEMORIALISTA_RUN_LEGACY_BROWSER_TEST") != "1" or sys.platform != "darwin",
    reason="Prueba manual heredada de dictado: requiere macOS, Chrome y habilitación explícita; la nueva frontera de login se verifica por separado.",
)
@pytest.mark.asyncio
async def test_dictado_por_voz_en_navegador():
    chrome_bin = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
    if not os.path.exists(chrome_bin):
        pytest.skip("Google Chrome no está instalado en /Applications")
    await run_browser_test()

if __name__ == '__main__':
    asyncio.run(run_browser_test())
