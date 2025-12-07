"""
Fix supplier names in existing certificates - use manufacturer instead of client
"""
import sqlite3
import json

db_path = "data/development/peptide_management.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

print("=" * 80)
print("FIX SUPPLIER NAMES - Use manufacturer instead of client")
print("=" * 80)

# 1. Update supplier_name in janoshik_certificates
print("\n🔄 Updating supplier_name from client to manufacturer...")

cur.execute("SELECT task_number, supplier_name, raw_data FROM janoshik_certificates")
rows = cur.fetchall()

updated = 0
for task_number, current_name, raw_data_json in rows:
    if not raw_data_json:
        continue
    
    try:
        raw_data = json.loads(raw_data_json)
        manufacturer = raw_data.get('manufacturer')
        client = raw_data.get('client')
        
        # Se manufacturer esiste e diverso da supplier_name corrente, aggiorna
        if manufacturer and manufacturer != current_name:
            cur.execute("""
                UPDATE janoshik_certificates 
                SET supplier_name = ?, supplier_website = ?
                WHERE task_number = ?
            """, (manufacturer, manufacturer, task_number))
            print(f"  ✓ #{task_number}: '{current_name}' → '{manufacturer}'")
            updated += 1
            
    except Exception as e:
        print(f"  ❌ #{task_number}: Error - {e}")

conn.commit()
print(f"\n✓ Updated {updated} certificates")

# 2. Delete duplicate rankings
print("\n🗑️ Cleaning up duplicate rankings...")
cur.execute("DELETE FROM supplier_rankings")
deleted = cur.rowcount
conn.commit()
print(f"  ✓ Deleted {deleted} old ranking entries")

conn.close()

print("\n" + "=" * 80)
print("✓ Fix completato! Ora ri-calcola i rankings con:")
print("  python reprocess_janoshik_certs.py")
print("=" * 80)
