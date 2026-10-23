# El Memorialista 5.0.2 — rediseño del generador

**23 de octubre de 2026.** Actualización enfocada en la apariencia, manteniendo el núcleo jurídico y sus funciones.

## Qué cambió

- Mismo menú lateral, marca tipográfica y colores del despacho privado, con marfil, verde y tipografía editorial.
- Navegación lateral a **Redactar escrito**, **Membrete y estilo**, **Historial**, **Términos y plazos** y **Cálculos jurídicos**; se reutilizan los botones de pestaña originales mediante un evento `click`.
- Accesos desde el generador a Agente, Jurisprudencia, Monitor, DMS, Firma electrónica, Asuntos y Editor y versiones, mediante las rutas privadas existentes.
- Barra superior con breadcrumb, enlace de retorno al Agente y cuenta.
- En pantallas pequeñas se muestra menú lateral desplegable, cortina de cierre accesible y tabs originales desplazables horizontalmente.
- Se actualiza el título de la pestaña según la sección elegida.
- El nuevo CSS se carga solo al abrir `/generador` con sesión válida y se expone únicamente por `/app/assets/generador-theme.css` tras comprobar la misma sesión.

## Qué NO cambió

- Motor y prompts de IA, 26 tipos de escrito, catálogo, requisitos, mecanismos de cálculo, plazos y auditoría.
- IDs de controles originales, manejo del estado, formularios, historial, recuperación, exportaciones y guardado en DMS.
- Configuración de tipografía, márgenes y membrete del contenido exportado: el diseño de la **aplicación** no reemplaza el diseño **del escrito**.
- Cuenta Supabase y los permisos de rutas existentes.

## Archivos

- `app/private/generador.html`: añade una navegación compatible y un script breve para seleccionar tabs y controlar el panel móvil.
- `app/private/generador-theme.css`: nueva capa de estilos aislada de los motores.
- `app/main.py`: autoriza servir solo este nuevo CSS en el endpoint privado de activos.
- `tests/test_generador_visual_v502.py`: controles visuales, conservación de IDs y comprobación de autorización.
- `docs/GUIA_USO_COMPLETA.md`: manual integral de usuario.
- `README.md`, `app/config.py`, `PROMPT_PARA_ANTIGRAVITY.md`: notas y número de versión.

## Comprobaciones de aceptación

1. Verificar `/generador` y el CSS con sesión real, y comprobar que ambos rechazan accesos sin sesión.
2. Activar cada tab desde barra y menú y comprobar que se muestra el panel esperado.
3. Confirmar que el generador conserva sus 26 tipos, los formularios condicionados y los estados de los botones de exportación.
4. Probar móviles 390 px y 320 px, menú, formularios, vista previa y descargas sin scroll horizontal general.
5. Comprobar un escrito real con el membrete configurado y verificar Word/PDF contra la versión anterior.
6. Revisar la impresión y versión móvil con el cliente final. Los screenshots entregados contienen solo información de ejemplo.

La revisión de código y pruebas locales no certifica el estado de tu instalación de Antigravity ni el comportamiento con sus servicios externos reales.
