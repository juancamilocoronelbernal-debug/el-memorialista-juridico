# Qué cambió respecto del generador original

**Comparación de la entrega previa, realizada el 22 de octubre de 2026.**

Sí se modificó el generador original: se cambió cómo se accede a él y cómo se separan, respaldan, recuperan, exportan y eliminan los datos de cada cuenta. También se ajustaron sus rutas, permisos de base de datos, configuración y pruebas. **El catálogo profesional, la construcción del prompt y los principales motores jurídicos conservaron su contenido.**

Este informe compara el ZIP original que entregó el usuario con nuestro ZIP anterior. **No describe las nuevas funciones de Claude incorporadas en la entrega integrada actual**, ni afirma que estos cambios estén publicados en un servidor, aplicados a una base de datos o probados con credenciales reales. El ZIP que acompaña este informe es posterior: las cifras de 183 archivos, 34 modificaciones y 66 archivos nuevos corresponden a la entrega previa comparada, cuyos hashes constan en el inventario JSON.

## 1. Fuentes y método

Se compararon las entradas de estos dos archivos:

| Fuente | Identificación |
| --- | --- |
| Generador original | `upload/el-memorialista-codigo-completo.zip`, 117 archivos |
| Nuestra entrega previa | `deliverables/el-memorialista-codigo-completo.zip`, 183 archivos |
| Copias usadas para leer el código | `comparacion-claude-4ksz3wu6/base/` y `comparacion-claude-4ksz3wu6/entrega/` |

La comparación usa los bytes de los ZIP, hashes SHA-256 y diferencias de texto. Se reconocen expresamente las dos reubicaciones indicadas más abajo: comparar solamente las mismas rutas confundiría la portada nueva con una eliminación del generador.

El [inventario verificable en JSON](CAMBIOS_GENERADOR_ORIGINAL.json) contiene los hashes de ambos ZIP, la correspondencia de **los 117 archivos originales**, su clasificación, tamaños, diferencias de líneas cuando corresponde y los archivos nuevos. Las rutas y líneas citadas en este documento corresponden a la **entrega previa**; pueden cambiar en la integración posterior.

### Resultado del inventario

| Medida | Resultado |
| --- | ---: |
| Archivos originales con contenido idéntico | **83**: 82 en su ruta y 1 reubicado |
| Archivos originales modificados | **34**, incluido el HTML del generador reubicado |
| Archivos originales sin correspondencia en la entrega | **0** |
| Archivos nuevos, después de reconocer reubicaciones | **66** |
| Total de la entrega previa | **183** |

Si se cuentan únicamente rutas, hay 34 rutas comunes cambiadas, 67 rutas añadidas y una ruta retirada. Es la misma comparación con un criterio distinto: el nuevo `app/static/index.html` es la portada ciudadana; el generador original continúa en `app/private/generador.html`.

## 2. Qué se movió y qué se reemplazó en su antigua ubicación

| Archivo original | Entrega previa | Qué ocurrió |
| --- | --- | --- |
| `app/static/index.html` | `app/private/generador.html` | Se reubicó **y se modificó**. Conserva la interfaz profesional y sus herramientas, con cambios de sesión, almacenamiento y cuenta detallados en este informe. |
| `app/static/index.html` | `app/static/index.html` | La antigua ruta física se reutilizó para una **portada ciudadana nueva**. No debe compararse esta portada como si fuese el nuevo código del generador. |
| `app/static/auditor.js` | `app/private/auditor.js` | Reubicación **sin cambiar un byte de su contenido**. Su entrega por HTTP pasó a requerir sesión. |

El generador original tiene 7.199 líneas y su equivalente privado, 7.170. La comparación de texto conserva 6.900 líneas idénticas; identifica 299 líneas retiradas o reemplazadas y 270 añadidas o reemplazadas. Estos conteos describen texto, no un porcentaje de funcionalidades conservadas ni una medida de calidad.

## 3. Cambios concretos dentro del generador profesional

### Acceso antes de abrir la mesa de trabajo

