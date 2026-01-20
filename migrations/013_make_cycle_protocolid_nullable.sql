-- Migration 013: Make cycles.protocol_id nullable for planner-generated cycles
-- Date: 2025-01-XX
-- Reason: Cycles generati dal treatment planner non appartengono a protocol tradizionali

-- SQLite doesn't support ALTER COLUMN, so we need to:
-- 1. Create new table with nullable protocol_id
-- 2. Copy data
-- 3. Drop old table
-- 4. Rename new table

-- Create temporary table with nullable protocol_id
CREATE TABLE cycles_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    protocol_id INTEGER,  -- Made nullable
    name TEXT NOT NULL,
    description TEXT,
    start_date DATE,
    planned_end_date DATE,
    actual_end_date DATE,
    days_on INTEGER,
    days_off INTEGER DEFAULT 0,
    cycle_duration_weeks INTEGER,
    protocol_snapshot TEXT,
    ramp_schedule TEXT,
    status TEXT DEFAULT 'active',
    plan_phase_id INTEGER,  -- Link to plan_phases
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP,
    FOREIGN KEY (protocol_id) REFERENCES protocols(id) ON DELETE CASCADE,
    FOREIGN KEY (plan_phase_id) REFERENCES plan_phases(id) ON DELETE SET NULL
);

-- Copy all data from old table
INSERT INTO cycles_new 
SELECT * FROM cycles;

-- Drop old table
DROP TABLE cycles;

-- Rename new table
ALTER TABLE cycles_new RENAME TO cycles;

-- Recreate indexes
CREATE INDEX IF NOT EXISTS idx_cycles_protocol_id ON cycles(protocol_id);
CREATE INDEX IF NOT EXISTS idx_cycles_plan_phase_id ON cycles(plan_phase_id);
CREATE INDEX IF NOT EXISTS idx_cycles_status ON cycles(status);
CREATE INDEX IF NOT EXISTS idx_cycles_deleted_at ON cycles(deleted_at);
