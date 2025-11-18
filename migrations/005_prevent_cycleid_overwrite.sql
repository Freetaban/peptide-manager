-- Prevent accidental overwrite of administrations.cycle_id
-- This trigger aborts any UPDATE that attempts to change an already-set cycle_id
-- to a different value (including NULL), enforcing one administration -> one cycle.
BEGIN TRANSACTION;

-- Drop existing trigger if present (SQLite doesn't support IF NOT EXISTS for CREATE TRIGGER)
DROP TRIGGER IF EXISTS prevent_cycleid_overwrite;

CREATE TRIGGER prevent_cycleid_overwrite
BEFORE UPDATE ON administrations
FOR EACH ROW
WHEN OLD.cycle_id IS NOT NULL AND (NEW.cycle_id IS NOT OLD.cycle_id)
BEGIN
    SELECT RAISE(ABORT, 'Cannot overwrite cycle_id once set');
END;

COMMIT;

-- Notes:
-- - This prevents changing an administration's cycle once assigned via application or manual SQL.
-- - If you need to allow unlinking in special cases, remove or alter this trigger accordingly.
