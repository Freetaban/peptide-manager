"""
Sistema migrazioni database
"""

import sqlite3
import sys
from pathlib import Path
from datetime import datetime

# Aggiungi parent directory al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.environment import get_environment


class MigrationManager:
    """Gestisce migrazioni database."""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.migrations_dir = Path(__file__).parent
        
        # Crea tabella tracking migrazioni
        self._init_migrations_table()
    
    def _init_migrations_table(self):
        """Crea tabella per tracking migrazioni."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS schema_migrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                migration_name TEXT UNIQUE NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                description TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def get_applied_migrations(self) -> set:
        """Recupera migrazioni già applicate."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT migration_name FROM schema_migrations')
        applied = {row[0] for row in cursor.fetchall()}
        
        conn.close()
        return applied
    
    def get_pending_migrations(self) -> list:
        """Recupera migrazioni pendenti."""
        applied = self.get_applied_migrations()
        
        # Trova tutti i file .sql nella directory migrations
        all_migrations = sorted(self.migrations_dir.glob('*.sql'))
        
        # Filtra già applicati
        pending = [
            m for m in all_migrations 
            if m.stem not in applied
        ]
        
        return pending
    
    def apply_migration(self, migration_file: Path) -> bool:
        """
        Applica una singola migrazione.
        
        Args:
            migration_file: Path al file SQL
        
        Returns:
            True se successo
        """
        
        print(f"\n📝 Applicazione: {migration_file.name}")
        
        # Leggi SQL
        with open(migration_file, 'r', encoding='utf-8') as f:
            sql = f.read()
        
        # Estrai descrizione (primo commento)
        description = None
        for line in sql.split('\n'):
            if line.strip().startswith('--'):
                description = line.strip('- ').strip()
                break
        
        # Applica migrazione
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Esegui SQL
            cursor.executescript(sql)
            
            # Registra migrazione applicata
            cursor.execute('''
                INSERT INTO schema_migrations (migration_name, description)
                VALUES (?, ?)
            ''', (migration_file.stem, description))
            
            conn.commit()
            print(f"   ✅ {description or 'Migrazione applicata'}")
            return True
            
        except Exception as e:
            # Handle some idempotent-safe errors (e.g., column already exists)
            err_text = str(e).lower()
            if 'duplicate column' in err_text or 'duplicate column name' in err_text or 'column .* already exists' in err_text:
                # Log warning, record migration as applied to avoid blocking dry-runs on DBs
                print(f"   ⚠️ Warning: possibile colonna già presente. Registriamo la migrazione come applicata (warning). Errore originale: {e}")
                try:
                    cursor.execute('''
                        INSERT OR IGNORE INTO schema_migrations (migration_name, description)
                        VALUES (?, ?)
                    ''', (migration_file.stem, description))
                    conn.commit()
                    return True
                except Exception as e2:
                    conn.rollback()
                    print(f"   ❌ Errore durante registrazione migration: {e2}")
                    return False
            else:
                conn.rollback()
                print(f"   ❌ Errore: {e}")
                return False
            
        finally:
            conn.close()
    
    def migrate(self) -> bool:
        """Applica tutte le migrazioni pendenti."""
        
        pending = self.get_pending_migrations()
        
        if not pending:
            print("✅ Database aggiornato, nessuna migrazione pendente")
            return True
        
        print(f"📋 {len(pending)} migrazioni pendenti:")
        for m in pending:
            print(f"   • {m.name}")
        print()
        
        # Applica una per una
        for migration in pending:
            success = self.apply_migration(migration)
            
            if not success:
                print("\n❌ Migrazione fallita! Stop.")
                return False
        
        print("\n✅ Tutte le migrazioni applicate con successo!")
        return True
    
    def status(self):
        """Mostra stato migrazioni."""
        
        applied = self.get_applied_migrations()
        pending = self.get_pending_migrations()
        
        print("="*60)
        print("STATO MIGRAZIONI DATABASE")
        print("="*60)
        print(f"📁 Database: {self.db_path}")
        print()
        
        print(f"✅ Applicate: {len(applied)}")
        if applied:
            for m in sorted(applied):
                print(f"   • {m}")
        print()
        
        print(f"⏳ Pendenti: {len(pending)}")
        if pending:
            for m in pending:
                print(f"   • {m.name}")
        else:
            print("   (nessuna)")
        print()


def main():
    """Entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Gestione migrazioni database')
    parser.add_argument(
        '--env',
        choices=['production', 'development', 'staging'],
        default='development',
        help='Ambiente target (default: development)'
    )
    parser.add_argument(
        '--status',
        action='store_true',
        help='Mostra solo stato migrazioni'
    )
    
    args = parser.parse_args()
    
    # Carica ambiente
    env = get_environment(args.env)
    
    # Warning se produzione
    if env.is_production():
        print()
        print("⚠️  ATTENZIONE: Stai per migrare il database di PRODUZIONE!")
        print()
        response = input("Continuare? (y/n): ")
        if response.lower() != 'y':
            print("Operazione annullata.")
            return
    
    # Crea manager
    manager = MigrationManager(env.db_path)
    
    # Status o migrate
    if args.status:
        manager.status()
    else:
        manager.migrate()


if __name__ == "__main__":
    main()