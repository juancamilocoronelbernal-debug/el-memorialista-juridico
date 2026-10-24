-- Migración Fase 2.2: Automatización Real del Conector, Validación Documental Obligatoria y Bandeja de Triage
BEGIN;

-- 1. Ampliar despacho_conector_corte_estado con programación, cursor incremental, bloqueo distribuido y estadísticas de validación
ALTER TABLE public.despacho_conector_corte_estado
  ADD COLUMN IF NOT EXISTS schedule_enabled boolean NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS schedule_interval_minutes integer NOT NULL DEFAULT 360,
  ADD COLUMN IF NOT EXISTS next_run_at timestamptz,
  ADD COLUMN IF NOT EXISTS last_run_started_at timestamptz,
  ADD COLUMN IF NOT EXISTS last_run_completed_at timestamptz,
  ADD COLUMN IF NOT EXISTS sync_cursor jsonb NOT NULL DEFAULT '{"offset": 0, "last_providencia": null, "last_fecha": null, "discovered_total": 0}'::jsonb,
  ADD COLUMN IF NOT EXISTS sync_lock_until timestamptz,
  ADD COLUMN IF NOT EXISTS lock_owner text,
  ADD COLUMN IF NOT EXISTS validation_stats jsonb NOT NULL DEFAULT '{"technically_validated": 0, "validation_failed": 0, "pending_review": 0, "human_approved": 0, "published": 0, "withdrawn": 0}'::jsonb;

-- 2. Ampliar despacho_corpus_documentos con estado de validación técnica y detalles de comprobaciones
ALTER TABLE public.despacho_corpus_documentos
  ADD COLUMN IF NOT EXISTS validation_status text NOT NULL DEFAULT 'pending'
    CHECK (validation_status IN ('pending', 'technically_validated', 'validation_failed', 'pending_legal_review', 'approved', 'published', 'withdrawn')),
  ADD COLUMN IF NOT EXISTS validation_details jsonb NOT NULL DEFAULT '{}'::jsonb;

-- Sincronizar validation_status de los documentos ya publicados existentes
UPDATE public.despacho_corpus_documentos
SET validation_status = 'published'
WHERE published = true AND integrity_status = 'complete' AND validation_status = 'pending';

-- 3. Funciones RPC para bloqueo concurrente distribuido (evita ejecuciones simultáneas de dos trabajadores)
CREATE OR REPLACE FUNCTION public.despacho_adquirir_bloqueo_conector(
  p_owner text,
  p_ttl_seconds integer DEFAULT 300
)
RETURNS boolean
LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $$
DECLARE
  v_acquired integer := 0;
BEGIN
  IF auth.role() <> 'service_role' THEN
    RAISE EXCEPTION 'No autorizado.' USING ERRCODE = '42501';
  END IF;

  UPDATE public.despacho_conector_corte_estado
  SET
    sync_lock_until = now() + (p_ttl_seconds || ' seconds')::interval,
    lock_owner = p_owner,
    last_run_started_at = now()
  WHERE id = 'corte_constitucional'
    AND (sync_lock_until IS NULL OR sync_lock_until < now() OR lock_owner = p_owner);

  GET DIAGNOSTICS v_acquired = ROW_COUNT;
  RETURN (v_acquired > 0);
END;
$$;

CREATE OR REPLACE FUNCTION public.despacho_liberar_bloqueo_conector(
  p_owner text
)
RETURNS boolean
LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $$
DECLARE
  v_released integer := 0;
BEGIN
  IF auth.role() <> 'service_role' THEN
    RAISE EXCEPTION 'No autorizado.' USING ERRCODE = '42501';
  END IF;

  UPDATE public.despacho_conector_corte_estado
  SET
    sync_lock_until = NULL,
    lock_owner = NULL,
    last_run_completed_at = now()
  WHERE id = 'corte_constitucional'
    AND (lock_owner = p_owner OR sync_lock_until < now());

  GET DIAGNOSTICS v_released = ROW_COUNT;
  RETURN (v_released > 0);
END;
$$;

