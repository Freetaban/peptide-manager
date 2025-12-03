"""Script per purgare cicli dal database staging.

Rimuove tutti i cicli e scollega le somministrazioni associate.
"""
import sqlite3
import sys
from pathlib import Path

def purge_cycles(db_path: str):
    """Purga tutti i cicli e scollega le somministrazioni."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # 1. Conta cicli esistenti
        cursor.execute('SELECT COUNT(*) FROM cycles')
        count = cursor.fetchone()[0]
        print(f"📊 Trovati {count} cicli nel database")
        
        if count == 0:
            print("✅ Database già pulito, nessun ciclo presente")
            return
        
        # 2. Scollega somministrazioni (imposta cycle_id a NULL)
        cursor.execute('SELECT COUNT(*) FROM administrations WHERE cycle_id IS NOT NULL')
        admin_count = cursor.fetchone()[0]
        print(f"🔗 {admin_count} somministrazioni collegate a cicli")
        
        cursor.execute('UPDATE administrations SET cycle_id = NULL WHERE cycle_id IS NOT NULL')
        print(f"✅ Scollegte {admin_count} somministrazioni")
        
        # 3. Elimina tutti i cicli
        cursor.execute('DELETE FROM cycles')
        print(f"🗑️  Eliminati {count} cicli")
        
        # 4. Reset autoincrement (opzionale)
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='cycles'")
        print("🔄 Reset contatore ID cicli")
        
        conn.commit()
        print("\n✅ Purga completata con successo!")
        print("\n💡 Ora puoi creare un nuovo ciclo dal menu 'Cicli' nella GUI")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Errore durante la purga: {e}")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == '__main__':
    # Default: staging DB
    db_path = Path(__file__).parent.parent / 'data' / 'staging' / 'peptide_management.db'
    
    # Verifica esistenza
    if not db_path.exists():
        print(f"❌ Database non trovato: {db_path}")
        sys.exit(1)
    
    print(f"🎯 Database: {db_path}")
    print("⚠️  ATTENZIONE: Questa operazione eliminerà tutti i cicli!")
    
    # Conferma
    risposta = input("\nContinuare? (sì/no): ").strip().lower()
    if risposta not in ['sì', 'si', 's', 'yes', 'y']:
        print("❌ Operazione annullata")
        sys.exit(0)
    
    print("\n🚀 Avvio purga...\n")
    purge_cycles(str(db_path))
