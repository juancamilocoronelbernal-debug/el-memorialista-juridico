# Comparación funcional del módulo ciudadano

> **Registro de una etapa anterior.** Las funciones y pruebas de la entrega integrada actual se describen en [INTEGRACION_COMPLETA.md](INTEGRACION_COMPLETA.md) y [VERIFICACION_INTEGRADA.md](VERIFICACION_INTEGRADA.md). Se conserva este informe para identificar qué existía en cada etapa.

Fecha de comparación: **22 de octubre de 2026**.

## Fuente comprobada

Se comparó la integración con la versión pública de referencia y su código, revisión `dc646a1c9472d630251929d29d6078187336bd50`. La comparación se realizó antes del ajuste posterior de identidad autorizado por el responsable del proyecto.

Los scripts públicos, el motor, los archivos del catálogo, el calendario, la hoja de estilo original, manifest, service worker, sitemap y robots descargados del sitio publicado coinciden byte por byte con ese commit. El HTML de inicio publicado añade el script de analítica de Cloudflare. No se trasladó esa analítica a la integración. No se afirma haber recorrido manualmente cada página del sitio original.

## Catálogo y formularios

| Elemento | Original comparado | Integración |
| --- | ---: | ---: |
| Casos activos | 66 | 66 |
| Casos conservados en el código | 70 | 70 |
| Tipos documentales | 10 | 10 |
| Referencias normativas | 169 | 169 |
| Categorías de entidades | 11 | 11 |
| Entidades del listado | 111 | 111 |
| Entradas del directorio de ayuda | 15 | 15 |
| Campos específicos de los casos activos | 618 | 618 |
| Opciones de esos campos | 903 | 903 |

Los campos de la tabla son los específicos de cada caso: no repiten los campos comunes de identificación, firma y destinatario. Los 70 casos presentes en el código suman 665 campos específicos y 931 opciones. Los cuatro casos retirados ya estaban retirados en el original; no los retiró esta integración.

Se contrastaron identificadores, orden, tipos, obligatoriedad, opciones y condiciones de los formularios. Se conservaron las cláusulas contractuales, las opciones de representación y las modalidades de anonimato cuando el modelo las contempla. En esa comparación, los archivos de contratos, campos comunes, entidades, sinónimos y peticiones3 coincidían íntegramente con los de referencia. El ajuste posterior de identidad puede cambiar comentarios o etiquetas sin modificar las reglas de esos módulos.

## Funciones conservadas y adaptación

| Función del original | Estado de la entrega actual |
| --- | --- |
| Catálogo, filtros, búsqueda y módulo de mujeres | Conservados; búsqueda ponderada y explicación de coincidencias añadidas. |
| Formularios y generación de documentos | Conservados; progreso, navegación entre secciones y validaciones añadidos. |
| Vista previa y edición | Conservadas; vista previa desplegable en pantallas pequeñas. |
| Word, texto, copiar, compartir, impresión/PDF | Conservados. Word sigue siendo HTML compatible con `.doc`; PDF utiliza la impresión del navegador. Compartir depende de las capacidades del navegador. |
| Historial, duplicación, actualización y eliminación | Conservados; se puede guardar también un formulario incompleto. |
| Exportación e importación JSON | Conservadas con validación, límites explícitos y protección ante historial incompatible. |
| Guías, glosario, ayuda y calculadora de plazos | Conservados, con las correcciones focales documentadas en ASESOR_CIUDADANO.md. |
| Modo claro y oscuro | Conservado. |
| Archivo HTML para usar sin internet | Conservado y adaptado al módulo ciudadano. |
| Instalación como aplicación web, PWA | Reincorporada con alcance `/asesor/` y caché exclusivamente pública. |
| Páginas individuales de los 66 casos e índice | Reincorporados con las mismas rutas de plantilla del original y contenido derivado del catálogo integrado. |
| Cuatro guías públicas independientes | Reincorporadas en las mismas rutas, con redacción adaptada para preparar y revisar documentos. No son copias literales de los artículos originales. |
| Metadatos sociales y para buscadores, sitemap, robots y llms | Reincorporados para el dominio configurado en `APP_BASE_URL`. |
| Generador profesional tras inicio de sesión | Integrado como espacio separado; no forma parte de la caché de la PWA. |

## Correcciones realizadas tras la comparación

La primera entrega ya preservaba el catálogo y el motor, pero no incluía la instalación PWA ni las páginas públicas individuales y su estructura para buscadores. Esta revisión cierra esas omisiones; no se presenta la primera entrega como equivalente a todo el sitio original.

La revisión detectó además que guardar desde la vista de documento podía sobrescribir un historial que no superase la validación nueva. Se corrigió unificando ambos botones de guardado en una lectura estricta: si el historial no se puede abrir, se aborta sin modificarlo y se permite descargar el contenido original desde Mis borradores. La importación tampoco escribe sobre un historial ilegible.

Se corrigió también la medición del tamaño: antes se contaban caracteres del almacenamiento compacto; ahora se cuentan los bytes UTF-8 del JSON completo que se exportará, incluido su formato y metadatos. Así, los nuevos guardados admitidos no producen copias que excedan por ese motivo el límite de reimportación.

## Diferencias deliberadas y límites

- La identidad visual y la información legal utilizan El Memorialista. Las referencias institucionales y los créditos anteriores se retiraron conforme a la autorización del titular que el responsable del proyecto manifestó tener. Este cambio no altera los resultados de la comparación funcional ni afirma una creación desde cero.
- La PWA se limita a `/asesor/`; no usa la caché del origen completo del sitio original. Las páginas privadas, APIs y respuestas de sesión no se almacenan. En línea, una sesión válida lleva al generador; sin conexión solo existe el contenido ciudadano ya preparado.
- La instalación y permanencia de la caché dependen del navegador, HTTPS o localhost, espacio disponible y una primera carga con conexión. El HTML descargable sigue siendo una alternativa.
- El archivo importado admite hasta 5 MB y 200 documentos, con identificadores, tipos y contenido válidos. Se acepta el array JSON original y el sobre nuevo; no se promete importar cualquier respaldo histórico. Una copia incompatible se conserva y puede descargarse para su recuperación.
- El almacenamiento no se transfiere automáticamente entre dominios distintos. La persona debe exportar e importar voluntariamente sus documentos.
- La calculadora rechaza fechas imposibles y fechas fuera del rango 1900–2100. Se quitaron plazos predeterminados incorrectos de ciertos asuntos de familia; eso cambia deliberadamente el resultado respecto del original.
- El asesor ciudadano sigue funcionando con plantillas y reglas locales. No se añadió un chatbot jurídico de IA ni radicación automática.
- Tener las mismas 169 referencias no implica una revisión jurídica integral de todas ellas. Las correcciones de contenido se limitan a los puntos identificados en `ASESOR_CIUDADANO.md`.

## Verificación y despliegue

Los resultados ejecutados y sus límites se registran en `VERIFICACION.md`. Las pruebas cubren generación de los 66 casos, contratos, representación, búsqueda, exportación, preservación del historial, páginas públicas y separación de caché y autenticación. No equivalen a probar todas las combinaciones posibles de respuestas ni a certificar jurídicamente los escritos.

Esta entrega actualiza el código de El Memorialista. No modifica el sitio de referencia ni configura por sí sola el dominio, Supabase, correos o proveedores de IA de la instalación de destino.
