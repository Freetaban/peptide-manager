"""
Verifica dettagliata dello schema treatment_plans
"""

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.environment import get_environment


def main():
    env = get_environment("production")
    conn = sqlite3.connect(env.db_path)
    cursor = conn.cursor()
    
    # Verifica se treatment_plans esiste
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='treatment_plans'
    """)
    
    if cursor.fetchone():
        print("✅ Tabella treatment_plans ESISTE!")
        print("\n📋 Colonne attuali:")
        cursor.execute("PRAGMA table_info(treatment_plans)")
        for row in cursor.fetchall():
            print(f"   • {row[1]} ({row[2]})")
    else:
        print("❌ Tabella treatment_plans NON esiste")
    
    print("\n📋 Tutte le tabelle nel database:")
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' 
        ORDER BY name
    """)
    for row in cursor.fetchall():
        print(f"   • {row[0]}")
    
    conn.close()


if __name__ == "__main__":
    main()
