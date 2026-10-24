-- Migración Fase 2.1: Auditoría de Integridad, Cobertura Completa sin Truncamiento y Ciclo de Vida Documental
BEGIN;

-- 1. Ampliar límite de ordinal en despacho_corpus_fragmentos de 199 a 4999
-- para permitir sentencias extensas (como C-141/10 con 737 fragmentos o C-055/22 con 707 fragmentos) sin truncamiento.
ALTER TABLE public.despacho_corpus_fragmentos
  DROP CONSTRAINT IF EXISTS despacho_corpus_fragmentos_ordinal_check;

ALTER TABLE public.despacho_corpus_fragmentos
  ADD CONSTRAINT despacho_corpus_fragmentos_ordinal_check CHECK (ordinal BETWEEN 0 AND 4999);

-- 2. Agregar columnas de estado de flujo documental e integridad en despacho_corpus_documentos
ALTER TABLE public.despacho_corpus_documentos
  ADD COLUMN IF NOT EXISTS workflow_status text NOT NULL DEFAULT 'published'
    CHECK (workflow_status IN ('discovered', 'retrieved', 'technically_validated', 'pending_legal_review', 'approved', 'published', 'withdrawn')),
  ADD COLUMN IF NOT EXISTS integrity_status text NOT NULL DEFAULT 'complete'
    CHECK (integrity_status IN ('complete', 'partial', 'pending'));

-- 3. Actualizar despacho_publicar_documento_corpus con soporte para ingesta incremental por lotes (p_finalize)
CREATE OR REPLACE FUNCTION public.despacho_publicar_documento_corpus(
  p_source_id text,
  p_source_url text,
  p_title text,
  p_hash text,
  p_chunks jsonb,
  p_metadata jsonb DEFAULT '{}'::jsonb,
  p_finalize boolean DEFAULT true
)
RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER SET search_path='' AS $$
DECLARE
  d public.despacho_corpus_documentos;
  row_chunk jsonb;
  ordinal_no integer := 0;
  chunk_ord integer;
  chunk_seg integer;
  expected_segments integer;
  current_segments integer;
BEGIN
  IF auth.role() <> 'service_role' THEN
    RAISE EXCEPTION 'No autorizado.' USING ERRCODE = '42501';
  END IF;

  IF length(p_source_id) NOT BETWEEN 2 AND 90 OR length(p_title) NOT BETWEEN 3 AND 240 OR
     p_source_url NOT LIKE 'https://%' OR length(p_source_url) > 2048 OR
     p_hash !~ '^[0-9a-f]{64}$' OR
     jsonb_typeof(p_chunks) <> 'array' OR jsonb_array_length(p_chunks) < 1 OR jsonb_array_length(p_chunks) > 250 OR
     octet_length(p_chunks::text) > 4500000 OR jsonb_typeof(p_metadata) <> 'object' OR
     octet_length(p_metadata::text) > 64000 THEN
    RAISE EXCEPTION 'Documento o índice inválido.' USING ERRCODE = '22023';
  END IF;

  SELECT * INTO d FROM public.despacho_corpus_documentos WHERE source_url = p_source_url FOR UPDATE;

  IF FOUND THEN
    SELECT count(*) INTO current_segments FROM public.despacho_corpus_fragmentos WHERE document_id = d.id;
    expected_segments := COALESCE((p_metadata->>'expected_segments')::integer, current_segments);
    IF d.content_hash = p_hash AND d.source_id = p_source_id AND d.published
       AND d.integrity_status = 'complete' AND current_segments = expected_segments THEN
      RETURN jsonb_build_object('id', d.id, 'version', d.version, 'unchanged', true, 'segments', current_segments);
    END IF;

    UPDATE public.despacho_corpus_documentos SET
      source_id = p_source_id,
      title = p_title,
      content_hash = p_hash,
      version = d.version + 1,
      published = false,
      workflow_status = 'technically_validated',
      integrity_status = 'pending',
      metadata = p_metadata,
      indexed_at = now(),
      reviewed_at = NULL
    WHERE id = d.id RETURNING * INTO d;

    DELETE FROM public.despacho_corpus_fragmentos WHERE document_id = d.id;
  ELSE
    INSERT INTO public.despacho_corpus_documentos(
      source_id, source_url, title, content_hash, published, workflow_status, integrity_status, metadata
    )
    VALUES(
      p_source_id, p_source_url, p_title, p_hash, false, 'technically_validated', 'pending', p_metadata
    ) RETURNING * INTO d;
  END IF;

  FOR row_chunk IN SELECT value FROM jsonb_array_elements(p_chunks) LOOP
    chunk_ord := COALESCE((row_chunk->>'ordinal')::integer, ordinal_no);
    chunk_seg := COALESCE((row_chunk->>'segment')::integer, chunk_ord + 1);
    INSERT INTO public.despacho_corpus_fragmentos(
      document_id, document_version, ordinal, segment, content, embedding, embedding_model, section
    )
    VALUES(
      d.id, d.version, chunk_ord, chunk_seg, row_chunk->>'content',
      CASE WHEN row_chunk->'embedding' IS NULL OR row_chunk->'embedding' = 'null'::jsonb THEN NULL
        ELSE (row_chunk->>'embedding')::extensions.vector END,
      NULLIF(row_chunk->>'embedding_model', ''),
      COALESCE(row_chunk->>'section', 'seccion_desconocida')
    );
    ordinal_no := ordinal_no + 1;
  END LOOP;

  IF p_finalize THEN
    UPDATE public.despacho_corpus_documentos SET
      published = true,
      workflow_status = 'published',
      integrity_status = 'complete',
      reviewed_at = now()
    WHERE id = d.id;
  END IF;

  RETURN jsonb_build_object(
    'id', d.id,
    'version', d.version,
    'unchanged', false,
    'segments', ordinal_no,
    'finalized', p_finalize
  );