Se añadió una pantalla temporal de comprobación de sesión y el título **«Mi despacho · El Memorialista»**, con instrucciones para no indexar la página. El arranque espera la validación de Supabase y la carga del catálogo antes de mostrar la aplicación. Cuando la sesión vence, se cierra o cambia de usuario en otra pestaña, se interrumpe el trabajo en curso y se conduce al acceso correspondiente.

El inicio de sesión dejó de depender del modal dentro del generador: se trasladó a `/login`, con contraseña, enlace al correo, recuperación de contraseña y registro opcional. Los controles heredados del modal que siguen en el HTML conducen al acceso separado. Se sustituyó la carga remota del SDK de Supabase por una copia servida desde el propio proyecto y un módulo de sesión común.

El cierre de sesión intenta guardar el borrador pendiente, cancela operaciones diferidas, borra la cookie de navegación, cierra la sesión local de Supabase y vuelve a la portada. Si falla, muestra el error y una opción de reintento. El regreso mediante la caché de navegación del navegador fuerza una nueva carga.

**Evidencia:** `app/private/generador.html:2–12`, `:1433–1508`, `:1544–1569`, `:7054–7170`; nuevos `app/static/auth/session.js`, `app/static/auth/login.js` y `app/static/login.html`.

### Separación de datos locales por cuenta

Antes, el almacenamiento utilizaba claves compartidas como `memorialista:perfil` y una base IndexedDB `memorialista_db`. Ahora usa un prefijo `memorialista:u:<usuario>:` y una base `memorialista_db_<usuario>`, establecidos después de comprobar la identidad. Esto separa membrete, imágenes, borradores e historial de las cuentas que usan un mismo perfil de navegador.

Los datos antiguos compartidos **no se asignan automáticamente al primer usuario que entra**. Se conservan y se muestra un aviso cuando se detectan determinadas claves heredadas. Su recuperación se hace mediante una copia que pertenezca al usuario. La importación de esa copia sigue siendo una acción explícita y conserva el comportamiento de reemplazar el historial local tras la confirmación prevista por el generador.

Se incorporaron mensajes sobre errores de almacenamiento y se aclaró en la interfaz que guardar localmente no equivale a guardar en la nube. Se añadió `Almacen.remoto()` con resultado `false`, que corresponde al almacenamiento local utilizado. En las operaciones de mezcla/importación se excluyen las claves `__proto__`, `constructor` y `prototype`; la importación limita el archivo a 30 MB, el historial a 5.000 entradas y los identificadores a 160 caracteres.

**Evidencia:** `app/private/generador.html:1202–1215`, `:1788–1912`, `:4911–4934`, `:6152–6192`, `:7158–7163`.

### Respaldo en la nube sin crear un expediente nuevo en cada guardado

El original insertaba nuevos casos, documentos y versiones en cada sincronización. La entrega previa usa identificadores estables derivados de cuenta, clase e identificador local; actualiza el mismo caso/documento y crea una versión cuando cambian el texto o los datos. Las sincronizaciones del mismo documento se ordenan en una cola y una repetición no vuelve a insertar una versión ya existente.

El respaldo manual actualiza campos del perfil, sube logo, firma y plantilla y recorre el historial del usuario. Se retiró la migración automática inicial que tomaba el historial compartido e inventaba fichas de clientes con valores como «Por registrar»: el respaldo nuevo conserva los datos del escrito y crea su caso, pero **ya no crea esas fichas de clientes automáticamente**.

Los fallos de sincronización dejan una advertencia visible. Se corrigieron operaciones de imágenes y plantillas que utilizaban `supabase.storage` en lugar del cliente inicializado `sbClient.storage`, y se usa el bucket de la configuración.

Se añadió **«Recuperar mis escritos de la nube»**. Recupera documentos propios por páginas de 500, conserva una copia local diferente y evita reimportar repetidamente la misma copia remota. Tiene un máximo explícito de 20.000 escritos por recorrido. Recupera escritos y sus datos/versiones embebidas; **no es una restauración automática integral del perfil, logo, firma y plantilla**.

Eliminar un escrito del historial local no borra su respaldo remoto; ahora el mensaje lo dice expresamente.

**Evidencia:** `app/private/generador.html:989–999`, `:1571–1707`, `:4880–4884`, `:4928–4933`, `:5960–6043`.

