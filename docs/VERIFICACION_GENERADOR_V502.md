# Verificación local de la actualización visual 5.0.2

Fecha: 23 de octubre de 2026.

## Alcance

- Conservación byte a byte del **script principal de negocio del generador**, comparado con el ZIP de la entrega anterior v5.0.1. No se modificaron el motor de prompts, los 26 tipos profesionales ni sus exportaciones.
- Conservación de los IDs de botones originales y las cinco vistas (`redactar`, `membrete`, `historial`, `plazos`, `calculos`).
- Comprobación en FastAPI de que el nuevo CSS se rechaza sin sesión con HTTP 401, sin montar directorios privados como estáticos.
- Tres comprobaciones de navegación visual en Chromium con dimensiones **1440, 390 y 320 px**; ausencia de desbordamiento horizontal general, botón de menú móvil, selección de sección y cierre del menú.
- Capturas de la apariencia nueva con **datos ficticios** en `docs/capturas/`. Las capturas no validan la autenticación real ni una generación de IA.

## Pruebas ejecutadas

- Pruebas específicas del estilo y navegación: **6 aprobadas** (3 Python estructurales y 3 de Chromium).
- Regresión focal de generador, prompt, plazos, revisión, límites, datos y permisos: **127 aprobadas** (incluye las pruebas de diseño).
- `npm run test:unit`: superado para motor ciudadano, características, respaldos, autenticación del cliente y PWA.
- La suite Python total en esta sesión **no se completó** antes del límite externo de ejecución; se detuvo cerca de la verificación de citas. No se declara el total histórico como nueva prueba completada.

## Pendiente de la instalación real

1. Comparar cambios locales de la instalación Antigravity y preservar sus personalizaciones.
2. Confirmar el nuevo CSS con sesión real en `/generador` y probar todas las pestañas y accesos a los cinco módulos privados.
3. Generar un escrito con Gemini, ajustar, comparar y exportar Word/PDF en tu servidor.
4. Verificar que la hoja exportada conserva membrete, tipografía y márgenes configurados.
5. Comprobar en dispositivos y navegadores de destino, incluidos móviles, el comportamiento con teclado y tecnologías de asistencia.
6. Revisar conexión de Supabase, almacenamiento DMS, OCR, firma y fuentes externas antes de publicar.

Esta revisión es visual: sus capturas y pruebas de maqueta no equivalen a una aceptación de producción ni a garantía de todos los servicios externos.
