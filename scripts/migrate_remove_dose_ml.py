"""
Apply migration 014: Remove dose_ml from protocols table.

Il dosaggio è definito a livello di peptide (mcg/giorno).
Il volume in ml viene calcolato in base alla concentrazione della preparazione.
"""

import sqlite3
import sys
from pathlib import Path

def apply_migration(db_path: str):
    """Apply migration to remove dose_ml from protocols."""
    
    print(f"Applying migration 014 to: {db_path}")
    
    # Leggi migration SQL
    migration_file = Path(__file__).parent.parent / "migrations" / "014_remove_protocol_dose_ml.sql"
    
    if not migration_file.exists():
        print(f"ERROR: Migration file not found: {migration_file}")
        return False
    
    with open(migration_file, 'r', encoding='utf-8') as f:
        migration_sql = f.read()
    
    # Connetti al database
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verifica se la colonna dose_ml esiste
        cursor.execute("PRAGMA table_info(protocols)")
        columns = cursor.fetchall()
        has_dose_ml = any(col[1] == 'dose_ml' for col in columns)
        
        if not has_dose_ml:
            print("✓ Column dose_ml does not exist in protocols table - migration not needed")
            conn.close()
            return True
        
        print("→ Column dose_ml found - applying migration...")
        
        # Esegui migration
        cursor.executescript(migration_sql)
        conn.commit()
        
        # Verifica risultato
        cursor.execute("PRAGMA table_info(protocols)")
        columns_after = cursor.fetchall()
        has_dose_ml_after = any(col[1] == 'dose_ml' for col in columns_after)
        
        if has_dose_ml_after:
            print("✗ ERROR: Column dose_ml still exists after migration")
            conn.rollback()
            conn.close()
            return False
        
        print("✓ Migration completed successfully")
        print(f"  Columns in protocols: {[col[1] for col in columns_after]}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"✗ ERROR applying migration: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Database paths
    db_paths = [
        "data/production/peptide_management.db",
        "data/development/peptide_management.db",
    ]
    
    for db_path in db_paths:
        if Path(db_path).exists():
            print(f"\n{'='*60}")
            success = apply_migration(db_path)
            if not success:
                print(f"Migration failed for {db_path}")
                sys.exit(1)
        else:
            print(f"\nSkipping {db_path} (file not found)")
    
    print(f"\n{'='*60}")
    print("✓ All migrations completed successfully")
