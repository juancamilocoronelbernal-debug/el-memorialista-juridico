# ⚖️ PAQUETE DE CONTEXTO Y ESPECIFICACIÓN TÉCNICA: EL MEMORIALISTA
> **Instrucciones para Claude:** Este documento contiene la arquitectura completa, contratos de API, flujo de datos y el estado actual de **El Memorialista** para diseñar e implementar mejoras de interfaz, prompts jurídicos y nuevas funcionalidades.

---

## 1. 📌 Visión General del Proyecto
**El Memorialista** es una aplicación web multi-usuario diseñada para litigantes y abogados en **Colombia**. Permite redactar de forma autónoma y en tiempo real (con efecto mecanografía / streaming) memoriales, demandas, acciones de tutela, incidentes de desacato y derechos de petición, aplicando la normativa procesal colombiana vigente (Ley 2213 de 2022, CGP, CPACA, Ley 2452 de 2025, Código Civil).

- **Repositorio GitHub:** [juancamilocoronelbernal-debug/el-memorialista-juridico](https://github.com/juancamilocoronelbernal-debug/el-memorialista-juridico)
- **Despliegue en Vivo (Producción):** [https://el-memorialista-juridico.onrender.com](https://el-memorialista-juridico.onrender.com)

---

## 2. 🏗️ Arquitectura Técnica

### A. Backend (FastAPI - Python 3.10)
- **`app/main.py`**:
  - Servidor FastAPI con CORS habilitado.
  - Servidor estático montado en `/static` que entrega `app/static/index.html` en la raíz `/`.
  - Worker de actividad en segundo plano (`keep_alive_worker`) que ejecuta un pulso HTTP cada 9 minutos a `/api/health` para evitar que Render hiberne el contenedor.
- **`app/services/gemini_service.py`**:
  - Motor de IA dual: Conexión primaria a **Google Gemini** (`gemini-2.5-flash`, `gemini-1.5-flash`, `gemini-2.0-flash`) mediante streaming REST (`streamGenerateContent?alt=sse`).
  - Respaldo automático a **Groq (OpenAI GPT-OSS-120B)** con razonamiento profundo si Gemini no está disponible o se congestiona.
- **`app/routers/documents.py`**:
  - Endpoints de generación y análisis de estilo.

### B. Frontend (`app/static/index.html`)
- Archivo SPA (Single Page Application) sin frameworks pesados (Vanilla JS, CSS modular moderno).
- Diseño temático: *"La Mesa del Memorialista"* (expediente a la izquierda, hoja membreteada a la derecha).
- Motor de renderizado de hoja que convierte el texto enriquecido de marcas (`##`, `###`, `|`, `>`, `-`, `[[FIRMA]]`) en visualización legal con tipografía notarial, espaciado e interlineado formal.
- **Persistencia Multi-Usuario:** Perfil del abogado, logos, firmas escaneadas, plantillas de Word e historial almacenados de forma aislada en el `localStorage` de cada usuario.
- **Exportadores:** Generación de documentos nativos en Word (`.docx` con `JSZip`) y PDF (`pdfmake`).

---

## 3. 🔌 Contratos de API (Endpoints Disponibles)

### 1. Generación de Escrito en Streaming
- **Ruta:** `POST /api/redactar`
- **Headers:** `Content-Type: application/json`
- **Request Body:**
  ```json
  {
    "prompt": "String con el prompt completo estructurado, contexto normativo y hechos",
    "modo": "nuevo | regenerar | ajuste",
    "instruccion": "Opcional: instrucción de cambio solicitada por el usuario (modo ajuste)",
    "texto_previo": "Opcional: texto de la versión anterior para aplicar ajustes",
    "calidad": "default | complex"
  }
  ```
- **Response:** `StreamingResponse` con `Content-Type: text/plain; charset=utf-8`. Los fragmentos de texto se transmiten progresivamente.

### 2. Análisis de Estilo Forense
- **Ruta:** `POST /api/analizar-estilo`
- **Headers:** `Content-Type: application/json`
- **Request Body:**
  ```json
  {
    "muestra": "Texto de un memorial previo del abogado (mínimo 100 caracteres)"
  }
  ```
- **Response:**
  ```json
  {
    "ok": true,
    "ficha": "Encabezado: ...\nPresentación: ...\nTratamiento: ...\nFórmulas: ...",
    "raw": { ... }
  }
  ```

### 3. Health Check
- **Ruta:** `GET /api/health`
- **Response:**
  ```json
  {
    "status": "online",
    "app": "El Memorialista",
    "gemini_configured": true,
    "model": "gemini-2.5-flash"
  }
  ```

---

## 4. 📑 Catálogo de Documentos Actual (25 Tipos)
1. Acción de tutela
2. Impugnación de fallo de tutela
3. Incidente de desacato
4. Acción de cumplimiento
5. Acción popular
6. Derecho de petición
7. Recursos en vía administrativa (reposición y apelación)
8. Revocatoria directa
9. Queja disciplinaria
10. Demanda declarativa (verbal y verbal sumario)
11. Demanda ejecutiva singular
12. Contestación de demanda y excepciones
13. Solicitud de conciliación extrajudicial
14. Divorcio / Cesación de efectos civiles
15. Fijación de cuota alimentaria
16. Demanda ordinaria laboral
17. Nulidad y restablecimiento del derecho
18. Reparación directa
19. Denuncia penal o querella
20. Recurso de reposición o apelación de autos
21. Apelación de sentencias
22. Alegatos de conclusión
23. Poder especial
24. Memorial o solicitud al despacho
25. Otro escrito personalizado

---

## 5. 🎯 Áreas Clave para que Claude Proponga Mejoras

1. **UX / Interfaz Visual:**
   - Mejoras en la barra de edición y control del texto en la hoja.
   - Modo oscuro afinado o selección de paletas visuales para bufetes de abogados.
   - Mejor experiencia táctil y responsive en dispositivos móviles / iPads.
2. **Potencia Jurídica y Prompts:**
   - Generación de fundamentos probatorios específicos según el tipo de proceso.
   - Banco de jurisprudencia unificada de altas cortes (Corte Constitucional, Consejo de Estado, Corte Suprema).
   - Detección automática de términos de caducidad o prescripción en las fechas ingresadas.
3. **Productividad:**
   - Biblioteca de cláusulas frecuentes reutilizables.
   - Búsqueda y filtrado avanzado en el historial de escritos redactados.
   - Exportación mejorada a formatos `.docx` respetando membretes complejos con tablas.
