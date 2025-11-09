"""
Backup automatico database produzione
"""

import shutil
from datetime import datetime, timedelta
from pathlib import Path
from environment import get_environment

def backup_production(retention_days: int = 30):
    """
    Crea backup database produzione.
    
    Args:
        retention_days: Giorni di retention backup vecchi
    """
    env = get_environment("production")
    
    if not env.db_path.exists():
        print(f"❌ Database produzione non trovato: {env.db_path}")
        return False
    
    # Crea directory backup
    env.backup_dir.mkdir(parents=True, exist_ok=True)
    
    # Nome backup con timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"peptide_management_{timestamp}.db"
    backup_path = env.backup_dir / backup_name
    
    # Copia database
    print(f"💾 Creazione backup: {backup_name}...")
    shutil.copy2(env.db_path, backup_path)
    
    size_mb = backup_path.stat().st_size / (1024 * 1024)
    print(f"✅ Backup creato ({size_mb:.2f}MB)")
    
    # Pulizia backup vecchi
    cleanup_old_backups(env.backup_dir, retention_days)
    
    return True


def cleanup_old_backups(backup_dir: Path, retention_days: int):
    """Elimina backup più vecchi di retention_days."""
    
    cutoff_date = datetime.now() - timedelta(days=retention_days)
    deleted = 0
    
    for backup_file in backup_dir.glob("peptide_management_*.db"):
        # Estrai data dal nome file
        try:
            timestamp_str = backup_file.stem.split("_")[2] + backup_file.stem.split("_")[3]
            file_date = datetime.strptime(timestamp_str, "%Y%m%d%H%M%S")
            
            if file_date < cutoff_date:
                backup_file.unlink()
                deleted += 1
                print(f"🗑️  Eliminato backup vecchio: {backup_file.name}")
        except:
            # Skip file con nome non valido
            continue
    
    if deleted > 0:
        print(f"✅ {deleted} backup vecchi eliminati")


if __name__ == "__main__":
    print("="*60)
    print("BACKUP DATABASE PRODUZIONE")
    print("="*60)
    print()
    
    backup_production(retention_days=30)