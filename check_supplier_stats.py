import sqlite3

conn = sqlite3.connect('data/production/peptide_management.db')
cur = conn.cursor()

print('='*70)
print('STATISTICHE FORNITORI')
print('='*70)

# Totale fornitori
cur.execute('SELECT COUNT(*) FROM suppliers WHERE deleted_at IS NULL')
total = cur.fetchone()[0]
print(f'\nTotale fornitori: {total}')

# Fornitori con score
cur.execute('SELECT COUNT(*) FROM suppliers WHERE deleted_at IS NULL AND janoshik_quality_score IS NOT NULL')
with_score = cur.fetchone()[0]
print(f'Fornitori con Score Janoshik: {with_score}')

# Fornitori senza score
cur.execute('SELECT COUNT(*) FROM suppliers WHERE deleted_at IS NULL AND janoshik_quality_score IS NULL')
without_score = cur.fetchone()[0]
print(f'Fornitori senza Score Janoshik: {without_score}')

print(f'\nPercentuale con score: {with_score/total*100:.1f}%')

# Mostra alcuni senza score
print('\n' + '='*70)
print('ESEMPI FORNITORI SENZA SCORE (primi 10):')
print('='*70)
cur.execute('''
    SELECT id, name, country
    FROM suppliers 
    WHERE deleted_at IS NULL AND janoshik_quality_score IS NULL
    ORDER BY name
    LIMIT 10
''')

for row in cur.fetchall():
    print(f'  ID {row[0]:3d}: {row[1][:40]:40} | {row[2] or "N/A"}')

# Verifica se hanno certificati Janoshik
print('\n' + '='*70)
print('VERIFICA: Questi fornitori hanno certificati Janoshik?')
print('='*70)

cur.execute('''
    SELECT s.name, COUNT(j.id) as cert_count
    FROM suppliers s
    LEFT JOIN janoshik_certificates j ON s.name = j.supplier_name
    WHERE s.deleted_at IS NULL AND s.janoshik_quality_score IS NULL
    GROUP BY s.name
    HAVING cert_count > 0
    ORDER BY cert_count DESC
    LIMIT 10
''')

rows = cur.fetchall()
if rows:
    print('\nFornitori con certificati MA senza score:')
    for row in rows:
        print(f'  {row[0][:40]:40} | Certificati: {row[1]}')
else:
    print('\nNessun fornitore con certificati ma senza score trovato.')
    print('(Questo è corretto - solo fornitori senza certificati non hanno score)')

conn.close()
