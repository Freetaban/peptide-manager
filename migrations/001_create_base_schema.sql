-- Migration 001: Create base schema
-- Definisce le tabelle base attese dall'applicazione

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS suppliers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
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
    name TEXT NOT NULL UNIQUE,
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
    vials_count INTEGER NOT NULL DEFAULT 1,
    vials_received INTEGER,
    vials_remaining INTEGER NOT NULL DEFAULT 0,
    mg_per_vial REAL,
    total_price REAL,
    price_per_vial REAL,
    currency TEXT DEFAULT 'EUR',
    purchase_date DATE,
    manufacturing_date DATE,
    expiry_date DATE,
    expiration_date DATE,
    storage_location TEXT,
    notes TEXT,
    coa_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP DEFAULT NULL,
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
);

CREATE INDEX IF NOT EXISTS idx_batches_supplier ON batches(supplier_id);

CREATE TABLE IF NOT EXISTS batch_composition (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id INTEGER NOT NULL,
    peptide_id INTEGER NOT NULL,
    mg_per_vial REAL NOT NULL,
    mg_amount REAL,
    FOREIGN KEY (batch_id) REFERENCES batches(id) ON DELETE CASCADE,
    FOREIGN KEY (peptide_id) REFERENCES peptides(id)
);

CREATE INDEX IF NOT EXISTS idx_batch_composition_batch ON batch_composition(batch_id);

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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (batch_id) REFERENCES batches(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_certificates_batch ON certificates(batch_id);

CREATE TABLE IF NOT EXISTS certificate_details (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    certificate_id INTEGER NOT NULL,
    test_parameter TEXT NOT NULL,
    result_value TEXT,
    unit TEXT,
    specification TEXT,
    pass_fail TEXT,
    FOREIGN KEY (certificate_id) REFERENCES certificates(id) ON DELETE CASCADE
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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP DEFAULT NULL,
    FOREIGN KEY (batch_id) REFERENCES batches(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_preparations_batch ON preparations(batch_id);

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
    target_dose_mcg REAL NOT NULL,
    FOREIGN KEY (protocol_id) REFERENCES protocols(id) ON DELETE CASCADE,
    FOREIGN KEY (peptide_id) REFERENCES peptides(id)
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
    injection_method TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP DEFAULT NULL,
    FOREIGN KEY (preparation_id) REFERENCES preparations(id),
    FOREIGN KEY (protocol_id) REFERENCES protocols(id)
);

CREATE INDEX IF NOT EXISTS idx_administrations_date ON administrations(administration_datetime);
CREATE INDEX IF NOT EXISTS idx_administrations_prep ON administrations(preparation_id);
