-- Migration 018: Remove duplicate expiration_date column from batches
-- The batches table incorrectly has both expiry_date AND expiration_date.
-- This migration removes the unused expiration_date column.

-- First, copy any data from expiration_date to expiry_date (if expiry_date is NULL)
UPDATE batches SET expiry_date = expiration_date WHERE expiry_date IS NULL AND expiration_date IS NOT NULL;

-- SQLite doesn't support DROP COLUMN directly before version 3.35.0
-- We need to recreate the table

-- Create backup of the data
CREATE TABLE batches_backup AS SELECT * FROM batches;

-- Drop the original table
DROP TABLE batches;

-- Recreate without expiration_date
CREATE TABLE batches (
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
    storage_location TEXT,
    notes TEXT,
    coa_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP DEFAULT NULL
);

-- Restore data from backup
INSERT INTO batches SELECT id, supplier_id, product_name, batch_number, vials_count, 
    vials_received, vials_remaining, mg_per_vial, total_price, price_per_vial, 
    currency, purchase_date, manufacturing_date, expiry_date, storage_location, 
    notes, coa_path, created_at, deleted_at 
FROM batches_backup;

-- Drop backup
DROP TABLE batches_backup;

-- Verify the column is gone
SELECT 'Migration 018 completed: expiration_date column removed from batches' as status;