### Exportaciones: qué cambió y qué se conservó

Los bloques que producen **DOCX y PDF de los escritos profesionales** no se reescribieron. Tampoco se sustituyeron el editor, el membrete, el análisis de estilo, la preparación de radicación ni la construcción del texto jurídico por el motor ciudadano.

Sí cambió **la exportación de datos de la cuenta**: el botón pasó de «Exportar todos mis datos» a **«Exportar mis datos de la nube»**, porque descarga registros remotos y no incluye todos los binarios de Storage ni el contenido local que nunca se haya respaldado. Se añadió una explicación del alcance en el JSON. Se eliminó, además, la barra de cuota que mostraba un 20 % fijo: no correspondía a consumo real.

**Evidencia:** cambios del HTML en `:989–999` y `:1532–1536`; exportación de datos en `app/services/supabase_service.py:113–173`. El diff del HTML no modifica los bloques de construcción de DOCX/PDF ni el análisis de estilo.

## 4. Cambios del servidor, rutas y autenticación

### Navegación pública y privada

| Ruta o recurso | Comportamiento de la entrega previa |
| --- | --- |
| `/` | Asesor ciudadano para visitantes; con sesión válida, redirección a `/app`. |
| `/login` | Acceso profesional separado; con sesión válida, redirección a `/app`. |
| `/auth/callback` | Procesa enlaces nuevos de acceso y recuperación, aunque exista una cookie anterior. |
| `/app`, `/generador` y variantes con barra final | Entregan el HTML profesional solo después de comprobar la sesión. |
| `/auditor.js`, `/static/auditor.js` | Entregan el auditor reubicado solo con sesión. |
| `/api/*` | Acceso profesional con Bearer por defecto, con excepciones explícitas para salud y configuración/puente de sesión. |

La comprobación general de las API ocurre antes de consumir cargas de archivos o empezar streaming. La cookie sirve para navegar al HTML; no sustituye el Bearer que requieren las API. Las rutas nuevas de salud, configuración y sesión conservan sus comprobaciones específicas cuando corresponde.

Se añadieron cabeceras contra caché e indexación en las rutas privadas; se cambió la política de referente a `no-referrer`, se bloqueó la inclusión en marcos con `DENY` y se añadió HSTS en producción. CORS dejó de admitir la cabecera del código compartido. `app/private/` no se publica como directorio estático.

**Evidencia:** `app/main.py:75–141`, `:152–211`.

### Autenticación efectiva

El original aceptaba tokens con prefijos de prueba `mock-`/`test-`, contemplaba una identidad local sin Supabase y admitía un código de acceso de respaldo. La entrega previa elimina esos caminos en el código que ejecuta la aplicación: el generador exige un token reconocido por Supabase, también en desarrollo.

La validación diferencia una sesión inválida de una indisponibilidad del proveedor; limita la caché a 30 segundos y a la expiración del token, almacena una clave hash por proyecto/token y evita registrar cuerpos remotos con posibles datos sensibles. Leer la fecha de expiración no se usa como prueba de identidad.

El nuevo puente de sesión utiliza una cookie `HttpOnly`, `SameSite=Lax`, segura en HTTPS/producción y con duración limitada por configuración y vencimiento del token. Comprueba el origen al crear o borrar esa cookie. Los sustitutos de autenticación usados en pruebas viven en fixtures aislados.

**Evidencia:** `app/services/limites.py:24–50`, `app/services/supabase_service.py:24–109`, nuevo `app/services/sesiones.py:20–76`, `app/routers/auth.py:31–77`, `tests/conftest.py`.

### Diagnóstico y auditoría del catálogo

`/api/health` conserva solo estado, nombre y versión. El diagnóstico de proveedores pasó a `/api/estado`, sujeto a autenticación.

La operación `/api/catalogo/auditar/{tipo_id}` sigue produciendo un dictamen, pero ahora aplica límite de uso y llama al auditor con `actualizar_json=False`. **Una sesión normal ya no permite que esa operación reescriba el catálogo global.** El motor `auditor_catalogo.py` permanece intacto; cambia cómo lo invoca la ruta.

