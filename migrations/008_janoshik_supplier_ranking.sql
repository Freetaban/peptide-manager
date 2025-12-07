-- Migration 008: Janoshik Supplier Ranking System
-- Aggiunge tabelle per monitoraggio certificati Janoshik e ranking supplier

PRAGMA foreign_keys = ON;

-- Tabella certificati Janoshik (storage temporaneo per elaborazione)
CREATE TABLE IF NOT EXISTS janoshik_certificates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_number TEXT UNIQUE NOT NULL,
    supplier_name TEXT NOT NULL,
    supplier_website TEXT,
    peptide_name TEXT NOT NULL,
    batch_number TEXT,
    test_date DATE NOT NULL,
    testing_ordered DATE,
    sample_received DATE,
    analysis_conducted DATE,
    purity_percentage REAL,
    quantity_tested_mg REAL,
    endotoxin_level REAL,  -- EU/mg (Endotoxin Units per mg)
    test_type TEXT,
    comments TEXT,
    verification_key TEXT,
    raw_data TEXT,  -- JSON completo estratto
    image_file TEXT,
    image_hash TEXT UNIQUE,  -- Hash SHA256 per deduplicazione
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_janoshik_supplier ON janoshik_certificates(supplier_name);
CREATE INDEX IF NOT EXISTS idx_janoshik_test_date ON janoshik_certificates(test_date);
CREATE INDEX IF NOT EXISTS idx_janoshik_processed ON janoshik_certificates(processed);
CREATE INDEX IF NOT EXISTS idx_janoshik_image_hash ON janoshik_certificates(image_hash);

-- Tabella storico ranking supplier
CREATE TABLE IF NOT EXISTS supplier_rankings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_name TEXT NOT NULL,
    supplier_website TEXT,
    
    -- Metriche base
    total_certificates INTEGER DEFAULT 0,
    recent_certificates INTEGER DEFAULT 0,  -- Ultimi 90 giorni
    certs_last_30d INTEGER DEFAULT 0,
    avg_purity REAL,
    min_purity REAL,
    max_purity REAL,
    std_purity REAL,
    avg_endotoxin_level REAL,  -- EU/mg
    certs_with_endotoxin INTEGER DEFAULT 0,
    volume_score REAL,
    quality_score REAL,
    consistency_score REAL,
    recency_score REAL,
    endotoxin_score REAL DEFAULT 0,
    
    -- Score finaleEAL,
    
    -- Score finale
    total_score REAL NOT NULL,
    rank_position INTEGER,
    
    -- Metadata
    days_since_last_cert INTEGER,
    avg_date_gap REAL,
    peptides_tested TEXT,  -- JSON array di peptidi testati
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_snapshot TEXT  -- JSON completo per analisi
);

CREATE INDEX IF NOT EXISTS idx_ranking_supplier ON supplier_rankings(supplier_name);
CREATE INDEX IF NOT EXISTS idx_ranking_score ON supplier_rankings(total_score DESC);
CREATE INDEX IF NOT EXISTS idx_ranking_date ON supplier_rankings(calculated_at);
CREATE INDEX IF NOT EXISTS idx_ranking_position ON supplier_rankings(rank_position);

-- Estendi tabella suppliers con informazioni Janoshik
ALTER TABLE suppliers ADD COLUMN janoshik_name TEXT;
ALTER TABLE suppliers ADD COLUMN janoshik_website TEXT;
ALTER TABLE suppliers ADD COLUMN janoshik_score REAL;
ALTER TABLE suppliers ADD COLUMN janoshik_rank INTEGER;
ALTER TABLE suppliers ADD COLUMN last_janoshik_update TIMESTAMP;

CREATE INDEX IF NOT EXISTS idx_suppliers_janoshik ON suppliers(janoshik_name);

-- Registra migration
INSERT INTO schema_migrations (migration_name, description)
VALUES ('008_janoshik_supplier_ranking', 'Aggiunge sistema ranking supplier Janoshik');
