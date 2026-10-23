# El Memorialista 5.0.2 — Manual completo de uso

**Guía de usuario para la orientación ciudadana, el despacho jurídico, el Agente, Jurisprudencia, Monitor, DMS, Firma electrónica y el generador de escritos.**

*Fecha de edición: 23 de octubre de 2026. Dirigida a quien está aprendiendo a usar la plataforma. Las pantallas y nombres corresponden al proyecto integrado. Una función disponible en el código puede requerir activar un servicio en tu instalación antes de funcionar con datos reales.*

> **Regla práctica:** conserva una copia de tus documentos importantes; verifica siempre las citas, los hechos y los plazos; y aprueba las actuaciones externas personalmente. La IA apoya la investigación y la redacción, pero no sustituye tu juicio profesional.

## 1. Primer ingreso y orientación de la plataforma

**La web tiene dos espacios diferentes.** La dirección `/` muestra la orientación jurídica ciudadana sin cuenta; `/login` sirve para entrar; `/app` es el **despacho profesional privado**; `/generador` es el **generador especializado de documentos**. Si intentas abrir los espacios privados sin sesión, el servidor exige iniciar sesión.

1. Abre la dirección en la que Antigravity haya desplegado la aplicación y pulsa **Iniciar sesión**.
2. Entra con tu cuenta habilitada en Supabase; si tu instalación admite acceso por correo, utiliza el enlace enviado a tu buzón. Los enlaces de recuperación requieren un dominio autorizado en Supabase.
3. Al entrar llegas al **Agente**, el chat principal del despacho.
4. A la izquierda verás **PRODUCTOS** (Agente, Jurisprudencia, Monitor, DMS, Firma electrónica) y **MI TRABAJO** (Encargos por etapas, Tareas programadas, Conexiones, Salas, Asuntos, Revisión en tabla, Editor y versiones, Ajustes).
5. En la parte inferior del menú encontrarás **Generador de escritos**. Al pulsarlo entras en el generador profesional con su nuevo aspecto visual.
6. En móvil, abre el menú ☰ y selecciona la sección. El generador muestra sus cinco pestañas debajo de la barra superior.

**Antes de usar datos de clientes:** crea un asunto ficticio y practica. Confirma en **Ajustes → Comprobar conexiones** que almacenamiento e IA están configurados. El estado “configurado” no garantiza por sí solo que una operación externa funcione; compruébala con un ejemplo.

## 2. Tu primer flujo completo — del documento a la firma

Este ejercicio ficticio enseña cómo se conectan los módulos:

1. Abre **Asuntos → Crear asunto**. Pon un título como “Contrato de prueba — Caso 001” y agrega una descripción que no contenga datos personales reales.
2. Ve a **DMS**, elige **Subir archivo** y adjunta un PDF o DOCX de prueba. Vincúlalo al asunto.
3. Si necesitas buscarlo por significado, utiliza **Indexar/Reindexar** tras cargarlo. Si es un PDF escaneado, revisa el resultado del **OCR** y sus advertencias.
4. En **Agente**, selecciona el asunto y pulsa **Adjuntar** para elegir el documento. Selecciona modo **Analizar** y escribe: “Resume las obligaciones, identifica riesgos y cita el fragmento de cada conclusión”.
5. Revisa la respuesta, los fragmentos recuperados, las citas y los avisos de cobertura. Corrige posibles errores antes de continuar.
6. Cambia a **Jurisprudencia** o al modo **Investigar** si necesitas buscar fuentes externas para ese problema jurídico.
7. Usa **Guardar escrito** en la respuesta, o entra en **Editor y versiones** para trabajar en el borrador. También puedes utilizar **Generador de escritos** si el caso corresponde a uno de sus 26 tipos especializados.
8. En el editor guarda una versión. Si redactas en el generador, utiliza **Guardar copia en DMS** después de producir el documento.
9. En **Firma electrónica**, prepara una solicitud con el PDF final, los destinatarios y el orden de firma. Haz la prueba con correos tuyos autorizados.
10. Comprueba la constancia cuando el destinatario acepte. **No confundas esta aceptación por correo con una firma digital certificada.**