**Evidencia:** `app/routers/documents.py:138–178`.

## 5. Exportar y eliminar una cuenta

La exportación remota utiliza siempre la clave pública más el token del usuario, preservando las políticas RLS. Recorre las tablas con paginación y devuelve un error si no puede completar la lectura; el original podía continuar ante fallos y entregar una exportación incompleta. El JSON incluye perfil, firma accesible y registros propios de clientes, casos, documentos y versiones; declara que no contiene los archivos binarios.

La baja de cuenta requiere una clave de servicio antes de efectuar escrituras. Comprueba si los casos o documentos tienen aportes de otras personas; en ese supuesto, detiene la baja para que un administrador transfiera los registros. Conserva firmas compartidas y datos ajenos, recorre las carpetas personales `logo/<usuario>/`, `firma/<usuario>/` y `plantilla/<usuario>/`, verifica las respuestas de borrado y finalmente solicita la baja en Auth. Tras el éxito, la interfaz limpia únicamente el almacenamiento local de esa cuenta y cierra la sesión.

**La baja no es una transacción única entre Storage, tablas y Auth.** Una falla intermedia puede dejar un borrado parcial, circunstancia que el código comunica. No se afirma que una comprobación de código pruebe el borrado efectivo en una instalación real.

**Evidencia:** `app/services/supabase_service.py:113–275`, `app/routers/auth.py:99–152`, `app/private/generador.html:1759–1783`.

## 6. Base de datos y Storage

Se conservan las seis tablas originales y sus campos: `firmas`, `perfiles`, `clientes`, `casos`, `documentos` y `versiones`. Los cambios principales están en funciones, triggers, permisos y políticas, no en un reemplazo del modelo de documentos.

Los ajustes impiden cambiar desde el cliente el despacho, rol, cuota o propietario de un registro; restringen la administración de miembros a una función autorizada para servicio/administración; exigen que las relaciones entre clientes, casos y documentos pertenezcan al mismo ámbito; y protegen la eliminación en cascada cuando existen versiones o documentos de otros integrantes. Las versiones no se editan mediante `UPDATE` desde el cliente.

Storage sigue siendo privado y mantiene un límite de 10 MB. Se delimitan las rutas personales y las compartidas del despacho; para escribir en estas últimas se exige administración. La lista de tipos admitidos se aplica también al actualizar el bucket y **retira SVG** de la lista anterior; conserva PNG, JPEG, WebP, DOCX y PDF.

La migración inicial original era un archivo de cuatro líneas con `\ir ../schema.sql`, un metacomando de psql. Se convirtió en SQL autocontenido. Se añadió `20261022010000_separacion_publica_privada_rls.sql` para aplicar las políticas a instalaciones existentes y una comprobación SQL de aislamiento.

Estas migraciones no trasladan automáticamente archivos antiguos, no reparan por sí solas registros heredados con un despacho equivocado y no acreditan que se hayan ejecutado en Supabase. La administración de membresía tampoco mueve documentos anteriores.

**Evidencia:** `supabase/schema.sql:173–489`, `supabase/migrations/20261022000000_supabase_auth_db_storage.sql`, `supabase/migrations/20261022010000_separacion_publica_privada_rls.sql`, `supabase/tests/aislamiento_cuentas.sql`.

## 7. Relación completa de archivos originales modificados

Esta tabla enumera los **19 archivos originales modificados que no son pruebas**. El apartado siguiente enumera los otros 15.

