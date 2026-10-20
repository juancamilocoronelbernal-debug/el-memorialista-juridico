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
