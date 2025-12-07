-- Migration 009: Add quantity accuracy tracking to supplier_rankings
-- Data: 4 Dicembre 2025
-- Scopo: Aggiungere metriche di accuracy (quantità dichiarata vs testata)

-- Add accuracy columns to supplier_rankings
ALTER TABLE supplier_rankings ADD COLUMN avg_accuracy REAL;
ALTER TABLE supplier_rankings ADD COLUMN certs_with_accuracy INTEGER DEFAULT 0;
ALTER TABLE supplier_rankings ADD COLUMN accuracy_score REAL DEFAULT 50.0;

-- Note: accuracy_score default 50 (neutro) per certificati senza dato quantità
