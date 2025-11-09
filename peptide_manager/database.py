"""
Database manager - gestisce connessione e repository.
"""

import sqlite3
from pathlib import Path
from typing import Optional

from .models import SupplierRepository, PeptideRepository


class DatabaseManager:
    """
    Manager centrale per gestire connessione database e repository.
    
    Questo sostituisce la vecchia classe PeptideManager monolitica.
    Ogni entità ha il suo repository dedicato.
    """
    
    def __init__(self, db_path: str = 'peptide_management.db'):
        """
        Inizializza il database manager.
        
        Args:
            db_path: Percorso del file database
        """
        self.db_path = db_path
        self.conn = self._create_connection()
        
        # Inizializza repository
        self.suppliers = SupplierRepository(self.conn)
        self.peptides = PeptideRepository(self.conn)
        # TODO: Aggiungi altri repository man mano
        # self.batches = BatchRepository(self.conn)
        # etc.
    
    def _create_connection(self) -> sqlite3.Connection:
        """
        Crea connessione al database con configurazione ottimale.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Per accesso dati come dict
        
        # Abilita foreign keys
        cursor = conn.cursor()
        cursor.execute('PRAGMA foreign_keys = ON')
        
        return conn
    
    def close(self):
        """Chiude la connessione al database."""
        if self.conn:
            self.conn.close()
    
    def __enter__(self):
        """Context manager support."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager support."""
        self.close()
    
    def get_stats(self) -> dict:
        """
        Recupera statistiche generali del database.
        
        Returns:
            Dict con conteggi delle varie entità
        """
        cursor = self.conn.cursor()
        
        stats = {}
        
        # Conta entità principali
        tables = ['suppliers', 'peptides', 'batches', 'preparations', 
                  'protocols', 'administrations', 'certificates']
        
        for table in tables:
            try:
                cursor.execute(f'SELECT COUNT(*) FROM {table}')
                stats[table] = cursor.fetchone()[0]
            except sqlite3.OperationalError:
                stats[table] = 0
        
        return stats
