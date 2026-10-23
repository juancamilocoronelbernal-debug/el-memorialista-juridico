# Integración del asesor ciudadano en El Memorialista

> **Registro de una etapa anterior.** Las funciones y pruebas de la entrega integrada actual se describen en [INTEGRACION_COMPLETA.md](INTEGRACION_COMPLETA.md) y [VERIFICACION_INTEGRADA.md](VERIFICACION_INTEGRADA.md). Se conserva este informe para identificar qué existía en cada etapa.

## Base técnica e identidad de la entrega

- Revisión técnica de referencia: `dc646a1c9472d630251929d29d6078187336bd50`.
- Fecha de integración: 22 de octubre de 2026.
- Datos preservados: 70 casos en los archivos de referencia, de los cuales 66 están activos; 169 entradas normativas.
- La distribución por tipo se calcula desde los datos. Algunos conteos de documentación anterior difieren de los datos actuales.

La integración conserva los datos, formularios condicionales, textos y motor documental de su base técnica. La interfaz editorial y las mejoras de navegación, accesibilidad e importación corresponden a esta integración. El ajuste de identidad no supone una reescritura de esos componentes ni una afirmación de creación desde cero.

## Identidad autorizada

El responsable del proyecto manifestó contar con autorización del titular para retirar las marcas, las referencias institucionales y los créditos de la versión anterior. Conforme a esa indicación, la interfaz y su información legal se presentan bajo la identidad **El Memorialista**. Esta nota registra la instrucción recibida; no añade condiciones, cesiones ni permisos distintos de los indicados.

La sección ciudadana continúa siendo gratuita y accesible sin cuenta. La información de uso y privacidad describe el funcionamiento efectivo de esta instalación. Las licencias y avisos de otras dependencias, incluido el SDK de Supabase, se conservan por separado.

## Arquitectura y límites de separación

- `/` carga `app/static/index.html`: exclusivamente la experiencia ciudadana.
- `/static/asesor/` contiene sus recursos públicos.
- El acceso al espacio privado se ofrece mediante el enlace `/login`; la navegación del asesor no se introduce en el generador.
- El asesor no utiliza APIs de generación, IA ni autenticación para preparar sus borradores.
- No utiliza un iframe.
- La aplicación instalable tiene alcance `/asesor/` y usa un service worker nuevo con una lista explícita de recursos públicos. No se reutiliza el worker original que interceptaba navegaciones de todo el origen. La nueva caché no incluye autenticación, generador ni APIs, y no guarda respuestas de navegación dependientes de cookies.
- Las garantías de autenticación y autorización del área privada pertenecen al servidor, no a esta interfaz. No basta con ocultar enlaces.

## Funcionalidades conservadas

Los 66 casos activos mantienen preguntas condicionales, opciones de representación, anonimato cuando el caso lo permite, datos de contraparte, contratos bilaterales, declaración unilateral, hechos, solicitudes, fundamentos, anexos y guías posteriores. Se conservan los cuatro casos retirados en el código, fuera del catálogo y de la importación.

También se mantienen búsqueda por sinónimos; filtros por tipo, entidad y módulo de mujeres; vista previa; edición; historial voluntario; duplicación y eliminación; exportación e importación; Word, texto, copia y compartir mediante las capacidades del dispositivo; impresión/PDF; guía, glosario, directorio; calendario nacional y calculadora de plazos.

**Formato de Word:** la salida `.doc` es HTML compatible con Word heredado del motor original. No se presenta como un archivo `.docx` nativo. El PDF se obtiene mediante la impresión del navegador; no existe radicación automática ni firma electrónica implementada.

## Mejoras implementadas

1. Portada editorial adaptable a escritorio y móvil, sin fuentes ni bibliotecas CDN.
2. Búsqueda local con ponderación de títulos, sinónimos, descripción, entidad y etapa del trámite; cada coincidencia muestra términos relacionados. Es búsqueda determinista: no un diagnóstico ni una recomendación jurídica individualizada por IA.
3. Navegación móvil accesible, enlace de salto, foco de encabezado en navegación, estado actual, modo claro/oscuro y respeto por movimiento reducido.
4. Progreso de campos obligatorios condicionado por respuestas; navegación a secciones; vista previa móvil opcional.
5. Guardado voluntario de un borrador incompleto, sin tener que finalizarlo. El resto del formulario permanece en memoria y se pierde si se cierra sin guardar.
6. Validación de fechas de calendario, correo e inputs; errores visibles, foco y anuncios accesibles.
7. Importación con validación completa antes de escribir: hasta 5 MB, 200 documentos, identificadores seguros y únicos, caso activo, metadatos válidos, datos escalares/listas y límites de tamaño. Rechaza propiedades de prototipo y objetos anidados. Compatible con el arreglo original y el sobre versionado nuevo.
8. Exportación JSON con versión, fecha y documentos. Omisión explicada de identificadores duplicados.
9. Identificadores escapados en el historial y motor con escape de HTML. El documento generado no ejecuta HTML escrito por el usuario.
10. Copia autónoma sin conexión regenerable, sin login ni generador privado.
11. PWA pública instalable, conservando también el archivo autónomo original como modalidad alternativa sin conexión.
12. Páginas públicas de los 66 casos, índice y cuatro guías con lectura sin JavaScript; canonical, Open Graph, datos estructurados, sitemap, robots y llms adaptados al dominio de instalación.
13. Lectura estricta del historial antes de cada guardado. Si una copia antigua resulta incompatible, se preserva sin cambios y se ofrece su descarga original; no se sobrescribe con un nuevo borrador.

