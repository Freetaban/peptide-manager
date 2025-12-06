"""Show certificate data"""
import sqlite3
import json

conn = sqlite3.connect('data/development/peptide_management.db')

# Get all task numbers first
tasks = conn.execute('SELECT task_number FROM janoshik_certificates ORDER BY task_number').fetchall()

for (task_num,) in tasks:
    print(f"\n{'='*80}")
    row = conn.execute(
        'SELECT task_number, peptide_name, purity_percentage, quantity_tested_mg, raw_data FROM janoshik_certificates WHERE task_number = ?',
        (task_num,)
    ).fetchone()
    
    task, peptide, purity, quantity, raw = row
    print(f"Task #{task}: {peptide}")
    print(f"Purity: {purity}% | Quantity: {quantity} mg")
    print(f"\nRaw Data Results:")
    
    if raw:
        try:
            data = json.loads(raw)
            if 'results' in data:
                for key, value in data['results'].items():
                    print(f"  {key}: {value}")
        except Exception as e:
            print(f"  Error: {e}")
    
conn.close()
