"""
Database schema e inizializzazione.
"""

import sqlite3
from pathlib import Path

def init_database(db_path='peptide_management.db'):
    """
    Inizializza il database con lo schema completo.
    
    Args:
        db_path: Percorso del file database
        
    Returns:
        sqlite3.Connection: Connessione al database
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Abilita foreign keys
    cursor.execute('PRAGMA foreign_keys = ON')
    
    # === SUPPLIERS ===
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS suppliers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        country TEXT,
        website TEXT,
        email TEXT,
        notes TEXT,
        reliability_rating INTEGER CHECK(reliability_rating >= 1 AND reliability_rating <= 5),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # === PEPTIDES ===
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS peptides (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        description TEXT,
        common_uses TEXT,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # === BATCHES ===
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS batches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        supplier_id INTEGER NOT NULL,
        product_name TEXT NOT NULL,
        batch_number TEXT,
        vials_count INTEGER NOT NULL,
        mg_per_vial REAL NOT NULL,
        total_price REAL NOT NULL,
        currency TEXT DEFAULT 'EUR',
        purchase_date DATE NOT NULL,
        expiry_date DATE,
        storage_location TEXT,
        vials_remaining INTEGER NOT NULL,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
    )
    ''')
    
    # === BATCH COMPOSITION ===
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS batch_composition (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        batch_id INTEGER NOT NULL,
        peptide_id INTEGER NOT NULL,
        mg_per_vial REAL NOT NULL,
        FOREIGN KEY (batch_id) REFERENCES batches(id) ON DELETE CASCADE,
        FOREIGN KEY (peptide_id) REFERENCES peptides(id),
        UNIQUE(batch_id, peptide_id)
    )
    ''')
    
    # === CERTIFICATES ===
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS certificates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        batch_id INTEGER NOT NULL,
        certificate_type TEXT NOT NULL CHECK(certificate_type IN ('manufacturer', 'third_party', 'personal')),
        lab_name TEXT,
        test_date DATE,
        file_path TEXT,
        file_name TEXT,
        purity_percentage REAL CHECK(purity_percentage >= 0 AND purity_percentage <= 100),
        endotoxin_level TEXT,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (batch_id) REFERENCES batches(id) ON DELETE CASCADE
    )
    ''')
    
    # === CERTIFICATE DETAILS ===
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS certificate_details (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        certificate_id INTEGER NOT NULL,
        test_parameter TEXT NOT NULL,
        result_value TEXT,
        unit TEXT,
        specification TEXT,
        pass_fail TEXT CHECK(pass_fail IN ('pass', 'fail', 'n/a')),
        FOREIGN KEY (certificate_id) REFERENCES certificates(id) ON DELETE CASCADE
    )
    ''')
    
    # === PREPARATIONS ===
    cursor.execute('''
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
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (batch_id) REFERENCES batches(id)
    )
    ''')
    
    # === PROTOCOLS ===
    cursor.execute('''
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
        active BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # === PROTOCOL PEPTIDES ===
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS protocol_peptides (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        protocol_id INTEGER NOT NULL,
        peptide_id INTEGER NOT NULL,
        target_dose_mcg REAL NOT NULL,
        FOREIGN KEY (protocol_id) REFERENCES protocols(id) ON DELETE CASCADE,
        FOREIGN KEY (peptide_id) REFERENCES peptides(id)
    )
    ''')
    
    # === ADMINISTRATIONS ===
    cursor.execute('''
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
        FOREIGN KEY (preparation_id) REFERENCES preparations(id),
        FOREIGN KEY (protocol_id) REFERENCES protocols(id)
    )
    ''')
    
    # === INDEXES ===
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_batches_supplier ON batches(supplier_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_batch_composition_batch ON batch_composition(batch_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_certificates_batch ON certificates(batch_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_preparations_batch ON preparations(batch_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_administrations_prep ON administrations(preparation_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_administrations_date ON administrations(administration_datetime)')
    
    conn.commit()
    
    print(f"✓ Database inizializzato: {db_path}")
    return conn


def get_schema_info(db_path='peptide_management.db'):
    """
    Restituisce informazioni sullo schema del database.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]
    
    schema_info = {}
    for table in tables:
        cursor.execute(f"PRAGMA table_info({table})")
        columns = cursor.fetchall()
        schema_info[table] = columns
    
    conn.close()
    return schema_info
