-- =============================================================================
-- FASE 2.3.2: UPSERT ATÓMICO Y PROTECCIÓN CONTRA DUPLICADOS EN SUPABASE
-- 1. Función de normalización e identidad canónica de providencias judiciales
-- 2. Columna 'identificador_canonico' y restricción UNIQUE en ambas tablas
-- 3. Triggers para auto-asignación y consistencia del identificador canónico
-- 4. RPC 'despacho_upsert_descubrimiento': Upsert atómico para providencias descubiertas
-- 5. RPC 'despacho_upsert_providencia_corpus_atomico': Ingesta, validación y sincronización transaccional
-- 6. Actualización de 'despacho_actualizar_validacion_documento' para sincronizar descubrimientos
-- 7. Wrapper retrocompatible para 'despacho_publicar_documento_corpus'
-- 8. Permisos de seguridad y RLS
-- =============================================================================

BEGIN;

-- 1. Función de normalización canónica de providencias judiciales
CREATE OR REPLACE FUNCTION public.despacho_normalizar_identificador_canonico(
  p_source text,
  p_sentencia text
)
RETURNS text
LANGUAGE plpgsql IMMUTABLE STRICT AS $$
DECLARE
  v_source text;
  v_clean text;
  v_parts text[];
  v_tipo text;
  v_num integer;
  v_year_str text;
  v_year integer;
BEGIN
  v_source := lower(trim(coalesce(p_source, 'constitucional')));
  IF v_source = '' THEN
    v_source := 'constitucional';
  END IF;
  
  v_clean := upper(trim(coalesce(p_sentencia, '')));
  
  -- Expresión regular para capturar Tipo (T, C, SU, A), Número y Año (2 o 4 dígitos)
  -- Soporta variantes como: T-100/24, T-100-24, T 100/2024, t-028/23, C-083/95, SU-073/20, A-012/23
  v_parts := regexp_matches(v_clean, '(T|C|SU|A)[-\s]?([0-9]{1,5})[\s\/\-]([0-9]{2,4})');
  IF v_parts IS NOT NULL AND array_length(v_parts, 1) = 3 THEN
    v_tipo := v_parts[1];
    v_num := v_parts[2]::integer;
    v_year_str := v_parts[3];
    IF length(v_year_str) = 2 THEN
      IF v_year_str::integer >= 90 THEN
        v_year := 1900 + v_year_str::integer;
      ELSE
        v_year := 2000 + v_year_str::integer;
      END IF;
    ELSE
      v_year := v_year_str::integer;
    END IF;
    RETURN v_source || ':' || v_tipo || '-' || v_num::text || '-' || v_year::text;
  END IF;
  
  -- Fallback seguro en caso de formatos no estándar
  RETURN v_source || ':' || regexp_replace(v_clean, '\s+', '_', 'g');
END;
$$;


-- 2. Añadir columna identificador_canonico y restricciones UNIQUE

-- 2.1 En despacho_conector_descubrimientos
ALTER TABLE public.despacho_conector_descubrimientos
  ADD COLUMN IF NOT EXISTS identificador_canonico text;

-- Poblar valores existentes con la función de normalización
UPDATE public.despacho_conector_descubrimientos
SET identificador_canonico = public.despacho_normalizar_identificador_canonico(
  COALESCE(metadata->>'source_id', 'constitucional'),
  sentencia
)
WHERE identificador_canonico IS NULL;

-- Asignar NOT NULL
ALTER TABLE public.despacho_conector_descubrimientos
  ALTER COLUMN identificador_canonico SET NOT NULL;

-- Restricción UNIQUE en identificador_canonico
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'despacho_conector_descubrimientos_canonico_key'
  ) THEN
    ALTER TABLE public.despacho_conector_descubrimientos
      ADD CONSTRAINT despacho_conector_descubrimientos_canonico_key UNIQUE (identificador_canonico);
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_descubrimientos_canonico
  ON public.despacho_conector_descubrimientos(identificador_canonico);


