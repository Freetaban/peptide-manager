import sqlite3

conn = sqlite3.connect('data/production/peptide_management.db')
cur = conn.cursor()

print('='*70)
print('VERIFICA MISMATCH NOMI')
print('='*70)

# Fornitori senza score
cur.execute('''
    SELECT s.id, s.name
    FROM suppliers s
    WHERE s.deleted_at IS NULL 
      AND s.janoshik_quality_score IS NULL
    ORDER BY s.name
    LIMIT 20
''')

suppliers_without_score = cur.fetchall()
print(f'\nFornitori senza score: {len(suppliers_without_score)}')

# Per ciascuno, cerca match in janoshik_certificates
print('\n' + '='*70)
print('RICERCA MATCH IN JANOSHIK_CERTIFICATES:')
print('='*70)

for supplier_id, supplier_name in suppliers_without_score:
    # Cerca match esatto
    cur.execute('''
        SELECT COUNT(*), GROUP_CONCAT(DISTINCT supplier_name)
        FROM janoshik_certificates
        WHERE supplier_name = ?
    ''', (supplier_name,))
    
    exact_match = cur.fetchone()
    
    # Cerca match parziale (case-insensitive, lowercase)
    cur.execute('''
        SELECT COUNT(*), GROUP_CONCAT(DISTINCT supplier_name)
        FROM janoshik_certificates
        WHERE LOWER(supplier_name) = LOWER(?)
    ''', (supplier_name,))
    
    case_match = cur.fetchone()
    
    print(f'\n{supplier_name}:')
    print(f'  Match esatto: {exact_match[0]} certificati')
    if case_match[0] > 0 and case_match[0] != exact_match[0]:
        print(f'  Match case-insensitive: {case_match[0]} certificati')
        print(f'  Varianti trovate: {case_match[1]}')
    
    if exact_match[0] == 0 and case_match[0] == 0:
        # Cerca simili
        cur.execute('''
            SELECT DISTINCT supplier_name
            FROM janoshik_certificates
            WHERE supplier_name LIKE ?
            LIMIT 3
        ''', (f'%{supplier_name[:10]}%',))
        
        similar = cur.fetchall()
        if similar:
            print(f'  Nomi simili in janoshik_certificates:')
            for sim in similar:
                print(f'    - {sim[0]}')

conn.close()
