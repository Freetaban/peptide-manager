-- Migration 011: Enhance suppliers table with Janoshik metrics
-- Date: 2025-12-06
-- Purpose: Add Janoshik quality metrics to suppliers table

-- Add Janoshik metrics columns
ALTER TABLE suppliers ADD COLUMN janoshik_certificates INTEGER DEFAULT 0;
ALTER TABLE suppliers ADD COLUMN janoshik_avg_purity REAL;
ALTER TABLE suppliers ADD COLUMN janoshik_min_purity REAL;
ALTER TABLE suppliers ADD COLUMN janoshik_max_purity REAL;
ALTER TABLE suppliers ADD COLUMN janoshik_last_test_date TEXT;
ALTER TABLE suppliers ADD COLUMN janoshik_days_since_last_test INTEGER;
ALTER TABLE suppliers ADD COLUMN janoshik_quality_score REAL; -- 0-100 score
ALTER TABLE suppliers ADD COLUMN janoshik_updated_at TIMESTAMP;

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_suppliers_janoshik_certificates ON suppliers(janoshik_certificates);
CREATE INDEX IF NOT EXISTS idx_suppliers_janoshik_quality ON suppliers(janoshik_quality_score);
