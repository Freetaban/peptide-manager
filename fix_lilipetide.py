import sqlite3

conn = sqlite3.connect('data/production/peptide_management.db')
cur = conn.cursor()

# Cerca varianti di Lilipetide in janoshik_certificates
print('='*70)
print('RICERCA LILIPETIDE/LLIPETIDE IN JANOSHIK_CERTIFICATES')
print('='*70)

cur.execute('''
    SELECT DISTINCT supplier_name, COUNT(*) as count
    FROM janoshik_certificates
    WHERE supplier_name LIKE '%lipetide%'
    GROUP BY supplier_name
''')

variants = cur.fetchall()
print(f'\nVarianti trovate: {len(variants)}')
for name, count in variants:
    print(f'  {name}: {count} certificati')

# Correggi nella tabella suppliers
print('\n' + '='*70)
print('CORREZIONE IN TABELLA SUPPLIERS')
print('='*70)

cur.execute("SELECT id, name FROM suppliers WHERE name LIKE '%lipetide%'")
suppliers = cur.fetchall()

if suppliers:
    for supplier_id, name in suppliers:
        print(f'\nID {supplier_id}: {name}')
        
        # Cerca il nome corretto in janoshik_certificates
        cur.execute('''
            SELECT DISTINCT supplier_name
            FROM janoshik_certificates
            WHERE supplier_name LIKE '%lipetide%'
            LIMIT 1
        ''')
        correct_name = cur.fetchone()
        
        if correct_name:
            print(f'  Correggo in: {correct_name[0]}')
            cur.execute('UPDATE suppliers SET name = ? WHERE id = ?', (correct_name[0], supplier_id))
            conn.commit()
        else:
            print('  Nessun match in janoshik_certificates')

print('\n✅ Correzione completata')

conn.close()
