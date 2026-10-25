-- =============================================================================
-- EL MEMORIALISTA — REMEDIACIÓN DE SEGURIDAD FASE 1 (EM-01, EM-02, EM-03)
-- Fecha: 2026-10-25
-- Objetivo:
-- 1. EM-01: Habilitar RLS y revocar permisos públicos/anónimos sobre tablas
--    del conector (`despacho_conector_descubrimientos`) y auditoría de
--    revisiones (`despacho_corpus_auditoria_revisiones`).
-- 2. EM-02: Impedir auto-escalación de privilegios en `public.perfiles` y
--    definir funciones de verificación de roles que consultan exclusivamente
--    `auth.users.raw_app_meta_data` (nunca `raw_user_meta_data`), respetando
--    el bloqueo por conflicto de roles (`pendiente_revision`).
-- 3. EM-03: Reemplazar la política abierta `incidencias_read_auth` (`USING true`)
--    en `public.despacho_corpus_incidencias` por aislamiento estricto:
--    un usuario ordinario solo puede leer sus propios reportes
--    (`evidence->>'reported_by_id' = auth.uid()::text`), mientras que los
--    gestores de calidad autorizados (`app_metadata`) pueden supervisar la bandeja.
-- 4. Revocar permisos de escritura (`INSERT, UPDATE, DELETE, TRUNCATE`) para
--    `anon` y `authenticated` sobre tablas históricas e internas del corpus.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. FUNCIONES DE AUTORIZACIÓN BASADAS EXCLUSIVAMENTE EN `app_metadata` (EM-02)
-- -----------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION public.es_admin_tecnico()
RETURNS BOOLEAN
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
    v_app_meta JSONB;
    v_role_en TEXT;
    v_role_es TEXT;
    v_primary TEXT;
BEGIN
    SELECT raw_app_meta_data INTO v_app_meta
    FROM auth.users
    WHERE id = (SELECT auth.uid());

    IF v_app_meta IS NULL THEN
        RETURN FALSE;
    END IF;

    -- Bloquear si existe conflicto explícito o estado pendiente_revision
    IF COALESCE(v_app_meta->>'role_conflict', 'false') = 'true'
       OR COALESCE(v_app_meta->>'estado_rol', '') = 'pendiente_revision'
       OR COALESCE(v_app_meta->>'is_technical_admin', 'true') = 'false' THEN
        RETURN FALSE;
    END IF;

    v_role_en := LOWER(BTRIM(COALESCE(v_app_meta->>'role', '')));
    v_role_es := LOWER(BTRIM(COALESCE(v_app_meta->>'rol', '')));

    IF v_role_en = 'pendiente_revision' OR v_role_es = 'pendiente_revision' THEN
        RETURN FALSE;
    END IF;

    IF v_role_en <> '' AND v_role_es <> '' AND v_role_en <> v_role_es THEN
        RETURN FALSE;
    END IF;

    v_primary := COALESCE(NULLIF(v_role_en, ''), v_role_es);

    RETURN v_primary IN ('admin', 'superadmin', 'administrador_tecnico', 'developer');
END;
$$;

REVOKE ALL ON FUNCTION public.es_admin_tecnico() FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.es_admin_tecnico() TO authenticated, service_role;


CREATE OR REPLACE FUNCTION public.es_profesional_juridico()
RETURNS BOOLEAN
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
    v_app_meta JSONB;
    v_role_en TEXT;
    v_role_es TEXT;
    v_primary TEXT;
    v_acred TEXT;
BEGIN
    SELECT raw_app_meta_data INTO v_app_meta
    FROM auth.users
    WHERE id = (SELECT auth.uid());

    IF v_app_meta IS NULL THEN
        RETURN FALSE;
    END IF;

    IF COALESCE(v_app_meta->>'role_conflict', 'false') = 'true'
       OR COALESCE(v_app_meta->>'estado_rol', '') = 'pendiente_revision' THEN
        RETURN FALSE;
    END IF;

    v_role_en := LOWER(BTRIM(COALESCE(v_app_meta->>'role', '')));
    v_role_es := LOWER(BTRIM(COALESCE(v_app_meta->>'rol', '')));

    IF v_role_en = 'pendiente_revision' OR v_role_es = 'pendiente_revision' THEN
        RETURN FALSE;
    END IF;

    IF v_role_en <> '' AND v_role_es <> '' AND v_role_en <> v_role_es THEN
        RETURN FALSE;
    END IF;

    v_acred := LOWER(BTRIM(COALESCE(v_app_meta->>'acreditacion_juridica_verificada', '')));
    IF v_acred = 'false' THEN
        RETURN FALSE;
    END IF;

    v_primary := COALESCE(NULLIF(v_role_en, ''), v_role_es);

    IF v_primary IN (
        'abogado',
        'abogado_acreditado',
        'relator',
        'magistrado',
        'auditor_juridico',
        'profesional_juridico',
        'revisor_juridico_humana'
    ) THEN
        RETURN TRUE;
    END IF;

    IF v_acred = 'true' THEN
        RETURN TRUE;
    END IF;

    RETURN FALSE;