-- 2.2 En despacho_corpus_documentos
ALTER TABLE public.despacho_corpus_documentos
  ADD COLUMN IF NOT EXISTS identificador_canonico text;

-- Poblar valores existentes
UPDATE public.despacho_corpus_documentos
SET identificador_canonico = public.despacho_normalizar_identificador_canonico(
  source_id,
  COALESCE(metadata->>'sentencia', title)
)
WHERE identificador_canonico IS NULL;

-- Asignar NOT NULL
ALTER TABLE public.despacho_corpus_documentos
  ALTER COLUMN identificador_canonico SET NOT NULL;

-- Restricción UNIQUE en identificador_canonico
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'despacho_corpus_documentos_canonico_key'
  ) THEN
    ALTER TABLE public.despacho_corpus_documentos
      ADD CONSTRAINT despacho_corpus_documentos_canonico_key UNIQUE (identificador_canonico);
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_corpus_doc_canonico
  ON public.despacho_corpus_documentos(identificador_canonico);


-- 3. Triggers para asegurar identificador canónico automático en ambas tablas
CREATE OR REPLACE FUNCTION public.trg_fn_set_descubrimiento_canonico()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.identificador_canonico IS NULL OR NEW.identificador_canonico = '' THEN
    NEW.identificador_canonico := public.despacho_normalizar_identificador_canonico('constitucional', NEW.sentencia);
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_despacho_descubrimientos_canonico ON public.despacho_conector_descubrimientos;
CREATE TRIGGER trg_despacho_descubrimientos_canonico
  BEFORE INSERT OR UPDATE OF sentencia ON public.despacho_conector_descubrimientos
  FOR EACH ROW EXECUTE FUNCTION public.trg_fn_set_descubrimiento_canonico();

CREATE OR REPLACE FUNCTION public.trg_fn_set_corpus_doc_canonico()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.identificador_canonico IS NULL OR NEW.identificador_canonico = '' THEN
    NEW.identificador_canonico := public.despacho_normalizar_identificador_canonico(
      NEW.source_id,
      COALESCE(NEW.metadata->>'sentencia', NEW.title)
    );
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_despacho_corpus_doc_canonico ON public.despacho_corpus_documentos;
CREATE TRIGGER trg_despacho_corpus_doc_canonico
  BEFORE INSERT OR UPDATE OF metadata, title, source_id ON public.despacho_corpus_documentos
  FOR EACH ROW EXECUTE FUNCTION public.trg_fn_set_corpus_doc_canonico();


-- 4. RPC: despacho_upsert_descubrimiento
-- Inserción / actualización atómica de providencias descubiertas protegiendo contra condiciones de carrera
CREATE OR REPLACE FUNCTION public.despacho_upsert_descubrimiento(
  p_data jsonb,
  p_fencing_token integer DEFAULT NULL
)
RETURNS jsonb
LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $$
DECLARE
  v_canonico text;
  v_sentencia text;
  v_source_id text;
  v_tipo text;
  v_anio integer;
  v_fecha text;
  v_magistrado text;
  v_sala text;
  v_expediente text;
  v_proceso text;
  v_tema text;
  v_dataset text;
  v_source_url text;
  v_source_status text;
  v_last_error text;
  v_doc_id uuid;
  v_metadata jsonb;
  v_curr_token integer;
  v_rec public.despacho_conector_descubrimientos;
  v_is_new boolean := false;
