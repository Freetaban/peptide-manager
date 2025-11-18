-- Aggiunge la colonna cycle_id alla tabella administrations per collegare somministrazioni ai cicli
BEGIN TRANSACTION;

ALTER TABLE administrations ADD COLUMN cycle_id INTEGER;

-- Creiamo un indice per ricerche veloci
CREATE INDEX IF NOT EXISTS idx_administrations_cycle_id ON administrations(cycle_id);

COMMIT;

-- Nota: questa migration è non distruttiva (colonna nullable). Eseguire su ambiente di sviluppo prima
-- di applicare in produzione e creare backup del DB.
