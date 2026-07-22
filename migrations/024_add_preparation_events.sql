-- Storico eventi preparazione: sprechi tracciabili, correggibili e cancellabili
--
-- Prima di questa migrazione gli sprechi erano accumulati in tre colonne piatte
-- su `preparations` (wastage_ml totale, wastage_reason sovrascritto, wastage_notes
-- testo libero append-only). I singoli episodi non avevano identita, quindi non
-- erano ne correggibili ne cancellabili.
--
-- Le colonne wastage_* su `preparations` restano come cache derivata (molti
-- lettori le usano) e vengono ricalcolate dagli eventi a ogni modifica.
--
-- Il backfill dai wastage_notes esistenti e' in scripts/backfill_preparation_events.py
-- (il parsing del testo libero non e' fattibile in SQL puro).
--
-- ROLLBACK:
--   DROP INDEX IF EXISTS idx_preparation_events_prep;
--   DROP TABLE IF EXISTS preparation_events;
--   -- le colonne wastage_* su preparations non sono state modificate

CREATE TABLE IF NOT EXISTS preparation_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    preparation_id INTEGER NOT NULL,
    event_type TEXT NOT NULL DEFAULT 'wastage'
        CHECK (event_type IN ('wastage', 'depletion')),
    volume_ml REAL NOT NULL,
    event_date DATE NOT NULL,
    reason TEXT
        CHECK (reason IS NULL OR reason IN ('measurement_error', 'spillage', 'contamination', 'other')),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    deleted_at TIMESTAMP DEFAULT NULL,
    FOREIGN KEY (preparation_id) REFERENCES preparations(id)
);

CREATE INDEX IF NOT EXISTS idx_preparation_events_prep
    ON preparation_events(preparation_id, event_date);