## 3. Agente — conversar con IA y trabajar sobre un asunto

**Para qué sirve.** Chat jurídico con contexto documental, redacción, análisis, cronologías, investigación y guardado del resultado. El motor configurado por defecto es Gemini; puede utilizar Groq como respaldo en operaciones compatibles. La ejecución depende de las claves y cuotas del servidor.

### Enviar una consulta

1. En **Agente**, elige un **Asunto del encargo** (o crea uno desde Asuntos).
2. En **Biblioteca para el agente** decide dónde debe buscar: **automática**, **sin recuperación**, **documentos DMS**, **fuentes jurídicas**, o **documentos y fuentes**. Elegir archivos específicos limita la recuperación a ellos.
3. Pulsa **Adjuntar** para seleccionar documentos ya incorporados al DMS. Si aún no existen, primero súbelos a la biblioteca.
4. Pulsa **Instrucciones** si quieres aplicar criterios de estilo guardados; puedes crearlos en Ajustes.
5. Selecciona el **Tipo de encargo**: **General**, **Analizar**, **Redactar**, **Cronología** o **Investigar**.
6. Escribe el objetivo y los límites. Ejemplo: “Ordena cronológicamente los hechos del expediente, distingue afirmaciones de pruebas y señala qué información falta”.
7. Pulsa **Enviar encargo**. Lee la respuesta, sus enlaces, advertencias y el apartado de cobertura. Puedes **Detener** una consulta en marcha.
8. Sobre la respuesta, usa **Copiar**, **Guardar escrito**, **Word** o **PDF**. Abre una conversación anterior desde la barra lateral o la lista de conversaciones.

**Interpretación de los modos:** General responde; Analizar examina hechos y documentos; Redactar prepara texto revisable; Cronología ordena acontecimientos; Investigar busca fuentes externas cuando el proveedor lo permite. El modo **Investigar** puede realizar consultas fuera del despacho: evita poner datos confidenciales innecesarios en la pregunta que se envía a un buscador.

### Consejos de mejores resultados

Pide siempre una salida verificable. Por ejemplo: “Presenta tabla Hecho / Fuente documental / Página / Riesgo / Dato que falta. No inventes referencias ni fechas”. Si un resultado declara que el contenido fue **truncado** o que solo se recuperó una parte, revisa el resto de los documentos antes de concluir que el análisis es completo.

## 4. Encargos por etapas — Agente con plan y aprobación

**Cuándo usarlo.** Cuando un trabajo necesita varios pasos relacionados: leer, investigar, redactar y revisar.

1. En la pantalla principal pulsa **Planificar y ejecutar**, o abre **Encargos por etapas**.
2. Describe el objetivo, el asunto y los documentos pertinentes. El sistema propone etapas.
3. **Revisa y edita cada etapa**. Una aprobación debe referirse a un plan concreto; si se modifica, revísalo y apruébalo de nuevo.
4. Inicia la ejecución. Observa el estado de cada paso: pendiente, en curso, completado, necesita revisión o error.
5. Si algo cambia, utiliza **Cancelar** o **Reintentar** según corresponda; no des por realizado un paso que muestre error o cobertura incompleta.
6. Revisa los resultados guardados y, si hay una actuación con efectos externos, confírmala personalmente antes de ejecutarla.

**Navegador supervisado:** la función depende de Chromium con aislamiento compatible o de Browserbase. La intervención manual exige configuración. **No es garantía de acceso a cualquier portal**, ni debe emplearse para eludir verificaciones o realizar presentaciones oficiales sin aprobación.

## 5. Tareas programadas