BEGIN
  IF auth.role() <> 'service_role' THEN
    RAISE EXCEPTION 'No autorizado.' USING ERRCODE = '42501';
  END IF;

  -- Validación de fencing token si fue provisto
  IF p_fencing_token IS NOT NULL THEN
    SELECT lock_fencing_token INTO v_curr_token
    FROM public.despacho_conector_corte_estado
    WHERE id = 'corte_constitucional';

    IF v_curr_token IS NOT NULL AND v_curr_token <> p_fencing_token THEN
      RAISE EXCEPTION 'Operación rechazada: el fencing token provisto (%) no coincide con el bloqueo activo (%).', p_fencing_token, v_curr_token
        USING ERRCODE = '55P03';
    END IF;
  END IF;

  v_sentencia := trim(upper(COALESCE(p_data->>'sentencia', '')));
  IF v_sentencia = '' THEN
    RAISE EXCEPTION 'Campo sentencia obligatorio.' USING ERRCODE = '22023';
  END IF;

  v_source_id := COALESCE(p_data->>'source_id', 'constitucional');
  v_canonico := public.despacho_normalizar_identificador_canonico(v_source_id, v_sentencia);

  -- Bloqueo consultivo transaccional a nivel de identificador canónico para evitar condiciones de carrera en inserciones simultáneas
  PERFORM pg_advisory_xact_lock(hashtext(v_canonico));

  v_tipo := COALESCE(p_data->>'tipo', CASE WHEN v_sentencia LIKE 'T-%' THEN 'T' WHEN v_sentencia LIKE 'C-%' THEN 'C' WHEN v_sentencia LIKE 'SU-%' THEN 'SU' ELSE 'A' END);
  v_fecha := p_data->>'fecha';
  v_anio := COALESCE((p_data->>'anio')::integer, CASE WHEN v_fecha ~ '^[0-9]{4}' THEN substring(v_fecha from 1 for 4)::integer ELSE NULL END);
  v_magistrado := p_data->>'magistrado';
  v_sala := p_data->>'sala';
  v_expediente := COALESCE(p_data->>'expediente', p_data->>'radicado');
  v_proceso := p_data->>'proceso';
  v_tema := COALESCE(p_data->>'tema', p_data->>'materia');
  v_dataset := COALESCE(p_data->>'source_dataset', 'v2k4-2t8s');
  v_source_url := p_data->>'source_url';
  v_source_status := COALESCE(p_data->>'source_status', 'discovered');
  v_last_error := p_data->>'last_error';
  v_metadata := COALESCE(p_data->'metadata', '{}'::jsonb);
  IF p_data->>'document_id' IS NOT NULL AND p_data->>'document_id' ~ '^[0-9a-f-]{36}$' THEN
    v_doc_id := (p_data->>'document_id')::uuid;
  END IF;

  -- Comprobar si ya existe previamente con bloqueo de fila
  SELECT * INTO v_rec FROM public.despacho_conector_descubrimientos
  WHERE identificador_canonico = v_canonico FOR UPDATE;

  IF NOT FOUND THEN
    v_is_new := true;
    INSERT INTO public.despacho_conector_descubrimientos (
      sentencia, tipo, anio, fecha, magistrado, sala, expediente, proceso, tema,
      source_dataset, source_url, source_status, last_error, first_discovered_at,
      last_checked_at, document_id, metadata, identificador_canonico
    ) VALUES (
      v_sentencia, v_tipo, v_anio, v_fecha, v_magistrado, v_sala, v_expediente, v_proceso, v_tema,
      v_dataset, v_source_url, v_source_status, v_last_error, now(), now(),
      v_doc_id, v_metadata, v_canonico
    ) RETURNING * INTO v_rec;
  ELSE
    -- Actualizar preservando estados publicados y document_id existente
    UPDATE public.despacho_conector_descubrimientos SET
      sentencia = v_sentencia,
      tipo = COALESCE(v_tipo, v_rec.tipo),
      anio = COALESCE(v_anio, v_rec.anio),
      fecha = COALESCE(v_fecha, v_rec.fecha),
      magistrado = COALESCE(v_magistrado, v_rec.magistrado),
      sala = COALESCE(v_sala, v_rec.sala),
      expediente = COALESCE(v_expediente, v_rec.expediente),
      proceso = COALESCE(v_proceso, v_rec.proceso),
      tema = COALESCE(v_tema, v_rec.tema),
      source_url = COALESCE(v_source_url, v_rec.source_url),
      source_status = CASE
        WHEN v_rec.source_status = 'published' THEN 'published'
        WHEN v_rec.document_id IS NOT NULL AND v_source_status IN ('discovered', 'pending_source') THEN v_rec.source_status
        ELSE v_source_status
      END,
      document_id = COALESCE(v_doc_id, v_rec.document_id),
      last_error = CASE WHEN v_source_status IN ('validation_failed', 'pending_source') THEN v_last_error ELSE v_rec.last_error END,
      last_checked_at = now(),
      metadata = v_rec.metadata || v_metadata
    WHERE id = v_rec.id
    RETURNING * INTO v_rec;
  END IF;

  RETURN jsonb_build_object(
    'id', v_rec.id,
    'sentencia', v_rec.sentencia,
    'identificador_canonico', v_rec.identificador_canonico,
    'source_status', v_rec.source_status,
    'document_id', v_rec.document_id,
    'is_new', v_is_new
  );
