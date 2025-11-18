"""Utility per applicare migrazioni su un DB specifico (dry-run stagings).

Uso:
    python scripts/run_migrations_on_db.py --db data/staging/peptide_management.db

Questo script istanzia MigrationManager passando esplicitamente il path al DB
in modo da non dipendere dalle variabili .env.
"""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from migrations.migrate import MigrationManager


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--db', required=True, help='Path al DB SQLite da migrare')
    parser.add_argument('--status', action='store_true', help='Mostra stato e esci')
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"DB target non trovato: {db_path}")
        return

    manager = MigrationManager(db_path)

    if args.status:
        manager.status()
        return

    ok = manager.migrate()
    if not ok:
        print('Alcune migrazioni non sono state applicate con successo')


if __name__ == '__main__':
    main()
