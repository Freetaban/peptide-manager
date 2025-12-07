"""Check for duplicates and naming issues in Janoshik data"""
import sqlite3

conn = sqlite3.connect('data/development/peptide_management.db')
cur = conn.cursor()

print("=" * 80)
print("ANALISI DUPLICATI E NAMING ISSUES")
print("=" * 80)

# 1. Duplicati in supplier_rankings
print("\n📊 DUPLICATI IN SUPPLIER_RANKINGS:")
cur.execute("""
    SELECT supplier_name, COUNT(*) as cnt
    FROM supplier_rankings
    GROUP BY supplier_name
    HAVING cnt > 1
    ORDER BY cnt DESC
""")
duplicates = cur.fetchall()
if duplicates:
    for row in duplicates:
        print(f"  ❌ {row[0]}: {row[1]} entries (DUPLICATO!)")
else:
    print("  ✓ Nessun duplicato trovato")

# 2. Nomi supplier nei certificati
print("\n🏢 NOMI SUPPLIER IN CERTIFICATI (raw_data):")
cur.execute("""
    SELECT task_number, supplier_name, supplier_website, raw_data
    FROM janoshik_certificates
    LIMIT 10
""")
import json
print("\n  task_number | supplier_name (DB) | manufacturer (raw_data)")
print("  " + "-" * 75)
for row in cur.fetchall():
    task_num, supplier_db, website, raw_data_json = row
    if raw_data_json:
        try:
            raw = json.loads(raw_data_json)
            manufacturer = raw.get('manufacturer', 'N/A')
            client = raw.get('client', 'N/A')
            print(f"  #{task_num} | {supplier_db} | mfr={manufacturer}, client={client}")
        except:
            print(f"  #{task_num} | {supplier_db} | (error parsing raw_data)")
    else:
        print(f"  #{task_num} | {supplier_db} | (no raw_data)")

# 3. Campi disponibili nel raw_data
print("\n📋 CAMPI IN RAW_DATA (sample):")
cur.execute("SELECT raw_data FROM janoshik_certificates WHERE raw_data IS NOT NULL LIMIT 1")
row = cur.fetchone()
if row:
    raw = json.loads(row[0])
    print("  Campi disponibili:")
    for key in raw.keys():
        print(f"    - {key}: {raw[key]}")

conn.close()
print("\n" + "=" * 80)
