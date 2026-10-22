# ⚖️ El Memorialista - Generador Jurídico con Inteligencia Artificial (Google Gemini)
### Aplicación Web Multi-Usuario para Abogados y Litigantes en Colombia 🇨🇴

Inspirado en la arquitectura del **Agente COD** (`dropshipping-cod-agent`), este sistema convierte el generador de documentos en una **aplicación web moderna, autónoma y multi-usuario** con backend en **FastAPI (Python)** y frontend reactivo en tiempo real mediante **Server-Sent Events (Streaming)** conectado a **Google Gemini**.

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/juancamilocoronelbernal-debug/el-memorialista-juridico)


---

## 🌟 Características Principales

1. **Redacción en Tiempo Real con Google Gemini:**
   - Redacta demandas, acciones de tutela, incidentes de desacato, derechos de petición, poderes y memoriales.
   - Efecto mecanografía en vivo (*streaming*) mientras Gemini genera el documento.
   - Aplica normas procesales colombianas vigentes (Ley 2213 de 2022, Ley 2452 de 2025, CGP, CPACA, Código Civil).

2. **Multi-Usuario e Independiente:**
   - Múltiples abogados o personas pueden acceder al mismo enlace web simultáneamente.
   - Cada usuario mantiene su membrete, sus datos profesionales, su firma y su historial guardados de forma privada y segura en su propio navegador.

3. **Análisis de Estilo Forense:**
   - Permite subir un escrito propio para que Gemini extraiga automáticamente la **Ficha de Estilo** (fórmulas, conectores, tratamiento al despacho, nivel de formalidad) y la aplique en futuros documentos.

4. **Exportación Flexible:**
   - Descarga de documentos con un solo clic.

5. **Verificación Oficial de Citas Jurídicas:**
   - Extrae providencias de la Corte Constitucional (T, C, SU, Autos), Leyes, Decretos y Códigos (CGP, CPACA, CC, CST, Ley 906).
   - Consulta URLs oficiales en la Relatoría de la Corte Constitucional y la Secretaría del Senado de Colombia con caché local SQLite.

6. **Auditoría de Fidelidad de Datos (Sin IA):**
   - Extrae y normaliza cédulas, NITs con dígito de verificación DIAN oficial, radicados de 23 dígitos (5-2-2-3-4-5-2), fechas, valores en pesos y matrículas inmobiliarias.
   - Detecta invenciones (datos en el escrito ausentes en el formulario) y omisiones.
   - Valida la concordancia estricta entre cifras numéricas y valores en letras ("M/CTE.").

7. **Checklist Normativo Procesal:**
   - Requisitos procesales y legales obligatorios para cada uno de los 25 tipos de documentos del catálogo.

---

## 🛡️ Evaluación y Control de Calidad Pre-Despliegue (`scripts/evaluar.py`)

> [!IMPORTANT]
> **POLÍTICA OBLIGATORIA DE DESPLIEGUE:**
> Correr la evaluación antes de cambiar de modelo, de prompt o de guía, y **no desplegar si empeora alguna métrica** (citas inexistentes, datos inventados, requisitos faltantes o tasa de semáforos verdes).

El repositorio incluye un marco integral de benchmarking con **75 casos de prueba oficiales** (3 por cada uno de los 25 tipos de documento) ubicados en `tests/casos/*.json`. Cada caso define datos reales de litigio colombiano y expectativas estrictas:
- **Secciones obligatorias** procesales requeridas en el escrito.
- **Entidades que deben aparecer** (partes, identificaciones, cuantías, hechos clave).
- **Entidades que NO deben aparecer** (detector de alucinaciones del modelo).
- **Rangos de longitud** mínima y máxima de caracteres.

### Cómo ejecutar la evaluación:

1. **Evaluación completa de los 75 casos oficiales:**
   ```bash
   python scripts/evaluar.py
   ```

2. **Evaluar un tipo de documento específico (ej. tutelas o demandas verbales):**
   ```bash
   python scripts/evaluar.py --tipo tutela
   python scripts/evaluar.py --tipo demanda_verbal
   ```

