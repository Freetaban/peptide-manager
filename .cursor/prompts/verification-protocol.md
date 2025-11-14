# Verification Protocol

Before marking any task complete, verify these items.

## Code Verification

### Syntax & Style
- [ ] No syntax errors
- [ ] No linter warnings/errors
- [ ] Code follows project style (PEP 8, type hints)
- [ ] No unused imports or variables
- [ ] No debug code left behind

### Functionality
- [ ] Code compiles/runs without errors
- [ ] All imports resolve correctly
- [ ] No circular dependencies
- [ ] Functions work as expected
- [ ] Edge cases handled

### Integration
- [ ] Changes integrate with existing code
- [ ] No breaking changes (or documented)
- [ ] Backward compatibility maintained
- [ ] All call sites updated
- [ ] Related modules still work

## Database Verification

### Schema Changes
- [ ] Alembic migration created
- [ ] Migration tested on dev database
- [ ] Foreign keys properly defined
- [ ] Indexes created where needed
- [ ] No data loss in migration

### Data Integrity
- [ ] Existing data still accessible
- [ ] Constraints properly enforced
- [ ] No orphaned records
- [ ] Relationships maintained

### Performance
- [ ] Queries use indexes
- [ ] No N+1 query problems
- [ ] Transactions properly scoped

## Testing Verification

### Unit Tests
- [ ] New tests written
- [ ] All tests pass
- [ ] Edge cases covered
- [ ] Error conditions tested
- [ ] Mocking used appropriately

### Integration Tests
- [ ] Integration tests updated
- [ ] End-to-end flows tested
- [ ] Database operations tested
- [ ] API contracts verified

### Manual Testing
- [ ] Feature works in GUI
- [ ] Feature works in CLI
- [ ] Error messages are clear
- [ ] User experience is good

## Documentation Verification

### Code Documentation
- [ ] Docstrings updated
- [ ] Type hints added
- [ ] Complex logic commented
- [ ] Examples in docstrings (if helpful)

### User Documentation
- [ ] README updated (if user-facing change)
- [ ] API docs updated (if API change)
- [ ] Migration guide updated (if needed)

### Architecture Documentation
- [ ] Architecture decisions logged
- [ ] Design patterns documented
- [ ] Dependencies updated

## Safety Verification

### Data Safety
- [ ] No production data at risk
- [ ] Backups exist (if DB changes)
- [ ] Rollback tested
- [ ] No data corruption possible

### System Safety
- [ ] No breaking changes to critical paths
- [ ] Error handling robust
- [ ] No resource leaks
- [ ] Proper cleanup on errors

### User Safety
- [ ] Destructive operations confirmed
- [ ] Clear error messages
- [ ] No data loss scenarios
- [ ] Recovery possible

## Checklist for Specific Task Types

### Database Migration Task
- [ ] Migration script created
- [ ] Tested on dev database
- [ ] Rollback tested
- [ ] Data migration verified
- [ ] Performance impact assessed
- [ ] Backup created before migration

### Repository Migration Task
- [ ] New repository created
- [ ] All CRUD operations implemented
- [ ] Tests written
- [ ] Adapter updated
- [ ] Old code removed
- [ ] All call sites updated

### UI Refactoring Task
- [ ] Component extracted
- [ ] Service layer used
- [ ] No business logic in UI
- [ ] Error handling implemented
- [ ] User feedback provided
- [ ] Tests updated (if applicable)

## Final Sign-off

Before marking TODO complete:

1. **Code Review**: Self-review using checklist above
2. **Test Run**: All tests pass, no regressions
3. **Manual Test**: Feature works as expected
4. **Documentation**: All docs updated
5. **Clean State**: No temporary files, debug code, or TODOs left

**Only then mark the task as complete.**