END;
$$;

REVOKE ALL ON FUNCTION public.despacho_publicar_documento_corpus(text, text, text, text, jsonb, jsonb, boolean) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.despacho_publicar_documento_corpus(text, text, text, text, jsonb, jsonb, boolean) TO service_role;

-- 4. Procedimiento para anexar lotes incrementales de fragmentos sin truncar sentencias extensas
CREATE OR REPLACE FUNCTION public.despacho_anexar_fragmentos_corpus(
  p_document_id uuid,
  p_version integer,
  p_chunks jsonb,
  p_finalize boolean DEFAULT false
)
RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER SET search_path='' AS $$
DECLARE
  d public.despacho_corpus_documentos;
  row_chunk jsonb;
  inserted_count integer := 0;
  total_segments integer := 0;
  chunk_ord integer;
  chunk_seg integer;
BEGIN
  IF auth.role() <> 'service_role' THEN
    RAISE EXCEPTION 'No autorizado.' USING ERRCODE = '42501';
  END IF;

  IF jsonb_typeof(p_chunks) <> 'array' OR jsonb_array_length(p_chunks) < 1 OR jsonb_array_length(p_chunks) > 250 OR
     octet_length(p_chunks::text) > 4500000 THEN
    RAISE EXCEPTION 'Lote de fragmentos inválido.' USING ERRCODE = '22023';
  END IF;

  SELECT * INTO d FROM public.despacho_corpus_documentos WHERE id = p_document_id AND version = p_version FOR UPDATE;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'Documento o versión no encontrada para anexar fragmentos.' USING ERRCODE = '22023';
  END IF;

  FOR row_chunk IN SELECT value FROM jsonb_array_elements(p_chunks) LOOP
    chunk_ord := (row_chunk->>'ordinal')::integer;
    chunk_seg := COALESCE((row_chunk->>'segment')::integer, chunk_ord + 1);
    INSERT INTO public.despacho_corpus_fragmentos(
      document_id, document_version, ordinal, segment, content, embedding, embedding_model, section
    )
    VALUES(
      d.id, d.version, chunk_ord, chunk_seg, row_chunk->>'content',
      CASE WHEN row_chunk->'embedding' IS NULL OR row_chunk->'embedding' = 'null'::jsonb THEN NULL
        ELSE (row_chunk->>'embedding')::extensions.vector END,
      NULLIF(row_chunk->>'embedding_model', ''),
      COALESCE(row_chunk->>'section', 'seccion_desconocida')
    )
    ON CONFLICT (document_id, ordinal) DO UPDATE SET
      document_version = EXCLUDED.document_version,
      segment = EXCLUDED.segment,
      content = EXCLUDED.content,
      embedding = EXCLUDED.embedding,
      embedding_model = EXCLUDED.embedding_model,
      section = EXCLUDED.section;
    inserted_count := inserted_count + 1;
  END LOOP;

  SELECT count(*) INTO total_segments FROM public.despacho_corpus_fragmentos WHERE document_id = d.id;

  IF p_finalize THEN
    UPDATE public.despacho_corpus_documentos SET
      published = true,
      workflow_status = 'published',
      integrity_status = 'complete',
      reviewed_at = now()
    WHERE id = d.id;
  END IF;

  RETURN jsonb_build_object(
    'id', d.id,
    'version', d.version,
    'inserted', inserted_count,
    'segments', total_segments,
    'finalized', p_finalize
  );
END;
$$;

REVOKE ALL ON FUNCTION public.despacho_anexar_fragmentos_corpus(uuid, integer, jsonb, boolean) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.despacho_anexar_fragmentos_corpus(uuid, integer, jsonb, boolean) TO service_role;

-- 5. Función administrativa reversible para retirar/aprobar/cambiar estado de un documento del corpus
CREATE OR REPLACE FUNCTION public.despacho_cambiar_estado_corpus(
  p_document_id uuid,
  p_workflow_status text,
  p_published boolean,
  p_reason text DEFAULT NULL
)
RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER SET search_path='' AS $$
DECLARE
  d public.despacho_corpus_documentos;
  new_meta jsonb;
