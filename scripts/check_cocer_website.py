"""Check Cocer Peptides website"""
import sqlite3

conn = sqlite3.connect('data/development/peptide_management.db')
cursor = conn.execute("""
    SELECT supplier_name, supplier_website, COUNT(*) as count
    FROM janoshik_certificates 
    WHERE supplier_name = 'Cocer Peptides'
    GROUP BY supplier_name, supplier_website
""")
for row in cursor.fetchall():
    print(f"Name: {row[0]}")
    print(f"Website: {row[1]}")
    print(f"Count: {row[2]}")
conn.close()