END;
$$;


-- 5. RPC: despacho_upsert_providencia_corpus_atomico
-- Ingesta, validación y sincronización atómica entre corpus, fragmentos, descubrimientos y auditoría
CREATE OR REPLACE FUNCTION public.despacho_upsert_providencia_corpus_atomico(
  p_source_id text,
  p_source_url text,
  p_title text,
  p_sentencia text,
  p_hash text,
  p_chunks jsonb,
  p_metadata jsonb,
  p_workflow_status text DEFAULT 'pending_legal_review',
  p_published boolean DEFAULT false,
  p_finalize boolean DEFAULT false,
  p_fencing_token integer DEFAULT NULL,
  p_responsible_id text DEFAULT 'validador_automatico',
  p_responsible_role text DEFAULT 'sistema',
  p_responsible_name text DEFAULT 'Motor Determinista de Validación (10 Puntos)',
  p_force_version_bump boolean DEFAULT false
)
RETURNS jsonb
LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $$
DECLARE
  v_canonico text;
  v_curr_token integer;
  d public.despacho_corpus_documentos;
  row_chunk jsonb;
  ordinal_no integer := 0;
  chunk_ord integer;
  chunk_seg integer;
  current_segments integer := 0;
  v_target_pub boolean;
  v_target_workflow text;
  v_op text;
  v_prev_version integer := 0;
  v_new_version integer := 1;
