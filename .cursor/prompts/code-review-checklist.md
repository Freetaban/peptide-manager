# Code Review Checklist

Use this checklist before marking a task as complete.

## Pre-Implementation
- [ ] Task clearly understood
- [ ] All related code reviewed
- [ ] Approach validated
- [ ] Dependencies identified

## Implementation
- [ ] Code follows project conventions
- [ ] Type hints added
- [ ] Docstrings added/updated
- [ ] Error handling implemented
- [ ] Edge cases handled
- [ ] No hardcoded values (use config/constants)

## Code Quality
- [ ] No linter errors
- [ ] No unused imports
- [ ] No commented-out code (unless temporary)
- [ ] No debug print statements (use logging)
- [ ] Functions are focused and single-purpose
- [ ] No code duplication

## Database Changes
- [ ] Alembic migration created (if schema change)
- [ ] Foreign keys properly defined
- [ ] Indexes added where needed
- [ ] Data migration script (if needed)
- [ ] Rollback tested

## Testing
- [ ] Unit tests written
- [ ] Integration tests updated
- [ ] Existing tests still pass
- [ ] Edge cases tested
- [ ] Error conditions tested

## Documentation
- [ ] Docstrings updated
- [ ] README updated (if user-facing)
- [ ] CHANGELOG updated (if breaking change)
- [ ] Architecture docs updated (if structural change)

## Compatibility
- [ ] Backward compatibility maintained
- [ ] Adapter pattern used (if needed)
- [ ] Old code removed only after migration complete
- [ ] No breaking changes to public APIs

## Safety
- [ ] No production data at risk
- [ ] Backups verified (if DB changes)
- [ ] Destructive operations confirmed
- [ ] Error messages are user-friendly

## Final Checks
- [ ] All files saved
- [ ] Git status clean (or staged appropriately)
- [ ] TODO status updated
- [ ] Related tasks identified