-- 4. Función RPC para actualizar validación técnica y decisión de triage de un documento
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

  -- Regla estricta de seguridad jurídica: un documento con validación técnica fallida JAMÁS puede publicarse
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

  RETURN jsonb_build_object(
    'id', d.id,
    'validation_status', d.validation_status,
    'workflow_status', d.workflow_status,
    'published', d.published,
    'integrity_status', d.integrity_status
  );
END;
$$;

-- 5. Función RPC para consultar la bandeja administrativa de revisión (triage)
CREATE OR REPLACE FUNCTION public.despacho_listar_bandeja_triage_corpus(
  p_limit integer DEFAULT 50,
  p_offset integer DEFAULT 0
)
RETURNS jsonb
LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $$
DECLARE
  v_items jsonb;
  v_total integer := 0;
BEGIN
  SELECT count(*) INTO v_total
  FROM public.despacho_corpus_documentos
  WHERE validation_status IN ('validation_failed', 'pending_legal_review', 'technically_validated')
    OR (workflow_status = 'pending_legal_review')
    OR (published = false AND workflow_status <> 'withdrawn');

  SELECT jsonb_agg(sub) INTO v_items FROM (
    SELECT
      id,
      title,
      source_url,
      source_id,
      version,
      published,
      workflow_status,
      integrity_status,
      validation_status,
      validation_details,
      metadata->>'sentencia' AS sentencia,
      metadata->>'magistrado' AS magistrado,
      metadata->>'fecha' AS fecha,
      metadata->>'materia' AS materia,
      metadata->>'expected_segments' AS expected_segments,
      indexed_at,
      first_seen_at
    FROM public.despacho_corpus_documentos
    WHERE validation_status IN ('validation_failed', 'pending_legal_review', 'technically_validated')
      OR (workflow_status = 'pending_legal_review')
      OR (published = false AND workflow_status <> 'withdrawn')
    ORDER BY first_seen_at DESC
    LIMIT LEAST(GREATEST(p_limit, 1), 100)
    OFFSET GREATEST(p_offset, 0)
  ) sub;

  RETURN jsonb_build_object(
    'total', v_total,
    'limit', p_limit,
    'offset', p_offset,
    'items', COALESCE(v_items, '[]'::jsonb)
  );
END;
$$;

-- 6. Función RPC para actualizar cursor y estadísticas del conector
CREATE OR REPLACE FUNCTION public.despacho_actualizar_cursor_conector(
  p_cursor jsonb,
  p_stats jsonb DEFAULT NULL
)
RETURNS jsonb
LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $$
DECLARE
  st public.despacho_conector_corte_estado;
BEGIN
  IF auth.role() <> 'service_role' THEN
    RAISE EXCEPTION 'No autorizado.' USING ERRCODE = '42501';
  END IF;

  UPDATE public.despacho_conector_corte_estado
  SET
    sync_cursor = p_cursor,
    validation_stats = COALESCE(p_stats, validation_stats),
    updated_at = now()
  WHERE id = 'corte_constitucional'
  RETURNING * INTO st;

  RETURN jsonb_build_object(
    'id', st.id,
    'sync_cursor', st.sync_cursor,
    'validation_stats', st.validation_stats,
    'updated_at', st.updated_at
  );
END;
$$;

-- Permisos RLS
REVOKE ALL ON FUNCTION public.despacho_adquirir_bloqueo_conector(text, integer) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.despacho_adquirir_bloqueo_conector(text, integer) TO service_role;

REVOKE ALL ON FUNCTION public.despacho_liberar_bloqueo_conector(text) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.despacho_liberar_bloqueo_conector(text) TO service_role;

REVOKE ALL ON FUNCTION public.despacho_actualizar_validacion_documento(uuid, text, jsonb, text, boolean) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.despacho_actualizar_validacion_documento(uuid, text, jsonb, text, boolean) TO service_role;

REVOKE ALL ON FUNCTION public.despacho_listar_bandeja_triage_corpus(integer, integer) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.despacho_listar_bandeja_triage_corpus(integer, integer) TO authenticated, service_role;

REVOKE ALL ON FUNCTION public.despacho_actualizar_cursor_conector(jsonb, jsonb) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.despacho_actualizar_cursor_conector(jsonb, jsonb) TO service_role;

COMMIT;
