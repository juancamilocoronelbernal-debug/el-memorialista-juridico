-- El Memorialista | Primer núcleo de corpus jurídico compartido (NO es biblioteca privada).
-- Aplicar DESPUÉS de 20261023050000_biblioteca_busqueda.sql.
-- No importa sentencias automáticamente; comienza VACÍO. Sólo service_role publica
-- documentos revisados respecto de permisos de reutilización y datos personales.
BEGIN;
CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA extensions;

CREATE TABLE IF NOT EXISTS public.despacho_corpus_documentos (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 source_id text NOT NULL CHECK(length(source_id) BETWEEN 2 AND 90),
 source_url text NOT NULL UNIQUE CHECK(length(source_url) BETWEEN 12 AND 2048 AND source_url LIKE 'https://%'),
 title text NOT NULL CHECK(length(title) BETWEEN 3 AND 240),
 content_hash text NOT NULL CHECK(content_hash ~ '^[0-9a-f]{64}$'),
 version integer NOT NULL DEFAULT 1 CHECK(version >= 1),
 published boolean NOT NULL DEFAULT false,
 metadata jsonb NOT NULL DEFAULT '{}'::jsonb CHECK(jsonb_typeof(metadata)='object'),
 review_notice text NOT NULL DEFAULT 'Publicación autorizada; vigencia jurídica y pertinencia sujetas a revisión.',
 first_seen_at timestamptz NOT NULL DEFAULT now(),
 indexed_at timestamptz NOT NULL DEFAULT now(),
 reviewed_at timestamptz,
 CHECK (NOT published OR reviewed_at IS NOT NULL)
);

CREATE TABLE IF NOT EXISTS public.despacho_corpus_fragmentos (
 document_id uuid NOT NULL REFERENCES public.despacho_corpus_documentos(id) ON DELETE CASCADE,
 document_version integer NOT NULL CHECK(document_version>=1),
 ordinal integer NOT NULL CHECK(ordinal BETWEEN 0 AND 199),
 segment integer NOT NULL CHECK(segment >= 1),
 content text NOT NULL CHECK(length(content) BETWEEN 1 AND 4000),
 embedding extensions.vector(768),
 embedding_model text,
 fts tsvector GENERATED ALWAYS AS (to_tsvector('spanish'::regconfig,content)) STORED,
 PRIMARY KEY(document_id,ordinal),
 CHECK ((embedding IS NULL)=(embedding_model IS NULL))
);
CREATE INDEX IF NOT EXISTS despacho_corpus_texto ON public.despacho_corpus_fragmentos USING gin(fts);
CREATE INDEX IF NOT EXISTS despacho_corpus_semantica ON public.despacho_corpus_fragmentos USING hnsw(embedding extensions.vector_cosine_ops);
CREATE INDEX IF NOT EXISTS despacho_corpus_origen ON public.despacho_corpus_documentos(source_id,published);

ALTER TABLE public.despacho_corpus_documentos ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.despacho_corpus_fragmentos ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.despacho_corpus_documentos FROM PUBLIC,anon,authenticated;
REVOKE ALL ON public.despacho_corpus_fragmentos FROM PUBLIC,anon,authenticated;
GRANT SELECT ON public.despacho_corpus_documentos TO authenticated;
GRANT SELECT ON public.despacho_corpus_fragmentos TO authenticated;
GRANT ALL ON public.despacho_corpus_documentos,public.despacho_corpus_fragmentos TO service_role;
GRANT USAGE ON SCHEMA extensions TO authenticated,service_role;

DROP POLICY IF EXISTS despacho_corpus_publicados ON public.despacho_corpus_documentos;
CREATE POLICY despacho_corpus_publicados ON public.despacho_corpus_documentos
 FOR SELECT TO authenticated USING (published = true);
DROP POLICY IF EXISTS despacho_corpus_fragmentos_publicados ON public.despacho_corpus_fragmentos;
CREATE POLICY despacho_corpus_fragmentos_publicados ON public.despacho_corpus_fragmentos
 FOR SELECT TO authenticated USING (
  EXISTS (SELECT 1 FROM public.despacho_corpus_documentos d
          WHERE d.id=document_id AND d.published=true)
 );

-- Operación administrativa atómica: no expone escritura pública ni a usuarios.
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
    octet_length(p_chunks::text)>1400000 OR jsonb_typeof(p_metadata)<>'object' OR
    octet_length(p_metadata::text)>16000 THEN
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
   INSERT INTO public.despacho_corpus_fragmentos(document_id,document_version,ordinal,segment,content,embedding,embedding_model)
   VALUES(d.id,d.version,ordinal_no,ordinal_no+1,row_chunk->>'content',
       CASE WHEN row_chunk->'embedding' IS NULL OR row_chunk->'embedding'='null'::jsonb THEN NULL
         ELSE (row_chunk->>'embedding')::extensions.vector END,
       NULLIF(row_chunk->>'embedding_model',''));
   ordinal_no:=ordinal_no+1;
 END LOOP;
 -- La publicación ocurre dentro de esta misma transacción después de grabar el índice.
 UPDATE public.despacho_corpus_documentos SET published=true,reviewed_at=now()
 WHERE id=d.id;
 RETURN jsonb_build_object('id',d.id,'version',d.version,'unchanged',false,'segments',ordinal_no);
