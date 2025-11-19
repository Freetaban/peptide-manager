-- Migration 006: Make cycles.start_date nullable
-- Permette di creare cicli "planned" senza data di inizio

-- SQLite non supporta ALTER COLUMN, quindi uso ricreazione tabella
-- Backup della tabella esistente
CREATE TABLE cycles_backup AS SELECT * FROM cycles;

-- Drop della tabella originale
DROP TABLE cycles;

-- Ricrea tabella con start_date nullable
CREATE TABLE IF NOT EXISTS cycles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    protocol_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    start_date DATE,  -- Rimosso NOT NULL
    planned_end_date DATE,
    actual_end_date DATE,
    days_on INTEGER,
    days_off INTEGER,
    cycle_duration_weeks INTEGER,
    protocol_snapshot TEXT,
    ramp_schedule TEXT,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP,
    FOREIGN KEY (protocol_id) REFERENCES protocols(id)
);

-- Ripristina dati
INSERT INTO cycles SELECT * FROM cycles_backup;

-- Drop backup
DROP TABLE cycles_backup;

-- Ricrea indici
CREATE INDEX IF NOT EXISTS idx_cycles_status ON cycles(status);
CREATE INDEX IF NOT EXISTS idx_cycles_protocol ON cycles(protocol_id);
