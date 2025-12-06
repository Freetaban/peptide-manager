-- Migration 006: Add Janoshik supplier ranking tables
-- Date: 2025-12-06
-- Description: Create tables for Janoshik certificate storage and supplier rankings

-- Janoshik certificates table
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
    updated_at TEXT DEFAULT (datetime('now'))
);

-- Supplier rankings table
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

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_janoshik_supplier ON janoshik_certificates(supplier_name);
CREATE INDEX IF NOT EXISTS idx_janoshik_test_date ON janoshik_certificates(test_date);
CREATE INDEX IF NOT EXISTS idx_janoshik_task ON janoshik_certificates(task_number);
CREATE INDEX IF NOT EXISTS idx_ranking_score ON supplier_rankings(total_score DESC);
CREATE INDEX IF NOT EXISTS idx_ranking_supplier ON supplier_rankings(supplier_name);