BEGIN
  IF auth.role() <> 'service_role' THEN
    RAISE EXCEPTION 'No autorizado.' USING ERRCODE = '42501';
  END IF;

  -- Validación de fencing token si fue provisto
  IF p_fencing_token IS NOT NULL THEN
    SELECT lock_fencing_token INTO v_curr_token
    FROM public.despacho_conector_corte_estado
    WHERE id = 'corte_constitucional';

    IF v_curr_token IS NOT NULL AND v_curr_token <> p_fencing_token THEN
      RAISE EXCEPTION 'Operación rechazada: fencing token provisto (%) no coincide con bloqueo activo (%).', p_fencing_token, v_curr_token
        USING ERRCODE = '55P03';
    END IF;
  END IF;

  v_canonico := public.despacho_normalizar_identificador_canonico(p_source_id, p_sentencia);

  -- Bloqueo consultivo transaccional a nivel de identificador canónico para serializar inserciones simultáneas
  PERFORM pg_advisory_xact_lock(hashtext(v_canonico));

  -- Bloquear y verificar si ya existe en despacho_corpus_documentos por identificador canónico o URL
  SELECT * INTO d FROM public.despacho_corpus_documentos
  WHERE identificador_canonico = v_canonico OR source_url = p_source_url
  FOR UPDATE;

  IF FOUND THEN
    v_prev_version := d.version;
    SELECT count(*) INTO current_segments FROM public.despacho_corpus_fragmentos WHERE document_id = d.id;

    -- Caso A: El contenido es IDÉNTICO (mismo hash) y no se fuerza nueva versión
    -- Solo actualización de METADATOS: NO incrementa versión, NO borra fragmentos, NO altera embeddings, NO despublica
    IF d.content_hash = p_hash AND NOT p_force_version_bump THEN
      v_op := 'metadata_synced';
      v_new_version := d.version;
      v_target_pub := CASE WHEN d.published THEN true ELSE (p_published AND p_finalize) END;
      v_target_workflow := CASE WHEN d.published THEN 'published' ELSE p_workflow_status END;

      UPDATE public.despacho_corpus_documentos SET
        identificador_canonico = v_canonico,
        source_id = p_source_id,
        source_url = p_source_url,
        title = p_title,
        metadata = d.metadata || p_metadata || jsonb_build_object('identificador_canonico', v_canonico),
        validation_status = COALESCE(p_metadata->>'validation_status', d.validation_status),
        validation_details = COALESCE(p_metadata->'validation_details', d.validation_details),
        published = v_target_pub,
        workflow_status = v_target_workflow,
        reviewed_at = CASE WHEN v_target_pub AND d.reviewed_at IS NULL THEN now() ELSE d.reviewed_at END,
        integrity_status = CASE WHEN v_target_pub AND d.integrity_status = 'pending' THEN 'complete' ELSE d.integrity_status END
      WHERE id = d.id RETURNING * INTO d;

    ELSE
      -- Caso B: Modificación real de CONTENIDO (nuevo hash) o versionado forzado
      v_op := 'version_bumped';
      v_new_version := d.version + 1;
      -- Si estaba publicada, la nueva versión entra a revisión jurídica
      v_target_pub := false;
      v_target_workflow := 'pending_legal_review';

      UPDATE public.despacho_corpus_documentos SET
        identificador_canonico = v_canonico,
        source_id = p_source_id,
        source_url = p_source_url,
        title = p_title,
        content_hash = p_hash,
        version = v_new_version,
        published = v_target_pub,
        workflow_status = v_target_workflow,
        integrity_status = CASE WHEN p_finalize THEN 'complete' ELSE 'pending' END,
        metadata = d.metadata || p_metadata || jsonb_build_object('identificador_canonico', v_canonico, 'previous_version', v_prev_version),
        validation_status = COALESCE(p_metadata->>'validation_status', 'technically_validated'),
        validation_details = COALESCE(p_metadata->'validation_details', '{}'::jsonb),
        indexed_at = now(),
        reviewed_at = NULL
      WHERE id = d.id RETURNING * INTO d;

      -- Reemplazar fragmentos para la nueva versión
      DELETE FROM public.despacho_corpus_fragmentos WHERE document_id = d.id;

      IF p_chunks IS NOT NULL AND jsonb_typeof(p_chunks) = 'array' THEN
        FOR row_chunk IN SELECT value FROM jsonb_array_elements(p_chunks) LOOP
          chunk_ord := COALESCE((row_chunk->>'ordinal')::integer, ordinal_no);
          chunk_seg := COALESCE((row_chunk->>'segment')::integer, chunk_ord + 1);
          INSERT INTO public.despacho_corpus_fragmentos(
            document_id, document_version, ordinal, segment, content, embedding, embedding_model, section
          ) VALUES (
            d.id, d.version, chunk_ord, chunk_seg, row_chunk->>'content',
            CASE WHEN row_chunk->'embedding' IS NULL OR row_chunk->'embedding' = 'null'::jsonb THEN NULL
              ELSE (row_chunk->>'embedding')::extensions.vector END,
            NULLIF(row_chunk->>'embedding_model', ''),
            COALESCE(row_chunk->>'section', 'seccion_desconocida')
          );
          ordinal_no := ordinal_no + 1;
        END LOOP;
      END IF;

      -- Registrar auditoría por incremento de versión
      INSERT INTO public.despacho_corpus_auditoria_revisiones (
        document_id, document_version, responsible_id, responsible_name, responsible_role,
        review_type, decision, reason, validation_summary,
        previous_workflow_status, new_workflow_status, previous_published, new_published
      ) VALUES (
        d.id, v_new_version, p_responsible_id, p_responsible_name, p_responsible_role,
        'validacion_tecnica_automatica', 'reopen',
        'Nueva versión de contenido detectada (hash modificado). Colocado en revisión.',
        COALESCE(p_metadata->'validation_details', '{}'::jsonb),
        d.workflow_status, v_target_workflow, d.published, v_target_pub
      );
    END IF;

  ELSE
    -- Caso C: INSERCIÓN de nueva providencia (primer ingreso al corpus)
    v_op := 'created';
    v_new_version := 1;
    v_target_pub := (p_published AND p_finalize);
    v_target_workflow := CASE WHEN v_target_pub THEN 'published' ELSE p_workflow_status END;

    INSERT INTO public.despacho_corpus_documentos (
      source_id, source_url, title, content_hash, version,
      published, workflow_status, integrity_status, metadata,
      validation_status, validation_details, identificador_canonico,
      indexed_at, reviewed_at
    ) VALUES (
      p_source_id, p_source_url, p_title, p_hash, 1,
      v_target_pub, v_target_workflow,
      CASE WHEN p_finalize THEN 'complete' ELSE 'pending' END,
      p_metadata || jsonb_build_object('identificador_canonico', v_canonico),
      COALESCE(p_metadata->>'validation_status', 'technically_validated'),
      COALESCE(p_metadata->'validation_details', '{}'::jsonb),
      v_canonico,
      now(),
      CASE WHEN v_target_pub THEN now() ELSE NULL END
    ) RETURNING * INTO d;

    -- Insertar fragmentos iniciales
    IF p_chunks IS NOT NULL AND jsonb_typeof(p_chunks) = 'array' THEN
      FOR row_chunk IN SELECT value FROM jsonb_array_elements(p_chunks) LOOP
        chunk_ord := COALESCE((row_chunk->>'ordinal')::integer, ordinal_no);
        chunk_seg := COALESCE((row_chunk->>'segment')::integer, chunk_ord + 1);
        INSERT INTO public.despacho_corpus_fragmentos(
          document_id, document_version, ordinal, segment, content, embedding, embedding_model, section
        ) VALUES (
          d.id, d.version, chunk_ord, chunk_seg, row_chunk->>'content',
          CASE WHEN row_chunk->'embedding' IS NULL OR row_chunk->'embedding' = 'null'::jsonb THEN NULL
            ELSE (row_chunk->>'embedding')::extensions.vector END,
          NULLIF(row_chunk->>'embedding_model', ''),
          COALESCE(row_chunk->>'section', 'seccion_desconocida')
        );
        ordinal_no := ordinal_no + 1;
      END LOOP;
    END IF;

    -- Auditoría de creación
    INSERT INTO public.despacho_corpus_auditoria_revisiones (
      document_id, document_version, responsible_id, responsible_name, responsible_role,
      review_type, decision, reason, validation_summary,
      previous_workflow_status, new_workflow_status, previous_published, new_published
    ) VALUES (
      d.id, 1, p_responsible_id, p_responsible_name, p_responsible_role,
      'validacion_tecnica_automatica', CASE WHEN v_target_pub THEN 'approve' ELSE 'reject' END,
      CASE WHEN v_target_pub THEN 'Providencia incorporada y publicada con validación 10/10.'
           ELSE 'Providencia validada técnicamente y estadificada en triage.' END,
      COALESCE(p_metadata->'validation_details', '{}'::jsonb),
      'discovered', v_target_workflow, false, v_target_pub
    );
  END IF;

  -- 6. Sincronización atómica inmediata en despacho_conector_descubrimientos
  -- Garantiza que NUNCA exista una providencia en el corpus sin su registro correspondiente en descubrimientos
  INSERT INTO public.despacho_conector_descubrimientos (
    sentencia, tipo, anio, fecha, magistrado, sala, expediente, proceso, tema,
    source_dataset, source_url, source_status, document_id, identificador_canonico,
    first_discovered_at, last_checked_at, metadata
  ) VALUES (
    upper(trim(p_sentencia)),
    COALESCE(p_metadata->>'tipo', substring(upper(trim(p_sentencia)) from '^(T|C|SU|A)'), 'T'),
    COALESCE((p_metadata->>'anio')::integer, CASE WHEN p_metadata->>'fecha' ~ '^[0-9]{4}' THEN substring(p_metadata->>'fecha' from 1 for 4)::integer ELSE NULL END),
    p_metadata->>'fecha',
    p_metadata->>'magistrado',
    p_metadata->>'sala',
    COALESCE(p_metadata->>'expediente', p_metadata->>'radicado'),
    p_metadata->>'proceso',
    COALESCE(p_metadata->>'materia', p_metadata->>'tema'),
    'relatoria_oficial',
    p_source_url,
    CASE WHEN d.published THEN 'published' ELSE 'technically_validated' END,
    d.id,
    v_canonico,
    now(),
    now(),
    jsonb_build_object('source_id', p_source_id)
  )
  ON CONFLICT (identificador_canonico) DO UPDATE SET
    document_id = d.id,
    source_url = p_source_url,
    source_status = CASE
      WHEN despacho_conector_descubrimientos.source_status = 'published' THEN 'published'
      WHEN d.published THEN 'published'
      ELSE 'technically_validated'
    END,
    magistrado = COALESCE(EXCLUDED.magistrado, despacho_conector_descubrimientos.magistrado),
    sala = COALESCE(EXCLUDED.sala, despacho_conector_descubrimientos.sala),
    expediente = COALESCE(EXCLUDED.expediente, despacho_conector_descubrimientos.expediente),
    proceso = COALESCE(EXCLUDED.proceso, despacho_conector_descubrimientos.proceso),
    tema = COALESCE(EXCLUDED.tema, despacho_conector_descubrimientos.tema),
    anio = COALESCE(EXCLUDED.anio, despacho_conector_descubrimientos.anio),
    fecha = COALESCE(EXCLUDED.fecha, despacho_conector_descubrimientos.fecha),
    last_checked_at = now();

  RETURN jsonb_build_object(
    'id', d.id,
    'version', d.version,
    'unchanged', (v_op = 'metadata_synced'),
    'operation', v_op,
    'identificador_canonico', v_canonico,
    'segments', CASE WHEN v_op = 'metadata_synced' THEN current_segments ELSE ordinal_no END,
    'published', d.published,
    'workflow_status', d.workflow_status
  );
