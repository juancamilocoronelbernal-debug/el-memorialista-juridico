# Verificación de la integración v3

> **Registro de una etapa anterior.** Las funciones y pruebas de la entrega integrada actual se describen en [INTEGRACION_COMPLETA.md](INTEGRACION_COMPLETA.md) y [VERIFICACION_INTEGRADA.md](VERIFICACION_INTEGRADA.md). Se conserva este informe para identificar qué existía en cada etapa.

Fecha: **22 de octubre de 2026**. Código integrado y comprobado localmente; no desplegado en un dominio de producción.

## Resultados ejecutados

| Comprobación | Resultado |
| --- | --- |
| `python -m pytest -q` | **247 aprobadas, 1 omitida, 0 fallos**. |
| `node tests/test_asesor_engine.cjs` | **84 aprobadas, 0 fallos**. |
| `node tests/test_auth_client.cjs` | **18 aprobadas, 0 fallos**. |
| `node tests/test_asesor_pwa.cjs` | **14 aprobadas, 0 fallos**. |
| `node scripts/build_asesor_paginas.cjs --check` | Catálogo derivado actualizado: **66 páginas**. |
| Sintaxis de scripts del asesor, autenticación, generador y archivo autónomo | **40 scripts comprobados con `node --check`**, sin errores. |
| `render.yaml` | YAML válido, variables sin duplicados y valores de texto. No aplicado a Render. |

Total: **363 pruebas aprobadas**. La prueba omitida corresponde a una comprobación manual heredada de dictado en Chrome/macOS, desactivada por defecto en otros entornos. Starlette emitió un aviso de deprecación sobre su adaptador de TestClient con httpx; no produjo fallos.

La ejecución completa detectó y permitió corregir una importación ausente de `contextlib` en el cierre del cliente Gemini, además de los defectos funcionales corregidos durante la integración.

## Qué cubren las comprobaciones

- Protección de rutas HTML, recursos privados y APIs; rechazo de sesiones ausentes, falsas, caducadas o no aceptadas por el proveedor; ausencia de bypass de desarrollo.
- Puente de sesión, cookies, control de origen, destinos tras el acceso, recuperación de contraseña y errores de cierre de sesión.
- Separación del almacenamiento local por cuenta, identificadores remotos estables y manejo explícito de errores Supabase.
- Repetición de respaldos sin versiones duplicadas aunque PostgreSQL reordene las claves JSON; reparación de una versión que no pudo insertarse; recuperación que conserva un borrador local distinto.
- Generación vacía y con datos de los 66 casos ciudadanos, los 10 tipos y las 169 entradas normativas; representación, contratos, búsqueda, anexos, títulos dinámicos, escape de HTML, respaldos y fechas.
- Regresiones del generador: prompts, cálculos, plazos, revisión, citas, auditoría, extracción, radicación y comparación de versiones.
- Nueve contratos estáticos del SQL de seguridad. Estas comprobaciones examinan las políticas y no las ejecutan en PostgreSQL.
- Evaluador real con token obligatorio y evaluador simulado sin red ni IA, sin confundir una simulación con una evaluación de producción.

Las pruebas automatizadas sustituyen las respuestas de servicios externos para ser reproducibles y no consumir credenciales o documentos reales. Los simuladores existen en las pruebas; no habilitan acceso simulado en la aplicación.

## Comprobación visual realizada

Se revisó la portada, el catálogo, un formulario ciudadano, su documento y el historial en un navegador de escritorio. Se completó una petición a una EPS con datos deliberadamente ficticios, se creó el documento y se comprobó su aparición en “Mis borradores”. Se revisó también la pantalla de acceso en estado de Supabase sin configurar, que informa que el acceso profesional no está habilitado y conserva el enlace al asesor.

La vista visual utilizó una copia estática de los activos públicos y una configuración de acceso no habilitada. No fue una sesión real contra el backend ni una prueba integral de Auth. Las rutas protegidas del servidor se verificaron mediante las pruebas HTTP automatizadas. El CSS incluye adaptación a pantallas pequeñas; no se atribuye a esta entrega una prueba visual en un dispositivo móvil real.

## Comprobaciones que dependen de la instalación de destino

1. **Supabase real:** aplicar el esquema o la migración y ejecutar `supabase/tests/aislamiento_cuentas.sql` en una instancia de prueba. Verificar dos usuarios distintos, colaboración autorizada y Storage. No hubo una instancia disponible en esta entrega.
2. **Correo y sesiones:** usar el dominio definitivo, sus URLs de retorno y cuentas de prueba para verificar confirmación, enlace de acceso, contraseña, recuperación y cierre. No se enviaron correos ni se crearon cuentas reales.
3. **IA:** realizar una evaluación con claves válidas, modelos disponibles y casos de prueba, revisando calidad, cuotas y errores del proveedor. No se enviaron escritos a Gemini o Groq en esta entrega.
4. **Despliegue y contenedor:** ejecutar el Blueprint o construir la imagen Docker en el entorno de destino. Se incluyen sus archivos, pero no se ha validado una imagen construida ni una URL publicada.

