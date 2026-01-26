"""
Script per recuperare e reinserire i template persi durante la sincronizzazione
"""

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.environment import get_environment


def main():
    print("="*70)
    print("RECUPERO TEMPLATE DA BACKUP DEVELOPMENT")
    print("="*70)
    print()
    
    # Source: backup development
    backup_db = Path("data/backups/development_before_sync_20260120_191701.db")
    
    # Target: production
    env = get_environment("production")
    
    if not backup_db.exists():
        print(f"❌ Backup non trovato: {backup_db}")
        return False
    
    print(f"📁 Source: {backup_db}")
    print(f"📁 Target: {env.db_path}")
    print()
    
    # Connetti a entrambi i database
    source_conn = sqlite3.connect(backup_db)
    target_conn = sqlite3.connect(env.db_path)
    
    source_cursor = source_conn.cursor()
    target_cursor = target_conn.cursor()
    
    # Recupera template dal backup
    source_cursor.execute("""
        SELECT name, short_name, category, total_phases, total_duration_weeks,
               is_active, phases_config, expected_outcomes, source, notes,
               is_system_template
        FROM treatment_plan_templates
        WHERE is_active = 1
    """)
    
    templates = source_cursor.fetchall()
    
    print(f"📚 Template trovati nel backup: {len(templates)}")
    print()
    
    if not templates:
        print("⚠️  Nessun template attivo trovato nel backup")
        return False
    
    # Mostra template e chiedi conferma
    for i, t in enumerate(templates, 1):
        name, short_name, category, phases, weeks = t[:5]
        print(f"  {i}. {name}")
        print(f"     - Short: {short_name}")
        print(f"     - Categoria: {category}")
        print(f"     - Fasi: {phases}, Settimane: {weeks}")
        print()
    
    response = input("Importare questi template nel database production? (s/n): ")
    if response.lower() != 's':
        print("❌ Operazione annullata")
        return False
    
    print()
    print("🔄 Importazione template...")
    print()
    
    # Inserisci template
    imported = 0
    skipped = 0
    
    for template in templates:
        name = template[0]
        
        # Verifica se esiste già
        target_cursor.execute("""
            SELECT id FROM treatment_plan_templates 
            WHERE name = ?
        """, (name,))
        
        if target_cursor.fetchone():
            print(f"  ⏭️  '{name}' - già presente, saltato")
            skipped += 1
            continue
        
        # Inserisci
        try:
            target_cursor.execute("""
                INSERT INTO treatment_plan_templates 
                (name, short_name, category, total_phases, total_duration_weeks,
                 is_active, phases_config, expected_outcomes, source, notes,
                 is_system_template)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, template)
            
            imported += 1
            print(f"  ✅ '{name}' - importato")
        except Exception as ex:
            print(f"  ❌ '{name}' - errore: {ex}")
    
    target_conn.commit()
    
    print()
    print("="*70)
    print(f"✅ COMPLETATO!")
    print(f"   Importati: {imported}")
    print(f"   Saltati: {skipped}")
    print("="*70)
    print()
    
    # Chiudi connessioni
    source_conn.close()
    target_conn.close()
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
