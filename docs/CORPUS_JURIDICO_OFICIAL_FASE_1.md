# El Memorialista · Fuentes jurídicas oficiales — fase 1

**Estado:** implementación incremental para integrar en el proyecto ya desplegado; no modifica el generador de escritos, el modo «Biblioteca: automática», el modelo principal de Gemini ni los trabajadores existentes. **No desplegado en Render ni aplicado a Supabase desde este entorno.**

## Qué se entrega en esta fase

- **Directorio de 43 colecciones**: las 41 enumeradas por el propietario, más SUIN-Juriscol y Función Pública. No significa que estén indexadas; los portales marcados como «pendiente» no tienen conector automatizado validado.
- **Conector real de metadatos de la Corte Constitucional** por el conjunto de datos público oficial `v2k4-2t8s` de datos.gov.co. Busca por número de sentencia, ponente, sala o proceso. **No busca asuntos jurídicos en el texto**: el dataset solo dispone de campos estadísticos. La sentencia completa deberá consultarse por separado en la Relatoría.
- **Corpus oficial compartido de El Memorialista**, separado del DMS y de los escritos privados: tablas con controles RLS, indexación textual y vectorial opcional, búsqueda híbrida y cobertura real (puede comenzar en cero).
- **Carga administrativa puntual** de un documento público desde una URL permitida y revisada. Exige confirmación expresa de condiciones de uso, privacidad y revisión del contenido. Repetir la misma versión no duplica registros y la actualización reemplaza fragmentos de forma atómica.
- **Pestaña «Corpus jurídico oficial»** dentro de Jurisprudencia, sin alterar «Investigar con IA», «Mi biblioteca jurídica» ni «Chat jurídico».

## Límite de la primera fase

No se descargaron ni indexaron automáticamente las sentencias de las 43 colecciones. Sólo hay **un conector de metadatos** y un mecanismo genérico de incorporación manual autorizado por administrador. Ni los 29.500 registros estadísticos, ni los textos completos, ni los portales internacionales se copian al servidor por instalar este parche.

No contiene contenido, índices, código ni credenciales de Magnar. La meta es una biblioteca jurídica propia, con fuentes autorizadas, no una copia de su base comercial.

## Cómo integrar de forma segura en Antigravity

1. Crea una rama y un respaldo de Supabase. Conserva `.env`, secretos y todo el código que Antigravity haya modificado después del ZIP de referencia.
2. Revisa `CAMBIOS_CODIGO.patch` con `git apply --check` sobre una rama de prueba. Si muestra conflictos (porque el proyecto ya cambió), fusiona por funciones; **no reemplaces `despacho.js` ni `main.py` íntegros**.
3. Conserva estos nuevos archivos: `app/services/despacho_corpus_fuentes.py`, `app/routers/despacho_corpus_fuentes.py`, `scripts/ingestar_corpus_juridico.py`, la migración SQL y sus pruebas.
4. Añade el `include_router` al servidor y la pestaña opcional en Jurisprudencia. La nueva API `GET /api/despacho/official/sources` exige sesión; el dataset público se consulta desde el servidor sin compartir JWT con datos.gov.co.
5. En un entorno Supabase **de pruebas**, aplica `supabase/migrations/20261023130000_corpus_juridico_compartido.sql` DESPUÉS de las anteriores. Verifica `pgvector` y que un usuario `authenticated` sólo pueda **leer** documentos revisados; ningún usuario debe poder **escribir** ni cambiar el estado `published`.
6. Despliega con las variables EXISTENTES. La búsqueda textual del corpus no necesita Google Search de pago. Los embeddings opcionales reutilizan el servicio ya configurado y consumen cuota de Gemini.
7. Comprueba en la pantalla Jurisprudencia → «Corpus jurídico oficial»: (a) catálogo con estados veraces, (b) consulta `T-100/24` en el dataset de Corte Constitucional, (c) cobertura del corpus inicialmente cero, (d) seguridad de acceso sin sesión y (e) búsqueda del contenido de un documento revisado que hayas incorporado.
8. Para incorporar un solo documento *después de verificar* permisos de reutilización y ausencia de datos personales que no deban redistribuirse, el administrador del servidor puede ejecutar:

```bash
python scripts/ingestar_corpus_juridico.py \
  --source-id constitucional \
  --url 'https://www.corteconstitucional.gov.co/relatoria/2024/T-100-24.htm' \
  --title 'Sentencia T-100/24' \
  --ack-rights-review --ack-privacy-review --ack-content-review
```

Es **solo un ejemplo** de URL oficial que debe revisarse; no es una orden de importación automática. Añadir `--semantic` sólo tras confirmar cuota y permiso para procesar el contenido con el proveedor de embeddings. El script exige `SUPABASE_SERVICE_ROLE_KEY` solo en servidor.

## Fuentes de verificación (23/10/2026)

- Dataset oficial de metadatos de sentencias, Corte Constitucional, Datos Abiertos Colombia: https://www.datos.gov.co/Justicia-y-Derecho/Sentencias-proferidas-por-la-Corte-Constitucional/v2k4-2t8s
- Formato oficial de API Socrata, SODA: https://support.socrata.com/hc/en-us/articles/202949298-Where-do-I-find-the-SODA-API-Endpoint
- Consejo de Estado, consulta de jurisprudencia: https://consejodeestado.gov.co/buscador-de-jurisprudencia2/
- Consejo de Estado, «Mi Relatoría» / SAMAI: https://samaijca.consejodeestado.gov.co/TitulacionRelatoria/BuscadorProvidenciasTituladas.aspx
- Colombia Compra Eficiente, Relatoría: https://www.colombiacompra.gov.co/normativa-y-relatoria/conoce-la-relatoria
- Función Pública, Gestor Normativo: https://www.funcionpublica.gov.co/eva/gestornormativo/consulta_avanzada.php

Los enlaces son fuentes públicas de consulta; **no constituyen autorización indiscriminada de extracción masiva, almacenamiento, redistribución o reutilización comercial**. Validar licencia, robots, restricciones, calidad, datos sensibles y condiciones de cada fuente antes de automatizar.

## Próximas fases (no están implementadas aquí)

1. Automatizar la extracción de cada fuente viable mediante API/feeds permitidos y checkpoints persistentes, con frecuencia, reglas de actualización, licencias y monitoreo.
2. Separar decisiones, actos y normativa por materia/fecha/órgano, con tesauros y búsqueda por temas, jurisprudencia vinculada y control temporal de vigencia.
3. Integrar el corpus revisado en el **Agente** mediante RAG con citas exactas a fragmentos; actualmente se puede **preparar manualmente un fragmento** para el Agente, pero no se añade automáticamente al contexto del chat.
4. Implementar panel de administración de lotes, fuentes con errores, opt-out, revisión humana, deduplicación global, políticas de eliminación y acuerdos de uso comercial.
5. Desarrollar conectores independientes de juzgados y bases internacionales donde exista acceso automatizado permitido, respetando restricciones, privacidad y límites.

## Pruebas y límites de la verificación

Las pruebas Python del módulo usan respuestas simuladas para Socrata, Supabase y embeddings. En este entorno no fue posible consultar directamente el API de datos.gov.co ni una instancia Supabase real. **No confundir compilación/pruebas de contrato con funcionamiento probado en producción**. El proyecto debe ejecutar una consulta real y comprobar RLS antes de anunciar el corpus como conectado.
