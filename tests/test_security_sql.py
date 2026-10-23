"""Contratos estáticos de la migración de aislamiento.

No sustituyen una ejecución RLS: supabase/tests/aislamiento_cuentas.sql ofrece
pruebas transaccionales con roles reales para una instancia de prueba.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = (ROOT / 'supabase/schema.sql').read_text(encoding='utf-8')
MIGRATION = (ROOT / 'supabase/migrations/20261022010000_separacion_publica_privada_rls.sql').read_text(encoding='utf-8')


def test_migracion_aplicable_en_sql_editor_sin_metacomandos():
    for path in (ROOT / 'supabase/migrations').glob('*.sql'):
        assert not re.search(r'^\s*\\', path.read_text(), re.M), path.name
    assert MIGRATION.strip() in SCHEMA


def test_security_definer_fija_search_path_en_todas_funciones():
    definitions = re.findall(r'CREATE OR REPLACE FUNCTION\s+(.*?)\$\$;', MIGRATION, re.S | re.I)
    assert definitions
    for definition in definitions:
        if 'SECURITY DEFINER' in definition:
            assert "SET search_path = ''" in definition, definition[:80]


def test_cierre_perfil_autoreasignacion_y_cuota():
    for field in ('id', 'firma_id', 'rol', 'limite_diario', 'redacciones_hoy', 'fecha_contador'):
        assert f'NEW.{field} IS DISTINCT FROM OLD.{field}' in MIGRATION
    assert 'BEFORE INSERT OR UPDATE ON public.perfiles' in MIGRATION
    assert "NEW.rol <> 'abogado'" in MIGRATION
    assert 'NEW.firma_id IS NOT NULL' in MIGRATION


def test_administracion_membresia_restringida_al_servidor():
    signature = 'public.administrar_membresia(UUID, UUID, TEXT)'
    assert f'REVOKE ALL ON FUNCTION {signature} FROM PUBLIC, anon, authenticated' in MIGRATION
    assert f'GRANT EXECUTE ON FUNCTION {signature} TO service_role' in MIGRATION
    assert 'FROM anon, authenticated' not in MIGRATION.split('REVOKE ALL ON TABLE')[1].split(';')[0]
    assert 'FROM PUBLIC, anon, authenticated' in MIGRATION.split('REVOKE ALL ON TABLE')[1].split(';')[0]


def test_propiedad_inmutable_y_relaciones_del_mismo_ambito():
    for table in ('clientes', 'casos', 'documentos'):
        assert f'BEFORE UPDATE ON public.{table}' in MIGRATION
    assert 'c.firma_id IS NOT DISTINCT FROM casos.firma_id' in MIGRATION
    assert 'c.firma_id IS NOT DISTINCT FROM documentos.firma_id' in MIGRATION
    assert 'creado_por = (SELECT auth.uid()) AND EXISTS' in MIGRATION


def test_politicas_idempotentes_y_grants_minimos():
    policies = re.findall(r'CREATE POLICY "([^"]+)" ON ([\w.]+)', MIGRATION)
    assert len(policies) >= 20
    for name, table in policies:
        assert f'DROP POLICY IF EXISTS "{name}" ON {table};' in MIGRATION
    assert 'GRANT SELECT, INSERT, DELETE ON public.versiones' in MIGRATION
    assert 'GRANT SELECT, UPDATE ON public.firmas' in MIGRATION


def test_borrado_valida_descendientes_para_evitar_cascadas_ajenas():
    for name, helper in (('casos_delete', 'puede_eliminar_caso'),
                         ('documentos_delete', 'puede_eliminar_documento')):
        policy = MIGRATION.split(f'CREATE POLICY "{name}"')[1].split(';')[0]
        assert f'USING (public.{helper}(id))' in policy
        assert f'REVOKE ALL ON FUNCTION public.{helper}(UUID) FROM PUBLIC, anon' in MIGRATION
    assert 'v.creado_por IS DISTINCT FROM (SELECT auth.uid())' in MIGRATION
    assert 'AND NOT public.puede_eliminar_documento(d.id)' in MIGRATION


def test_storage_actualizacion_valida_ruta_destino_y_origen():
    policy = MIGRATION.split('CREATE POLICY "storage_archivos_privados_update"')[1].split(';')[0]
    assert 'USING' in policy and 'WITH CHECK' in policy
    assert policy.count('public.puede_acceder_archivo_privado(name, true)') == 2
    assert "IN ('logo', 'firma', 'plantilla')" in MIGRATION
    assert "[1] = 'despacho'" in MIGRATION
    assert 'NOT escritura OR public.soy_admin_de_firma' in MIGRATION
    assert "image/svg+xml" not in MIGRATION
    assert "public = false" in MIGRATION


def test_script_real_cubre_roles_y_revierte_datos():
    sql = (ROOT / 'supabase/tests/aislamiento_cuentas.sql').read_text(encoding='utf-8')
    assert 'SET LOCAL ROLE authenticated' in sql
    assert 'SET LOCAL ROLE anon' in sql
    assert 'request.jwt.claims' in sql
    assert sql.strip().endswith('ROLLBACK;')
