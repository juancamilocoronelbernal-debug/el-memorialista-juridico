-- =============================================================================
-- EL MEMORIALISTA 3.0 · CIERRE DE AISLAMIENTO POR CUENTA Y FIRMA
-- Aplicar como propietario de la base (SQL Editor). Es idempotente.
-- No cambia ni elimina datos existentes. Reemplaza políticas de esta aplicación.
-- =============================================================================

-- Solo el trigger de Auth crea la firma personal. Nunca se aceptan firma/rol
-- procedentes de user_metadata. Los SECURITY DEFINER fijan search_path vacío.
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE
    nueva_firma_id UUID;
    nombre_defecto TEXT;
BEGIN
    nombre_defecto := left(COALESCE(NULLIF(NEW.raw_user_meta_data->>'nombre', ''),
                                  split_part(COALESCE(NEW.email, ''), '@', 1), 'Usuario'), 200);
    INSERT INTO public.firmas (nombre, correo, creado_por)
    VALUES ('Despacho de ' || nombre_defecto, COALESCE(NEW.email, ''), NEW.id)
    RETURNING id INTO nueva_firma_id;
    INSERT INTO public.perfiles (id, firma_id, email, nombre_completo, rol)
    VALUES (NEW.id, nueva_firma_id, COALESCE(NEW.email, ''), nombre_defecto, 'admin');
    RETURN NEW;
END;
$$;
REVOKE ALL ON FUNCTION public.handle_new_user() FROM PUBLIC, anon, authenticated;
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

CREATE OR REPLACE FUNCTION public.obtener_mi_firma_id()
RETURNS UUID LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
    SELECT firma_id FROM public.perfiles WHERE id = (SELECT auth.uid());
$$;
REVOKE ALL ON FUNCTION public.obtener_mi_firma_id() FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.obtener_mi_firma_id() TO authenticated, service_role;

CREATE OR REPLACE FUNCTION public.soy_admin_de_firma(p_firma UUID)
RETURNS BOOLEAN LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
    SELECT EXISTS (SELECT 1 FROM public.perfiles
        WHERE id = (SELECT auth.uid()) AND firma_id = p_firma AND rol = 'admin');
$$;
REVOKE ALL ON FUNCTION public.soy_admin_de_firma(UUID) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.soy_admin_de_firma(UUID) TO authenticated, service_role;

-- La política de una fila no basta para impedir editar sus columnas de permiso.
-- Este trigger se ejecuta con el rol invocante; las tareas administrativas y el
-- trigger de alta siguen pudiendo crear perfiles de despacho legítimos.
CREATE OR REPLACE FUNCTION public.proteger_permisos_perfil()
RETURNS TRIGGER LANGUAGE plpgsql SET search_path = '' AS $$
BEGIN
    IF current_user IN ('authenticated', 'anon') THEN
        IF TG_OP = 'INSERT' THEN
            IF NEW.id IS DISTINCT FROM auth.uid() OR NEW.firma_id IS NOT NULL
               OR NEW.rol <> 'abogado' OR NEW.limite_diario IS DISTINCT FROM 50
               OR NEW.redacciones_hoy IS DISTINCT FROM 0
               OR NEW.fecha_contador IS DISTINCT FROM CURRENT_DATE THEN
                RAISE EXCEPTION 'Los permisos del perfil solo los administra el servidor.' USING ERRCODE = '42501';
            END IF;
        ELSIF NEW.id IS DISTINCT FROM OLD.id
           OR NEW.firma_id IS DISTINCT FROM OLD.firma_id
           OR NEW.rol IS DISTINCT FROM OLD.rol
           OR NEW.limite_diario IS DISTINCT FROM OLD.limite_diario
           OR NEW.redacciones_hoy IS DISTINCT FROM OLD.redacciones_hoy
           OR NEW.fecha_contador IS DISTINCT FROM OLD.fecha_contador THEN
            RAISE EXCEPTION 'No puedes cambiar tu firma, rol ni cuota desde el cliente.' USING ERRCODE = '42501';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;
