# Verificación de la entrega integrada

**Cierre de la revisión: 23 de octubre de 2026 (UTC).** Trabajo iniciado el 22 de octubre. Código completo comprobado localmente; no desplegado en la instalación del propietario.

## Resultado de esta versión

| Suite ejecutada | Aprobadas | Fallos | Omitidas |
| --- | ---: | ---: | ---: |
| `python -m pytest -q -p no:cacheprovider` | 285 | 0 | 1 |
| `node tests/test_asesor_engine.cjs` | 84 | 0 | 0 |
| `node tests/test_asesor_features.cjs` | 88 | 0 | 0 |
| `node tests/test_asesor_respaldo.cjs` | 21 | 0 | 0 |
| `node tests/test_auth_client.cjs` | 18 | 0 | 0 |
| `node tests/test_asesor_pwa.cjs` | 14 | 0 | 0 |
| `node tests/test_asesor_browser.mjs` | 5 | 0 | 0 |
| **Total** | **515** | **0** | **1** |

Los totales corresponden a las suites finales de esta integración; no se suman ejecuciones anteriores ni repeticiones. La prueba omitida es la comprobación manual heredada de dictado en Chrome/macOS, desactivada por defecto. Starlette emitió una advertencia de deprecación relativa a su adaptador de TestClient con httpx; no causó un fallo.

También se reconstruyeron el catálogo público, el HTML autónomo y la PWA. `node scripts/build_asesor_paginas.cjs --check` confirmó que las 66 páginas derivadas están actualizadas. Los archivos de despliegue usan `--no-proxy-headers`; el YAML se validó sin variables duplicadas. No se construyó una imagen Docker ni se publicó el proyecto.

## Cobertura funcional

### Motor y exportación ciudadana

Se conservaron los 66 casos activos, 10 tipos y 169 entradas normativas. Las pruebas generan los casos, verifican textos y estructuras e inspeccionan DOCX y PDF producidos por los exportadores reales. No equivalen a una revisión jurídica completa de todas las combinaciones de respuestas.

Las regresiones detectan títulos vacíos, pérdida de Unicode, XML sin escapar, firmas o textos extensos que se pierden al paginar y confusión entre consulta y reclamo de datos personales. Se corrigió un error del motor que consideraba un arreglo vacío como título o saludo válido y por ello omitía el texto predeterminado.

El PDF incorpora fuentes locales y mapas Unicode. Se verificaron español, latín extendido, griego, cirílico y varios signos; para escrituras o caracteres no representables fielmente informa un error con alternativas Word o impresión. No se afirma cobertura tipográfica universal.

### Orientador, búsqueda y seguimiento

Se comprobó que los 22 nodos del orientador son alcanzables y sus 80 salidas apuntan a casos activos. La búsqueda tolera erratas y respeta los filtros. Se probaron plazos por tipo de solicitud, diferencias entre servicios domiciliarios y comunicaciones, apertura de desacato, recepción del expediente en segunda instancia y notificación para impugnar.

La notificación al usuario y el inicio de cumplimiento de la orden se registran por separado. El módulo no presume un plazo de 48 horas. Las pruebas diferencian horas continuas, días calendario enteros y días hábiles; la exportación ICS mantiene el instante correspondiente en distintas zonas horarias. El seguimiento muestra referencias y alternativas, sin declarar automáticamente una decisión favorable.

El prellenado reutiliza datos pertinentes y conserva el enlace al documento de origen; no copia ciegamente anexos o pretensiones de otro trámite. Las rutas de los siguientes escritos y los valores de sus campos se comprobaron contra el catálogo real.

### Respaldos ciudadanos

Las pruebas importan arreglos heredados de Claude y copias v1/v2, conservando `datos`, `seguimiento` y `origen`. Incluyen nuevas fechas y horas, además de copias antiguas que no las tienen. En estas últimas no se inventa un inicio de cumplimiento.

Se comprueban el rechazo íntegro de datos inválidos o versiones futuras; la conservación byte por byte de un historial corrupto; errores de lectura y cuota sin éxito falso; deduplicación de copias idénticas; conflictos que conservan las dos versiones; y reasignación de enlaces de padres, hijos y nietos. Una importación válida escribe una sola vez y respeta el máximo de 200 documentos y 5 MB.

