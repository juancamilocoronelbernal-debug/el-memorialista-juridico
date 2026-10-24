-- Migración incremental y no destructiva para RAG Jurídico Inteligente 2.0
-- Clasificación de secciones procesales en el corpus compartido

ALTER TABLE public.despacho_corpus_fragmentos
  ADD COLUMN IF NOT EXISTS section text DEFAULT 'seccion_desconocida';

CREATE INDEX IF NOT EXISTS despacho_corpus_fragmentos_seccion
  ON public.despacho_corpus_fragmentos (section);

COMMENT ON COLUMN public.despacho_corpus_fragmentos.section IS
  'Clasificación jurídica del fragmento: encabezado, identificacion, antecedentes, hechos, problema_juridico, consideraciones, fundamentos_juridicos, ratio_decidendi, obiter_dicta, parte_resolutiva, salvamento_voto, aclaracion_voto, referencias_normativas, seccion_desconocida.';
