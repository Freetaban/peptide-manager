"""
Script per verificare e applicare selettivamente migration mancanti
"""

import sqlite3
import sys
from pathlib import Path
from datetime import datetime

# Add parent dir to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.environment import get_environment


def check_table_exists(cursor, table_name):
    """Verifica se una tabella esiste."""
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name=?
    """, (table_name,))
    return cursor.fetchone() is not None


def check_column_exists(cursor, table_name, column_name):
    """Verifica se una colonna esiste in una tabella."""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns


def main():
    print("="*70)
    print("VERIFICA SCHEMA DATABASE PRODUCTION")
    print("="*70)
    print()
    
    # Get production environment
    env = get_environment("production")
    
    if not env.db_path.exists():
        print(f"❌ Database production non trovato: {env.db_path}")
        return False
    
    conn = sqlite3.connect(env.db_path)
    cursor = conn.cursor()
    
    # Verifica tabelle critiche
    critical_tables = [
        'treatment_plans',
        'plan_phases',
        'plan_resources',
        'plan_simulations',
        'treatment_plan_templates',
        'vendor_products',
        'consumable_defaults',
        'user_preferences',
        'janoshik_certificates',
        'supplier_rankings'
    ]
    
    print("📋 Verifica tabelle:")
    missing_tables = []
    for table in critical_tables:
        exists = check_table_exists(cursor, table)
        status = "✅" if exists else "❌"
        print(f"   {status} {table}")
        if not exists:
            missing_tables.append(table)
    
    print()
    
    # Verifica colonne critiche nella tabella supplier_rankings
    if check_table_exists(cursor, 'supplier_rankings'):
        print("📋 Colonne supplier_rankings:")
        cursor.execute("PRAGMA table_info(supplier_rankings)")
        columns = [row[1] for row in cursor.fetchall()]
        for col in columns:
            print(f"   • {col}")
        print()
    
    # Verifica migration applicate
    cursor.execute('SELECT migration_name FROM schema_migrations ORDER BY migration_name')
    applied = [row[0] for row in cursor.fetchall()]
    
    print(f"✅ Migration registrate ({len(applied)}):")
    for m in applied:
        print(f"   • {m}")
    print()
    
    conn.close()
    
    if missing_tables:
        print(f"⚠️ Tabelle mancanti: {', '.join(missing_tables)}")
        print()
        print("Queste tabelle devono essere create applicando le migration:")
        if 'treatment_plans' in missing_tables:
            print("   • 012_add_treatment_planner.sql")
        if 'user_preferences' in missing_tables:
            print("   • 015_add_vendor_pricing.sql")
    else:
        print("✅ Tutte le tabelle critiche esistono!")
    
    return True


if __name__ == "__main__":
    main()
