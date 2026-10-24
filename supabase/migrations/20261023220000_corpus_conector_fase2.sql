-- Migración Fase 2: Biblioteca Jurídica Automática y Conector Corte Constitucional
BEGIN;

-- 1. Actualizar procedimiento atómico de publicación para registrar 'section' en los fragmentos
CREATE OR REPLACE FUNCTION public.despacho_publicar_documento_corpus(
 p_source_id text, p_source_url text, p_title text, p_hash text,
 p_chunks jsonb, p_metadata jsonb DEFAULT '{}'::jsonb)
RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER SET search_path='' AS $$
DECLARE d public.despacho_corpus_documentos; row_chunk jsonb; ordinal_no integer:=0;
BEGIN
 IF auth.role()<>'service_role' THEN RAISE EXCEPTION 'No autorizado.' USING ERRCODE='42501'; END IF;
 IF length(p_source_id) NOT BETWEEN 2 AND 90 OR length(p_title) NOT BETWEEN 3 AND 240 OR
    p_source_url NOT LIKE 'https://%' OR length(p_source_url)>2048 OR
    p_hash !~ '^[0-9a-f]{64}$' OR
    jsonb_typeof(p_chunks)<>'array' OR jsonb_array_length(p_chunks)<1 OR jsonb_array_length(p_chunks)>200 OR
    octet_length(p_chunks::text)>4500000 OR jsonb_typeof(p_metadata)<>'object' OR
    octet_length(p_metadata::text)>32000 THEN
   RAISE EXCEPTION 'Documento o índice inválido.' USING ERRCODE='22023';
 END IF;
 SELECT * INTO d FROM public.despacho_corpus_documentos WHERE source_url=p_source_url FOR UPDATE;
 IF FOUND AND d.content_hash=p_hash AND d.source_id=p_source_id AND d.published THEN
   RETURN jsonb_build_object('id',d.id,'version',d.version,'unchanged',true,'segments',(
     SELECT count(*) FROM public.despacho_corpus_fragmentos WHERE document_id=d.id));
 END IF;
 IF FOUND THEN
   UPDATE public.despacho_corpus_documentos SET
     source_id=p_source_id,title=p_title,content_hash=p_hash,version=d.version+1,published=false,
     metadata=p_metadata,indexed_at=now(),reviewed_at=NULL WHERE id=d.id RETURNING * INTO d;
   DELETE FROM public.despacho_corpus_fragmentos WHERE document_id=d.id;
 ELSE
   INSERT INTO public.despacho_corpus_documentos(source_id,source_url,title,content_hash,published,metadata)
   VALUES(p_source_id,p_source_url,p_title,p_hash,false,p_metadata) RETURNING * INTO d;
 END IF;
 FOR row_chunk IN SELECT value FROM jsonb_array_elements(p_chunks) LOOP
   INSERT INTO public.despacho_corpus_fragmentos(
     document_id,document_version,ordinal,segment,content,embedding,embedding_model,section)
   VALUES(
     d.id,d.version,ordinal_no,ordinal_no+1,row_chunk->>'content',
     CASE WHEN row_chunk->'embedding' IS NULL OR row_chunk->'embedding'='null'::jsonb THEN NULL
       ELSE (row_chunk->>'embedding')::extensions.vector END,
     NULLIF(row_chunk->>'embedding_model',''),
     COALESCE(row_chunk->>'section', 'seccion_desconocida'));
   ordinal_no:=ordinal_no+1;
 END LOOP;
 UPDATE public.despacho_corpus_documentos SET published=true,reviewed_at=now()
 WHERE id=d.id;
 RETURN jsonb_build_object('id',d.id,'version',d.version,'unchanged',false,'segments',ordinal_no);
END;
$$;

-- 2. Tabla para estado operativo del conector de actualización incremental
CREATE TABLE IF NOT EXISTS public.despacho_conector_corte_estado (
 id text PRIMARY KEY,
 source_name text NOT NULL DEFAULT 'Corte Constitucional de Colombia (v2k4-2t8s)',
 status text NOT NULL DEFAULT 'idle' CHECK (status IN ('idle', 'discovering', 'retrieving', 'indexing', 'completed', 'paused', 'error')),
 discovered_count integer NOT NULL DEFAULT 0,
 retrieved_count integer NOT NULL DEFAULT 0,
 rejected_count integer NOT NULL DEFAULT 0,
 pending_review_count integer NOT NULL DEFAULT 0,
 published_count integer NOT NULL DEFAULT 0,
 fragments_count integer NOT NULL DEFAULT 0,
 embeddings_count integer NOT NULL DEFAULT 0,
 estimated_cost_usd numeric NOT NULL DEFAULT 0.0,
 last_sync_at timestamptz,
 errors jsonb NOT NULL DEFAULT '[]'::jsonb,
 details jsonb NOT NULL DEFAULT '{}'::jsonb,
 updated_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.despacho_conector_corte_estado ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.despacho_conector_corte_estado FROM PUBLIC,anon,authenticated;
GRANT SELECT ON public.despacho_conector_corte_estado TO authenticated;
GRANT ALL ON public.despacho_conector_corte_estado TO service_role;

DROP POLICY IF EXISTS despacho_conector_estado_read ON public.despacho_conector_corte_estado;
CREATE POLICY despacho_conector_estado_read ON public.despacho_conector_corte_estado
 FOR SELECT TO authenticated USING (true);

INSERT INTO public.despacho_conector_corte_estado (id, status, last_sync_at)
VALUES ('corte_constitucional', 'idle', now())
ON CONFLICT (id) DO NOTHING;

COMMIT;
