"""
Script per backup del database.
"""

import shutil
from datetime import datetime
from pathlib import Path


def backup_database(db_path='peptide_management.db', backup_dir='backups'):
    """Crea un backup del database."""
    Path(backup_dir).mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = Path(backup_dir) / f'peptide_db_backup_{timestamp}.db'
    
    shutil.copy2(db_path, backup_path)
    print(f"✓ Backup creato: {backup_path}")
    
    return str(backup_path)


if __name__ == '__main__':
    backup_database()