BEGIN
  IF auth.role() <> 'service_role' THEN
    RAISE EXCEPTION 'No autorizado.' USING ERRCODE = '42501';
  END IF;

  SELECT * INTO d FROM public.despacho_corpus_documentos WHERE id = p_document_id FOR UPDATE;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'Documento no encontrado.' USING ERRCODE = '22023';
  END IF;

  new_meta := d.metadata || jsonb_build_object(
    'last_workflow_transition', jsonb_build_object(
      'from_status', d.workflow_status,
      'to_status', p_workflow_status,
      'published', p_published,
      'reason', COALESCE(p_reason, 'Transición administrativa de estado'),
      'transition_at', now()
    )
  );

  UPDATE public.despacho_corpus_documentos SET
    workflow_status = p_workflow_status,
    published = p_published,
    reviewed_at = CASE WHEN p_published THEN COALESCE(reviewed_at, now()) ELSE reviewed_at END,
    metadata = new_meta
  WHERE id = p_document_id RETURNING * INTO d;

  RETURN jsonb_build_object(
    'id', d.id,
    'workflow_status', d.workflow_status,
    'published', d.published,
    'integrity_status', d.integrity_status
  );
END;
$$;

REVOKE ALL ON FUNCTION public.despacho_cambiar_estado_corpus(uuid, text, boolean, text) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.despacho_cambiar_estado_corpus(uuid, text, boolean, text) TO service_role;

-- 6. Actualizar despacho_consultar_corpus_publicado para resolver decision_date desde 'decision_date' o 'fecha'
CREATE OR REPLACE FUNCTION public.despacho_consultar_corpus_publicado(
  p_query text,
  p_vector extensions.vector DEFAULT NULL,
  p_model text DEFAULT NULL,
  p_limit integer DEFAULT 12
)
RETURNS TABLE(
  title text,
  excerpt text,
  source_url text,
  source_id text,
  decision_date text,
  document_version integer,
  segment integer,
  score double precision,
  method text
)
LANGUAGE sql STABLE SECURITY INVOKER SET search_path='' AS $$
  WITH eligible AS (
    SELECT f.document_id, f.ordinal, f.segment, f.content, f.fts, f.embedding, f.embedding_model,
           d.title, d.source_url, d.source_id, d.version, d.metadata
    FROM public.despacho_corpus_fragmentos f
    JOIN public.despacho_corpus_documentos d ON d.id = f.document_id AND d.version = f.document_version
    WHERE d.published = true AND d.integrity_status = 'complete'
  ), lexical AS (
    SELECT document_id, ordinal, row_number() OVER (
      ORDER BY ts_rank_cd(fts, websearch_to_tsquery('spanish', left(p_query, 800))) DESC, document_id, ordinal) AS r
    FROM eligible WHERE fts @@ websearch_to_tsquery('spanish', left(p_query, 800)) LIMIT 75
  ), semantic AS (
    SELECT document_id, ordinal, row_number() OVER (
      ORDER BY embedding OPERATOR(extensions.<=>) p_vector, document_id, ordinal) AS r
    FROM eligible WHERE p_vector IS NOT NULL AND embedding IS NOT NULL AND embedding_model = p_model
      AND embedding OPERATOR(extensions.<=>) p_vector < 0.75
    ORDER BY embedding OPERATOR(extensions.<=>) p_vector LIMIT 75
  ), ranked AS (
    SELECT COALESCE(l.document_id, s.document_id) id, COALESCE(l.ordinal, s.ordinal) ordinal,
      (coalesce(1.0 / (60 + l.r), 0) + coalesce(1.0 / (60 + s.r), 0))::double precision AS relevance,
      CASE WHEN l.r IS NOT NULL AND s.r IS NOT NULL THEN 'hybrid'
           WHEN s.r IS NOT NULL THEN 'semantic' ELSE 'text' END AS method
    FROM lexical l FULL JOIN semantic s ON s.document_id = l.document_id AND s.ordinal = l.ordinal
  )
  SELECT e.title, e.content, e.source_url, e.source_id,
         COALESCE(e.metadata->>'decision_date', e.metadata->>'fecha'),
         e.version, e.segment, r.relevance, r.method
  FROM ranked r JOIN eligible e ON e.document_id = r.id AND e.ordinal = r.ordinal
  ORDER BY r.relevance DESC, e.document_id, e.ordinal LIMIT LEAST(GREATEST(p_limit, 1), 30);
$$;

REVOKE ALL ON FUNCTION public.despacho_consultar_corpus_publicado(text, extensions.vector, text, integer) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.despacho_consultar_corpus_publicado(text, extensions.vector, text, integer) TO authenticated, service_role;

COMMIT;