REVOKE ALL ON FUNCTION public.proteger_permisos_perfil() FROM PUBLIC, anon, authenticated;
DROP TRIGGER IF EXISTS trg_perfiles_permisos ON public.perfiles;
CREATE TRIGGER trg_perfiles_permisos BEFORE INSERT OR UPDATE ON public.perfiles
    FOR EACH ROW EXECUTE FUNCTION public.proteger_permisos_perfil();

-- Conservar la identidad y el ámbito de una fila al actualizar impide apropiarse
-- de datos compartidos o publicarlos accidentalmente en otro despacho.
CREATE OR REPLACE FUNCTION public.proteger_propiedad_fila()
RETURNS TRIGGER LANGUAGE plpgsql SET search_path = '' AS $$
DECLARE columna TEXT;
BEGIN
    IF current_user IN ('authenticated', 'anon') THEN
        FOREACH columna IN ARRAY TG_ARGV LOOP
            IF (to_jsonb(NEW)->columna) IS DISTINCT FROM (to_jsonb(OLD)->columna) THEN
                RAISE EXCEPTION 'No puedes reasignar la propiedad o firma de este registro.' USING ERRCODE = '42501';
            END IF;
        END LOOP;
    END IF;
    RETURN NEW;
END;
$$;
REVOKE ALL ON FUNCTION public.proteger_propiedad_fila() FROM PUBLIC, anon, authenticated;
DROP TRIGGER IF EXISTS trg_firmas_propiedad ON public.firmas;
CREATE TRIGGER trg_firmas_propiedad BEFORE UPDATE ON public.firmas
    FOR EACH ROW EXECUTE FUNCTION public.proteger_propiedad_fila('id', 'creado_por');
DROP TRIGGER IF EXISTS trg_clientes_propiedad ON public.clientes;
CREATE TRIGGER trg_clientes_propiedad BEFORE UPDATE ON public.clientes
    FOR EACH ROW EXECUTE FUNCTION public.proteger_propiedad_fila('id', 'user_id', 'firma_id');
DROP TRIGGER IF EXISTS trg_casos_propiedad ON public.casos;
CREATE TRIGGER trg_casos_propiedad BEFORE UPDATE ON public.casos
    FOR EACH ROW EXECUTE FUNCTION public.proteger_propiedad_fila('id', 'user_id', 'firma_id');
DROP TRIGGER IF EXISTS trg_documentos_propiedad ON public.documentos;
CREATE TRIGGER trg_documentos_propiedad BEFORE UPDATE ON public.documentos
    FOR EACH ROW EXECUTE FUNCTION public.proteger_propiedad_fila('id', 'creado_por', 'firma_id');

-- Administración explícita, exclusivamente desde backend con service_role o
-- SQL Editor. No es una RPC que los usuarios puedan invocar para autoinscribirse.
-- Reasignar una persona no traslada automáticamente sus documentos anteriores.
CREATE OR REPLACE FUNCTION public.administrar_membresia(
    p_usuario UUID, p_firma UUID, p_rol TEXT DEFAULT 'abogado')
RETURNS VOID LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
BEGIN
    IF p_rol IS NULL OR p_rol NOT IN ('admin', 'abogado', 'asistente') THEN
        RAISE EXCEPTION 'Rol inválido.' USING ERRCODE = '22023';
    END IF;
    IF p_firma IS NOT NULL AND NOT EXISTS (SELECT 1 FROM public.firmas WHERE id = p_firma) THEN
        RAISE EXCEPTION 'La firma no existe.' USING ERRCODE = '22023';
    END IF;
    UPDATE public.perfiles SET firma_id = p_firma, rol = p_rol WHERE id = p_usuario;
    IF NOT FOUND THEN RAISE EXCEPTION 'El usuario no tiene perfil.' USING ERRCODE = '22023'; END IF;
END;
$$;
REVOKE ALL ON FUNCTION public.administrar_membresia(UUID, UUID, TEXT) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.administrar_membresia(UUID, UUID, TEXT) TO service_role;

