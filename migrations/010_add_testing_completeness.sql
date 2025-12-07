-- Migration 010: Testing Completeness Tracking
-- Aggiunge campi per tracciare test opzionali (heavy metals, microbiology, endotoxin)
-- per valutare completezza e affidabilità dei vendor

PRAGMA foreign_keys = ON;

-- Aggiungi campi per test opzionali in janoshik_certificates
ALTER TABLE janoshik_certificates ADD COLUMN heavy_metals_result TEXT;  -- JSON: {"Pb": 0.5, "Cd": 0.1, "Hg": 0.05, "As": 0.2} ppm
ALTER TABLE janoshik_certificates ADD COLUMN microbiology_tamc INTEGER;  -- Total Aerobic Microbial Count (CFU/g)
ALTER TABLE janoshik_certificates ADD COLUMN microbiology_tymc INTEGER;  -- Total Yeast/Mold Count (CFU/g)
ALTER TABLE janoshik_certificates ADD COLUMN test_category TEXT;  -- 'purity', 'endotoxin', 'heavy_metals', 'microbiology'

-- Indici per query per peptide+supplier (use case: "mostrami tutti i test per Ipamorelin da vendor X")
CREATE INDEX IF NOT EXISTS idx_janoshik_peptide_supplier ON janoshik_certificates(peptide_name, supplier_name);
CREATE INDEX IF NOT EXISTS idx_janoshik_test_category ON janoshik_certificates(test_category);
CREATE INDEX IF NOT EXISTS idx_janoshik_batch ON janoshik_certificates(batch_number);

-- Aggiungi metriche di testing completeness ai supplier_rankings
ALTER TABLE supplier_rankings ADD COLUMN testing_completeness_score REAL DEFAULT 50.0;  -- Score 0-100
ALTER TABLE supplier_rankings ADD COLUMN batches_fully_tested INTEGER DEFAULT 0;  -- Batch con tutti 4 test
ALTER TABLE supplier_rankings ADD COLUMN total_batches_tracked INTEGER DEFAULT 0;  -- Totale batch tracciati
ALTER TABLE supplier_rankings ADD COLUMN avg_tests_per_batch REAL DEFAULT 1.0;  -- Media test per batch (1-4)

-- Indice per ordinare per completeness
CREATE INDEX IF NOT EXISTS idx_ranking_testing_completeness ON supplier_rankings(testing_completeness_score DESC);

-- Registra migration
INSERT OR IGNORE INTO schema_migrations (migration_name, description)
VALUES ('010_add_testing_completeness', 'Aggiunge tracking per test opzionali (heavy metals, microbiology) e score completeness');
