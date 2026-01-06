"""Verifica se task_number ha constraint UNIQUE nel database."""
import sqlite3

conn = sqlite3.connect('data/development/peptide_management.db')
cursor = conn.execute(
    "SELECT sql FROM sqlite_master WHERE type='table' AND name='janoshik_certificates'"
)
schema = cursor.fetchone()[0]
print("Schema janoshik_certificates:")
print("=" * 80)
print(schema)
print("=" * 80)

# Verifica se UNIQUE è presente
if 'task_number' in schema and 'UNIQUE' in schema:
    print("\n✅ task_number ha constraint UNIQUE nel database")
    print("✓ Il database previene l'inserimento di duplicati a livello SQL")
else:
    print("\n⚠️ task_number NON ha constraint UNIQUE nel database")
    print("⚠️ Dipende solo dal filtering applicativo")

# Conta duplicati attuali
cursor = conn.execute("""
    SELECT task_number, COUNT(*) as count
    FROM janoshik_certificates
    GROUP BY task_number
    HAVING count > 1
""")
duplicates = cursor.fetchall()

if duplicates:
    print(f"\n❌ Trovati {len(duplicates)} task_number duplicati:")
    for task, count in duplicates:
        print(f"  - task {task}: {count} copie")
else:
    print(f"\n✅ Nessun duplicato presente nel database")

conn.close()