-- Las cascadas FK no vuelven a evaluar la política DELETE de cada descendiente.
-- Antes de borrar un documento/caso, comprobar también sus versiones/documentos
-- evita que su autor borre el trabajo de un compañero indirectamente. Estas
-- consultas leen el árbol completo (incluso datos heredados con ámbitos errados).
CREATE OR REPLACE FUNCTION public.puede_eliminar_documento(p_documento UUID)
RETURNS BOOLEAN LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
    SELECT EXISTS (SELECT 1 FROM public.documentos d WHERE d.id = p_documento
        AND (public.soy_admin_de_firma(d.firma_id)
            OR (d.creado_por = (SELECT auth.uid())
                AND NOT EXISTS (SELECT 1 FROM public.versiones v
                    WHERE v.documento_id = d.id
                      AND v.creado_por IS DISTINCT FROM (SELECT auth.uid())))));
$$;
REVOKE ALL ON FUNCTION public.puede_eliminar_documento(UUID) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.puede_eliminar_documento(UUID) TO authenticated, service_role;

CREATE OR REPLACE FUNCTION public.puede_eliminar_caso(p_caso UUID)
RETURNS BOOLEAN LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
    SELECT EXISTS (SELECT 1 FROM public.casos c WHERE c.id = p_caso
        AND (c.user_id = (SELECT auth.uid()) OR public.soy_admin_de_firma(c.firma_id))
        AND NOT EXISTS (SELECT 1 FROM public.documentos d WHERE d.caso_id = c.id
            AND NOT public.puede_eliminar_documento(d.id)));
$$;
REVOKE ALL ON FUNCTION public.puede_eliminar_caso(UUID) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.puede_eliminar_caso(UUID) TO authenticated, service_role;

-- RLS + permisos de tabla. Ninguna tabla de expedientes es pública.
ALTER TABLE public.firmas ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.perfiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.clientes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.casos ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.documentos ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.versiones ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.firmas, public.perfiles, public.clientes,
    public.casos, public.documentos, public.versiones FROM PUBLIC, anon, authenticated;
GRANT SELECT, UPDATE ON public.firmas TO authenticated;
GRANT SELECT, INSERT, UPDATE ON public.perfiles TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.clientes, public.casos, public.documentos TO authenticated;
GRANT SELECT, INSERT, DELETE ON public.versiones TO authenticated;
GRANT ALL ON public.firmas, public.perfiles, public.clientes,
    public.casos, public.documentos, public.versiones TO service_role;

DROP POLICY IF EXISTS "firmas_select" ON public.firmas;
CREATE POLICY "firmas_select" ON public.firmas
    FOR SELECT TO authenticated
    USING (id = public.obtener_mi_firma_id() OR creado_por = (SELECT auth.uid()));

DROP POLICY IF EXISTS "firmas_update" ON public.firmas;
CREATE POLICY "firmas_update" ON public.firmas
    FOR UPDATE TO authenticated
    USING (public.soy_admin_de_firma(id))
    WITH CHECK (public.soy_admin_de_firma(id));

DROP POLICY IF EXISTS "firmas_insert" ON public.firmas;

DROP POLICY IF EXISTS "perfiles_select" ON public.perfiles;
CREATE POLICY "perfiles_select" ON public.perfiles
    FOR SELECT TO authenticated
    USING (id = (SELECT auth.uid()) OR (firma_id IS NOT NULL AND firma_id = public.obtener_mi_firma_id()));

DROP POLICY IF EXISTS "perfiles_update" ON public.perfiles;
CREATE POLICY "perfiles_update" ON public.perfiles
    FOR UPDATE TO authenticated
    USING (id = (SELECT auth.uid()))
    WITH CHECK (id = (SELECT auth.uid()));

DROP POLICY IF EXISTS "perfiles_insert" ON public.perfiles;
CREATE POLICY "perfiles_insert" ON public.perfiles
    FOR INSERT TO authenticated
    WITH CHECK (id = (SELECT auth.uid()) AND firma_id IS NULL AND rol = 'abogado' AND limite_diario = 50 AND redacciones_hoy = 0 AND fecha_contador = CURRENT_DATE);

DROP POLICY IF EXISTS "clientes_select" ON public.clientes;
CREATE POLICY "clientes_select" ON public.clientes
    FOR SELECT TO authenticated
    USING (user_id = (SELECT auth.uid()) OR (firma_id IS NOT NULL AND firma_id = public.obtener_mi_firma_id()));

DROP POLICY IF EXISTS "clientes_insert" ON public.clientes;
CREATE POLICY "clientes_insert" ON public.clientes
    FOR INSERT TO authenticated
    WITH CHECK (user_id = (SELECT auth.uid()) AND (firma_id IS NULL OR firma_id = public.obtener_mi_firma_id()));