## Privacidad

Las respuestas del asesor se procesan en el navegador. No se realizan solicitudes de generación ni se envían respuestas a un servidor o modelo. El navegador guarda documentos únicamente cuando el usuario lo solicita; “Recordar mis datos” también es una elección expresa. El tema y el cierre del aviso usan preferencias locales.

El historial usa la clave `aj_documentos`, los datos recordados `aj_misdatos` y las preferencias `aj_tema` y `aj_aviso`. Los datos locales no están cifrados por esta aplicación: quien utilice el mismo perfil del navegador podría acceder a ellos. La interfaz explica el uso en equipos compartidos y ofrece borrado de documentos/datos. Se conservan las claves y el formato de respaldo del proyecto de origen, con los límites y la validación indicados arriba; no se promete importar cualquier archivo histórico. Los datos de otro dominio no se trasladan automáticamente: se exportan e importan voluntariamente.

El alojamiento puede registrar metadatos técnicos y el acceso privado puede establecer cookies de sesión. La información de privacidad distingue el procesamiento local de los formularios públicos del funcionamiento del espacio privado.

## Versión autónoma

Generar después de cambiar recursos públicos:

```bash
python scripts/build_asesor_offline.py
```

Salida:

```text
app/static/asesor/descargas/el-memorialista-ciudadano-sin-internet.html
```

El script incrusta únicamente las hojas de estilo y los scripts explícitos bajo `/static/asesor/`. Rechaza recursos fuera de ese directorio y enlaces privados persistentes. El archivo incluye `window.AJ_SIN_INTERNET=true`, elimina el enlace de sesión y no requiere servidor. Los enlaces oficiales externos sí requieren conexión. Algunos navegadores restringen localStorage en archivos locales; exportar una copia cuando se quiera conservar el trabajo.

## API de integración para mantenimiento y pruebas

```javascript
AJ.mejoras.buscar(texto, tipoOpcional, categoriaOpcional); // casos ordenados
AJ.mejoras.reasons; // Map casoId -> términos coincidentes
AJ.mejoras.datosSeguros(objeto); // objeto normalizado o excepción
AJ.mejoras.validarRespaldo(arregloOSobre); // registros normalizados o excepción
AJ.mejoras.leerHistorial(); // no convierte errores en un historial vacío
AJ.mejoras.guardarBorrador(registro); // valida y conserva los demás borradores
AJ.ui.camposDelCaso(caso);
AJ.ui.inicializarDatos(caso, previosOpcionales);
AJ.ui.visible(campo, datos);
AJ.motor.generar(caso, datos); // html, texto y bloques
AJ.festivos.parseISO('2026-02-31'); // null
```

Orden de carga: calendario → normas → entidades → campos comunes → casos → sinónimos → motor → mejoras → app. `AJ.ui` permite pruebas del motor y formularios sin duplicar reglas.

## Verificación y mantenimiento jurídico

La revisión técnica no constituye auditoría jurídica integral ni certifica vigencia de cada una de las 169 entradas. Los textos y fuentes sectoriales forman parte del catálogo integrado. La calculadora es orientativa, usa festivos nacionales y no representa cierres extraordinarios, suspensiones, vacancia o todas las reglas de cada despacho. La interfaz hace visible esta limitación.

Antes de publicar cambios normativos, verificar la disposición y la jurisprudencia aplicable en las fuentes oficiales, registrar fecha y alcance de la revisión, y revisar las plantillas afectadas. No debe anunciarse una revisión profesional completa por el solo hecho de haber integrado el código.

## Comprobaciones técnicas iniciales realizadas

- Sintaxis JavaScript de app, mejoras y calendario.
- Evaluación de datos/motor en Node: 66 casos activos y 169 normas.
- Búsqueda por problemas de EPS, petición sin respuesta e incumplimiento de tutela.
- Rechazo de fecha imposible y de identificadores HTML en la importación.
- Construcción de la copia autónoma con verificación de recursos y enlaces privados.

El conjunto de pruebas del proyecto y la revisión visual complementan estas comprobaciones. Mantener actualizada la información de funcionamiento y regenerar la versión autónoma después de cualquier corrección.


## Correcciones focales posteriores a la integración — 22 de octubre de 2026

Se revisaron errores concretos detectados durante QA y se contrastaron los puntos indicados con fuentes oficiales. **Esta revisión está limitada a esos puntos: no es una auditoría integral de las 169 referencias ni una garantía de vigencia, procedencia o resultado de los documentos.**

