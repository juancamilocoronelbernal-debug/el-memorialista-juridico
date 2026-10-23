-- V5: contenido indexado por propietario, búsqueda textual + vectorial.
-- Los originales, permisos y versiones siguen en despacho_items.
BEGIN;
UPDATE storage.buckets SET allowed_mime_types=ARRAY['application/pdf','application/vnd.openxmlformats-officedocument.wordprocessingml.document',
 'text/plain','text/markdown','image/png','image/jpeg','image/tiff','image/webp','message/rfc822'] WHERE id='despacho-documentos';
CREATE SCHEMA IF NOT EXISTS extensions;
CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA extensions;
-- SECURITY INVOKER conserva RLS; el rol también necesita resolver el tipo vector.
GRANT USAGE ON SCHEMA extensions TO authenticated,service_role;

CREATE TABLE IF NOT EXISTS public.despacho_indice (
    owner_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    document_id uuid NOT NULL,
    document_version integer NOT NULL CHECK(document_version>0),
    ordinal integer NOT NULL CHECK(ordinal BETWEEN 0 AND 499),
    page integer CHECK(page>0),
    segment integer CHECK(segment>0),
    content text NOT NULL CHECK(char_length(content) BETWEEN 1 AND 4000),
    embedding extensions.vector(768),
    embedding_model text,
    fts tsvector GENERATED ALWAYS AS (to_tsvector('spanish'::regconfig, content)) STORED,
    indexed_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY(owner_id,document_id,ordinal),
    FOREIGN KEY(owner_id,document_id) REFERENCES public.despacho_items(owner_id,id) ON DELETE CASCADE,
    CHECK((embedding IS NULL)=(embedding_model IS NULL))
);
CREATE INDEX IF NOT EXISTS despacho_indice_fts ON public.despacho_indice USING gin(fts);
CREATE INDEX IF NOT EXISTS despacho_indice_owner ON public.despacho_indice(owner_id,document_id,document_version);
CREATE INDEX IF NOT EXISTS despacho_indice_vector ON public.despacho_indice USING hnsw(embedding extensions.vector_cosine_ops);
ALTER TABLE public.despacho_indice ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.despacho_indice FROM PUBLIC,anon,authenticated;
GRANT SELECT,INSERT,DELETE ON public.despacho_indice TO authenticated;
GRANT ALL ON public.despacho_indice TO service_role;
DROP POLICY IF EXISTS despacho_indice_owner ON public.despacho_indice;
CREATE POLICY despacho_indice_owner ON public.despacho_indice FOR ALL TO authenticated
 USING(owner_id=(SELECT auth.uid())) WITH CHECK(owner_id=(SELECT auth.uid()));

CREATE OR REPLACE FUNCTION public.despacho_indexar_documento(p_document_id uuid,p_version integer,p_chunks jsonb)
RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER SET search_path='' AS $$
DECLARE d public.despacho_items; c jsonb; n integer=0;
BEGIN
 IF auth.uid() IS NULL OR jsonb_typeof(p_chunks)<>'array' OR jsonb_array_length(p_chunks)>500
    OR octet_length(p_chunks::text)>12582912 THEN
   RAISE EXCEPTION 'Índice inválido.' USING ERRCODE='22023';
 END IF;
 SELECT * INTO d FROM public.despacho_items WHERE id=p_document_id AND owner_id=auth.uid() AND kind='document' FOR SHARE;
 IF NOT FOUND THEN RAISE EXCEPTION 'Documento no accesible.' USING ERRCODE='42501'; END IF;
 IF d.version<>p_version THEN RAISE EXCEPTION 'El documento cambió durante la indexación.' USING ERRCODE='40001'; END IF;
 DELETE FROM public.despacho_indice WHERE document_id=p_document_id AND owner_id=auth.uid();
 FOR c IN SELECT value FROM jsonb_array_elements(p_chunks) LOOP
   INSERT INTO public.despacho_indice(owner_id,document_id,document_version,ordinal,page,segment,content,embedding,embedding_model)
   VALUES(auth.uid(),p_document_id,p_version,n,NULLIF(c->>'page','')::integer,NULLIF(c->>'segment','')::integer,c->>'content',
     CASE WHEN c->'embedding' IS NULL OR c->'embedding'='null'::jsonb THEN NULL ELSE (c->>'embedding')::extensions.vector END,
     NULLIF(c->>'embedding_model',''));
   n=n+1;
 END LOOP;
 RETURN jsonb_build_object('document_id',p_document_id,'document_version',p_version,'chunks',n);