DROP POLICY IF EXISTS "clientes_update" ON public.clientes;
CREATE POLICY "clientes_update" ON public.clientes
    FOR UPDATE TO authenticated
    USING (user_id = (SELECT auth.uid()) OR (firma_id IS NOT NULL AND firma_id = public.obtener_mi_firma_id()))
    WITH CHECK ((user_id = (SELECT auth.uid()) OR (firma_id IS NOT NULL AND firma_id = public.obtener_mi_firma_id())));

DROP POLICY IF EXISTS "clientes_delete" ON public.clientes;
CREATE POLICY "clientes_delete" ON public.clientes
    FOR DELETE TO authenticated
    USING (user_id = (SELECT auth.uid()) OR public.soy_admin_de_firma(firma_id));

DROP POLICY IF EXISTS "casos_select" ON public.casos;
CREATE POLICY "casos_select" ON public.casos
    FOR SELECT TO authenticated
    USING (user_id = (SELECT auth.uid()) OR (firma_id IS NOT NULL AND firma_id = public.obtener_mi_firma_id()));

DROP POLICY IF EXISTS "casos_insert" ON public.casos;
CREATE POLICY "casos_insert" ON public.casos
    FOR INSERT TO authenticated
    WITH CHECK (user_id = (SELECT auth.uid()) AND (firma_id IS NULL OR firma_id = public.obtener_mi_firma_id()) AND (cliente_id IS NULL OR EXISTS (SELECT 1 FROM public.clientes c WHERE c.id = casos.cliente_id AND c.firma_id IS NOT DISTINCT FROM casos.firma_id)));

DROP POLICY IF EXISTS "casos_update" ON public.casos;
CREATE POLICY "casos_update" ON public.casos
    FOR UPDATE TO authenticated
    USING (user_id = (SELECT auth.uid()) OR (firma_id IS NOT NULL AND firma_id = public.obtener_mi_firma_id()))
    WITH CHECK ((user_id = (SELECT auth.uid()) OR (firma_id IS NOT NULL AND firma_id = public.obtener_mi_firma_id())) AND (cliente_id IS NULL OR EXISTS (SELECT 1 FROM public.clientes c WHERE c.id = casos.cliente_id AND c.firma_id IS NOT DISTINCT FROM casos.firma_id)));

DROP POLICY IF EXISTS "casos_delete" ON public.casos;
CREATE POLICY "casos_delete" ON public.casos
    FOR DELETE TO authenticated
    USING (public.puede_eliminar_caso(id));

DROP POLICY IF EXISTS "documentos_select" ON public.documentos;
CREATE POLICY "documentos_select" ON public.documentos
    FOR SELECT TO authenticated
    USING (creado_por = (SELECT auth.uid()) OR (firma_id IS NOT NULL AND firma_id = public.obtener_mi_firma_id()));

DROP POLICY IF EXISTS "documentos_insert" ON public.documentos;
CREATE POLICY "documentos_insert" ON public.documentos
    FOR INSERT TO authenticated
    WITH CHECK (creado_por = (SELECT auth.uid()) AND (firma_id IS NULL OR firma_id = public.obtener_mi_firma_id()) AND (caso_id IS NULL OR EXISTS (SELECT 1 FROM public.casos c WHERE c.id = documentos.caso_id AND c.firma_id IS NOT DISTINCT FROM documentos.firma_id)));

DROP POLICY IF EXISTS "documentos_update" ON public.documentos;
CREATE POLICY "documentos_update" ON public.documentos
    FOR UPDATE TO authenticated
    USING (creado_por = (SELECT auth.uid()) OR (firma_id IS NOT NULL AND firma_id = public.obtener_mi_firma_id()))
    WITH CHECK ((creado_por = (SELECT auth.uid()) OR (firma_id IS NOT NULL AND firma_id = public.obtener_mi_firma_id())) AND (caso_id IS NULL OR EXISTS (SELECT 1 FROM public.casos c WHERE c.id = documentos.caso_id AND c.firma_id IS NOT DISTINCT FROM documentos.firma_id)));

