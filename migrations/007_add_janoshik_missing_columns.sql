-- Migration 007: Add missing columns to janoshik_certificates
-- Date: 2025-12-06
-- Purpose: Align database schema with JanoshikCertificate model

-- Add supplier_website
ALTER TABLE janoshik_certificates ADD COLUMN supplier_website TEXT;

-- Add peptide_name (renamed from product_name)
ALTER TABLE janoshik_certificates ADD COLUMN peptide_name TEXT;

-- Add batch_number
ALTER TABLE janoshik_certificates ADD COLUMN batch_number TEXT;

-- Add date fields
ALTER TABLE janoshik_certificates ADD COLUMN testing_ordered TEXT;
ALTER TABLE janoshik_certificates ADD COLUMN sample_received TEXT;
ALTER TABLE janoshik_certificates ADD COLUMN analysis_conducted TEXT;

-- Add quantity_tested_mg
ALTER TABLE janoshik_certificates ADD COLUMN quantity_tested_mg REAL;

-- Add heavy_metals_result (JSON)
ALTER TABLE janoshik_certificates ADD COLUMN heavy_metals_result TEXT;

-- Add microbiology fields
ALTER TABLE janoshik_certificates ADD COLUMN microbiology_tamc INTEGER;
ALTER TABLE janoshik_certificates ADD COLUMN microbiology_tymc INTEGER;

-- Add test categorization
ALTER TABLE janoshik_certificates ADD COLUMN test_type TEXT;
ALTER TABLE janoshik_certificates ADD COLUMN test_category TEXT;

-- Add comments
ALTER TABLE janoshik_certificates ADD COLUMN comments TEXT;

-- Add verification_key
ALTER TABLE janoshik_certificates ADD COLUMN verification_key TEXT;

-- Add raw_data (JSON)
ALTER TABLE janoshik_certificates ADD COLUMN raw_data TEXT;

-- Add scraped_at
ALTER TABLE janoshik_certificates ADD COLUMN scraped_at TEXT;

-- Add processed flag
ALTER TABLE janoshik_certificates ADD COLUMN processed INTEGER DEFAULT 0;
