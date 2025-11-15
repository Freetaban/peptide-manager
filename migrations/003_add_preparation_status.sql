-- Migration 003: Add preparation status and wastage tracking
-- Gestisce il problema del volume mancante/perdite di misurazione

-- Add status column (active, depleted, expired, discarded)
ALTER TABLE preparations ADD COLUMN status TEXT DEFAULT 'active' 
    CHECK(status IN ('active', 'depleted', 'expired', 'discarded'));

-- Add depletion tracking
ALTER TABLE preparations ADD COLUMN actual_depletion_date DATE;

-- Add wastage tracking
ALTER TABLE preparations ADD COLUMN wastage_ml REAL;
ALTER TABLE preparations ADD COLUMN wastage_reason TEXT 
    CHECK(wastage_reason IN ('measurement_error', 'spillage', 'contamination', 'other'));
ALTER TABLE preparations ADD COLUMN wastage_notes TEXT;

-- Create index for filtering by status
CREATE INDEX IF NOT EXISTS idx_preparations_status ON preparations(status);

-- Create index for active preparations (most common query)
CREATE INDEX IF NOT EXISTS idx_preparations_active ON preparations(status, deleted_at, volume_remaining_ml);

-- Update existing preparations to 'active' status
UPDATE preparations 
SET status = 'active' 
WHERE status IS NULL;

-- Mark preparations with 0 volume as 'depleted'
UPDATE preparations 
SET status = 'depleted',
    actual_depletion_date = CURRENT_DATE
WHERE volume_remaining_ml <= 0 AND status = 'active';