DROP POLICY IF EXISTS "documentos_delete" ON public.documentos;
CREATE POLICY "documentos_delete" ON public.documentos
    FOR DELETE TO authenticated
    USING (public.puede_eliminar_documento(id));

DROP POLICY IF EXISTS "versiones_select" ON public.versiones;
CREATE POLICY "versiones_select" ON public.versiones
    FOR SELECT TO authenticated
    USING (EXISTS (SELECT 1 FROM public.documentos d WHERE d.id = versiones.documento_id));

DROP POLICY IF EXISTS "versiones_insert" ON public.versiones;
CREATE POLICY "versiones_insert" ON public.versiones
    FOR INSERT TO authenticated
    WITH CHECK (creado_por = (SELECT auth.uid()) AND EXISTS (SELECT 1 FROM public.documentos d WHERE d.id = versiones.documento_id));

DROP POLICY IF EXISTS "versiones_delete" ON public.versiones;
CREATE POLICY "versiones_delete" ON public.versiones
    FOR DELETE TO authenticated
    USING (EXISTS (SELECT 1 FROM public.documentos d WHERE d.id = versiones.documento_id) AND (creado_por = (SELECT auth.uid()) OR EXISTS (SELECT 1 FROM public.documentos d WHERE d.id = versiones.documento_id AND public.soy_admin_de_firma(d.firma_id))));

DROP POLICY IF EXISTS "versiones_update" ON public.versiones;

-- Bucket privado. No se permiten rutas arbitrarias ni cruces entre carpetas.
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES ('archivos-privados', 'archivos-privados', false, 10485760,
    ARRAY['image/png', 'image/jpeg', 'image/webp',
          'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/pdf'])
ON CONFLICT (id) DO UPDATE SET public = false,
    file_size_limit = EXCLUDED.file_size_limit,
    allowed_mime_types = EXCLUDED.allowed_mime_types;

CREATE OR REPLACE FUNCTION public.puede_acceder_archivo_privado(ruta TEXT, escritura BOOLEAN DEFAULT false)
RETURNS BOOLEAN LANGUAGE sql STABLE SET search_path = '' AS $$
    SELECT (auth.uid() IS NOT NULL) AND (
        ((storage.foldername(ruta))[1] IN ('logo', 'firma', 'plantilla')
            AND (storage.foldername(ruta))[2] = auth.uid()::text)
        OR ((storage.foldername(ruta))[1] = 'despacho'
            AND (storage.foldername(ruta))[2] = public.obtener_mi_firma_id()::text
            AND (NOT escritura OR public.soy_admin_de_firma(public.obtener_mi_firma_id())))
    );
$$;
REVOKE ALL ON FUNCTION public.puede_acceder_archivo_privado(TEXT, BOOLEAN) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.puede_acceder_archivo_privado(TEXT, BOOLEAN) TO authenticated, service_role;
DROP POLICY IF EXISTS "storage_archivos_privados_select" ON storage.objects;
CREATE POLICY "storage_archivos_privados_select" ON storage.objects
    FOR SELECT TO authenticated
    USING (bucket_id = 'archivos-privados' AND public.puede_acceder_archivo_privado(name, false));

DROP POLICY IF EXISTS "storage_archivos_privados_insert" ON storage.objects;
CREATE POLICY "storage_archivos_privados_insert" ON storage.objects
    FOR INSERT TO authenticated
    WITH CHECK (bucket_id = 'archivos-privados' AND public.puede_acceder_archivo_privado(name, true));

DROP POLICY IF EXISTS "storage_archivos_privados_update" ON storage.objects;
CREATE POLICY "storage_archivos_privados_update" ON storage.objects
    FOR UPDATE TO authenticated
    USING (bucket_id = 'archivos-privados' AND public.puede_acceder_archivo_privado(name, true))
    WITH CHECK (bucket_id = 'archivos-privados' AND public.puede_acceder_archivo_privado(name, true));

DROP POLICY IF EXISTS "storage_archivos_privados_delete" ON storage.objects;
CREATE POLICY "storage_archivos_privados_delete" ON storage.objects
    FOR DELETE TO authenticated
    USING (bucket_id = 'archivos-privados' AND public.puede_acceder_archivo_privado(name, true));
