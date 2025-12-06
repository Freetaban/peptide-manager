"""Quick script to check raw_data from certificates"""
import sqlite3
import json

conn = sqlite3.connect('data/development/peptide_management.db')
query = "SELECT task_number, sample, raw_data, purity_percentage, quantity_tested_mg FROM janoshik_certificates ORDER BY task_number"
cursor = conn.execute(query)

for row in cursor.fetchall():
    task, sample, raw_data, purity, quantity = row
    print(f"\n{'='*80}")
    print(f"Task #{task}: {sample}")
    print(f"Purity: {purity}% | Quantity: {quantity} mg")
    print(f"\nRaw Data:")
    try:
        data = json.loads(raw_data)
        print(json.dumps(data, indent=2))
    except Exception as e:
        print(f"Error parsing JSON: {e}")
        print(raw_data[:200])
    
conn.close()