END;
$$;


-- 6. Actualización de despacho_actualizar_validacion_documento
CREATE OR REPLACE FUNCTION public.despacho_actualizar_validacion_documento(
  p_document_id uuid,
  p_validation_status text,
  p_validation_details jsonb,
  p_workflow_status text DEFAULT NULL,
  p_published boolean DEFAULT NULL
)
RETURNS jsonb
LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $$
DECLARE
  d public.despacho_corpus_documentos;
  v_new_workflow text;
  v_new_pub boolean;
BEGIN
  IF auth.role() <> 'service_role' THEN
    RAISE EXCEPTION 'No autorizado.' USING ERRCODE = '42501';
  END IF;

  SELECT * INTO d FROM public.despacho_corpus_documentos WHERE id = p_document_id FOR UPDATE;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'Documento no encontrado.' USING ERRCODE = 'P0002';
  END IF;

  v_new_workflow := COALESCE(p_workflow_status, d.workflow_status);
  v_new_pub := COALESCE(p_published, d.published);

  IF p_validation_status = 'validation_failed' THEN
    v_new_pub := false;
    IF v_new_workflow = 'published' THEN
      v_new_workflow := 'pending_legal_review';
    END IF;
  END IF;

  UPDATE public.despacho_corpus_documentos SET
    validation_status = p_validation_status,
    validation_details = p_validation_details,
    workflow_status = v_new_workflow,
    published = v_new_pub,
    integrity_status = CASE WHEN v_new_pub AND d.integrity_status = 'pending' THEN 'complete' ELSE d.integrity_status END,
    reviewed_at = CASE WHEN v_new_pub THEN COALESCE(reviewed_at, now()) ELSE reviewed_at END
  WHERE id = p_document_id
  RETURNING * INTO d;

  -- Sincronizar automáticamente despacho_conector_descubrimientos
  UPDATE public.despacho_conector_descubrimientos SET
    source_status = CASE
      WHEN v_new_pub THEN 'published'
      WHEN p_validation_status = 'validation_failed' THEN 'validation_failed'
      ELSE 'technically_validated'
    END,
    last_checked_at = now()
  WHERE document_id = p_document_id;

  RETURN jsonb_build_object(
    'id', d.id,
    'validation_status', d.validation_status,
    'workflow_status', d.workflow_status,
    'published', d.published,
    'integrity_status', d.integrity_status
  );
