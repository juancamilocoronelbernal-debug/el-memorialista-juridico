# Incorporar esta entrega al proyecto existente

Integra este código completo de **El Memorialista** en mi proyecto actual y comprueba que funcione con mi configuración. Conserva una copia o commit de la versión existente y mis datos antes de actualizar. Lee primero `README.md`, `docs/INTEGRACION_COMPLETA.md`, `docs/VERIFICACION_INTEGRADA.md` y `docs/CAMBIOS_GENERADOR_ORIGINAL.md`.

El código ya incluye la integración. Revisa y adapta las diferencias necesarias a mi instalación; no reconstruyas el generador ni sustituyas su catálogo, sus prompts o sus motores jurídicos por una nueva implementación. Conserva mi `.env`, las variables del alojamiento, mis credenciales, el proyecto Supabase y sus datos. Usa `.env.example` solo para comparar nombres y añadir lo que falte. No muestres valores secretos ni los añadas al repositorio o al frontend.

El flujo requerido es: orientación ciudadana pública antes del acceso; tras una sesión válida, entrada a `/app` y navegación exclusivamente del despacho. Las rutas privadas y APIs deben exigir autorización del servidor. Mantén la identidad de El Memorialista y las licencias de sus dependencias.

Conserva todas las funciones integradas: orientador, DOCX OOXML, PDF con fuentes locales, seguimiento, prellenado, accesibilidad, búsqueda tolerante a erratas, copias ciudadanas compatibles, aislamiento de datos privados por cuenta, controles de importación, permisos y eliminación. No mezcles automáticamente borradores públicos con una cuenta privada.

Si Supabase ya tiene el esquema original, aplica la migración de seguridad `supabase/migrations/20261022010000_separacion_publica_privada_rls.sql` como propietario; no vuelvas a crear las tablas. Para una instancia nueva usa `supabase/schema.sql`. Si mi esquema real tiene cambios adicionales, compáralos y adapta la migración sin perderlos. Comprueba las políticas con `supabase/tests/aislamiento_cuentas.sql` en una instancia de prueba.

Configura el dominio, HTTPS, retornos de Supabase Auth, correo, bucket privado y modelos disponibles usando los servicios existentes. Mantén `--no-proxy-headers`; configura cabeceras de IP únicamente con la cadena de proxies real. La clave administrativa de Supabase y las de IA pertenecen al servidor.

Ejecuta las suites indicadas en la guía y el recorrido Playwright completo, incluidas PWA y copia autónoma sin conexión. Si cambias recursos públicos, regenera catálogo, HTML autónomo y PWA. Haz una prueba real con dos cuentas para comprobar aislamiento, respaldo/recuperación, sesión y permisos; verifica también acceso y recuperación por correo, una generación con IA y las exportaciones profesionales. Usa datos ficticios para estas comprobaciones.

Entrega un informe de los cambios específicos de mi instalación y los resultados. Distingue pruebas con proveedores reales de respuestas simuladas; no declares funcional un servicio únicamente porque `/api/health` responda. Si falta una configuración o acceso indispensable, identifica exactamente cuál sin reemplazarlo por botones simulados ni sesiones de prueba.