END;
$$;

REVOKE ALL ON FUNCTION public.es_profesional_juridico() FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.es_profesional_juridico() TO authenticated, service_role;


CREATE OR REPLACE FUNCTION public.es_gestor_calidad_autorizado()
RETURNS BOOLEAN
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
    v_app_meta JSONB;
    v_role_en TEXT;
    v_role_es TEXT;
    v_primary TEXT;
BEGIN
    IF public.es_admin_tecnico() OR public.es_profesional_juridico() THEN
        RETURN TRUE;
    END IF;

    SELECT raw_app_meta_data INTO v_app_meta
    FROM auth.users
    WHERE id = (SELECT auth.uid());

    IF v_app_meta IS NULL THEN
        RETURN FALSE;
    END IF;

    IF COALESCE(v_app_meta->>'role_conflict', 'false') = 'true'
       OR COALESCE(v_app_meta->>'estado_rol', '') = 'pendiente_revision' THEN
        RETURN FALSE;
    END IF;

    v_role_en := LOWER(BTRIM(COALESCE(v_app_meta->>'role', '')));
    v_role_es := LOWER(BTRIM(COALESCE(v_app_meta->>'rol', '')));

    IF v_role_en <> '' AND v_role_es <> '' AND v_role_en <> v_role_es THEN
        RETURN FALSE;
    END IF;

    v_primary := COALESCE(NULLIF(v_role_en, ''), v_role_es);

    RETURN v_primary IN ('auditor_documental', 'auditor_calidad', 'gestor_corpus');
END;
$$;

REVOKE ALL ON FUNCTION public.es_gestor_calidad_autorizado() FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.es_gestor_calidad_autorizado() TO authenticated, service_role;


-- -----------------------------------------------------------------------------
-- 2. PROTECCIÓN DE COLUMNAS DE ROL Y PROPIEDAD EN `public.perfiles` Y DMS (EM-02)
-- -----------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION public.proteger_permisos_perfil()
RETURNS TRIGGER
LANGUAGE plpgsql
SET search_path = ''
AS $$
BEGIN
    IF current_user IN ('authenticated', 'anon') THEN
        IF TG_OP = 'INSERT' THEN
            IF NEW.id IS DISTINCT FROM auth.uid()
               OR NEW.firma_id IS NOT NULL
               OR NEW.rol NOT IN ('abogado', 'asistente', 'usuario', 'lector') THEN
                RAISE EXCEPTION 'Los permisos del perfil solo los administra el servidor.'
                    USING ERRCODE = '42501';
            END IF;
        ELSIF NEW.id IS DISTINCT FROM OLD.id
           OR NEW.firma_id IS DISTINCT FROM OLD.firma_id
           OR NEW.rol IS DISTINCT FROM OLD.rol
           OR NEW.email IS DISTINCT FROM OLD.email THEN
            RAISE EXCEPTION 'No puedes cambiar tu firma, rol ni correo desde el cliente.'
                USING ERRCODE = '42501';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_perfiles_permisos ON public.perfiles;
CREATE TRIGGER trg_perfiles_permisos
    BEFORE INSERT OR UPDATE ON public.perfiles
    FOR EACH ROW EXECUTE FUNCTION public.proteger_permisos_perfil();


CREATE OR REPLACE FUNCTION public.proteger_propiedad_fila()
RETURNS TRIGGER
LANGUAGE plpgsql
SET search_path = ''
AS $$
DECLARE
    columna TEXT;
BEGIN
    IF current_user IN ('authenticated', 'anon') THEN
        FOREACH columna IN ARRAY TG_ARGV LOOP
            IF (to_jsonb(NEW)->columna) IS DISTINCT FROM (to_jsonb(OLD)->columna) THEN
                RAISE EXCEPTION 'No puedes reasignar la propiedad o firma de este registro.'
                    USING ERRCODE = '42501';
            END IF;
        END LOOP;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_firmas_propiedad ON public.firmas;
CREATE TRIGGER trg_firmas_propiedad
    BEFORE UPDATE ON public.firmas
    FOR EACH ROW EXECUTE FUNCTION public.proteger_propiedad_fila('id', 'creado_por');

DROP TRIGGER IF EXISTS trg_clientes_propiedad ON public.clientes;
CREATE TRIGGER trg_clientes_propiedad
    BEFORE UPDATE ON public.clientes
    FOR EACH ROW EXECUTE FUNCTION public.proteger_propiedad_fila('id', 'user_id', 'firma_id');

DROP TRIGGER IF EXISTS trg_casos_propiedad ON public.casos;
CREATE TRIGGER trg_casos_propiedad
    BEFORE UPDATE ON public.casos
    FOR EACH ROW EXECUTE FUNCTION public.proteger_propiedad_fila('id', 'user_id', 'firma_id');

DROP TRIGGER IF EXISTS trg_documentos_propiedad ON public.documentos;
CREATE TRIGGER trg_documentos_propiedad
    BEFORE UPDATE ON public.documentos
    FOR EACH ROW EXECUTE FUNCTION public.proteger_propiedad_fila('id', 'creado_por', 'firma_id');