END;
$$;
REVOKE ALL ON FUNCTION public.despacho_publicar_documento_corpus(text,text,text,text,jsonb,jsonb) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.despacho_publicar_documento_corpus(text,text,text,text,jsonb,jsonb) TO service_role;

CREATE OR REPLACE FUNCTION public.despacho_consultar_corpus_publicado(
 p_query text, p_vector extensions.vector DEFAULT NULL, p_model text DEFAULT NULL, p_limit integer DEFAULT 12)
RETURNS TABLE(title text,excerpt text,source_url text,source_id text,decision_date text,
 document_version integer,segment integer,score double precision,method text)
LANGUAGE sql STABLE SECURITY INVOKER SET search_path='' AS $$
 WITH eligible AS (
  SELECT f.document_id,f.ordinal,f.segment,f.content,f.fts,f.embedding,f.embedding_model,
         d.title,d.source_url,d.source_id,d.version,d.metadata
  FROM public.despacho_corpus_fragmentos f
  JOIN public.despacho_corpus_documentos d ON d.id=f.document_id AND d.version=f.document_version
  WHERE d.published=true
 ), lexical AS (
  SELECT document_id,ordinal,row_number() OVER (
    ORDER BY ts_rank_cd(fts,websearch_to_tsquery('spanish',left(p_query,800))) DESC,document_id,ordinal) AS r
  FROM eligible WHERE fts @@ websearch_to_tsquery('spanish',left(p_query,800)) LIMIT 75
 ), semantic AS (
  SELECT document_id,ordinal,row_number() OVER (
    ORDER BY embedding OPERATOR(extensions.<=>) p_vector,document_id,ordinal) AS r
  FROM eligible WHERE p_vector IS NOT NULL AND embedding IS NOT NULL AND embedding_model=p_model
    AND embedding OPERATOR(extensions.<=>) p_vector < 0.75
  ORDER BY embedding OPERATOR(extensions.<=>) p_vector LIMIT 75
 ), ranked AS (
  SELECT COALESCE(l.document_id,s.document_id) id,COALESCE(l.ordinal,s.ordinal) ordinal,
   (coalesce(1.0/(60+l.r),0)+coalesce(1.0/(60+s.r),0))::double precision AS relevance,
   CASE WHEN l.r IS NOT NULL AND s.r IS NOT NULL THEN 'hybrid'
        WHEN s.r IS NOT NULL THEN 'semantic' ELSE 'text' END AS method
  FROM lexical l FULL JOIN semantic s ON s.document_id=l.document_id AND s.ordinal=l.ordinal
 )
 SELECT e.title,e.content,e.source_url,e.source_id,e.metadata->>'decision_date',
        e.version,e.segment,r.relevance,r.method
 FROM ranked r JOIN eligible e ON e.document_id=r.id AND e.ordinal=r.ordinal
 ORDER BY r.relevance DESC,e.document_id,e.ordinal LIMIT LEAST(GREATEST(p_limit,1),30);
$$;
REVOKE ALL ON FUNCTION public.despacho_consultar_corpus_publicado(text,extensions.vector,text,integer) FROM PUBLIC,anon;
GRANT EXECUTE ON FUNCTION public.despacho_consultar_corpus_publicado(text,extensions.vector,text,integer) TO authenticated;

CREATE OR REPLACE FUNCTION public.despacho_estado_corpus_publicado()
RETURNS jsonb LANGUAGE sql STABLE SECURITY INVOKER SET search_path='' AS $$
 SELECT jsonb_build_object(
 'published_documents',(SELECT count(*) FROM public.despacho_corpus_documentos WHERE published=true),
 'published_sources',(SELECT count(DISTINCT source_id) FROM public.despacho_corpus_documentos WHERE published=true),
 'indexed_fragments',(SELECT count(*) FROM public.despacho_corpus_fragmentos f
       JOIN public.despacho_corpus_documentos d ON d.id=f.document_id WHERE d.published=true),
 'semantic_documents',(SELECT count(DISTINCT f.document_id) FROM public.despacho_corpus_fragmentos f
       JOIN public.despacho_corpus_documentos d ON d.id=f.document_id
       WHERE d.published=true AND f.embedding IS NOT NULL),
 'last_indexed',(SELECT max(indexed_at) FROM public.despacho_corpus_documentos WHERE published=true))
$$;
REVOKE ALL ON FUNCTION public.despacho_estado_corpus_publicado() FROM PUBLIC,anon;
GRANT EXECUTE ON FUNCTION public.despacho_estado_corpus_publicado() TO authenticated;
COMMIT;
