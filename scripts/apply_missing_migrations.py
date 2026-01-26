"""
Script per applicare migration mancanti al database production
"""

import sys
import shutil
from pathlib import Path
from datetime import datetime

# Add parent dir to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from migrations.migrate import MigrationManager
from scripts.environment import get_environment


def backup_database(db_path: Path) -> Path:
    """Crea backup del database prima delle migration."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = db_path.parent.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    backup_path = backup_dir / f"production_before_migrations_{timestamp}.db"
    shutil.copy2(db_path, backup_path)
    
    size_mb = backup_path.stat().st_size / (1024 * 1024)
    print(f"💾 Backup creato: {backup_path.name} ({size_mb:.2f}MB)")
    
    return backup_path


def main():
    print("="*70)
    print("APPLICAZIONE MIGRATION MANCANTI - DATABASE PRODUCTION")
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
    
    # Inizializza migration manager
    manager = MigrationManager(env.db_path)
    
    # Mostra migration applicate
    applied = manager.get_applied_migrations()
    print(f"✅ Migration già applicate: {len(applied)}")
    for m in sorted(applied):
        print(f"   • {m}")
    print()
    
    # Mostra migration pendenti
    pending = manager.get_pending_migrations()
    print(f"📋 Migration pendenti: {len(pending)}")
    for m in pending:
        print(f"   • {m.name}")
    print()
    
    if not pending:
        print("✅ Nessuna migration da applicare!")
        return True
    
    # Chiedi conferma
    response = input("Procedere con l'applicazione delle migration? (s/n): ")
    if response.lower() != 's':
        print("❌ Operazione annullata")
        return False
    
    print()
    print("🔄 Applicazione migration...")
    print()
    
    # Applica migration
    success = manager.migrate()
    
    if success:
        print()
        print("="*70)
        print("✅ MIGRATION APPLICATE CON SUCCESSO!")
        print("="*70)
        print(f"💾 Backup disponibile: {backup_path}")
        print()
    else:
        print()
        print("="*70)
        print("❌ ERRORE NELL'APPLICAZIONE DELLE MIGRATION")
        print("="*70)
        print(f"💾 Database può essere ripristinato da: {backup_path}")
        print()
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