1. Abre **Tareas programadas**.
2. Crea una tarea indicando objetivo, frecuencia y condiciones permitidas.
3. Guarda y verifica que el estado sea **activo**, que su próxima ejecución esté calculada y que el alojamiento tenga un trabajador continuo.
4. Revisa el historial de ejecuciones y sus errores. Pausa lo que no necesites.

**Importante:** cerrar tu navegador no debería detener una tarea correctamente desplegada, pero si el alojamiento suspende el servicio, no habrá ejecuciones garantizadas. El sistema aplica cuotas persistentes a automatizaciones; la ausencia de resultados no demuestra que una fuente no cambió.

## 6. Jurisprudencia — investigar con fuentes

1. En **Jurisprudencia** formula una pregunta con **jurisdicción, época, jurisdicción territorial y problema jurídico**. Ejemplo: “¿Qué criterios recientes ha expuesto la Corte Constitucional de Colombia sobre ...? Incluye fecha, identificación y enlaces originales”.
2. Selecciona modo **Investigar** si no está activo y envía la consulta.
3. Examina cada enlace y abre el documento original de la fuente. Comprueba que el texto realmente diga lo que afirma la respuesta.
4. Si la fuente es relevante, incorpórala a tu **biblioteca jurídica** desde el panel correspondiente, sujeto a que la dirección esté permitida.
5. Usa la búsqueda textual o semántica para localizar pasajes guardados. Para la búsqueda por significado debes activar embeddings e indexar los documentos.
6. Contrasta vigencia, jerarquía de la autoridad, hechos del precedente y citas antes de llevar el análisis a un escrito.

**Diferencia esencial:** la investigación web usa el proveedor y fuentes recuperadas; la biblioteca jurídica propia solo contiene lo que hayas importado. No es un repositorio exhaustivo ni una base comercial equivalente a Magnar.

## 7. DMS — guardar, encontrar y versionar documentos

**DMS significa gestor documental.** Ordena originales, textos, versiones y asuntos dentro de la cuenta privada.

### Subir y organizar

1. Abre **DMS** → **Subir archivo**.
2. Selecciona PDF, DOCX, TXT, Markdown o alguno de los formatos de imagen compatibles, y elige su asunto.
3. Asigna un título claro. Guarda y comprueba que aparezca en la biblioteca.
4. Abre el documento para revisar el texto extraído. En un PDF escaneado, verifica si OCR pudo leer todas las páginas importantes.
5. Usa **Indexar/Reindexar** para habilitar búsqueda por significado y para reflejar una versión nueva. La búsqueda textual puede funcionar sin embeddings.

### Editar y conservar versiones

1. Entra a **Editor y versiones**, o selecciona **Editar** desde la biblioteca.
2. Cambia el texto y pulsa **Guardar versión**.
3. Abre **Historial** o **Comparar cambios** para revisar las diferencias y, si corresponde, **Restaurar versión**.
4. Si el documento es final, protégelo para impedir ediciones accidentales. Una modificación simultánea en otra pestaña puede generar un conflicto: resuélvelo antes de sobrescribir.
5. Descarga por separado los originales binarios importantes. Un respaldo JSON de metadatos **no sustituye** una copia de esos binarios.

**Límites:** el DMS se separa por cuenta y no habilita por sí mismo colaboración entre varios abogados en una biblioteca común. Al pasar documentos a la IA, se envían los fragmentos seleccionados al proveedor configurado.

## 8. Asuntos y expedientes

1. Abre **Asuntos → Nuevo asunto**.
2. Añade un nombre preciso, estado y descripción. Evita exponer datos sensibles en el título si después vas a compartir referencias.
3. Vincula documentos, conversaciones y trabajos al asunto.
4. Filtra los documentos o inicia un nuevo encargo con ese asunto seleccionado.
5. Cuando se cierre el asunto, revisa documentos finales, firmas y respaldos antes de archivar.

**Ejemplo:** “Arrendamiento — prueba 2026” agrupa contrato, comunicaciones, cronología, derecho de petición, revisión y constancias.

