-- Migration 007: Remove dose_ml from protocols table
-- The dose in ml depends on preparation concentration, not protocol definition

-- SQLite doesn't support DROP COLUMN directly, so we need to recreate the table

-- 1. Create new table without dose_ml
CREATE TABLE protocols_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    frequency_per_day INTEGER DEFAULT 1,
    days_on INTEGER,
    days_off INTEGER DEFAULT 0,
    cycle_duration_weeks INTEGER,
    notes TEXT,
    active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP DEFAULT NULL
);

-- 2. Copy data (excluding dose_ml)
INSERT INTO protocols_new (id, name, description, frequency_per_day, days_on, days_off, cycle_duration_weeks, notes, active, created_at, deleted_at)
SELECT id, name, description, frequency_per_day, days_on, days_off, cycle_duration_weeks, notes, active, created_at, deleted_at
FROM protocols;

-- 3. Drop old table
DROP TABLE protocols;

-- 4. Rename new table
ALTER TABLE protocols_new RENAME TO protocols;

-- Log migration
INSERT INTO schema_migrations (migration_name, description, applied_at) 
VALUES ('007_remove_protocol_dose_ml', 'Removed dose_ml from protocols table', CURRENT_TIMESTAMP);

SELECT '✅ Migration 007: Removed dose_ml from protocols table' as message;
