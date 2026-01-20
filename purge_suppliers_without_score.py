import sqlite3
from datetime import datetime

conn = sqlite3.connect('data/production/peptide_management.db')
cur = conn.cursor()

print('='*70)
print('ELIMINAZIONE SUPPLIERS SENZA SCORE')
print('='*70)

# Trova suppliers senza score
cur.execute('''
    SELECT id, name, country, website
    FROM suppliers
    WHERE deleted_at IS NULL
      AND janoshik_quality_score IS NULL
    ORDER BY name
''')

suppliers_to_delete = cur.fetchall()

print(f'\nSuppliers da eliminare: {len(suppliers_to_delete)}')
print('\nElenco:')
print('-'*70)

for supplier_id, name, country, website in suppliers_to_delete:
    print(f'  ID {supplier_id:3d}: {name[:40]:40} | {country or "N/A":15} | {website or ""}')

# Conferma
print('\n' + '='*70)
print('ATTENZIONE: Stai per eliminare (soft delete) questi fornitori')
print('='*70)

# Soft delete (imposta deleted_at)
deleted_at = datetime.now().isoformat()

cur.execute('''
    UPDATE suppliers
    SET deleted_at = ?
    WHERE deleted_at IS NULL
      AND janoshik_quality_score IS NULL
''', (deleted_at,))

deleted_count = cur.rowcount
conn.commit()

print(f'\n✅ Eliminati {deleted_count} suppliers (soft delete)')

# Verifica
cur.execute('SELECT COUNT(*) FROM suppliers WHERE deleted_at IS NULL')
remaining = cur.fetchone()[0]
print(f'✅ Suppliers rimanenti: {remaining}')

cur.execute('SELECT COUNT(*) FROM suppliers WHERE deleted_at IS NULL AND janoshik_quality_score IS NOT NULL')
with_score = cur.fetchone()[0]
print(f'✅ Suppliers con score: {with_score}')

conn.close()
