-- Migration 006: Add Janoshik supplier ranking tables
-- Date: 2025-12-06
-- Description: Create tables for Janoshik certificate storage and supplier rankings

-- Janoshik certificates table (complete schema from development)
CREATE TABLE IF NOT EXISTS janoshik_certificates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_number TEXT UNIQUE NOT NULL,
    image_url TEXT NOT NULL,
    image_hash TEXT UNIQUE,
    local_image_path TEXT,
    supplier_name TEXT,
    product_name TEXT,
    test_date TEXT,
    purity_percentage REAL,
    purity_mg_per_vial REAL,
    endotoxin_eu_per_mg REAL,
    testing_lab TEXT DEFAULT 'Janoshik Analytical',
    raw_llm_response TEXT,
    extraction_timestamp TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    supplier_website TEXT,
    peptide_name TEXT,
    batch_number TEXT,
    testing_ordered TEXT,
    sample_received TEXT,
    analysis_conducted TEXT,
    quantity_tested_mg REAL,
    heavy_metals_result TEXT,
    microbiology_tamc INTEGER,
    microbiology_tymc INTEGER,
    test_type TEXT,
    test_category TEXT,
    comments TEXT,
    verification_key TEXT,
    raw_data TEXT,
    scraped_at TEXT,
    processed INTEGER DEFAULT 0,
    peptide_name_std TEXT,
    quantity_nominal REAL,
    unit_of_measure TEXT
);

-- Supplier rankings table (deprecated, kept for backward compatibility)
CREATE TABLE IF NOT EXISTS supplier_rankings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_name TEXT UNIQUE NOT NULL,
    total_score REAL NOT NULL,
    volume_score REAL,
    quality_score REAL,
    consistency_score REAL,
    recency_score REAL,
    endotoxin_score REAL,
    cert_count INTEGER DEFAULT 0,
    avg_purity REAL,
    min_purity REAL,
    purity_std_dev REAL,
    recent_cert_count INTEGER DEFAULT 0,
    last_cert_date TEXT,
    avg_endotoxin REAL,
    has_endotoxin_tests INTEGER DEFAULT 0,
    rank_position INTEGER,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

-- Add Janoshik cache columns to suppliers table
ALTER TABLE suppliers ADD COLUMN janoshik_certificates INTEGER DEFAULT 0;
ALTER TABLE suppliers ADD COLUMN janoshik_avg_purity REAL;
ALTER TABLE suppliers ADD COLUMN janoshik_min_purity REAL;
ALTER TABLE suppliers ADD COLUMN janoshik_max_purity REAL;
ALTER TABLE suppliers ADD COLUMN janoshik_last_test_date TEXT;
ALTER TABLE suppliers ADD COLUMN janoshik_days_since_last_test INTEGER;
ALTER TABLE suppliers ADD COLUMN janoshik_quality_score REAL;
ALTER TABLE suppliers ADD COLUMN janoshik_updated_at TIMESTAMP;

-- Indexes for janoshik_certificates
CREATE INDEX IF NOT EXISTS idx_janoshik_supplier ON janoshik_certificates(supplier_name);
CREATE INDEX IF NOT EXISTS idx_janoshik_test_date ON janoshik_certificates(test_date);
CREATE INDEX IF NOT EXISTS idx_janoshik_task ON janoshik_certificates(task_number);
CREATE INDEX IF NOT EXISTS idx_janoshik_image_hash ON janoshik_certificates(image_hash);
CREATE INDEX IF NOT EXISTS idx_janoshik_processed ON janoshik_certificates(processed);

-- Indexes for supplier_rankings
CREATE INDEX IF NOT EXISTS idx_ranking_score ON supplier_rankings(total_score DESC);
CREATE INDEX IF NOT EXISTS idx_ranking_supplier ON supplier_rankings(supplier_name);

-- Indexes for suppliers Janoshik columns
CREATE INDEX IF NOT EXISTS idx_suppliers_janoshik_certificates ON suppliers(janoshik_certificates);
CREATE INDEX IF NOT EXISTS idx_suppliers_janoshik_quality ON suppliers(janoshik_quality_score);