REVOKE ALL ON TABLE public.firmas, public.perfiles, public.clientes,
    public.casos, public.documentos, public.versiones FROM PUBLIC, anon;


-- -----------------------------------------------------------------------------
-- 3. CIERRE DE TABLAS DEL CONECTOR Y AUDITORÍA DE REVISIONES (EM-01)
-- -----------------------------------------------------------------------------

ALTER TABLE public.despacho_conector_descubrimientos ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.despacho_corpus_auditoria_revisiones ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.despacho_conector_descubrimientos,
    public.despacho_corpus_auditoria_revisiones FROM PUBLIC, anon, authenticated;

GRANT SELECT ON TABLE public.despacho_conector_descubrimientos,
    public.despacho_corpus_auditoria_revisiones TO authenticated;

GRANT ALL ON TABLE public.despacho_conector_descubrimientos,
    public.despacho_corpus_auditoria_revisiones TO service_role;

DROP POLICY IF EXISTS "descubrimientos_service_all" ON public.despacho_conector_descubrimientos;
CREATE POLICY "descubrimientos_service_all"
    ON public.despacho_conector_descubrimientos
    FOR ALL TO service_role
    USING (true)
    WITH CHECK (true);

DROP POLICY IF EXISTS "descubrimientos_read_auditores" ON public.despacho_conector_descubrimientos;
CREATE POLICY "descubrimientos_read_auditores"
    ON public.despacho_conector_descubrimientos
    FOR SELECT TO authenticated
    USING (public.es_gestor_calidad_autorizado());

DROP POLICY IF EXISTS "auditoria_revisiones_service_all" ON public.despacho_corpus_auditoria_revisiones;
CREATE POLICY "auditoria_revisiones_service_all"
    ON public.despacho_corpus_auditoria_revisiones
    FOR ALL TO service_role
    USING (true)
    WITH CHECK (true);

DROP POLICY IF EXISTS "auditoria_revisiones_read_auditores" ON public.despacho_corpus_auditoria_revisiones;
CREATE POLICY "auditoria_revisiones_read_auditores"
    ON public.despacho_corpus_auditoria_revisiones
    FOR SELECT TO authenticated
    USING (public.es_gestor_calidad_autorizado());


-- -----------------------------------------------------------------------------
-- 4. AISLAMIENTO ESTRICTO DE INCIDENCIAS Y EVOLUCIÓN JURISPRUDENCIAL (EM-03)
-- -----------------------------------------------------------------------------

ALTER TABLE public.despacho_corpus_incidencias ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.despacho_corpus_incidencias FROM PUBLIC, anon, authenticated;
GRANT SELECT ON TABLE public.despacho_corpus_incidencias TO authenticated;
GRANT ALL ON TABLE public.despacho_corpus_incidencias TO service_role;

DROP POLICY IF EXISTS "incidencias_read_auth" ON public.despacho_corpus_incidencias;
DROP POLICY IF EXISTS "incidencias_read_own_or_authorized" ON public.despacho_corpus_incidencias;

CREATE POLICY "incidencias_read_own_or_authorized"
    ON public.despacho_corpus_incidencias
    FOR SELECT TO authenticated
    USING (
        (evidence->>'reported_by_id') = (SELECT auth.uid()::text)
        OR public.es_gestor_calidad_autorizado()
    );

ALTER TABLE public.despacho_corpus_evolucion_jurisprudencial ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.despacho_corpus_evolucion_jurisprudencial FROM PUBLIC, anon, authenticated;
GRANT SELECT ON TABLE public.despacho_corpus_evolucion_jurisprudencial TO authenticated;
GRANT ALL ON TABLE public.despacho_corpus_evolucion_jurisprudencial TO service_role;

DROP POLICY IF EXISTS "evolucion_read_auth" ON public.despacho_corpus_evolucion_jurisprudencial;
CREATE POLICY "evolucion_read_auth"
    ON public.despacho_corpus_evolucion_jurisprudencial
    FOR SELECT TO authenticated
    USING (
        status = 'verificado_humano'
        OR public.es_gestor_calidad_autorizado()
    );


-- -----------------------------------------------------------------------------
-- 5. REVOCACIÓN DE PERMISOS DE ESCRITURA EN TABLAS HISTÓRICAS DEL CORPUS
-- -----------------------------------------------------------------------------

ALTER TABLE public.despacho_corpus_documentos_historicos ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.despacho_corpus_fragmentos_historicos ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.despacho_corpus_documentos_historicos,
    public.despacho_corpus_fragmentos_historicos FROM PUBLIC, anon, authenticated;

GRANT SELECT ON TABLE public.despacho_corpus_documentos_historicos,
    public.despacho_corpus_fragmentos_historicos TO authenticated;

GRANT ALL ON TABLE public.despacho_corpus_documentos_historicos,
    public.despacho_corpus_fragmentos_historicos TO service_role;