3. **Evaluar contra un servidor en ejecución:**
   ```bash
   python scripts/evaluar.py --servidor http://127.0.0.1:8000
   ```

4. **Modo simulado / CI (sin consumo de cuota de API de IA):**
   ```bash
   python scripts/evaluar.py --mock
   ```

5. **Modo estricto (falla el build si hay advertencias amarillas o rojas):**
   ```bash
   python scripts/evaluar.py --estricto
   ```

### Métricas evaluadas y Reporte HTML (`reporte_evaluacion.html`):
El script genera automáticamente un reporte visual e interactivo con:
- **Semáforo por caso:**
  - 🟢 **Verde (Aprobado):** Cumple al 100% las expectativas, sin alucinaciones, sin citas inexistentes ni requisitos omitidos.
  - 🟡 **Amarillo (Advertencia):** Citas sin verificar o advertencias no críticas.
  - 🔴 **Rojo (Falla crítica):** Citas inexistentes, alucinaciones de entidades prohibidas, omisión de secciones obligatorias o incumplimiento de requisitos normativos críticos.
- **Totales agregados:**
  - **Citas inexistentes:** Total de citas no halladas en fuentes oficiales.
  - **Datos inventados:** Entidades generadas en el texto ausentes en los datos del caso.
  - **Requisitos faltantes:** Normas y cláusulas procesales insatisfechas.
  - **Tiempos y Tokens:** Consumo exacto de tokens (in/out) y segundos de respuesta.

---

---

## 📂 Estructura del Proyecto

```
el-memorialista-app/
├── app/
│   ├── __init__.py
│   ├── config.py                 # Configuración y variables de entorno (.env)
│   ├── main.py                   # Servidor FastAPI y montaje de frontend
│   ├── services/
│   │   └── gemini_service.py     # Motor IA con Streaming SSE y fallback de modelos
│   ├── routers/
│   │   └── documents.py          # Endpoints /api/redactar y /api/analizar-estilo
│   └── static/
│       └── index.html            # Interfaz visual "La Mesa del Memorialista"
├── .env.example                  # Plantilla de configuración
├── .env                          # Variables de entorno locales
├── requirements.txt              # Dependencias de Python
├── render.yaml                   # Configuración para despliegue en Render.com
└── README.md                     # Documentación completa
```

---

## 🚀 Puesta en Marcha Local (3 Pasos)

### 1. Clave de Google Gemini
Obtén tu API Key gratuita en [Google AI Studio](https://aistudio.google.com/).

Abre tu archivo `.env` y pega tu clave:
```env
GEMINI_API_KEY=AIzaSy...tu_clave_aqui
GEMINI_MODEL=gemini-2.5-flash
```

### 2. Activar el entorno e instalar dependencias
```bash
cd el-memorialista-app
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Iniciar el servidor
```bash
uvicorn app.main:app --reload --port 8000
```
Abre tu navegador en: [http://localhost:8000](http://localhost:8000)

---

## ☁️ Cómo Dejarlo en Línea Gratis para Todos (Despliegue en Render)

El proyecto incluye el archivo `render.yaml` pre-configurado para despliegue automático:

1. **Sube el código a GitHub:**
   Crea un repositorio en tu GitHub (ej. `el-memorialista-app`) y sube esta carpeta.

2. **Conéctalo a Render:**
   - Entra a [dashboard.render.com](https://dashboard.render.com/).
   - Haz clic en **New +** > **Blueprint**.
   - Selecciona tu repositorio de GitHub. Render leerá automáticamente el archivo `render.yaml`.

3. **Configura tu variable secreta:**
   - En el panel de Render, agrega en **Environment Variables**:
     - `GEMINI_API_KEY` = `tu_clave_de_gemini`
   - Haz clic en **Apply**.

¡En 2 minutos tendrás una URL pública HTTPS (ejemplo: `https://el-memorialista-juridico.onrender.com`) lista para compartir con tu equipo o clientes!
