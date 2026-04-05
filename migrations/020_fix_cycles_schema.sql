-- Migration 020: Fix cycles table — make protocol_id nullable, add plan_phase_id
-- Necessario per i cicli generati dal treatment planner (non collegati a protocol tradizionali)

-- SQLite non supporta ALTER COLUMN: ricreazione tabella

CREATE TABLE cycles_020 (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    protocol_id           INTEGER,                        -- ora nullable
    name                  TEXT NOT NULL,
    description           TEXT,
    start_date            DATE,
    planned_end_date      DATE,
    actual_end_date       DATE,
    days_on               INTEGER,
    days_off              INTEGER,
    cycle_duration_weeks  INTEGER,
    protocol_snapshot     TEXT,
    ramp_schedule         TEXT,
    status                TEXT DEFAULT 'active',
    plan_phase_id         INTEGER,                        -- nuovo: link a plan_phases
    created_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at            TIMESTAMP,
    FOREIGN KEY (protocol_id)  REFERENCES protocols(id),
    FOREIGN KEY (plan_phase_id) REFERENCES plan_phases(id)
);

INSERT INTO cycles_020 (
    id, protocol_id, name, description,
    start_date, planned_end_date, actual_end_date,
    days_on, days_off, cycle_duration_weeks,
    protocol_snapshot, ramp_schedule, status,
    created_at, updated_at, deleted_at
)
SELECT
    id, protocol_id, name, description,
    start_date, planned_end_date, actual_end_date,
    days_on, days_off, cycle_duration_weeks,
    protocol_snapshot, ramp_schedule, status,
    created_at, updated_at, deleted_at
FROM cycles;

DROP TABLE cycles;
ALTER TABLE cycles_020 RENAME TO cycles;

CREATE INDEX IF NOT EXISTS idx_cycles_status       ON cycles(status);
CREATE INDEX IF NOT EXISTS idx_cycles_protocol_id  ON cycles(protocol_id);
CREATE INDEX IF NOT EXISTS idx_cycles_plan_phase_id ON cycles(plan_phase_id);