## 9. Revisión en tabla — analizar varios documentos a la vez

1. En **Revisión en tabla**, selecciona los documentos que quieres comparar.
2. Define las columnas necesarias: “Parte”, “Fecha”, “Obligación”, “Monto”, “Prueba”, “Riesgo”, “Fragmento de respaldo”.
3. Describe tus reglas: “Si no aparece la fecha, escribe ‘No identificada’ y no la infieras”.
4. Ejecuta **Analizar**.
5. Verifica filas, citas y fragmentos. Exporta como CSV cuando la pantalla lo permita.

No interpretes una celda generada como prueba documental hasta abrir la fuente correspondiente.

## 10. Monitor — vigilar páginas y condiciones

1. En **Monitor**, pulsa **Crear monitor**.
2. Selecciona una **fuente oficial permitida** y especifica su dirección web.
3. Escoge **Palabras clave** para coincidencias literales, o **Evaluación con IA** para una condición más amplia escrita en lenguaje natural.
4. Indica la frecuencia y guarda. Activa la vigilancia si tu alojamiento dispone del proceso automático.
5. Pulsa **Comprobar ahora** para establecer la primera lectura. La primera revisión es **línea base**, no necesariamente una alerta de cambio.
6. En revisiones posteriores, abre **Hallazgos**, revisa el texto capturado, las fechas, el estado y los avisos de cobertura.
7. Puedes **Editar**, **Pausar**, **Activar** o **Eliminar** el monitor. Eliminarlo elimina también su historial, según el aviso de confirmación.

**Estados a interpretar:** primera lectura guardada; sin cambios; cambio con coincidencias; cambio sin coincidencias; revisión parcial; error. **Una fuente que falló o se leyó solo parcialmente no equivale a “sin novedades”.**

El módulo no garantiza vigilancia universal de procesos judiciales por número de radicado, ni correos automáticos; consulta los resultados en el despacho. El análisis de IA requiere proveedor y presupuesto de uso.

## 11. Firma electrónica — documentos, firmantes y constancia

1. Revisa y finaliza el documento primero; la solicitud utilizará una **copia fija** de su contenido.
2. En **Firma electrónica** elige la vista de solicitudes actualizadas y pulsa **Nueva solicitud**.
3. Añade uno o varios documentos, firmantes, nombre y correo correctos.
4. Configura orden **secuencial** o **en paralelo**, vencimiento e instrucciones.
5. Revisa el resumen y crea la solicitud. Si SMTP está configurado, se envían invitaciones y códigos a los destinatarios según el flujo.
6. El destinatario abre el enlace, comprueba el documento, recibe o introduce su código de acceso y presta consentimiento expreso.
7. Revisa el estado desde Firma electrónica y descarga la **Constancia PDF** con la evidencia registrada. Cancela o revoca solicitudes que no deban seguir vigentes.

**Qué acredita:** acceso al correo utilizado, aceptación y evidencias técnicas del documento. **Qué no acredita por sí sola:** identidad civil verificada, firma digital con certificado acreditado, biometría ni validez automática para todos los negocios jurídicos. Verifica el nivel de firma que requiere cada acto.

**Nunca envíes enlaces de firma con datos reales en un entorno de prueba sin autorización de los destinatarios.**

## 12. Salas de documentos — compartir con clientes

1. Abre **Salas de documentos → Nueva sala** y elige las copias PDF que quieres compartir.
2. Configura el enlace: permiso de visualización, descarga o aporte; fecha de vencimiento; marca de agua si corresponde.
3. Comparte el enlace únicamente con el destinatario previsto. La posesión del enlace habilita los permisos asignados.
4. Consulta las visitas y descargas registradas.
5. Si el cliente sube archivos, estos aparecen **pendientes de revisión**. Abre cada aporte, revísalo y luego elige **Incorporar al expediente** o **Rechazar**.
6. Revoca el enlace cuando ya no sea necesario.

