"""Check supplier website field"""
import sqlite3

conn = sqlite3.connect('data/production/peptide_management.db')
cursor = conn.execute("""
    SELECT supplier_name, supplier_website, image_url 
    FROM janoshik_certificates 
    WHERE supplier_name = 'Zztai Tech' 
    LIMIT 1
""")
row = cursor.fetchone()
if row:
    print(f"Vendor: {row[0]}")
    print(f"Website: {row[1]}")
    print(f"Image URL: {row[2]}")
else:
    print("No data found")
conn.close()
