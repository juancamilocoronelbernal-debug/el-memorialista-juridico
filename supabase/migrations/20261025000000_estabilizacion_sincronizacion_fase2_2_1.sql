-- Migración Fase 2.2.1: Estabilización Definitiva de la Sincronización Automática
-- 1. Tabla de descubrimientos y reintentos (pending_source / temporarily_unavailable)
-- 2. Tabla inmutable de auditoría de revisiones (distingue técnica, administrativa y jurídica humana)
-- 3. Ampliación de despacho_conector_corte_estado con tokens de esgrima (fencing), marcas de agua y control de procesos
-- 4. Funciones RPC para bloqueo con fencing token, renovación (heartbeat), reintentos y auditoría

BEGIN;

-- 1. Tabla inmutable de auditoría de revisiones jurídicas y administrativas
CREATE TABLE IF NOT EXISTS public.despacho_corpus_auditoria_revisiones (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id uuid NOT NULL REFERENCES public.despacho_corpus_documentos(id) ON DELETE CASCADE,
  document_version integer NOT NULL DEFAULT 1,
  responsible_id text NOT NULL DEFAULT 'anon',
  responsible_name text NOT NULL DEFAULT 'Sistema',
  responsible_role text NOT NULL DEFAULT 'sistema',
  review_type text NOT NULL CHECK (
    review_type IN ('validacion_tecnica_automatica', 'aprobacion_administrativa', 'revision_juridica_humana')
  ),
  decision text NOT NULL CHECK (
    decision IN ('approve', 'reject', 'withdraw', 'reopen')
  ),
  reason text,
  validation_summary jsonb NOT NULL DEFAULT '{}'::jsonb,
  previous_workflow_status text,
  new_workflow_status text,
  previous_published boolean,
  new_published boolean,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_corpus_auditoria_doc ON public.despacho_corpus_auditoria_revisiones(document_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_corpus_auditoria_type ON public.despacho_corpus_auditoria_revisiones(review_type);

-- 2. Tabla de seguimiento de descubrimientos oficiales y reintentos
CREATE TABLE IF NOT EXISTS public.despacho_conector_descubrimientos (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  sentencia text NOT NULL UNIQUE,
  tipo text NOT NULL,
  anio integer,
  fecha text,
  magistrado text,
  sala text,
  expediente text,
  proceso text,
  tema text,
  source_dataset text NOT NULL DEFAULT 'v2k4-2t8s',
  source_url text,
  source_status text NOT NULL DEFAULT 'discovered' CHECK (
    source_status IN (
      'discovered',
      'pending_source',
      'temporarily_unavailable',
      'retrieved',
      'technically_validated',
      'pending_legal_review',
      'approved',
      'published',
      'validation_failed',
      'permanently_unavailable',
      'withdrawn'
    )
  ),
  retry_count integer NOT NULL DEFAULT 0,
  max_retries integer NOT NULL DEFAULT 10,
  next_retry_at timestamptz,
  last_error text,
  first_discovered_at timestamptz NOT NULL DEFAULT now(),
  last_checked_at timestamptz,
  document_id uuid REFERENCES public.despacho_corpus_documentos(id) ON DELETE SET NULL,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_descubrimientos_sentencia ON public.despacho_conector_descubrimientos(sentencia);
CREATE INDEX IF NOT EXISTS idx_descubrimientos_status_retry ON public.despacho_conector_descubrimientos(source_status, next_retry_at)
  WHERE source_status IN ('pending_source', 'temporarily_unavailable');

-- 3. Ampliar despacho_conector_corte_estado con fencing tokens, marcas de agua y control de procesos
ALTER TABLE public.despacho_conector_corte_estado
  ADD COLUMN IF NOT EXISTS lock_fencing_token integer NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS process_status text NOT NULL DEFAULT 'idle'
    CHECK (process_status IN ('idle', 'syncing', 'paused', 'error')),
  ADD COLUMN IF NOT EXISTS last_successful_run_at timestamptz,
  ADD COLUMN IF NOT EXISTS last_error text,
  ADD COLUMN IF NOT EXISTS active_run_id text,
  ADD COLUMN IF NOT EXISTS batch_progress jsonb NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS watermark_fecha text,
  ADD COLUMN IF NOT EXISTS watermark_sentencia text,
  ADD COLUMN IF NOT EXISTS discovered_watermark jsonb NOT NULL DEFAULT '{"latest_fecha": null, "latest_sentencia": null, "oldest_fecha": null, "oldest_sentencia": null}'::jsonb;

-- 4. RPC: Adquirir bloqueo con fencing token
CREATE OR REPLACE FUNCTION public.despacho_adquirir_bloqueo_conector_v2(
  p_owner text,
  p_ttl_seconds integer DEFAULT 600,
  p_run_id text DEFAULT NULL
)
RETURNS jsonb
LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $$
DECLARE
  st public.despacho_conector_corte_estado;
  v_new_token integer;
BEGIN
  IF auth.role() <> 'service_role' THEN
    RAISE EXCEPTION 'No autorizado.' USING ERRCODE = '42501';
  END IF;

  SELECT * INTO st FROM public.despacho_conector_corte_estado
  WHERE id = 'corte_constitucional' FOR UPDATE;

  IF NOT FOUND THEN
    RAISE EXCEPTION 'Estado de conector no inicializado.' USING ERRCODE = 'P0002';
  END IF;

  -- Comprobar si hay un bloqueo vigente de otro propietario
  IF st.sync_lock_until IS NOT NULL AND st.sync_lock_until > now() AND st.lock_owner <> p_owner THEN
    RETURN jsonb_build_object(
      'acquired', false,
      'reason', 'locked_by_other_worker',
      'current_owner', st.lock_owner,
      'lock_until', st.sync_lock_until,
      'fencing_token', st.lock_fencing_token
    );
  END IF;

  v_new_token := st.lock_fencing_token + 1;

  UPDATE public.despacho_conector_corte_estado
  SET
    sync_lock_until = now() + (p_ttl_seconds || ' seconds')::interval,
    lock_owner = p_owner,
    lock_fencing_token = v_new_token,
    process_status = 'syncing',
    last_run_started_at = now(),
    active_run_id = COALESCE(p_run_id, 'run_' || v_new_token || '_' || to_char(now(), 'YYYYMMDD_HH24MISS')),
    updated_at = now()
  WHERE id = 'corte_constitucional'
  RETURNING * INTO st;

  RETURN jsonb_build_object(
    'acquired', true,
    'owner', st.lock_owner,
    'fencing_token', st.lock_fencing_token,
    'lock_until', st.sync_lock_until,
    'run_id', st.active_run_id
  );
END;
$$;

-- 5. RPC: Renovar bloqueo periódicamente (heartbeat anti-expiración)
CREATE OR REPLACE FUNCTION public.despacho_renovar_bloqueo_conector(
  p_owner text,
  p_fencing_token integer,
  p_extend_seconds integer DEFAULT 600,
  p_progress jsonb DEFAULT NULL
)
RETURNS boolean
LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $$
DECLARE
  v_updated integer := 0;
BEGIN
  IF auth.role() <> 'service_role' THEN
    RAISE EXCEPTION 'No autorizado.' USING ERRCODE = '42501';
  END IF;

  UPDATE public.despacho_conector_corte_estado
  SET
    sync_lock_until = now() + (p_extend_seconds || ' seconds')::interval,
    batch_progress = COALESCE(p_progress, batch_progress),
    updated_at = now()
  WHERE id = 'corte_constitucional'
    AND lock_owner = p_owner
    AND lock_fencing_token = p_fencing_token;

  GET DIAGNOSTICS v_updated = ROW_COUNT;
  RETURN (v_updated > 0);
END;
$$;

-- 6. RPC: Liberar bloqueo de forma segura con fencing token
CREATE OR REPLACE FUNCTION public.despacho_liberar_bloqueo_conector_v2(
  p_owner text,
  p_fencing_token integer,
  p_success boolean DEFAULT true,
  p_error text DEFAULT NULL
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
    process_status = CASE WHEN p_success THEN 'idle' ELSE 'error' END,
    last_run_completed_at = now(),
    last_successful_run_at = CASE WHEN p_success THEN now() ELSE last_successful_run_at END,
    last_error = p_error,
    active_run_id = NULL,
    updated_at = now()
  WHERE id = 'corte_constitucional'
    AND (
      (lock_owner = p_owner AND lock_fencing_token = p_fencing_token)
      OR sync_lock_until < now()
    );

  GET DIAGNOSTICS v_released = ROW_COUNT;
  RETURN (v_released > 0);
END;
$$;

-- 7. RPC: Limpiar bloqueo huérfano (recuperación tras reinicio de Render o crash)
CREATE OR REPLACE FUNCTION public.despacho_limpiar_bloqueo_huerfano()
RETURNS jsonb
LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $$
DECLARE
  st public.despacho_conector_corte_estado;
  v_cleared boolean := false;
BEGIN
  IF auth.role() <> 'service_role' THEN
    RAISE EXCEPTION 'No autorizado.' USING ERRCODE = '42501';
  END IF;

  SELECT * INTO st FROM public.despacho_conector_corte_estado
  WHERE id = 'corte_constitucional' FOR UPDATE;

  IF st.sync_lock_until IS NOT NULL AND st.sync_lock_until < now() THEN
    UPDATE public.despacho_conector_corte_estado
    SET
      sync_lock_until = NULL,
      lock_owner = NULL,
      process_status = 'idle',
      last_error = 'Bloqueo huérfano recuperado tras expiración de tiempo de arrendamiento (crash o reinicio del contenedor).',
      active_run_id = NULL,
      updated_at = now()
    WHERE id = 'corte_constitucional'
    RETURNING * INTO st;
    v_cleared := true;
  END IF;

  RETURN jsonb_build_object(
    'cleared', v_cleared,
    'lock_owner', st.lock_owner,
    'sync_lock_until', st.sync_lock_until,
    'process_status', st.process_status
  );
END;
$$;

-- 8. RPC: Registrar auditoría de revisión documental
CREATE OR REPLACE FUNCTION public.despacho_registrar_auditoria_revision(
  p_document_id uuid,
  p_document_version integer,
  p_responsible_id text,
  p_responsible_name text,
  p_responsible_role text,
  p_review_type text,
  p_decision text,
  p_reason text,
  p_validation_summary jsonb DEFAULT '{}'::jsonb,
  p_previous_workflow text DEFAULT NULL,
  p_new_workflow text DEFAULT NULL,
  p_previous_pub boolean DEFAULT NULL,
  p_new_pub boolean DEFAULT NULL
)
RETURNS jsonb
LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $$
DECLARE
  v_id uuid;
BEGIN
  IF auth.role() <> 'service_role' THEN
    RAISE EXCEPTION 'No autorizado.' USING ERRCODE = '42501';
  END IF;

  INSERT INTO public.despacho_corpus_auditoria_revisiones(
    document_id, document_version, responsible_id, responsible_name, responsible_role,
    review_type, decision, reason, validation_summary,
    previous_workflow_status, new_workflow_status, previous_published, new_published
  )
  VALUES (
    p_document_id, p_document_version, p_responsible_id, p_responsible_name, p_responsible_role,
    p_review_type, p_decision, p_reason, p_validation_summary,
    p_previous_workflow, p_new_workflow, p_previous_pub, p_new_pub
  )
  RETURNING id INTO v_id;

  RETURN jsonb_build_object('audit_id', v_id, 'recorded', true, 'created_at', now());
END;
$$;

-- 9. RPC: Consultar historial de auditoría de un documento
CREATE OR REPLACE FUNCTION public.despacho_listar_auditoria_corpus(
  p_document_id uuid DEFAULT NULL,
  p_limit integer DEFAULT 50
)
RETURNS jsonb
LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $$
DECLARE
  v_items jsonb;
BEGIN
  SELECT jsonb_agg(sub) INTO v_items FROM (
    SELECT
      a.id,
      a.document_id,
      d.title AS document_title,
      a.document_version,
      a.responsible_id,
      a.responsible_name,
      a.responsible_role,
      a.review_type,
      a.decision,
      a.reason,
      a.previous_workflow_status,
      a.new_workflow_status,
      a.previous_published,
      a.new_published,
      a.created_at
    FROM public.despacho_corpus_auditoria_revisiones a
    LEFT JOIN public.despacho_corpus_documentos d ON d.id = a.document_id
    WHERE (p_document_id IS NULL OR a.document_id = p_document_id)
    ORDER BY a.created_at DESC
    LIMIT LEAST(GREATEST(p_limit, 1), 100)
  ) sub;

  RETURN COALESCE(v_items, '[]'::jsonb);
END;
$$;

-- 10. RPC: Consultar providencias pendientes de reintento
CREATE OR REPLACE FUNCTION public.despacho_listar_pendientes_reintento(
  p_limit integer DEFAULT 50
)
RETURNS jsonb
LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $$
DECLARE
  v_items jsonb;
BEGIN
  SELECT jsonb_agg(sub) INTO v_items FROM (
    SELECT
      id,
      sentencia,
      tipo,
      anio,
      fecha,
      magistrado,
      source_status,
      retry_count,
      max_retries,
      next_retry_at,
      last_error,
      first_discovered_at,
      last_checked_at
    FROM public.despacho_conector_descubrimientos
    WHERE source_status IN ('pending_source', 'temporarily_unavailable')
    ORDER BY next_retry_at ASC NULLS FIRST
    LIMIT LEAST(GREATEST(p_limit, 1), 100)
  ) sub;

  RETURN COALESCE(v_items, '[]'::jsonb);
END;
$$;

-- Permisos RLS
REVOKE ALL ON FUNCTION public.despacho_adquirir_bloqueo_conector_v2(text, integer, text) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.despacho_adquirir_bloqueo_conector_v2(text, integer, text) TO service_role;

REVOKE ALL ON FUNCTION public.despacho_renovar_bloqueo_conector(text, integer, integer, jsonb) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.despacho_renovar_bloqueo_conector(text, integer, integer, jsonb) TO service_role;

REVOKE ALL ON FUNCTION public.despacho_liberar_bloqueo_conector_v2(text, integer, boolean, text) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.despacho_liberar_bloqueo_conector_v2(text, integer, boolean, text) TO service_role;

REVOKE ALL ON FUNCTION public.despacho_limpiar_bloqueo_huerfano() FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.despacho_limpiar_bloqueo_huerfano() TO service_role;

REVOKE ALL ON FUNCTION public.despacho_registrar_auditoria_revision(uuid, integer, text, text, text, text, text, text, jsonb, text, text, boolean, boolean) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.despacho_registrar_auditoria_revision(uuid, integer, text, text, text, text, text, text, jsonb, text, text, boolean, boolean) TO service_role;

REVOKE ALL ON FUNCTION public.despacho_listar_auditoria_corpus(uuid, integer) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.despacho_listar_auditoria_corpus(uuid, integer) TO authenticated, service_role;

REVOKE ALL ON FUNCTION public.despacho_listar_pendientes_reintento(integer) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.despacho_listar_pendientes_reintento(integer) TO authenticated, service_role;

COMMIT;
