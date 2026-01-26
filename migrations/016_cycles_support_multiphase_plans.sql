-- Migration 016: Support multi-phase plans in cycles table
-- Rende protocol_id nullable e aggiunge plan_phase_id per collegare cycles a fasi di piani multi-fase

-- SQLite non supporta ALTER COLUMN, quindi dobbiamo ricreare la tabella

-- 1. Crea tabella temporanea con la nuova struttura
CREATE TABLE cycles_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    protocol_id INTEGER NULL,  -- Ora nullable
    name TEXT NOT NULL,
    description TEXT,
    start_date DATE,
    planned_end_date DATE,
    actual_end_date DATE,
    days_on INTEGER DEFAULT 7,
    days_off INTEGER DEFAULT 0,
    cycle_duration_weeks INTEGER,
    protocol_snapshot TEXT,
    ramp_schedule TEXT,
    status TEXT DEFAULT 'active',
    plan_phase_id INTEGER,  -- NUOVO: collega a plan_phases
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP,
    FOREIGN KEY (protocol_id) REFERENCES protocols(id),
    FOREIGN KEY (plan_phase_id) REFERENCES plan_phases(id)
);

-- 2. Copia dati esistenti
INSERT INTO cycles_new 
SELECT id, protocol_id, name, description, start_date, planned_end_date, 
       actual_end_date, days_on, days_off, cycle_duration_weeks, 
       protocol_snapshot, ramp_schedule, status,
       NULL as plan_phase_id,  -- Vecchi cycles non hanno plan_phase_id
       created_at, updated_at, deleted_at
FROM cycles;

-- 3. Elimina vecchia tabella
DROP TABLE cycles;

-- 4. Rinomina nuova tabella
ALTER TABLE cycles_new RENAME TO cycles;

-- 5. Ricrea indici se esistevano
CREATE INDEX IF NOT EXISTS idx_cycles_protocol_id ON cycles(protocol_id);
CREATE INDEX IF NOT EXISTS idx_cycles_plan_phase_id ON cycles(plan_phase_id);
CREATE INDEX IF NOT EXISTS idx_cycles_status ON cycles(status);
CREATE INDEX IF NOT EXISTS idx_cycles_start_date ON cycles(start_date);