Las salas no verifican automáticamente la identidad civil del visitante y no crean una cuenta profesional para el cliente.

## 13. Conexiones — Drive, OneDrive, SharePoint y Outlook

1. En **Conexiones**, identifica el proveedor a utilizar.
2. Si está disponible, pulsa **Conectar** y autoriza la cuenta a través de su pantalla OAuth.
3. Busca los documentos o mensajes permitidos. Elige **Importar** para copiar al DMS.
4. Verifica título, origen, propietario, tamaño y texto extraído; relaciona la copia con un asunto.
5. En **Conexiones** puedes revisar el estado y **Desconectar** cuando ya no sea necesario.

**Alcance real:** permite **lectura e importación**. No habilita sincronización bidireccional, envío desde Outlook ni administración remota de los archivos originales. Si el proveedor aparece “por configurar”, un administrador debe registrar la aplicación, completar sus secretos en el servidor y autorizar las URIs de retorno.

## 14. Generador de escritos — todos sus apartados, con la nueva apariencia

En el menú del despacho pulsa **Generador de escritos**. El generador conserva su motor y sus **26 tipos profesionales**. En escritorio verás la misma navegación lateral del despacho; en móvil verás las cinco pestañas en la barra superior. La apariencia cambió, **no la lógica de redacción ni los identificadores de los controles**.

### 14.1 Redactar

1. En **Redactar escrito** busca o escoge el tipo profesional adecuado del catálogo.
2. Completa los campos del formulario con hechos, pretensiones, partes, documentos y fechas, sin adivinar los datos que faltan.
3. Si está disponible la **extracción de documentos**, adjunta los archivos del caso y revisa las propuestas antes de aplicar valores al formulario.
4. Revisa términos o alertas de vencimiento. Si falta información esencial, complétala.
5. Pulsa **Redactar escrito**. Durante la generación puedes utilizar **Detener** si necesitas cancelar.
6. Revisa el documento en la hoja derecha. Si hace falta, usa **Ajustar con IA** y describe un cambio concreto; **Regenerar** prepara otra versión; **Comparar versiones** permite ver diferencias cuando las haya.
7. Usa **Copiar**, **Word** o **PDF** para exportar. **Guardar copia en DMS** crea una copia en la biblioteca profesional. **Preparar radicación** genera un paquete para revisión; no lo presenta automáticamente ante una autoridad.
8. Revisa las verificaciones y citas. Las observaciones sobre normas, pruebas y auditoría requieren evaluación profesional.

### 14.2 Membrete y estilo

1. Abre **Membrete y estilo**.
2. Completa tus datos profesionales con precisión: nombre, tratamiento, firma/despacho y los demás campos que correspondan.
3. Configura el aspecto de la hoja y, si tu flujo lo permite, añade logo, firma o plantilla autorizada.
4. Guarda y comprueba en la vista previa que el membrete y los márgenes son los deseados.
5. Para analizar tu estilo puedes adjuntar una muestra propia y pulsar **Analizar mi estilo** cuando el proveedor esté configurado.

**Importante:** el rediseño visual del programa no modifica la tipografía, los márgenes ni el membrete de los documentos generados; esos parámetros siguen bajo tu control.

### 14.3 Historial

1. Abre **Historial**, utiliza el buscador y abre un escrito anterior.
2. Revisa la fecha y el tipo antes de recuperar o duplicar.
3. Descarga una **copia de seguridad** para conservar tus datos locales del generador, incluidas las partes compatibles de perfil, logo, firma, plantilla e historial.
4. En la ventana de cuenta podrás utilizar **Respaldar mis datos en la nube**, **Recuperar mis escritos de la nube** y **Exportar mis datos**, según disponibilidad y permisos. El alcance de cada copia es diferente.

**Advertencia:** recuperar escritos de la nube no equivale a restaurar automáticamente todas las imágenes, estilos y plantillas locales. Una eliminación local no borra necesariamente el respaldo remoto.

