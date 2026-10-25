-- =============================================================================
-- FASE 2.3.2+: PRESERVACIÓN HISTÓRICA INMUTABLE DE VERSIONES Y CITAS JURÍDICAS
-- 1. Tabla 'despacho_corpus_documentos_historicos' para archivo de metadatos y hash
-- 2. Tabla 'despacho_corpus_fragmentos_historicos' para preservar fragmentos antiguos
-- 3. Actualización de 'despacho_upsert_providencia_corpus_atomico' para archivar
--    automáticamente antes de cualquier reemplazo de fragmentos por cambio de hash
-- 4. Seguridad RLS y permisos
-- =============================================================================

BEGIN;

-- 1. Tabla histórica de documentos (versiones anteriores)
CREATE TABLE IF NOT EXISTS public.despacho_corpus_documentos_historicos (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  document_id uuid NOT NULL REFERENCES public.despacho_corpus_documentos(id) ON DELETE CASCADE,
  document_version integer NOT NULL CHECK (document_version >= 1),
  identificador_canonico text NOT NULL,
  source_id text NOT NULL,
  source_url text,
  title text NOT NULL,
  content_hash text NOT NULL,
  metadata jsonb DEFAULT '{}'::jsonb,
  validation_status text,
  validation_details jsonb,
  archived_at timestamp with time zone DEFAULT now() NOT NULL,
  CONSTRAINT despacho_corpus_docs_hist_doc_ver_key UNIQUE (document_id, document_version)
);

CREATE INDEX IF NOT EXISTS idx_corpus_docs_hist_doc_ver 
  ON public.despacho_corpus_documentos_historicos(document_id, document_version);

CREATE INDEX IF NOT EXISTS idx_corpus_docs_hist_canonico 
  ON public.despacho_corpus_documentos_historicos(identificador_canonico);

-- 2. Tabla histórica de fragmentos (versiones anteriores)
CREATE TABLE IF NOT EXISTS public.despacho_corpus_fragmentos_historicos (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  document_id uuid NOT NULL REFERENCES public.despacho_corpus_documentos(id) ON DELETE CASCADE,
  document_version integer NOT NULL CHECK (document_version >= 1),
  ordinal integer NOT NULL,
  segment integer NOT NULL,
  content text NOT NULL,
  section text,
  archived_at timestamp with time zone DEFAULT now() NOT NULL,
  CONSTRAINT despacho_corpus_frags_hist_doc_ver_ord_key UNIQUE (document_id, document_version, ordinal)
);

CREATE INDEX IF NOT EXISTS idx_corpus_frags_hist_lookup 
  ON public.despacho_corpus_fragmentos_historicos(document_id, document_version, segment);

CREATE INDEX IF NOT EXISTS idx_corpus_frags_hist_doc 
  ON public.despacho_corpus_fragmentos_historicos(document_id, document_version);

-- 3. RLS y permisos para tablas históricas
ALTER TABLE public.despacho_corpus_documentos_historicos ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.despacho_corpus_fragmentos_historicos ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON public.despacho_corpus_documentos_historicos FROM PUBLIC, anon;
REVOKE ALL ON public.despacho_corpus_fragmentos_historicos FROM PUBLIC, anon;

GRANT SELECT ON public.despacho_corpus_documentos_historicos TO authenticated, service_role;
GRANT SELECT ON public.despacho_corpus_fragmentos_historicos TO authenticated, service_role;
GRANT ALL ON public.despacho_corpus_documentos_historicos TO service_role;
GRANT ALL ON public.despacho_corpus_fragmentos_historicos TO service_role;

DROP POLICY IF EXISTS despacho_corpus_docs_hist_lectura ON public.despacho_corpus_documentos_historicos;
CREATE POLICY despacho_corpus_docs_hist_lectura ON public.despacho_corpus_documentos_historicos
  FOR SELECT TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.despacho_corpus_documentos d
      WHERE d.id = despacho_corpus_documentos_historicos.document_id AND d.published = true
    )
  );

DROP POLICY IF EXISTS despacho_corpus_frags_hist_lectura ON public.despacho_corpus_fragmentos_historicos;
CREATE POLICY despacho_corpus_frags_hist_lectura ON public.despacho_corpus_fragmentos_historicos
  FOR SELECT TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.despacho_corpus_documentos d
      WHERE d.id = despacho_corpus_fragmentos_historicos.document_id AND d.published = true
    )
  );

-- 4. Actualización de 'despacho_upsert_providencia_corpus_atomico' con preservación histórica garantizada
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

      -- =========================================================================
      -- PRESERVACIÓN HISTÓRICA INMUTABLE: ARCHIVAR ANTES DE SOBRESCRIBIR
      -- =========================================================================
      -- 1. Archivar versión previa del documento
      INSERT INTO public.despacho_corpus_documentos_historicos (
        document_id, document_version, identificador_canonico, source_id, source_url,
        title, content_hash, metadata, validation_status, validation_details, archived_at
      ) VALUES (
        d.id, d.version, d.identificador_canonico, d.source_id, d.source_url,
        d.title, d.content_hash, d.metadata, d.validation_status, d.validation_details, now()
      ) ON CONFLICT (document_id, document_version) DO UPDATE SET
        content_hash = EXCLUDED.content_hash,
        metadata = EXCLUDED.metadata;

      -- 2. Archivar fragmentos históricos completos de la versión previa
      INSERT INTO public.despacho_corpus_fragmentos_historicos (
        document_id, document_version, ordinal, segment, content, section, archived_at
      )
      SELECT document_id, document_version, ordinal, segment, content, section, now()
      FROM public.despacho_corpus_fragmentos
      WHERE document_id = d.id
      ON CONFLICT (document_id, document_version, ordinal) DO UPDATE SET
        content = EXCLUDED.content,
        section = EXCLUDED.section;

      -- 3. Actualizar cabecera documental a la nueva versión
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

      -- 4. Reemplazar fragmentos de trabajo activo para la nueva versión
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

      -- 5. Registrar auditoría por incremento de versión
      INSERT INTO public.despacho_corpus_auditoria_revisiones (
        document_id, document_version, responsible_id, responsible_name, responsible_role,
        review_type, decision, reason, validation_summary,
        previous_workflow_status, new_workflow_status, previous_published, new_published
      ) VALUES (
        d.id, v_new_version, p_responsible_id, p_responsible_name, p_responsible_role,
        'validacion_tecnica_automatica', 'reopen',
        'Nueva versión de contenido detectada (hash modificado). Colocado en revisión. Versión anterior archivada inmutablemente.',
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

COMMIT;
