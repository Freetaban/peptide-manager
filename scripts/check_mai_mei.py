"""Check Mai vs Mei certificates"""
import sqlite3

conn = sqlite3.connect('data/production/peptide_management.db')

print("=== MAI PEPTIDES (1 cert) ===")
cursor = conn.execute("""
    SELECT task_number, peptide_name, purity_percentage, test_date, supplier_website
    FROM janoshik_certificates 
    WHERE supplier_name = 'Mai Peptides'
""")
for row in cursor.fetchall():
    print(f"Task {row[0]}: {row[1]} - {row[2]}% - {row[3]}")
    print(f"  Website: {row[4]}")

print("\n=== MEI PEPTIDE (15 certs - first 3) ===")
cursor = conn.execute("""
    SELECT task_number, peptide_name, purity_percentage, test_date, supplier_website
    FROM janoshik_certificates 
    WHERE supplier_name = 'Mei Peptide'
    LIMIT 3
""")
for row in cursor.fetchall():
    print(f"Task {row[0]}: {row[1]} - {row[2]}% - {row[3]}")
    print(f"  Website: {row[4]}")

conn.close()