| Punto corregido | Cambio aplicado | Fuente oficial de contraste |
| --- | --- | --- |
| Petición previa en salud | Se elimina la presentación de una petición como requisito universal para acudir a tutela. Se indica buscar atención y orientación inmediata ante urgencia para salud o vida. | [Ley 1755 de 2015, artículo 20](https://www1.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=65334); [Decreto 2591 de 1991, artículos 6, 7 y 9](https://www1.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=5304) |
| Resultado y cumplimiento de tutela | Se eliminan resultados garantizados y el plazo de 48 horas como consecuencia uniforme. La guía remite a las órdenes y al plazo concreto del fallo. Las pretensiones que solicitan un plazo se mantienen como solicitudes, no como resultados obtenidos. | [Decreto 2591 de 1991, artículos 23, 27 y 29](https://www1.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=5304) |
| Silencio en servicios públicos | Se precisa el ámbito del contrato de servicios públicos domiciliarios y las excepciones por prueba y demora atribuible al usuario. Se elimina la promesa automática sin condiciones. | [Ley 142 de 1994, anotación del artículo 158 subrogado](https://normograma.superservicios.gov.co/NORMOGRAMA/compilacion/docs/ley_0142_1994.htm); [Concepto SSPD 160 de 2024](https://normograma.superservicios.gov.co/NORMOGRAMA/compilacion/docs/concepto_superservicios_0000160_2024.htm) |
| Falta de respuesta a reclamación de consumo | Se corrige la afirmación de aceptación automática: la falta de respuesta puede valorarse como indicio grave. Se distingue la reclamación previa a demanda de protección al consumidor de una denuncia administrativa. | [Ley 1480 de 2011, artículo 58.5.f](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=44306); [SIC, reclamaciones de saldos](https://sedeelectronica.sic.gov.co/publicaciones/boletin-juridico/concepto/reclamaciones-de-saldos-favor-del-consumidor-inmobiliario) |

| Postulación en asuntos de consumo | Se sustituye la regla incorrecta de “menor cuantía” por la referencia a mínima cuantía y a las reglas de postulación; no se promete actuación sin abogado para cualquier monto. | [SFC, requisitos para demandas contractuales](https://www.superfinanciera.gov.co/publicaciones/10104080/consumidor-financierofunciones-jurisdiccionales-abc-para-poner-una-demandaque-debe-hacerque-debe-hacer-problemas-contractuales-con-entidades-vigiladas-10104080/); [SFC, preguntas frecuentes de protección al consumidor financiero](https://www.superfinanciera.gov.co/preguntas-frecuentes/23/23-accion-jurisdiccional-de-proteccion-al-consumidor-financiero/) |
| Conciliación de alimentos y custodia | Se elimina el plazo genérico de quince días para todo el trámite y la gratuidad universal. Se distingue alimentos de menores del régimen de adultos: la referencia al artículo 111 y las medidas administrativas allí previstas no se trasladan automáticamente a adultos. | [Ley 2220 de 2022, artículo 60](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=188766); [MinJusticia, aumento de cuota alimentaria](https://www.minjusticia.gov.co/programas-co/LegalApp/Paginas/%C2%BFEn-cu%C3%A1les-casos-se-puede-solicitar-un-aumento-a-la-cuota-de-alimentos.aspx); [ICBF, fijación de cuota de alimentos](https://www.icbf.gov.co/portafolio-de-servicios-icbf/fijacion-cuota-de-alimentos); [Ley 1098 de 2006, artículo 111](https://www1.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=22106) |
| Atención tras violencia sexual | Se aclara que debe buscarse atención también después de 72 horas, sin esperar a presentar una petición o denuncia. El equipo de salud valora las medidas según el tiempo transcurrido. | [Ministerio de Salud, Resolución 459 de 2012](https://www.minsalud.gov.co/Normatividad_Nuevo/Resoluci%C3%B3n%200459%20de%202012.pdf); [Ministerio de Salud, orientación clínica](https://herramientaclinicaprimerainfancia.minsalud.gov.co/alarmas/M013/M13-002/M13-002.pdf) |
| Caducidad de acciones por acoso laboral | Se corrige seis meses por tres años conforme a Ley 2209 de 2022, sin confundir ese término con las garantías de represalias del artículo 11. No se promete que cualquier despido sea automáticamente ineficaz. | [Ley 2209 de 2022](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=186987); [Ley 1010 de 2006 consolidada](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=18843) |

Además se corrigieron dos errores de fidelidad documental: el motor ya no inventa una copia de identidad como anexo cuando no se seleccionó ningún adjunto, y los títulos dinámicos se evalúan en lugar de imprimir la función JavaScript. La guía distingue las reglas de presentación judicial digital del ámbito de la Ley 2213 de 2022 de una petición administrativa o denuncia; los contratos mantienen su guía específica. Ningún archivo de soporte se adjunta ni se presenta ante autoridades de forma automática.
