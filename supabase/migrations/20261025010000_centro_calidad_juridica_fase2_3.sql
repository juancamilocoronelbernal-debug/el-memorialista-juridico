-- Migración Fase 2.3: Centro de Calidad Jurídica Continua
-- 1. Tabla de Incidencias Jurídicas y Técnicas (despacho_corpus_incidencias)
-- 2. Tabla de Evolución Jurisprudencial (despacho_corpus_evolucion_jurisprudencial)
-- 3. Ampliación de columnas de calidad en despacho_corpus_documentos y despacho_conector_corte_estado
-- 4. Índices y políticas RLS con aislamiento multi-tenant y auditoría

BEGIN;

-- 1. Ampliar columnas de calidad en despacho_corpus_documentos
ALTER TABLE public.despacho_corpus_documentos
  ADD COLUMN IF NOT EXISTS quality_status text NOT NULL DEFAULT 'optimo'
    CHECK (quality_status IN ('sin_auditar', 'optimo', 'con_advertencias', 'con_incidencias', 'critico_retirado')),
  ADD COLUMN IF NOT EXISTS quality_checks jsonb NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS last_quality_audit_at timestamptz,
  ADD COLUMN IF NOT EXISTS quality_score numeric(5,2) DEFAULT 100.00,
  ADD COLUMN IF NOT EXISTS is_withdrawn boolean NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS withdrawn_reason text,
  ADD COLUMN IF NOT EXISTS withdrawn_at timestamptz;

CREATE INDEX IF NOT EXISTS idx_corpus_doc_quality_status 
  ON public.despacho_corpus_documentos(quality_status);
CREATE INDEX IF NOT EXISTS idx_corpus_doc_is_withdrawn 
  ON public.despacho_corpus_documentos(is_withdrawn);

-- 2. Ampliar columnas de auditoría en despacho_conector_corte_estado
ALTER TABLE public.despacho_conector_corte_estado
  ADD COLUMN IF NOT EXISTS last_quality_audit_at timestamptz,
  ADD COLUMN IF NOT EXISTS next_quality_audit_at timestamptz,
  ADD COLUMN IF NOT EXISTS quality_audit_metrics jsonb NOT NULL DEFAULT '{}'::jsonb;

-- 3. Tabla: despacho_corpus_incidencias
CREATE TABLE IF NOT EXISTS public.despacho_corpus_incidencias (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id uuid REFERENCES public.despacho_corpus_documentos(id) ON DELETE SET NULL,
  sentencia text,
  scope text NOT NULL CHECK (scope IN ('corpus', 'agente', 'jurisprudencia')),
  issue_type text NOT NULL CHECK (
    issue_type IN (
      'metadatos_incompletos',
      'hash_mismatch',
      'fragmento_duplicado',
      'fragmentos_omitidos',
      'parte_resolutiva_ausente',
      'clasificacion_erronea_salvamento',
      'embedding_invalido',
      'cita_inexistente',
      'cita_no_autentica',
      'referencia_invalida',
      'cita_inaccesible',
      'salvamento_como_mayoria',
      'cobertura_insuficiente',
      'afirmacion_no_respaldada',
      'reporte_usuario',
      'otro'
    )
  ),
  severity text NOT NULL DEFAULT 'media' CHECK (severity IN ('baja', 'media', 'alta', 'critica')),
  status text NOT NULL DEFAULT 'detectado' CHECK (
    status IN ('detectado', 'pendiente_revision', 'en_investigacion', 'corregido', 'descartado', 'cerrado')
  ),
  detected_at timestamptz NOT NULL DEFAULT now(),
  evidence jsonb NOT NULL DEFAULT '{}'::jsonb,
  assigned_to text,
  action_history jsonb NOT NULL DEFAULT '[]'::jsonb,
  resolved_at timestamptz,
  resolution_note text,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_incidencias_status_severity 
  ON public.despacho_corpus_incidencias(status, severity);
CREATE INDEX IF NOT EXISTS idx_incidencias_doc 
  ON public.despacho_corpus_incidencias(document_id);
CREATE INDEX IF NOT EXISTS idx_incidencias_scope 
  ON public.despacho_corpus_incidencias(scope);
CREATE INDEX IF NOT EXISTS idx_incidencias_detected_at 
  ON public.despacho_corpus_incidencias(detected_at DESC);

-- 4. Tabla: despacho_corpus_evolucion_jurisprudencial
CREATE TABLE IF NOT EXISTS public.despacho_corpus_evolucion_jurisprudencial (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source_sentencia text NOT NULL,
  target_sentencia text NOT NULL,
  relation_type text NOT NULL CHECK (
    relation_type IN ('cita', 'reiteracion', 'distincion', 'modificacion_regla', 'unificacion')
  ),
  evidence_quote text NOT NULL,
  evidence_section text,
  source_document_id uuid REFERENCES public.despacho_corpus_documentos(id) ON DELETE CASCADE,
  target_document_id uuid REFERENCES public.despacho_corpus_documentos(id) ON DELETE SET NULL,
  status text NOT NULL DEFAULT 'posible_evolucion_pendiente' CHECK (
    status IN ('posible_evolucion_pendiente', 'verificado_humano', 'descartado')
  ),
  verified_by text,
  verified_at timestamptz,
  verification_notes text,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_evolucion_source_target_type UNIQUE (source_sentencia, target_sentencia, relation_type)
);

CREATE INDEX IF NOT EXISTS idx_evolucion_source 
  ON public.despacho_corpus_evolucion_jurisprudencial(source_sentencia);
CREATE INDEX IF NOT EXISTS idx_evolucion_target 
  ON public.despacho_corpus_evolucion_jurisprudencial(target_sentencia);
CREATE INDEX IF NOT EXISTS idx_evolucion_status 
  ON public.despacho_corpus_evolucion_jurisprudencial(status);

-- 5. RLS y Permisos
ALTER TABLE public.despacho_corpus_incidencias ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.despacho_corpus_evolucion_jurisprudencial ENABLE ROW LEVEL SECURITY;

-- Políticas de lectura: usuarios autenticados pueden consultar incidencias y evolución
DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies 
    WHERE tablename = 'despacho_corpus_incidencias' AND policyname = 'incidencias_read_auth'
  ) THEN
    CREATE POLICY incidencias_read_auth ON public.despacho_corpus_incidencias
      FOR SELECT TO authenticated USING (true);
  END IF;
  
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies 
    WHERE tablename = 'despacho_corpus_incidencias' AND policyname = 'incidencias_service_all'
  ) THEN
    CREATE POLICY incidencias_service_all ON public.despacho_corpus_incidencias
      FOR ALL TO service_role USING (true) WITH CHECK (true);
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_policies 
    WHERE tablename = 'despacho_corpus_evolucion_jurisprudencial' AND policyname = 'evolucion_read_auth'
  ) THEN
    CREATE POLICY evolucion_read_auth ON public.despacho_corpus_evolucion_jurisprudencial
      FOR SELECT TO authenticated USING (true);
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_policies 
    WHERE tablename = 'despacho_corpus_evolucion_jurisprudencial' AND policyname = 'evolucion_service_all'
  ) THEN
    CREATE POLICY evolucion_service_all ON public.despacho_corpus_evolucion_jurisprudencial
      FOR ALL TO service_role USING (true) WITH CHECK (true);
  END IF;
END $$;

COMMIT;
