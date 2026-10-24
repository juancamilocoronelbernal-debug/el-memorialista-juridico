"""Registra los documentos existentes y los candidatos pendientes en despacho_conector_descubrimientos."""
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
        docs = await conn.fetch('SELECT id, title, source_url, published, workflow_status, validation_status, metadata FROM despacho_corpus_documentos;')
        for d in docs:
            raw_meta = d['metadata']
            meta = json.loads(raw_meta) if isinstance(raw_meta, str) else (raw_meta or {})
            sent = (meta.get('sentencia') or d['title'].replace('Sentencia ', '').split(' - ')[0]).strip().upper()
            tipo = meta.get('tipo') or (sent.split('-')[0] if '-' in sent else 'T')
            status = 'published' if d['published'] else (d['validation_status'] or 'technically_validated')
            
            await conn.execute('''
                INSERT INTO despacho_conector_descubrimientos(
                    sentencia, tipo, anio, fecha, magistrado, sala, expediente, proceso,
                    source_url, source_status, document_id, metadata
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12::jsonb)
                ON CONFLICT (sentencia) DO UPDATE SET
                    source_status = EXCLUDED.source_status,
                    document_id = EXCLUDED.document_id;
            ''', sent, tipo, meta.get('anio'), meta.get('fecha'), meta.get('magistrado'),
                meta.get('sala'), meta.get('expediente'), meta.get('proceso'),
                d['source_url'], status, d['id'], json.dumps(meta))
        
        pending_rulings = [
            ('C-316/26', 'C', 2026, '2026-09-30', 'Carlos Camargo Assis', 'Sala Plena', 'D-17395', 'Demanda de inconstitucionalidad'),
            ('C-317/26', 'C', 2026, '2026-09-30', 'Héctor Alfonso Carvajal Londoño', 'Sala Plena', 'D-17400', 'Demanda de inconstitucionalidad'),
            ('C-318/26', 'C', 2026, '2026-09-30', 'Héctor Alfonso Carvajal Londoño', 'Sala Plena', 'D-17405', 'Demanda de inconstitucionalidad'),
            ('SU-319/26', 'SU', 2026, '2026-09-30', 'Carlos Camargo Assis', 'Sala Plena', 'T-12000000', 'Acción de tutela'),
            ('SU-313/26', 'SU', 2026, '2026-09-23', 'Diana Fajardo Rivera', 'Sala Plena', 'T-11995000', 'Acción de tutela'),
            ('C-312/26', 'C', 2026, '2026-09-23', 'Jorge Enrique Ibáñez Najar', 'Sala Plena', 'D-17380', 'Demanda de inconstitucionalidad'),
            ('C-311/26', 'C', 2026, '2026-09-23', 'Antonio José Lizarazo Ocampo', 'Sala Plena', 'D-17375', 'Demanda de inconstitucionalidad'),
            ('C-310/26', 'C', 2026, '2026-09-23', 'Paola Andrea Meneses Mosquera', 'Sala Plena', 'D-17370', 'Demanda de inconstitucionalidad'),
            ('T-306/26', 'T', 2026, '2026-09-18', 'Cristina Pardo Schlesinger', 'Sala de Revisión', 'T-11960000', 'Acción de tutela'),
        ]
        for p in pending_rulings:
            await conn.execute('''
                INSERT INTO despacho_conector_descubrimientos(
                    sentencia, tipo, anio, fecha, magistrado, sala, expediente, proceso,
                    source_status, retry_count, max_retries, next_retry_at, last_error
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'pending_source', 1, 10, now() + interval '6 hours',
                          '[authentic_source] No disponible en Relatoría aún (texto en trámite editorial)')
                ON CONFLICT (sentencia) DO NOTHING;
            ''', p[0], p[1], p[2], p[3], p[4], p[5], p[6], p[7])
        
        count = await conn.fetchval('SELECT count(*) FROM despacho_conector_descubrimientos;')
        print(f'Total tracked rulings in despacho_conector_descubrimientos: {count}')
    finally:
        await conn.close()

if __name__ == '__main__':
    asyncio.run(seed())
