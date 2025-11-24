"""
Copia database da produzione a sviluppo
"""

import shutil
import os
from datetime import datetime
from pathlib import Path
from environment import get_environment

def copy_prod_to_dev():
    """Copia DB produzione in sviluppo."""
    
    # Carica ambienti (pulisci variabili tra chiamate per evitare conflitti)
    prod_env = get_environment("production")
    
    # Pulisci variabili d'ambiente per evitare contaminazione
    for key in ['ENVIRONMENT', 'DB_PATH', 'BACKUP_DIR', 'AUTO_BACKUP', 'LOG_LEVEL']:
        os.environ.pop(key, None)
    
    dev_env = get_environment("development")
    
    # Verifica esistenza DB produzione
    if not prod_env.db_path.exists():
        print(f"❌ Database produzione non trovato: {prod_env.db_path}")
        return False
    
    # Backup del DB sviluppo corrente
    if dev_env.db_path.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = dev_env.db_path.with_suffix(f".backup_{timestamp}")
        shutil.copy2(dev_env.db_path, backup_path)
        print(f"💾 Backup sviluppo: {backup_path}")
    
    # Copia prod → dev
    print(f"📋 Copio {prod_env.db_path} → {dev_env.db_path}...")
    shutil.copy2(prod_env.db_path, dev_env.db_path)
    
    # Verifica dimensione
    size_mb = dev_env.db_path.stat().st_size / (1024 * 1024)
    print(f"✅ Database sviluppo aggiornato ({size_mb:.2f}MB)")
    print(f"   Ora puoi lavorare su: {dev_env.db_path}")
    
    return True


if __name__ == "__main__":
    print("="*60)
    print("COPIA DATABASE: PRODUZIONE → SVILUPPO")
    print("="*60)
    print()
    
    response = input("⚠️  Il DB sviluppo corrente sarà sovrascritto. Continuare? (y/n): ")
    
    if response.lower() == 'y':
        copy_prod_to_dev()
    else:
        print("Operazione annullata.")