-- Migration 014: Rimuove colonna dose_ml da protocols
-- Motivo: Il dosaggio è definito a livello di peptide (mcg/giorno),
--         il volume in ml viene calcolato in base alla concentrazione della preparazione

-- SQLITE non supporta ALTER TABLE DROP COLUMN prima della versione 3.35.0
-- Dobbiamo ricreare la tabella senza la colonna dose_ml

-- Backup dati esistenti
CREATE TABLE protocols_backup AS
SELECT id, name, description, frequency_per_day, days_on, days_off,
       cycle_duration_weeks, notes, active, created_at, deleted_at
FROM protocols;

-- Elimina tabella originale
DROP TABLE protocols;

-- Ricrea tabella senza dose_ml
CREATE TABLE protocols (
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

-- Ripristina dati
INSERT INTO protocols (id, name, description, frequency_per_day, days_on, days_off,
                       cycle_duration_weeks, notes, active, created_at, deleted_at)
SELECT id, name, description, frequency_per_day, days_on, days_off,
       cycle_duration_weeks, notes, active, created_at, deleted_at
FROM protocols_backup;

-- Elimina backup
DROP TABLE protocols_backup;

-- Ricrea index se necessario
-- (Non ci sono index su protocols nella struttura attuale)

-- Verifica
SELECT 'Migration 014 completed: dose_ml removed from protocols' as status;