### 14.4 Términos y plazos

1. Entra en **Términos y plazos**.
2. Elige el tipo de actuación o término que corresponda y registra las fechas que exige la herramienta.
3. Revisa festivos, suspensiones, notificaciones efectivas, prórrogas y reglas especiales antes de utilizar la fecha calculada.
4. Utiliza los resultados como apoyo, no como validación final de vencimientos procesales.

### 14.5 Cálculos jurídicos

1. Abre **Cálculos jurídicos**.
2. Selecciona la clase de cálculo disponible e introduce importes, tasas, fechas o periodos según las indicaciones.
3. Lee el detalle y verifica manualmente unidades, redondeos y norma aplicable antes de usarlo en un escrito.

## 15. Editor y versiones / complemento Word

El **Editor y versiones** del despacho es diferente de **Redactar** en el generador. El primero es un editor documental general para guardar y comparar textos. El segundo construye escritos de tipos especializados a partir de formularios y prompts del generador.

Desde el editor puedes: crear, guardar versión, comparar cambios, pedir **Ajustar con IA**, abrir historial, y descargar Word/PDF. Los documentos protegidos no se deben sobrescribir sin desbloqueo autorizado.

En **Ajustes → El Memorialista en Word**, descarga el manifiesto y abre el complemento si tu instalación lo admite. Requiere Word compatible, alojamiento HTTPS e instalación autorizada. No se agrega automáticamente a Microsoft Word por abrir la web.

## 16. Orientación jurídica ciudadana — parte pública

Es un espacio separado del despacho y no requiere cuenta. Se construye con reglas y plantillas locales, no con el chat de Gemini.

1. Entra en la portada pública sin sesión.
2. Busca tu situación o utiliza el **Orientador**, que formula preguntas y sugiere casos.
3. Abre uno de los **66 casos activos** y completa su formulario guiado.
4. Revisa la vista previa, corrige datos y descarga **DOCX**, **PDF** o utiliza **Imprimir**.
5. En **Mis documentos** guarda, duplica, actualiza o elimina borradores en el navegador. Usa copia JSON para respaldo.
6. Si registras una radicación o respuesta, abre **Seguimiento**, agrega la fecha y prepara el siguiente escrito cuando corresponda.
7. Puedes utilizar la versión descargable sin internet. La instalación PWA depende del navegador y de HTTPS.

**Privacidad:** los borradores ciudadanos residen en el navegador y pueden ser accesibles a otras personas con el mismo perfil de navegador. No se trasladan automáticamente al despacho privado. El seguimiento ciudadano no consulta expedientes oficiales ni envía alertas automáticas.

## 17. Ajustes, datos y respaldos: qué significa cada copia

| Dónde | Qué incluye | Qué no debes dar por incluido |
| --- | --- | --- |
| Asesor público → copia JSON | Borradores y su seguimiento local compatibles. | Cuenta privada, documentos DMS, identidad de Supabase. |
| Generador → Descargar copia | Datos locales del generador, perfil, historial y recursos incluidos en su formato. | Todos los registros y binarios remotos del despacho. |
| Generador → Recuperar de la nube | Escritos propios respaldados por el servicio. | Reconstrucción automática de toda la plantilla local y el membrete. |
| Despacho → Exportar despacho | Registros y textos admitidos del despacho, de acuerdo con el formato. | Archivos binarios originales de Storage y credenciales de servicios. |
| DMS → Descargar original | Archivo individual original. | Base de datos completa o índice de búsqueda. |

**Para proteger tu trabajo:** descarga copias de la base y Storage antes de migraciones; prueba la restauración en un entorno aislado; no guardes claves de IA ni contraseñas dentro de un respaldo JSON compartible.

## 18. Problemas frecuentes y cómo interpretarlos

