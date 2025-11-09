"""
Gestione ambienti produzione/sviluppo
"""

import os
from pathlib import Path
from dotenv import load_dotenv

class Environment:
    """Gestisce configurazione ambiente."""
    
    def __init__(self, env_name: str = None):
        """
        Inizializza ambiente.
        
        Args:
            env_name: 'production', 'development', o None (usa ENV_FILE da .env)
        """
        self.root = Path(__file__).parent.parent
        
        # Determina quale .env usare
        if env_name:
            env_file = self.root / f".env.{env_name}"
        else:
            # Carica .env per vedere ENV_FILE
            load_dotenv(self.root / ".env")
            env_file_name = os.getenv("ENV_FILE", ".env.development")
            env_file = self.root / env_file_name
        
        if not env_file.exists():
            raise FileNotFoundError(f"File configurazione non trovato: {env_file}")
        
        # Carica configurazione
        load_dotenv(env_file)
        
        self.name = os.getenv("ENVIRONMENT")
        self.db_path = self.root / os.getenv("DB_PATH")
        self.backup_dir = self.root / os.getenv("BACKUP_DIR")
        self.auto_backup = os.getenv("AUTO_BACKUP", "false").lower() == "true"
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        
        print(f"🌍 Ambiente: {self.name}")
        print(f"📁 Database: {self.db_path}")
    
    def is_production(self) -> bool:
        """Verifica se è ambiente produzione."""
        return self.name == "production"
    
    def is_development(self) -> bool:
        """Verifica se è ambiente sviluppo."""
        return self.name == "development"


def get_environment(env_name: str = None) -> Environment:
    """Factory per creare ambiente."""
    return Environment(env_name)