| Archivo original | Cambio en la entrega previa |
| --- | --- |
| `.env.example` | Configuración de Supabase y sesión, `APP_BASE_URL`, depuración desactivada, `KEEP_ALIVE=False`, cuotas explícitas y retirada del código compartido. Los niveles de pensamiento se escriben explícitamente como `high`/`medium`, coincidiendo con los valores de la clase de configuración. |
| `PROMPT_PARA_CLAUDE.md` | Sustituye las instrucciones de mantenimiento por la arquitectura integrada, rutas, sesión y límites reales. **No es el prompt que recibe Gemini.** |
| `README.md` | Documentación de instalación, configuración, separación pública/privada, funciones, alcance y verificación de la entrega. |
| `app/config.py` | Versión 3.0.0; origen público, registro opcional y duración de cookie validada entre 60 y 86.400 segundos; código compartido marcado obsoleto. |
| `app/main.py` | Rutas públicas/privadas, comprobación general de API, cabeceras y montaje de recursos públicos. |
| `app/routers/auth.py` | Puente de sesión, configuración pública actualizada y manejo explícito de fallos de exportación/baja. |
| `app/routers/documents.py` | Salud pública reducida, diagnóstico privado y auditoría sin escritura automática del catálogo. |
| `app/services/gemini_service.py` | **Únicamente añade `import contextlib`**; no modifica selección de modelos, prompts ni lógica de redacción. |
| `app/services/limites.py` | Sustituye las alternativas de acceso por validación Bearer obligatoria; conserva el algoritmo de cuotas. |
| `app/services/supabase_service.py` | Validación real, caché acotada, exportación paginada con RLS y baja comprobada. |
| `app/static/index.html` → `app/private/generador.html` | Reubicación y cambios de sesión, almacenamiento, respaldo/recuperación y cuenta descritos arriba. La antigua ruta aloja la portada nueva. |
| `render.yaml` | Python 3.12.14 en lugar de 3.13.5; `runtime`, constraints, comprobación de salud y variables de sesión/Supabase. Groq pasa a configuración opcional manual. No cambia los nombres de modelos Gemini. |
| `requirements-dev.txt` | Añade `pytest-asyncio>=1.0`. |
| `scripts/build_catalog.py` | Usa la ruta privada, Node y delimitadores semánticos; bloquea la extracción sobre un catálogo dinámico para no sobrescribir los JSON canónicos. |
| `scripts/evaluar.py` | Evaluación real con token explícito; simulación sin red/IA; errores sin exponer tokens y reportes que distinguen simulación de validación real. |
| `scripts/update_index_html.py` | Corrige ruta absoluta heredada y bloquea la reaplicación de esta migración histórica sobre v3. |
| `scripts/update_verificador_frontend.py` | Igual protección para la migración histórica del verificador. |
| `supabase/schema.sql` | Funciones, triggers, permisos RLS y reglas de Storage descritos en el apartado 6. |
| `supabase/migrations/20261022000000_supabase_auth_db_storage.sql` | Pasa del enlace psql a un esquema inicial autocontenido. Gran parte de su aumento es copia del esquema, no otro motor nuevo. |

### Los 15 archivos de pruebas originales modificados

| Archivo | Ajuste |
| --- | --- |
| `tests/test_auditor.py` | Ruta del auditor privado y ejecución de JavaScript con Node en lugar de `osascript`. |
| `tests/test_auditor_catalogo.py` | Solicitudes autenticadas mediante fixture. |
| `tests/test_auth_supabase.py` | Rechaza tokens ficticios; usa sustitutos explícitos de proveedor en las pruebas de rutas, exportación y baja; comprueba `/app`. |
| `tests/test_backend.py` | Autenticación explícita, rechazo del código compartido y nuevo contrato de salud. |
| `tests/test_browser_dictado.py` | La prueba heredada de Chrome/macOS queda condicionada a macOS y habilitación explícita; no se presenta como ejecutada en otros entornos. |
| `tests/test_calculos.py` | Autenticación explícita para las llamadas a API. |
| `tests/test_comparador_versiones.py` | Autenticación explícita para las llamadas a API. |
| `tests/test_evaluar.py` | Pruebas nuevas del token, simulación sin red y etiquetado honesto del reporte. |
| `tests/test_extraer.py` | Autenticación y consulta del generador en `/app`. |
| `tests/test_nit_radicado_letras.py` | Auditor privado, ejecución Node y autenticación de API. |
| `tests/test_plazos.py` | Autenticación explícita para las llamadas a API. |
| `tests/test_prompt.py` | Referencia JavaScript ejecutada con Node, fecha UTC y autenticación. La referencia y el constructor de prompts no cambian. |
| `tests/test_radicacion.py` | Autenticación explícita para las llamadas a API. |
| `tests/test_revisar.py` | Autenticación explícita para las llamadas a API. |
| `tests/test_verificar_citas.py` | Autenticación explícita para las llamadas a API. |

