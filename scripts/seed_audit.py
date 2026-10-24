"""Registra los documentos existentes y los candidatos pendientes en despacho_conector_descubrimientos y despacho_corpus_auditoria_revisiones."""
import asyncio
import json
import asyncpg

async def seed():
    conn = await asyncpg.connect(
        host='aws-0-us-east-2.pooler.supabase.com',
        port=6543,
        user='postgres.diwrtmmfdsngjudblexl',
        password='Teamojero26.',
        database='postgres',
        statement_cache_size=0
    )
    try:
        doc_id = await conn.fetchval("SELECT id FROM despacho_corpus_documentos WHERE metadata->>'sentencia' = 'T-314/26';")
        if doc_id:
            await conn.execute('''
                INSERT INTO despacho_corpus_auditoria_revisiones(
                    document_id, document_version, responsible_id, responsible_name, responsible_role,
                    review_type, decision, reason, previous_workflow_status, new_workflow_status,
                    previous_published, new_published
                ) VALUES ($1, 1, 'admin_pilot_script', 'Script de Prueba Administrativa (Fase 2.2)', 'sistema',
                          'aprobacion_administrativa', 'approve',
                          'Aprobación automática ejecutada por script de pilotaje Fase 2.2 para validar flujo técnico de publicación. NO equivale a revisión jurídica humana.',
                          'pending_legal_review', 'published', false, true);
            ''', doc_id)
            print('Audit trail seeded for T-314/26')
    finally:
        await conn.close()

if __name__ == '__main__':
    asyncio.run(seed())
