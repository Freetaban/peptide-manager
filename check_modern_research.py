"""Verifica certificati Modern Research"""
import sqlite3

conn = sqlite3.connect('data/production/peptide_management.db')
cur = conn.cursor()

print('Certificati Modern Research:')
print('=' * 80)
for row in cur.execute('''
    SELECT task_number, supplier_website, raw_llm_response
    FROM janoshik_certificates 
    WHERE supplier_name = "Modern Research" 
    LIMIT 3
''').fetchall():
    print(f'\nTask: {row[0]}')
    print(f'Website: {row[1] or "(vuoto)"}')
    if row[2]:
        # Cerca "client" nella risposta LLM
        llm_lower = row[2].lower()
        if 'modernpeptides' in llm_lower or 'modern peptides' in llm_lower:
            start = max(0, llm_lower.find('client') - 20)
            end = min(len(row[2]), llm_lower.find('client') + 100)
            print(f'LLM (estratto): ...{row[2][start:end]}...')

conn.close()