El alcance jurídico de las correcciones se describe por separado en `ASESOR_CIUDADANO.md`: fue una revisión focal de ocho grupos de textos, no una certificación de validez de todos los documentos posibles.

## Revisión visual posterior

Se preparó un recorrido visual separado del producto, con la portada y el asesor reales y dos pantallas de demostración (acceso y despacho con datos ficticios). Se comprobó la navegación entre las tres vistas y el encuadre móvil de 390 px. En esta revisión se corrigió la barra de acciones del asesor para mantenerla al final del formulario, evitando que tapara las preguntas, y se regeneró la versión autónoma. La autenticación del producto no se modificó.

## Revisión de paridad con la versión pública de referencia

La comparación con el sitio publicado confirmó que sus activos públicos corresponden al commit de origen incorporado. Se detectaron dos omisiones de la entrega inicial —PWA y páginas públicas para buscadores— y se incorporaron: aplicación instalable con alcance `/asesor/`, 66 páginas de plantillas con sus rutas originales, índice, cuatro guías, sitemap, robots, llms y metadatos. El detalle está en `PARIDAD_ASESOR.md`.

También se corrigieron dos regresiones de respaldos: guardar sobre un historial inválido ya no lo sobrescribe y el límite de tamaño usa los bytes UTF-8 de la copia exportada completa. Las pruebas verifican la conservación exacta del historial anterior y la exportación/reimportación cerca del límite.

La suite Python incluye **38 pruebas nuevas de páginas públicas** y **16 de las rutas de PWA**. Las 14 pruebas Node de PWA ejercitan el worker con eventos, respuestas y cachés simulados: precarga verificada, exclusión de rutas privadas, navegación offline, redirección de sesión sin guardado, rechazo de respuestas personalizadas y actualización limitada a la caché pública. Las rutas y los generadores de HTML de las 71 páginas adicionales se probaron sin depender de JavaScript.

La instalación, actualización y reapertura sin conexión de la PWA no se probaron en dispositivos reales. Requieren HTTPS o localhost, una primera carga con internet y soporte del navegador. La autenticación, Supabase y los servicios externos mantienen las limitaciones de validación indicadas arriba. La demostración visual permanece separada del producto y contiene datos ficticios; se actualizaron sus funciones públicas de guardado.

## Ajuste de identidad visible en el pie de página

En un primer ajuste se retiraron del pie de la portada y de las páginas públicas las menciones institucionales anteriores. La identidad visible pasó a ser El Memorialista y la descripción, Orientación ciudadana. En esa etapa se mantuvo la referencia de autoría en la sección legal. Se actualizaron la demostración, la copia autónoma y el shell PWA; sus hashes de caché se regeneraron.

Verificación posterior al ajuste: **38 pruebas de páginas públicas y 14 del worker PWA aprobadas**. Se comprobó además que los pies de la portada, la demostración, el HTML autónomo y la PWA no contenían las marcas retiradas; la referencia legal aún se conservaba en esa etapa. No se modificó la lógica de formularios, documentos o autenticación.

## Ajuste posterior de la información legal

El responsable del proyecto manifestó contar con autorización del titular para retirar también las marcas, las referencias institucionales y los créditos anteriores de la información legal. Se actualizó la documentación de la entrega para reflejar esa instrucción, conservando la evidencia de las comprobaciones técnicas previas, las fuentes normativas y los avisos de otras dependencias. El ajuste de identidad no se describe como una reescritura desde cero ni amplía los permisos indicados por el responsable.

El cambio se aplicó a la portada, “Acerca de”, la sección legal, las páginas públicas y los nombres de las descargas de respaldos. Se regeneraron el catálogo público, la copia autónoma y los recursos de la PWA, incluidos el nombre visible de la aplicación y los hashes de caché. La vista previa incorpora los mismos textos y conserva sus tres pantallas.

Comprobaciones ejecutadas después de este ajuste: **152 pruebas aprobadas, 0 fallos** (84 del motor ciudadano, 14 del worker PWA y 54 de páginas públicas y rutas PWA). El catálogo generado sigue cubriendo 66 casos. Se comprobaron además los **23 scripts JavaScript de la demostración**, sin errores de sintaxis, y la ausencia de las marcas retiradas en el código, la documentación, los archivos generados y las pantallas de la vista previa. No se modificaron las reglas de generación ni la autenticación.
