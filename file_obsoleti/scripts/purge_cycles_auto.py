"""Script per purgare cicli dal database staging (auto mode).

Disabilita temporaneamente il trigger prevent_cycleid_overwrite per permettere
la pulizia delle somministrazioni.
"""
import sqlite3
from pathlib import Path

db_path = Path(__file__).parent.parent / 'data' / 'staging' / 'peptide_management.db'
conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

try:
    # Conta cicli
    cursor.execute('SELECT COUNT(*) FROM cycles')
    count = cursor.fetchone()[0]
    print(f"📊 Trovati {count} cicli")
    
    # Scollega amministrazioni
    cursor.execute('SELECT COUNT(*) FROM administrations WHERE cycle_id IS NOT NULL')
    admin_count = cursor.fetchone()[0]
    print(f"🔗 {admin_count} somministrazioni collegate")
    
    # STEP 1: Drop trigger temporaneamente
    print("🔧 Disabilito trigger prevent_cycleid_overwrite...")
    cursor.execute('DROP TRIGGER IF EXISTS prevent_cycleid_overwrite')
    print("✅ Trigger rimosso")
    
    # STEP 2: Scollega somministrazioni
    cursor.execute('UPDATE administrations SET cycle_id = NULL WHERE cycle_id IS NOT NULL')
    print(f"✅ Scollegte {admin_count} somministrazioni")
    
    # STEP 3: Elimina cicli
    cursor.execute('DELETE FROM cycles')
    print(f"🗑️  Eliminati {count} cicli")
    
    # STEP 4: Reset autoincrement
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='cycles'")
    print("🔄 Reset contatore ID")
    
    # STEP 5: Ricrea trigger
    print("🔧 Ricreo trigger prevent_cycleid_overwrite...")
    cursor.execute('''
        CREATE TRIGGER prevent_cycleid_overwrite
        BEFORE UPDATE OF cycle_id ON administrations
        FOR EACH ROW
        WHEN OLD.cycle_id IS NOT NULL AND NEW.cycle_id IS NOT NULL AND OLD.cycle_id != NEW.cycle_id
        BEGIN
            SELECT RAISE(ABORT, 'Cannot overwrite cycle_id once set');
        END
    ''')
    print("✅ Trigger ricreato")
    
    conn.commit()
    print("\n✅ PURGA COMPLETATA!\n")
    print("💡 Ora puoi avviare la GUI e creare un nuovo ciclo")
    print("\n📋 Comandi per testare:")
    print("   python gui.py --db data\\staging\\peptide_management.db")
    
except Exception as e:
    conn.rollback()
    print(f"\n❌ Errore: {e}")
    import traceback
    traceback.print_exc()
finally:
    conn.close()
