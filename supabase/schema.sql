-- =============================================================================
-- EL MEMORIALISTA JURÍDICO · ESQUEMA COMPLETO DE BASE DE DATOS Y STORAGE SUPABASE
-- Versión: 2.3.0
-- Incluye: Auth (Magic Link), Tablas relacionales, Row Level Security (RLS)
-- por usuario y por firma, y configuración de Storage Privado (logo, firma, plantilla).
-- =============================================================================

-- Extensiones necesarias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- -----------------------------------------------------------------------------
-- 1. TABLA: FIRMAS (Despachos y oficinas de abogados)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.firmas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre TEXT NOT NULL,
    nit TEXT,
    dv TEXT,
    direccion TEXT,
    ciudad TEXT DEFAULT 'Bogotá D.C.',
    telefono TEXT,
    correo TEXT,
    logo_storage_path TEXT,
    plantilla_storage_path TEXT,
    configuracion JSONB DEFAULT '{}'::jsonb,
    creado_por UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- -----------------------------------------------------------------------------
-- 2. TABLA: PERFILES (Abogados y usuarios asociados a auth.users)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.perfiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    firma_id UUID REFERENCES public.firmas(id) ON DELETE SET NULL,
    email TEXT NOT NULL,
    nombre_completo TEXT NOT NULL DEFAULT '',
    tarjeta_profesional TEXT,
    cedula TEXT,
    telefono TEXT,
    direccion TEXT,
    ciudad TEXT DEFAULT 'Bogotá D.C.',
    firma_grafica_path TEXT,
    rol TEXT NOT NULL DEFAULT 'abogado' CHECK (rol IN ('admin', 'abogado', 'asistente')),
    limite_diario INT DEFAULT 50,
    redacciones_hoy INT DEFAULT 0,
    fecha_contador DATE DEFAULT CURRENT_DATE,
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- -----------------------------------------------------------------------------
-- 3. TABLA: CLIENTES (Persona natural o jurídica con DV y representante legal)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.clientes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    firma_id UUID REFERENCES public.firmas(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    tipo_persona TEXT NOT NULL DEFAULT 'natural' CHECK (tipo_persona IN ('natural', 'juridica')),
    tipo_documento TEXT NOT NULL DEFAULT 'CC' CHECK (tipo_documento IN ('CC', 'NIT', 'CE', 'TI', 'PASAPORTE', 'OTRO')),
    numero_documento TEXT NOT NULL,
    dv TEXT,
    nombre_razon_social TEXT NOT NULL,
    domicilio TEXT,
    ciudad TEXT DEFAULT 'Bogotá D.C.',
    correo TEXT,
    telefono TEXT,
    representante_legal JSONB DEFAULT NULL,
    notas TEXT,
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- -----------------------------------------------------------------------------
-- 4. TABLA: CASOS (Expedientes judiciales y administrativos)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.casos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    firma_id UUID REFERENCES public.firmas(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    cliente_id UUID REFERENCES public.clientes(id) ON DELETE SET NULL,
    nombre_caso TEXT NOT NULL,
    contraparte TEXT NOT NULL DEFAULT '',
    radicado TEXT,
    despacho TEXT,
    tipo_proceso TEXT,
    estado TEXT NOT NULL DEFAULT 'activo' CHECK (estado IN ('activo', 'en_traslado', 'para_fallo', 'archivado', 'terminado')),
    cuantia TEXT,
    fecha_notificacion DATE,
    fecha_vencimiento DATE,
    notas TEXT,
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- -----------------------------------------------------------------------------
-- 5. TABLA: DOCUMENTOS (Memoriales y escritos redactados)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.documentos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    firma_id UUID REFERENCES public.firmas(id) ON DELETE CASCADE,
    caso_id UUID REFERENCES public.casos(id) ON DELETE CASCADE,
    tipo TEXT NOT NULL,
    titulo TEXT NOT NULL,
    datos JSONB NOT NULL DEFAULT '{}'::jsonb,
    texto TEXT NOT NULL DEFAULT '',
    version INT NOT NULL DEFAULT 1,
    creado_por UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- -----------------------------------------------------------------------------
-- 6. TABLA: VERSIONES (Historial de ajustes y versiones por documento)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.versiones (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    documento_id UUID NOT NULL REFERENCES public.documentos(id) ON DELETE CASCADE,
    version INT NOT NULL,
    texto TEXT NOT NULL,
    datos JSONB NOT NULL DEFAULT '{}'::jsonb,
    creado_por UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    comentario TEXT,
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- -----------------------------------------------------------------------------
-- 7. ÍNDICES DE ALTO RENDIMIENTO
-- -----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_perfiles_firma ON public.perfiles(firma_id);
CREATE INDEX IF NOT EXISTS idx_clientes_firma ON public.clientes(firma_id);
CREATE INDEX IF NOT EXISTS idx_clientes_user ON public.clientes(user_id);
CREATE INDEX IF NOT EXISTS idx_casos_cliente ON public.casos(cliente_id);
CREATE INDEX IF NOT EXISTS idx_casos_firma ON public.casos(firma_id);
CREATE INDEX IF NOT EXISTS idx_casos_user ON public.casos(user_id);
CREATE INDEX IF NOT EXISTS idx_casos_radicado ON public.casos(radicado);
CREATE INDEX IF NOT EXISTS idx_documentos_caso ON public.documentos(caso_id);
CREATE INDEX IF NOT EXISTS idx_documentos_firma ON public.documentos(firma_id);
CREATE INDEX IF NOT EXISTS idx_documentos_creado_por ON public.documentos(creado_por);
CREATE INDEX IF NOT EXISTS idx_versiones_documento ON public.versiones(documento_id);

-- -----------------------------------------------------------------------------
-- 8. TRIGGERS Y FUNCIONES AUTOMÁTICAS
-- -----------------------------------------------------------------------------

-- Función para actualizar updated_at
CREATE OR REPLACE FUNCTION public.actualizar_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = TIMEZONE('utc'::text, NOW());
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_firmas_updated_at ON public.firmas;
CREATE TRIGGER trg_firmas_updated_at BEFORE UPDATE ON public.firmas FOR EACH ROW EXECUTE FUNCTION public.actualizar_updated_at();

DROP TRIGGER IF EXISTS trg_perfiles_updated_at ON public.perfiles;
CREATE TRIGGER trg_perfiles_updated_at BEFORE UPDATE ON public.perfiles FOR EACH ROW EXECUTE FUNCTION public.actualizar_updated_at();

DROP TRIGGER IF EXISTS trg_clientes_updated_at ON public.clientes;
CREATE TRIGGER trg_clientes_updated_at BEFORE UPDATE ON public.clientes FOR EACH ROW EXECUTE FUNCTION public.actualizar_updated_at();

DROP TRIGGER IF EXISTS trg_casos_updated_at ON public.casos;
CREATE TRIGGER trg_casos_updated_at BEFORE UPDATE ON public.casos FOR EACH ROW EXECUTE FUNCTION public.actualizar_updated_at();

DROP TRIGGER IF EXISTS trg_documentos_updated_at ON public.documentos;
CREATE TRIGGER trg_documentos_updated_at BEFORE UPDATE ON public.documentos FOR EACH ROW EXECUTE FUNCTION public.actualizar_updated_at();

-- Función para crear perfil y firma personal automáticamente al registrarse en auth.users
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
DECLARE
    nueva_firma_id UUID;
    nombre_defecto TEXT;
BEGIN
    nombre_defecto := COALESCE(NEW.raw_user_meta_data->>'nombre', split_part(NEW.email, '@', 1));
    
    -- Crea una firma por defecto para el nuevo usuario
    INSERT INTO public.firmas (nombre, correo, creado_por)
    VALUES ('Despacho de ' || nombre_defecto, NEW.email, NEW.id)
    RETURNING id INTO nueva_firma_id;

    -- Crea el perfil asociado al usuario y su firma
    INSERT INTO public.perfiles (id, firma_id, email, nombre_completo, rol)
    VALUES (NEW.id, nueva_firma_id, NEW.email, nombre_defecto, 'admin');

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- Helper para consultar la firma del usuario autenticado de forma segura
CREATE OR REPLACE FUNCTION public.obtener_mi_firma_id()
RETURNS UUID AS $$
    SELECT firma_id FROM public.perfiles WHERE id = auth.uid();
$$ LANGUAGE sql STABLE SECURITY DEFINER;

-- -----------------------------------------------------------------------------
-- 9. ROW LEVEL SECURITY (RLS) POR USUARIO Y POR FIRMA
-- -----------------------------------------------------------------------------

ALTER TABLE public.firmas ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.perfiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.clientes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.casos ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.documentos ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.versiones ENABLE ROW LEVEL SECURITY;

-- Políticas para FIRMAS
CREATE POLICY "firmas_select" ON public.firmas
    FOR SELECT TO authenticated
    USING (id = public.obtener_mi_firma_id() OR creado_por = auth.uid());

CREATE POLICY "firmas_update" ON public.firmas
    FOR UPDATE TO authenticated
    USING (id = public.obtener_mi_firma_id() OR creado_por = auth.uid())
    WITH CHECK (id = public.obtener_mi_firma_id() OR creado_por = auth.uid());

CREATE POLICY "firmas_insert" ON public.firmas
    FOR INSERT TO authenticated
    WITH CHECK (auth.uid() IS NOT NULL);

-- Políticas para PERFILES
CREATE POLICY "perfiles_select" ON public.perfiles
    FOR SELECT TO authenticated
    USING (id = auth.uid() OR (firma_id IS NOT NULL AND firma_id = public.obtener_mi_firma_id()));

CREATE POLICY "perfiles_update" ON public.perfiles
    FOR UPDATE TO authenticated
    USING (id = auth.uid())
    WITH CHECK (id = auth.uid());

CREATE POLICY "perfiles_insert" ON public.perfiles
    FOR INSERT TO authenticated
    WITH CHECK (id = auth.uid());

-- Políticas para CLIENTES
CREATE POLICY "clientes_select" ON public.clientes
    FOR SELECT TO authenticated
    USING (user_id = auth.uid() OR (firma_id IS NOT NULL AND firma_id = public.obtener_mi_firma_id()));

CREATE POLICY "clientes_insert" ON public.clientes
    FOR INSERT TO authenticated
    WITH CHECK (user_id = auth.uid() OR (firma_id IS NOT NULL AND firma_id = public.obtener_mi_firma_id()));

CREATE POLICY "clientes_update" ON public.clientes
    FOR UPDATE TO authenticated
    USING (user_id = auth.uid() OR (firma_id IS NOT NULL AND firma_id = public.obtener_mi_firma_id()))
    WITH CHECK (user_id = auth.uid() OR (firma_id IS NOT NULL AND firma_id = public.obtener_mi_firma_id()));

CREATE POLICY "clientes_delete" ON public.clientes
    FOR DELETE TO authenticated
    USING (user_id = auth.uid() OR (firma_id IS NOT NULL AND firma_id = public.obtener_mi_firma_id()));

-- Políticas para CASOS
CREATE POLICY "casos_select" ON public.casos
    FOR SELECT TO authenticated
    USING (user_id = auth.uid() OR (firma_id IS NOT NULL AND firma_id = public.obtener_mi_firma_id()));

CREATE POLICY "casos_insert" ON public.casos
    FOR INSERT TO authenticated
    WITH CHECK (user_id = auth.uid() OR (firma_id IS NOT NULL AND firma_id = public.obtener_mi_firma_id()));

CREATE POLICY "casos_update" ON public.casos
    FOR UPDATE TO authenticated
    USING (user_id = auth.uid() OR (firma_id IS NOT NULL AND firma_id = public.obtener_mi_firma_id()))
    WITH CHECK (user_id = auth.uid() OR (firma_id IS NOT NULL AND firma_id = public.obtener_mi_firma_id()));

CREATE POLICY "casos_delete" ON public.casos
    FOR DELETE TO authenticated
    USING (user_id = auth.uid() OR (firma_id IS NOT NULL AND firma_id = public.obtener_mi_firma_id()));

-- Políticas para DOCUMENTOS
CREATE POLICY "documentos_select" ON public.documentos
    FOR SELECT TO authenticated
    USING (creado_por = auth.uid() OR (firma_id IS NOT NULL AND firma_id = public.obtener_mi_firma_id()));

CREATE POLICY "documentos_insert" ON public.documentos
    FOR INSERT TO authenticated
    WITH CHECK (creado_por = auth.uid() OR (firma_id IS NOT NULL AND firma_id = public.obtener_mi_firma_id()));

CREATE POLICY "documentos_update" ON public.documentos
    FOR UPDATE TO authenticated
    USING (creado_por = auth.uid() OR (firma_id IS NOT NULL AND firma_id = public.obtener_mi_firma_id()))
    WITH CHECK (creado_por = auth.uid() OR (firma_id IS NOT NULL AND firma_id = public.obtener_mi_firma_id()));

CREATE POLICY "documentos_delete" ON public.documentos
    FOR DELETE TO authenticated
    USING (creado_por = auth.uid() OR (firma_id IS NOT NULL AND firma_id = public.obtener_mi_firma_id()));

-- Políticas para VERSIONES
CREATE POLICY "versiones_select" ON public.versiones
    FOR SELECT TO authenticated
    USING (documento_id IN (
        SELECT id FROM public.documentos
        WHERE creado_por = auth.uid() OR (firma_id IS NOT NULL AND firma_id = public.obtener_mi_firma_id())
    ));

CREATE POLICY "versiones_insert" ON public.versiones
    FOR INSERT TO authenticated
    WITH CHECK (documento_id IN (
        SELECT id FROM public.documentos
        WHERE creado_por = auth.uid() OR (firma_id IS NOT NULL AND firma_id = public.obtener_mi_firma_id())
    ));

CREATE POLICY "versiones_delete" ON public.versiones
    FOR DELETE TO authenticated
    USING (documento_id IN (
        SELECT id FROM public.documentos
        WHERE creado_por = auth.uid() OR (firma_id IS NOT NULL AND firma_id = public.obtener_mi_firma_id())
    ));

-- -----------------------------------------------------------------------------
-- 10. CONFIGURACIÓN DE STORAGE PRIVADO
-- -----------------------------------------------------------------------------
-- Crea el bucket privado 'archivos-privados' para logo, firma y plantilla
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'archivos-privados',
    'archivos-privados',
    false,
    10485760, -- 10 MB
    ARRAY['image/png', 'image/jpeg', 'image/webp', 'image/svg+xml', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/pdf']
)
ON CONFLICT (id) DO UPDATE SET
    public = false,
    file_size_limit = 10485760;

-- Políticas de RLS en storage.objects
CREATE POLICY "storage_archivos_privados_select" ON storage.objects
    FOR SELECT TO authenticated
    USING (
        bucket_id = 'archivos-privados' AND (
            (storage.foldername(name))[2] = auth.uid()::text OR
            (storage.foldername(name))[2] = public.obtener_mi_firma_id()::text
        )
    );

CREATE POLICY "storage_archivos_privados_insert" ON storage.objects
    FOR INSERT TO authenticated
    WITH CHECK (
        bucket_id = 'archivos-privados' AND (
            (storage.foldername(name))[2] = auth.uid()::text OR
            (storage.foldername(name))[2] = public.obtener_mi_firma_id()::text
        )
    );

CREATE POLICY "storage_archivos_privados_update" ON storage.objects
    FOR UPDATE TO authenticated
    USING (
        bucket_id = 'archivos-privados' AND (
            (storage.foldername(name))[2] = auth.uid()::text OR
            (storage.foldername(name))[2] = public.obtener_mi_firma_id()::text
        )
    );

CREATE POLICY "storage_archivos_privados_delete" ON storage.objects
    FOR DELETE TO authenticated
    USING (
        bucket_id = 'archivos-privados' AND (
            (storage.foldername(name))[2] = auth.uid()::text OR
            (storage.foldername(name))[2] = public.obtener_mi_firma_id()::text
        )
    );