END;
$$;
REVOKE ALL ON FUNCTION public.despacho_indexar_documento(uuid,integer,jsonb) FROM PUBLIC,anon;
GRANT EXECUTE ON FUNCTION public.despacho_indexar_documento(uuid,integer,jsonb) TO authenticated;

CREATE OR REPLACE FUNCTION public.despacho_buscar_conocimiento_interno(
 p_owner uuid,p_query text,p_embedding extensions.vector DEFAULT NULL,p_model text DEFAULT NULL,
 p_scope text DEFAULT 'documents',p_matter_id uuid DEFAULT NULL,p_filters jsonb DEFAULT '{}'::jsonb,p_limit integer DEFAULT 20)
RETURNS TABLE(document_id uuid,title text,excerpt text,page integer,segment integer,source_url text,
 document_version integer,score double precision,method text)
LANGUAGE sql STABLE SECURITY INVOKER SET search_path='' AS $$
 WITH eligible AS (
   SELECT i.*,d.title,d.data FROM public.despacho_indice i
   JOIN public.despacho_items d ON d.id=i.document_id AND d.owner_id=i.owner_id AND d.version=i.document_version
   WHERE i.owner_id=p_owner AND (p_owner=auth.uid() OR auth.role()='service_role') AND d.kind='document'
   AND ((p_scope='legal' AND d.data->>'legal_source'='true') OR (p_scope='documents' AND COALESCE(d.data->>'legal_source','false')<>'true'))
   AND (p_matter_id IS NULL OR d.matter_id=p_matter_id)
   AND (p_filters->'document_ids' IS NULL OR d.id::text IN (SELECT jsonb_array_elements_text(p_filters->'document_ids')))
   AND (NULLIF(p_filters->>'court','') IS NULL OR d.data->'legal_metadata'->>'court'=p_filters->>'court')
   AND (NULLIF(p_filters->>'year','') IS NULL OR d.data->'legal_metadata'->>'year'=p_filters->>'year')
   AND (NULLIF(p_filters->>'document_type','') IS NULL OR d.data->'legal_metadata'->>'document_type'=p_filters->>'document_type')
 ), lexical AS (
   SELECT document_id,ordinal,row_number() OVER(ORDER BY ts_rank_cd(fts,websearch_to_tsquery('spanish',left(p_query,4000))) DESC,document_id,ordinal) AS r
   FROM eligible WHERE fts @@ websearch_to_tsquery('spanish',left(p_query,4000)) LIMIT 100
 ), semantic AS (
   SELECT document_id,ordinal,row_number() OVER(ORDER BY embedding OPERATOR(extensions.<=>) p_embedding,document_id,ordinal) AS r
   FROM eligible WHERE p_embedding IS NOT NULL AND embedding IS NOT NULL AND embedding_model=p_model
     AND embedding OPERATOR(extensions.<=>) p_embedding < 0.75
   ORDER BY embedding OPERATOR(extensions.<=>) p_embedding LIMIT 100
 ), ranked AS (
   SELECT COALESCE(l.document_id,s.document_id) document_id,COALESCE(l.ordinal,s.ordinal) ordinal,
     COALESCE(1.0/(60+l.r),0)+COALESCE(1.0/(60+s.r),0) AS relevance,
     CASE WHEN l.r IS NOT NULL AND s.r IS NOT NULL THEN 'hybrid' WHEN s.r IS NOT NULL THEN 'semantic' ELSE 'text' END AS method
   FROM lexical l FULL OUTER JOIN semantic s ON s.document_id=l.document_id AND s.ordinal=l.ordinal
 ) SELECT e.document_id,e.title,e.content,e.page,e.segment,e.data->>'source_url',e.document_version,r.relevance::double precision,r.method
 FROM ranked r JOIN eligible e ON e.document_id=r.document_id AND e.ordinal=r.ordinal
 ORDER BY r.relevance DESC,e.document_id,e.ordinal LIMIT LEAST(GREATEST(p_limit,1),50);
$$;
REVOKE ALL ON FUNCTION public.despacho_buscar_conocimiento_interno(uuid,text,extensions.vector,text,text,uuid,jsonb,integer) FROM PUBLIC,anon;
GRANT EXECUTE ON FUNCTION public.despacho_buscar_conocimiento_interno(uuid,text,extensions.vector,text,text,uuid,jsonb,integer) TO authenticated,service_role;

