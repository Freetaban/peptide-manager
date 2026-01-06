"""Check janoshik_certificates schema"""
import sqlite3

conn = sqlite3.connect('data/development/peptide_management.db')
cursor = conn.execute('PRAGMA table_info(janoshik_certificates)')
print("Columns in janoshik_certificates:")
for row in cursor.fetchall():
    print(f"  {row[1]} ({row[2]})")

# Check if there's a local image path
cursor = conn.execute("""
    SELECT task_number, image_url, local_image_path, image_hash 
    FROM janoshik_certificates 
    WHERE task_number IS NOT NULL 
    LIMIT 3
""")
print("\nSample data:")
for row in cursor.fetchall():
    print(f"  Task: {row[0]}")
    print(f"  URL: {row[1]}")
    print(f"  Local Path: {row[2]}")
    print(f"  Hash: {row[3]}")
    print()

conn.close()