### Acceso privado, servidor y permisos

Las pruebas Python y de autenticación cubren rutas protegidas, cookies, sesión, origen, separación por cuenta, recuperación de escritos y tratamiento de errores de proveedor. Incluyen configuración de proxies y CSP de las rutas públicas y del acceso. Las respuestas de Supabase y de IA se sustituyen por respuestas controladas en las pruebas: no se usaron cuentas ni claves reales.

Los nueve contratos estáticos de SQL forman parte de la suite Python. Se revisó además que la migración de seguridad existente cubre las 25 políticas originales y conserva las seis tablas y sus columnas. No se ejecutó esa migración en un Supabase real. La prueba transaccional `supabase/tests/aislamiento_cuentas.sql` queda incluida para la instalación de destino.

## Recorrido real en navegador

Se utilizó Chromium local con FastAPI, su política CSP efectiva y datos ficticios. Gemini, Groq y Supabase estuvieron sin configurar. Las cinco pruebas de navegador cubrieron:

1. Escritorio: orientador, petición a una EPS, formulario, PDF y DOCX descargados, guardado, seguimiento, archivo ICS, tutela prellenada, seguimiento judicial y exportación/borrado/importación de la copia. Una copia inválida no alteró el historial. Al recargar, los datos, seguimiento y origen restaurados coincidían con los exportados.
2. Pantalla de 350 px: menú, orientador, formulario, vista previa, letra al 140 %, alto contraste, modo oscuro y persistencia.
3. Pantalla de 390 px: el mismo recorrido de presentación y accesibilidad.
4. PWA con la red cortada después de preparar su caché: catálogo de 66 casos, orientación, formulario y descargas DOCX/PDF; la caché excluye recursos privados.
5. HTML autónomo abierto como `file://`, sin red: orientación, formulario, generación y descargas; no muestra controles exclusivos de la web conectada.

En las comprobaciones instrumentadas no aparecieron errores JavaScript, violaciones CSP ni solicitudes de las páginas a dominios externos. Se corrigieron y verificaron el desbordamiento horizontal del orientador y del título a 350 px/140 %, y un callback de progreso que intentaba actualizar un formulario ya retirado de la página.

Los tres modos produjeron archivos reales. `pdftotext` extrajo del ejemplo final 5 páginas y 9.156 caracteres, conservando «MARÍA PRUEBA ÑANDÚ» y «EPS DE PRUEBA», sin caracteres de sustitución. Los DOCX eran paquetes ZIP válidos y contenían el título «DERECHO DE PETICIÓN» y el texto esperado. Las páginas primera y última del PDF se renderizaron a 144 dpi y se inspeccionaron: título, párrafos, firma y contactos completos, sin cortes ni solapamientos y separados del pie. Las capturas revisadas corresponden a la aplicación ejecutada y no a imágenes generadas.

Esta revisión utiliza tamaños móviles simulados en Chromium. No es una certificación WCAG ni una comprobación en dispositivos físicos, Safari o Firefox. Voz local, dictado, portapapeles, compartir e instalación dependen de las capacidades y permisos del dispositivo.

## Comprobaciones pendientes en la instalación de destino

- Sesiones y correos reales de Supabase: contraseña, enlace de acceso, recuperación y cierre, con el dominio y las URLs de retorno definitivos.
- Migración y RLS en PostgreSQL, pruebas con dos cuentas y colaboración autorizada, Storage privado y eliminación administrativa.
- Generación con las claves y modelos reales de Gemini/Groq, con revisión de contenido, cuotas y errores del proveedor.
- Construcción Docker o despliegue en el alojamiento elegido, HTTPS, cadena real de proxies e instalación PWA en los navegadores de uso.

Los pasos están en [INTEGRACION_COMPLETA.md](INTEGRACION_COMPLETA.md). El registro de lo que se modificó en la entrega anterior frente al generador original está en [CAMBIOS_GENERADOR_ORIGINAL.md](CAMBIOS_GENERADOR_ORIGINAL.md), acompañado de su inventario JSON. Ninguna de estas comprobaciones locales sustituye la configuración ni una prueba real de los proveedores del propietario.