| Mensaje o síntoma | Posible causa | Qué comprobar |
| --- | --- | --- |
| Te envía a `/login` al abrir el generador | No hay sesión válida. | Supabase Auth, cookies, dominio, correo y URLs de retorno. |
| El chat dice que falta proveedor de IA | No está configurada o habilitada la API. | `GEMINI_API_KEY`, modelo admitido, cuota, salida HTTPS y logs del servidor. |
| Investigación sin citas comprobables | El proveedor no devolvió fuentes o la cobertura es parcial. | Modo Investigar, enlaces originales y advertencias. No inventes una cita. |
| Un documento no aparece en búsqueda semántica | No está indexado, cambió de versión o embeddings no está activo. | Indexar/Reindexar y estado del proveedor semántico. |
| OCR no lee todo un PDF | PDF escaneado complejo, páginas limitadas o presupuesto agotado. | Avisos, cantidad de páginas y necesidad de revisión manual. |
| Monitor muestra “primera lectura” | Todavía no hay segunda observación. | Ejecuta una comprobación posterior y compara el contenido. |
| Monitor muestra error o parcial | No obtuvo todo el contenido. | URL permitida, permisos, bloqueos externos y logs. No concluyas “sin novedades”. |
| Una firma no envía el correo | SMTP o secreto OTP pendientes, o destinatario incorrecto. | Configuración del servidor, dominio HTTPS y prueba con correo autorizado. |
| Drive/Microsoft aparece “por configurar” | Falta registro OAuth o consentimiento. | Conexiones del despacho y configuración administrativa. |
| El navegador supervisado no inicia | Falta aislamiento compatible o Browserbase. | Entorno de ejecución y configuración de Browserbase/Chromium. |
| Word/PDF o botones del generador no responden | Falta sesión, no hay documento generado o servicio de exportación falló. | Estado del botón, campo requerido, respuesta del servidor y consola. |

## 19. Lista de verificación para aprender y para publicar

**Práctica inicial segura:** crea un asunto ficticio; sube un contrato de prueba; analiza con Agente; investiga una fuente; guarda una versión; haz un monitor manual; prueba una firma entre correos propios; descarga la constancia; crea y exporta un escrito del generador. Comprueba que al cerrar y reabrir la sesión recuperas los datos correctos.

**Antes de producción:** exige a Antigravity evidencia de pruebas reales de Supabase, Gemini, OCR, OAuth, SMTP, Monitor programado y firmas; dos cuentas de prueba para aislamiento; revisión del dominio HTTPS y las migraciones; copias completas de base y Storage; y comprobación de cada ruta privada. Las pruebas automatizadas con servicios simulados son útiles, pero **no sustituyen esas comprobaciones**.

## 20. Glosario práctico

- **Asunto:** expediente de trabajo que vincula documentos, conversaciones y tareas.
- **Agente:** chat jurídico con IA y acciones controladas.
- **RAG / recuperación documental:** búsqueda de fragmentos relevantes para aportar contexto a la IA.
- **Indexar:** preparar texto y/o vectores para que un documento pueda buscarse.
- **Embedding:** representación numérica del significado de un texto; no prueba la corrección jurídica.
- **OCR:** extracción de texto a partir de imágenes o escaneos.
- **DMS:** sistema de gestión documental y versiones.
- **Monitor:** seguimiento de cambios en fuentes configuradas.
- **SMTP:** servicio para enviar invitaciones y códigos por correo.
- **OAuth:** autorización de acceso a Drive o Microsoft sin entregar la contraseña a El Memorialista.
- **Supabase:** servicio de identidad, base de datos y almacenamiento.
- **RLS:** reglas en la base que limitan el acceso a los registros de una cuenta.
- **Constancia de firma:** archivo que reúne el documento y la evidencia de la aceptación registrada.

---

*Guía correspondiente al código entregado, no una certificación del despliegue personal del usuario. El Memorialista es una herramienta de apoyo jurídico; cada documento y cita debe revisarse antes de firmarlo, enviarlo o presentarlo.*