END;
$$;


-- 7. Wrapper retrocompatible para despacho_publicar_documento_corpus
CREATE OR REPLACE FUNCTION public.despacho_publicar_documento_corpus(
  p_source_id text,
  p_source_url text,
  p_title text,
  p_hash text,
  p_chunks jsonb,
  p_metadata jsonb DEFAULT '{}'::jsonb,
  p_finalize boolean DEFAULT false
)
RETURNS jsonb
LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $$
DECLARE
  v_sentencia text;
  v_pub boolean;
  v_wf text;
BEGIN
  IF auth.role() <> 'service_role' THEN
    RAISE EXCEPTION 'No autorizado.' USING ERRCODE = '42501';
  END IF;

  v_sentencia := COALESCE(p_metadata->>'sentencia', p_title);
  v_pub := (p_finalize AND COALESCE((p_metadata->>'published')::boolean, true));
  v_wf := CASE WHEN v_pub THEN 'published' ELSE 'technically_validated' END;

  RETURN public.despacho_upsert_providencia_corpus_atomico(
    p_source_id := p_source_id,
    p_source_url := p_source_url,
    p_title := p_title,
    p_sentencia := v_sentencia,
    p_hash := p_hash,
    p_chunks := p_chunks,
    p_metadata := p_metadata,
    p_workflow_status := v_wf,
    p_published := v_pub,
    p_finalize := p_finalize,
    p_fencing_token := NULL
  );
