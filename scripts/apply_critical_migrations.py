"""
Script per applicare solo le migration critiche mancanti
Applica SOLO 012 e 015 che contengono le tabelle realmente mancanti
"""

import sqlite3
import sys
from pathlib import Path
from datetime import datetime
import shutil

# Add parent dir to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.environment import get_environment


def backup_database(db_path: Path) -> Path:
    """Crea backup del database."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = db_path.parent.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    backup_path = backup_dir / f"production_before_critical_migrations_{timestamp}.db"
    shutil.copy2(db_path, backup_path)
    
    size_mb = backup_path.stat().st_size / (1024 * 1024)
    print(f"💾 Backup creato: {backup_path.name} ({size_mb:.2f}MB)")
    
    return backup_path


def apply_sql_migration(conn, migration_path: Path) -> bool:
    """Applica una migration SQL."""
    print(f"\n📝 Applicazione: {migration_path.name}")
    
    cursor = conn.cursor()
    
    try:
        # Leggi contenuto migration
        sql_content = migration_path.read_text(encoding='utf-8')
        
        # Rimuovi eventuali INSERT di schema_migrations dalla migration stessa
        # Li gestiremo manualmente
        lines = []
        for line in sql_content.split('\n'):
            if 'schema_migrations' not in line.lower():
                lines.append(line)
        
        sql_content = '\n'.join(lines)
        
        # Esegui SQL
        cursor.executescript(sql_content)
        
        # Registra migration applicata
        cursor.execute('''
            INSERT OR IGNORE INTO schema_migrations (migration_name, description)
            VALUES (?, ?)
        ''', (migration_path.stem, f"Applied {migration_path.name}"))
        
        conn.commit()
        print(f"   ✅ Migration applicata con successo")
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"   ❌ Errore: {e}")
        return False


def main():
    print("="*70)
    print("APPLICAZIONE MIGRATION CRITICHE - DATABASE PRODUCTION")
    print("="*70)
    print()
    
    # Get production environment
    env = get_environment("production")
    
    if not env.db_path.exists():
        print(f"❌ Database production non trovato: {env.db_path}")
        return False
    
    print(f"📁 Database: {env.db_path}")
    print()
    
    # Backup
    print("🔄 Creazione backup di sicurezza...")
    backup_path = backup_database(env.db_path)
    print()
    
    # Prepara migration da applicare
    migrations_dir = Path(__file__).parent.parent / "migrations"
    critical_migrations = [
        migrations_dir / "012_add_treatment_planner.sql",
        migrations_dir / "015_add_vendor_pricing.sql"
    ]
    
    print("📋 Migration da applicare:")
    for m in critical_migrations:
        if m.exists():
            print(f"   ✅ {m.name}")
        else:
            print(f"   ❌ {m.name} - FILE NON TROVATO!")
            return False
    print()
    
    # Chiedi conferma
    response = input("Procedere con l'applicazione? (s/n): ")
    if response.lower() != 's':
        print("❌ Operazione annullata")
        return False
    
    # Connetti al database
    conn = sqlite3.connect(env.db_path)
    
    # Applica migration una per una
    success = True
    for migration_path in critical_migrations:
        if not apply_sql_migration(conn, migration_path):
            success = False
            break
    
    conn.close()
    
    print()
    if success:
        print("="*70)
        print("✅ MIGRATION CRITICHE APPLICATE CON SUCCESSO!")
        print("="*70)
        print(f"💾 Backup disponibile: {backup_path}")
        print()
        print("🚀 Ora puoi riavviare l'app con: python gui_modular/app.py --env production")
    else:
        print("="*70)
        print("❌ ERRORE NELL'APPLICAZIONE DELLE MIGRATION")
        print("="*70)
        print(f"💾 Database può essere ripristinato da: {backup_path}")
        print()
        print("Per ripristinare:")
        print(f"   copy \"{backup_path}\" \"{env.db_path}\"")
    
    print()
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
