# Investigación externa — módulo incremental de Jurisprudencia

**Compatibilidad:** parte privada de El Memorialista, API FastAPI existente, búsqueda de Google mediante Gemini, Supabase y DMS ya configurados. No reemplaza el generador ni la biblioteca automática del Agente.

## Qué se implementa

La sección **Jurisprudencia** ofrece tres pestañas independientes:

1. **Investigar con IA:** texto del problema jurídico y territorio opcional. La petición se envía al Gemini configurado en el servidor con la herramienta `googleSearch`. Se presentan el análisis, las fuentes que llegaron en los metadatos del proveedor, su procedencia y las advertencias de cobertura. No necesita documentos previamente importados.
2. **Mi biblioteca jurídica:** mantiene exactamente la búsqueda textual/semántica, las fuentes importadas, los filtros, el índice y los controles anteriores.
3. **Chat jurídico:** conserva el chat y la investigación conversacional existentes, incluidas las opciones de biblioteca; no se modifica la lógica de selección automática de fuentes del Agente.

Una fuente descubierta **no se considera validada**. El botón **Comprobar el original** sólo se habilita para URLs HTTPS de dominios que el servidor admita; el servidor aplica su protección SSRF antes de leerla. Si el documento es recuperable, se muestra una vista de texto y el botón **Incorporar a mi biblioteca**. Guardar es siempre una acción separada del usuario; se conserva el original y se indexa mediante la lógica existente. Las URL externas no admitidas pueden abrirse para revisión, pero no se importan mediante esta ruta. La incorporación puede requerir una URL directa distinta de un enlace redirigido por el motor de búsqueda.

También se puede guardar el análisis como **borrador de DMS pendiente de revisar**, sin confundirlo con una sentencia verificada.

## Archivos del cambio

- `app/services/despacho_legal_research.py` — orquestación de investigación web, clasificación de fuentes y comprobación del original.
- `app/routers/despacho_knowledge.py` — rutas privadas `POST /api/despacho/knowledge/research` y `POST /api/despacho/knowledge/verify`.
- `app/private/despacho.js` y `app/private/despacho.css` — pestañas y acciones de investigación.
- `tests/test_legal_research_external.py` — pruebas de fuentes, autenticación, ausencia de escrituras automáticas, errores y tiempo máximo.
- `tests/test_despacho_browser.mjs` y `tests/test_despacho_v5_browser.mjs` — regresiones de las nuevas pestañas y del flujo bajo respuestas HTTP controladas.

**No requiere nuevas migraciones** ni una clave de IA distinta si ya funciona el modo Investigar del Agente. No cambia `GEMINI_MODEL`, `render.yaml`, los workers, la recuperación automática ni las advertencias de la biblioteca.

## Protección y verificación

- Todo endpoint comprueba una sesión válida y aplica el limitador existente.
- Se envía a Gemini **sólo el texto que el usuario escribe en la investigación y el territorio**; esta ruta no adjunta documentos privados ni consultas al DMS.
- Sólo se aceptan enlaces obtenidos de los metadatos de grounding del proveedor, no URLs inventadas dentro de la respuesta libre.
- Las fuentes pueden estar desactualizadas o no ser pertinentes: **ningún dominio admitido constituye por sí mismo prueba de autenticidad o vigencia**. La lectura del original tampoco certifica validez jurídica. No se promete cobertura exhaustiva de jurisprudencia colombiana.
- Si el proveedor no devuelve enlaces utilizables, se muestra explícitamente que el análisis no acredita haber encontrado fuentes.
- Las importaciones usan la protección existente por dominio y dirección pública, redirecciones controladas, límite de descarga, propiedad de cuenta y políticas RLS.
- Las búsquedas con Google pueden consumir cuota; el servidor limita solicitudes y tiempos.

## Pruebas recomendadas en Antigravity/Render

1. Crear una rama o copia del proyecto **más reciente** (el que contiene la activación reciente de embeddings); aplicar el parche mediante fusión. No reemplazar archivos completos de la versión activa a ciegas.
2. Ejecutar `python -m pytest -q tests/test_legal_research_external.py` y las pruebas existentes (`python -m pytest -q`).
3. Abrir `/app`, ingresar con una cuenta de prueba y entrar en Jurisprudencia → Investigar con IA.
4. Buscar: `Normativa y jurisprudencia relacionada con competencias de mantenimiento de la red vial municipal en Bucaramanga` con territorio `Bucaramanga, Santander`.
5. Comprobar que hay resultados con enlaces del proveedor, sin prometer que todas son oficiales; observar que no se crean documentos automáticamente.
6. Elegir una URL HTTPS directa de un dominio admitido, usar **Comprobar el original**, revisar texto, **Incorporar a mi biblioteca** y confirmar que queda guardada e indexada en **Mi biblioteca jurídica**.
7. Comprobar que **Chat jurídico** mantiene su forma anterior y que el Agente conserva la opción «Biblioteca: automática» sin cambios.
8. Repetir con dos cuentas; verificar que una no accede a los documentos guardados por la otra. Usar fuentes no admitidas, URLs privadas, redirecciones, enlaces rotos y errores de Gemini para revisar que no se presentan como éxitos.
9. Revisar cuota, tiempos, registros y políticas de Render/Supabase. Probar la búsqueda textual/semántica sólo con fuentes incorporadas y las migraciones que Antigravity ya aplicó.

## Alcance de la prueba local incluida

El código se ha sometido a pruebas unitarias y de regresión con respuestas simuladas. La ejecución de Gemini real, el acceso a sitios externos y la interfaz sobre la instalación de Render deben confirmarse con los servicios reales del propietario. La suite de navegador basada en Chromium necesita un entorno que permita navegación de prueba; aquí el navegador está bloqueado por la política de red del entorno, y no se considera aprobada por ese motivo.