END;
$$;


-- 8. Permisos de seguridad y RLS
REVOKE ALL ON FUNCTION public.despacho_normalizar_identificador_canonico(text, text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.despacho_normalizar_identificador_canonico(text, text) TO authenticated, service_role;

REVOKE ALL ON FUNCTION public.despacho_upsert_descubrimiento(jsonb, integer) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.despacho_upsert_descubrimiento(jsonb, integer) TO service_role;

REVOKE ALL ON FUNCTION public.despacho_upsert_providencia_corpus_atomico(text, text, text, text, text, jsonb, jsonb, text, boolean, boolean, integer, text, text, text, boolean) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.despacho_upsert_providencia_corpus_atomico(text, text, text, text, text, jsonb, jsonb, text, boolean, boolean, integer, text, text, text, boolean) TO service_role;

REVOKE ALL ON FUNCTION public.despacho_actualizar_validacion_documento(uuid, text, jsonb, text, boolean) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.despacho_actualizar_validacion_documento(uuid, text, jsonb, text, boolean) TO service_role;

REVOKE ALL ON FUNCTION public.despacho_publicar_documento_corpus(text, text, text, text, jsonb, jsonb, boolean) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.despacho_publicar_documento_corpus(text, text, text, text, jsonb, jsonb, boolean) TO service_role;

COMMIT;