Cambiar la preparación de una prueba no significa que se hayan cambiado los cálculos o reglas que verifica. Los nuevos archivos de pruebas de seguridad, datos, cliente de sesión, asesor y PWA figuran por separado en el inventario JSON.

## 8. Qué quedó idéntico

La comparación byte a byte confirma lo siguiente:

- **Los 35 JSON de `app/catalogo/`:** 26 tipos de escritos y 9 archivos de áreas, calendario judicial, contexto normativo, formato, grupo de redacción, IPC, radicado, reglas obligatorias y tasas SFC. No se añadieron ni retiraron tipos profesionales respecto del original.
- **`app/services/prompt.py`** y **`tests/reference_prompt.js`**: constructor del prompt y referencia de equivalencia.
- **`app/private/auditor.js`**, idéntico al anterior `app/static/auditor.js`.
- Los servicios `auditor_catalogo.py`, `auditor_fidelidad.py`, `calculos.py`, `comparador_versiones.py`, `extractor_documentos.py`, `nit.py`, `numeros_letras.py`, `plazos.py`, `radicacion.py`, `radicado.py`, `revisor_requisitos.py` y `verificador_citas.py`.
- **`app/routers/calculos.py`**: contenido intacto; cambia el acceso efectivo por el middleware del servidor.
- **Los 26 archivos de `tests/casos/`, con 78 casos**, `scripts/build_test_cases.py`, `requirements.txt`, `pytest.ini` y los tres archivos `__init__.py` originales.

Los valores de modelos y límites de generación existentes en `app/config.py` también se conservan. La selección de `gemini-3.8-flash`, `gemini-4-argon`, sus alternativas, el límite de salida y la lógica de continuaciones no se reemplazaron por otra configuración de IA en esta entrega.

Conservar el contenido de un archivo no conserva necesariamente su acceso anónimo: por ejemplo, los cálculos y el catálogo intactos quedan detrás de la nueva autenticación. Tampoco implica que las respuestas de un proveedor de IA sean idénticas entre ejecuciones.

## 9. Archivos nuevos y artefactos generados

Los 66 archivos nuevos, identificados individualmente en el JSON, se agrupan en:

- Portada y asesor ciudadano: datos, motor, interfaz, estilos, páginas de lectura y recursos visuales. No reemplazan el catálogo profesional.
- Acceso profesional: página y estilos de login, cliente de sesión, servicio de cookies y SDK de Supabase con su licencia.
- PWA y copia autónoma: scripts de construcción, worker, manifiesto, iconos y HTML generado.
- Instalación: `Dockerfile`, `.dockerignore`, `.gitignore` y `constraints.txt`. Las dependencias directas de `requirements.txt` no cambian, pero Render/Docker instalan bajo las versiones fijadas en constraints.
- Documentación, migración de aislamiento y pruebas adicionales.

`app/data/asesor_paginas.json`, el shell/worker de PWA y la copia HTML sin internet son salidas generadas. Su tamaño no representa una reescritura del generador profesional.

El ZIP previo también contiene **`citas_cache.sqlite3`**, una caché generada. Se incluye en el inventario porque efectivamente estaba dentro del archivo; no se cuenta como catálogo ni código del generador. Su copia extraída puede cambiar al ejecutar pruebas: el hash registrado es el del ZIP. Para una entrega limpia de código debe excluirse este artefacto.

## 10. Alcance de la comprobación

Esta auditoría acredita qué archivos y fragmentos cambiaron entre dos entregas concretas. No ejecutó migraciones, no inició sesión en un proyecto real de Supabase, no llamó a Gemini ni verificó un despliegue. Las nuevas integraciones se deben revisar separadamente y conservar este documento como registro de la entrega previa.

Los cambios más relevantes para quien ya usa el generador son: acceso obligatorio, datos locales separados por cuenta, recuperación del legado mediante copia explícita, respaldo remoto sin duplicados por guardado, exportación con alcance declarado y baja de cuenta con controles sobre datos compartidos.
