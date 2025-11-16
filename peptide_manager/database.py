"""
Database manager - gestisce connessione e repository.
"""

import sqlite3
from pathlib import Path
from typing import Optional

from .models.supplier import SupplierRepository
from .models.peptide import PeptideRepository
from .models.batch import BatchRepository  
from .models.batch_composition import BatchCompositionRepository
from .models.preparation import PreparationRepository
from .models.protocol import ProtocolRepository
from .models.administration import AdministrationRepository
from .models.certificate import CertificateRepository


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
        self.batches = BatchRepository(self.conn)
        self.batch_composition = BatchCompositionRepository(self.conn)
        self.preparations = PreparationRepository(self.conn)
        self.protocols = ProtocolRepository(self.conn)
        self.administrations = AdministrationRepository(self.conn)
        self.certificates = CertificateRepository(self.conn)
        
    
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


def init_database(db_path: str = 'peptide_management.db') -> sqlite3.Connection:
    """
    Inizializza il database sul percorso `db_path` e applica le migration SQL presenti
    nella cartella `migrations/` (ordinandole per nome). Ritorna una connessione
    `sqlite3.Connection` pronta per l'uso.

    Questa funzione mantiene compatibilità con i test che si aspettano una
    connessione SQLite e assicura che le tabelle siano create.
    """
    db_path = str(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Abilita foreign keys
    cur = conn.cursor()
    cur.execute('PRAGMA foreign_keys = ON')

    # Applicare tutte le migration SQL disponibili (ordine alfabetico)
    project_root = Path(__file__).resolve().parent.parent
    migrations_dir = project_root / 'migrations'
    # Se il database è nuovo, creare lo schema base necessario per i test e l'app
    base_schema = r"""
    -- Schema base essenziale
    CREATE TABLE IF NOT EXISTS suppliers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        country TEXT,
        website TEXT,
        email TEXT,
        notes TEXT,
        reliability_rating INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        deleted_at TIMESTAMP DEFAULT NULL
    );

    CREATE TABLE IF NOT EXISTS peptides (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        common_uses TEXT,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        deleted_at TIMESTAMP DEFAULT NULL
    );

    CREATE TABLE IF NOT EXISTS batches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        supplier_id INTEGER NOT NULL,
        product_name TEXT NOT NULL,
        batch_number TEXT,
        vials_count INTEGER NOT NULL,
        vials_received INTEGER DEFAULT NULL,
        mg_per_vial REAL,
        total_price REAL,
        price_per_vial REAL,
        currency TEXT DEFAULT 'EUR',
        purchase_date DATE,
        expiry_date DATE,
        storage_location TEXT,
        vials_remaining INTEGER NOT NULL DEFAULT 0,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        deleted_at TIMESTAMP DEFAULT NULL,
        manufacturing_date DATE,
        expiration_date DATE,
        coa_path TEXT
    );

    CREATE TABLE IF NOT EXISTS batch_composition (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        batch_id INTEGER NOT NULL,
        peptide_id INTEGER NOT NULL,
        mg_per_vial REAL NOT NULL,
        mg_amount REAL
    );

    CREATE TABLE IF NOT EXISTS certificates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        batch_id INTEGER NOT NULL,
        certificate_type TEXT NOT NULL,
        lab_name TEXT,
        test_date DATE,
        file_path TEXT,
        file_name TEXT,
        purity_percentage REAL,
        endotoxin_level TEXT,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS certificate_details (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        certificate_id INTEGER NOT NULL,
        test_parameter TEXT NOT NULL,
        result_value TEXT,
        unit TEXT,
        specification TEXT,
        pass_fail TEXT
    );

    CREATE TABLE IF NOT EXISTS preparations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        batch_id INTEGER NOT NULL,
        vials_used INTEGER NOT NULL,
        volume_ml REAL NOT NULL,
        diluent TEXT DEFAULT 'BAC Water',
        preparation_date DATE NOT NULL,
        expiry_date DATE,
        volume_remaining_ml REAL NOT NULL,
        storage_location TEXT,
        notes TEXT,
        status TEXT DEFAULT 'available',
        actual_depletion_date DATE,
        wastage_ml REAL,
        wastage_reason TEXT,
        wastage_notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        deleted_at TIMESTAMP DEFAULT NULL
    );

    CREATE TABLE IF NOT EXISTS protocols (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        dose_ml REAL NOT NULL,
        frequency_per_day INTEGER DEFAULT 1,
        days_on INTEGER,
        days_off INTEGER DEFAULT 0,
        cycle_duration_weeks INTEGER,
        notes TEXT,
        active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        deleted_at TIMESTAMP DEFAULT NULL
    );

    CREATE TABLE IF NOT EXISTS protocol_peptides (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        protocol_id INTEGER NOT NULL,
        peptide_id INTEGER NOT NULL,
        target_dose_mcg REAL NOT NULL
    );

    CREATE TABLE IF NOT EXISTS administrations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        preparation_id INTEGER NOT NULL,
        protocol_id INTEGER,
        administration_datetime TIMESTAMP NOT NULL,
        dose_ml REAL NOT NULL,
        injection_site TEXT,
        notes TEXT,
        side_effects TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        injection_method TEXT,
        deleted_at TIMESTAMP DEFAULT NULL
    );
    """
    conn.executescript(base_schema)
    if migrations_dir.exists() and migrations_dir.is_dir():
        sql_files = sorted(migrations_dir.glob('*.sql'))
        for sql_file in sql_files:
            with sql_file.open('r', encoding='utf-8') as f:
                sql = f.read()
                if not sql.strip():
                    continue
                try:
                    conn.executescript(sql)
                except sqlite3.OperationalError as e:
                    # Alcune migration possono già essere state applicate
                    # (colonne duplicate). Ignoriamo errori di colonne duplicate
                    # per non bloccare l'inizializzazione in ambienti di test.
                    msg = str(e).lower()
                    if 'duplicate column name' in msg or 'duplicate column' in msg:
                        continue
                    raise

    return conn