CREATE OR REPLACE FUNCTION public.despacho_buscar_conocimiento(
 p_query text,p_embedding extensions.vector DEFAULT NULL,p_model text DEFAULT NULL,
 p_scope text DEFAULT 'documents',p_matter_id uuid DEFAULT NULL,p_filters jsonb DEFAULT '{}'::jsonb,p_limit integer DEFAULT 20)
RETURNS TABLE(document_id uuid,title text,excerpt text,page integer,segment integer,source_url text,
 document_version integer,score double precision,method text)
LANGUAGE sql STABLE SECURITY INVOKER SET search_path='' AS $$
 SELECT * FROM public.despacho_buscar_conocimiento_interno(auth.uid(),p_query,p_embedding,p_model,p_scope,p_matter_id,p_filters,p_limit);
$$;
REVOKE ALL ON FUNCTION public.despacho_buscar_conocimiento(text,extensions.vector,text,text,uuid,jsonb,integer) FROM PUBLIC,anon;
GRANT EXECUTE ON FUNCTION public.despacho_buscar_conocimiento(text,extensions.vector,text,text,uuid,jsonb,integer) TO authenticated;

CREATE OR REPLACE FUNCTION public.despacho_cobertura_indice_interna(p_owner uuid,p_model text)
RETURNS jsonb LANGUAGE sql STABLE SECURITY INVOKER SET search_path='' AS $$
 SELECT jsonb_build_object(
  'documents',(SELECT count(*) FROM public.despacho_items WHERE owner_id=p_owner AND kind='document'),
  'indexed_documents',(SELECT count(DISTINCT i.document_id) FROM public.despacho_indice i JOIN public.despacho_items d
     ON d.id=i.document_id AND d.owner_id=i.owner_id AND d.version=i.document_version WHERE i.owner_id=p_owner),
  'semantic_documents',(SELECT count(DISTINCT i.document_id) FROM public.despacho_indice i JOIN public.despacho_items d
     ON d.id=i.document_id AND d.owner_id=i.owner_id AND d.version=i.document_version
     WHERE i.owner_id=p_owner AND i.embedding IS NOT NULL AND (p_model IS NULL OR i.embedding_model=p_model)),
  'embedding_model',p_model,
  'legal_documents',(SELECT count(*) FROM public.despacho_items WHERE owner_id=p_owner AND kind='document' AND data->>'legal_source'='true')
 ) WHERE p_owner=auth.uid() OR auth.role()='service_role';
$$;
REVOKE ALL ON FUNCTION public.despacho_cobertura_indice_interna(uuid,text) FROM PUBLIC,anon;
GRANT EXECUTE ON FUNCTION public.despacho_cobertura_indice_interna(uuid,text) TO authenticated,service_role;
CREATE OR REPLACE FUNCTION public.despacho_cobertura_indice_interna(p_owner uuid)
RETURNS jsonb LANGUAGE sql STABLE SECURITY INVOKER SET search_path='' AS $$
 SELECT public.despacho_cobertura_indice_interna(p_owner,NULL);
$$;
REVOKE ALL ON FUNCTION public.despacho_cobertura_indice_interna(uuid) FROM PUBLIC,anon;
GRANT EXECUTE ON FUNCTION public.despacho_cobertura_indice_interna(uuid) TO authenticated,service_role;
CREATE OR REPLACE FUNCTION public.despacho_cobertura_indice(p_model text)
RETURNS jsonb LANGUAGE sql STABLE SECURITY INVOKER SET search_path='' AS $$
 SELECT public.despacho_cobertura_indice_interna(auth.uid(),p_model);
$$;
REVOKE ALL ON FUNCTION public.despacho_cobertura_indice(text) FROM PUBLIC,anon;
GRANT EXECUTE ON FUNCTION public.despacho_cobertura_indice(text) TO authenticated;
CREATE OR REPLACE FUNCTION public.despacho_cobertura_indice()
RETURNS jsonb LANGUAGE sql STABLE SECURITY INVOKER SET search_path='' AS $$
 SELECT public.despacho_cobertura_indice_interna(auth.uid());
$$;
REVOKE ALL ON FUNCTION public.despacho_cobertura_indice() FROM PUBLIC,anon;
GRANT EXECUTE ON FUNCTION public.despacho_cobertura_indice() TO authenticated;
COMMIT;
