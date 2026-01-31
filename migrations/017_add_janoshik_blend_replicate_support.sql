-- Migration: Add support for blend and replicate certificates in Janoshik system
-- Date: 2026-01-27
-- Description: Adds columns for multi-peptide blends, replicate measurements, and verification key index

-- Add new columns for blend support
ALTER TABLE janoshik_certificates ADD COLUMN protocol_name TEXT;
ALTER TABLE janoshik_certificates ADD COLUMN is_blend INTEGER DEFAULT 0;
ALTER TABLE janoshik_certificates ADD COLUMN blend_components TEXT;  -- JSON array

-- Add new columns for replicate support
ALTER TABLE janoshik_certificates ADD COLUMN has_replicates INTEGER DEFAULT 0;
ALTER TABLE janoshik_certificates ADD COLUMN replicate_measurements TEXT;  -- JSON array
ALTER TABLE janoshik_certificates ADD COLUMN replicate_statistics TEXT;  -- JSON object

-- Create indexes for efficient querying
CREATE INDEX idx_janoshik_is_blend ON janoshik_certificates(is_blend);
CREATE INDEX idx_janoshik_has_replicates ON janoshik_certificates(has_replicates);
CREATE INDEX idx_janoshik_protocol ON janoshik_certificates(protocol_name);

-- Add UNIQUE index for verification_key (critical for certificate validation)
-- Use IF NOT EXISTS to avoid errors if index already exists
CREATE UNIQUE INDEX IF NOT EXISTS idx_janoshik_verification_key
ON janoshik_certificates(verification_key)
WHERE verification_key IS NOT NULL;

-- Populate existing records with default values (single peptide, no replicates)
UPDATE janoshik_certificates
SET is_blend = 0,
    has_replicates = 0,
    protocol_name = NULL,
    blend_components = NULL,
    replicate_measurements = NULL,
    replicate_statistics = NULL
WHERE is_blend IS NULL OR has_replicates IS NULL;
