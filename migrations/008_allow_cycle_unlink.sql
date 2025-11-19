-- Allow unlinking administrations from cycles (setting cycle_id to NULL)
-- This modifies the trigger to only prevent changing from one cycle to another,
-- but allows setting cycle_id to NULL for unlinking purposes.

BEGIN TRANSACTION;

-- Drop existing trigger
DROP TRIGGER IF EXISTS prevent_cycleid_overwrite;

-- Recreate with modified condition:
-- Prevents changing from one non-NULL cycle_id to another non-NULL cycle_id
-- But ALLOWS: cycle_id -> NULL (unlinking)
CREATE TRIGGER prevent_cycleid_overwrite
BEFORE UPDATE ON administrations
FOR EACH ROW
WHEN OLD.cycle_id IS NOT NULL AND NEW.cycle_id IS NOT NULL AND (NEW.cycle_id != OLD.cycle_id)
BEGIN
    SELECT RAISE(ABORT, 'Cannot change cycle_id from one cycle to another');
END;

COMMIT;

-- Notes:
-- - Allows setting cycle_id to NULL (unlinking administration from cycle)
-- - Still prevents changing from one cycle to another (e.g., cycle 1 -> cycle 2)
-- - Allows setting cycle_id on a previously unlinked administration (NULL -> cycle_id)
