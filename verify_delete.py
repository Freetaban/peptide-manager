import sqlite3

conn = sqlite3.connect('data/production/peptide_management.db')
cur = conn.cursor()

# Verifica soft delete
cur.execute('''
    SELECT id, name, deleted_at
    FROM suppliers
    WHERE name IN ('Alpha Pro', 'Dragon Pharma', 'Https://T.Me/Glasscompounds', 
                   'Raw Pharma', 'Santeria Pharmaceuticals', 'Xenolabs')
''')

print('Stato fornitori:')
for row in cur.fetchall():
    supplier_id, name, deleted_at = row
    status = "ELIMINATO" if deleted_at else "ATTIVO"
    print(f'  {name}: {status} (deleted_at: {deleted_at})')

# Conta attivi
cur.execute('SELECT COUNT(*) FROM suppliers WHERE deleted_at IS NULL')
print(f'\nSuppliers attivi: {cur.fetchone()[0]}')

conn.close()
