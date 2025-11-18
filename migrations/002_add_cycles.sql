-- Aggiunge supporto per Cycles tracking
-- Tabelle: cycles, cycle_peptides, cycle_preparations, cycle_alerts

CREATE TABLE IF NOT EXISTS cycles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    protocol_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    start_date DATE NOT NULL,
    planned_end_date DATE,
    actual_end_date DATE,
    days_on INTEGER,
    days_off INTEGER,
    cycle_duration_weeks INTEGER,
    protocol_snapshot TEXT, -- JSON snapshot of protocol targets/frequencies at cycle start
    ramp_schedule TEXT,     -- JSON structured ramp schedule (optional)
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP,
    FOREIGN KEY (protocol_id) REFERENCES protocols(id)
);

-- (resto delle tabelle cycles...)

CREATE INDEX IF NOT EXISTS idx_cycles_status ON cycles(status);
CREATE INDEX IF NOT EXISTS idx_cycles_protocol ON cycles(protocol_id);