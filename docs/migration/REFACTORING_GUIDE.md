# Refactoring Guide

This guide provides step-by-step instructions for safely refactoring the Peptide Management System.

## Workflow Overview

```
1. Select Task from TODO
   ↓
2. Pre-Code Analysis (use checklist)
   ↓
3. Design & Plan
   ↓
4. Implement Incrementally
   ↓
5. Verify & Test
   ↓
6. Document & Update
   ↓
7. Mark Complete
```

## Detailed Steps

### Step 1: Task Selection

1. Review TODO list
2. Select ONE task (atomic, focused)
3. Mark as "in_progress" in TODO
4. Read task description carefully
5. Understand acceptance criteria

### Step 2: Pre-Code Analysis

Use `.cursor/prompts/pre-code-analysis.md`:

1. **Understand the Task**
   - What exactly needs to be done?
   - What does "done" look like?

2. **Explore Codebase**
   - Search for related code
   - Read relevant files completely
   - Map dependencies

3. **Identify Alternatives**
   - Consider different approaches
   - Evaluate pros/cons
   - Choose simplest solution

4. **Plan Implementation**
   - Break into small steps
   - Identify test points
   - Consider edge cases

5. **Risk Assessment**
   - What can break?
   - Rollback plan?
   - Safety checks?

### Step 3: Design & Plan

1. **Document Current State**
   - Show existing implementation
   - Explain current patterns

2. **Propose Changes**
   - Describe new approach
   - Show what will change
   - List affected files

3. **Get Confirmation** (if major change)
   - Explain rationale
   - Show alternatives considered
   - Wait for approval

### Step 4: Implementation

Follow incremental approach:

1. **Create New Code** (if needed)
   - Write tests first (TDD)
   - Implement functionality
   - Add type hints
   - Add docstrings

2. **Integrate Gradually**
   - Update one call site at a time
   - Test after each change
   - Keep old code until migrated

3. **Validate Continuously**
   - Run linter after each file
   - Run tests after logical changes
   - Check for regressions

### Step 5: Verification

Use `.cursor/prompts/verification-protocol.md`:

1. **Code Verification**
   - No syntax errors
   - No linter errors
   - All imports resolve

2. **Functionality Verification**
   - Code works as expected
   - Edge cases handled
   - Error handling works

3. **Integration Verification**
   - Integrates with existing code
   - No breaking changes
   - Related modules work

4. **Testing Verification**
   - Unit tests pass
   - Integration tests pass
   - Manual testing complete

### Step 6: Documentation

1. **Code Documentation**
   - Update docstrings
   - Add type hints
   - Comment complex logic

2. **User Documentation**
   - Update README if needed
   - Update API docs if changed
   - Update migration guide

3. **Architecture Documentation**
   - Log decisions in DECISIONS.md
   - Update ARCHITECTURE.md
   - Note patterns used

### Step 7: Completion

1. **Final Checks**
   - All tests pass
   - No linter errors
   - Documentation updated
   - TODO marked complete

2. **Cleanup**
   - Remove temporary code
   - Remove debug statements
   - Clean up imports

## Task-Specific Guidelines

### Database Migration Tasks

1. **Before Starting**
   - Backup database
   - Review current schema
   - Plan migration steps

2. **During Implementation**
   - Create Alembic revision
   - Test on dev database
   - Verify data integrity

3. **After Completion**
   - Test rollback
   - Update documentation
   - Verify in production (carefully)

### Repository Migration Tasks

1. **Before Starting**
   - Review existing code
   - Understand data model
   - Plan repository interface

2. **During Implementation**
   - Create repository class
   - Implement CRUD methods
   - Write tests
   - Update adapter

3. **After Completion**
   - Remove old code
   - Update all call sites
   - Verify functionality

### UI Refactoring Tasks

1. **Before Starting**
   - Identify UI components
   - Understand current structure
   - Plan component hierarchy

2. **During Implementation**
   - Extract components
   - Create service layer
   - Update error handling
   - Test UI flows

3. **After Completion**
   - Verify all UI works
   - Test error scenarios
   - Update user docs

## Common Pitfalls to Avoid

1. **Working on Multiple Tasks**
   - ❌ Don't: Start new task before finishing current
   - ✅ Do: Complete one task fully before moving on

2. **Skipping Analysis**
   - ❌ Don't: Start coding immediately
   - ✅ Do: Complete pre-code analysis first

3. **Making Assumptions**
   - ❌ Don't: Assume code exists or works a certain way
   - ✅ Do: Verify by searching and reading code

4. **Breaking Compatibility**
   - ❌ Don't: Change APIs without migration path
   - ✅ Do: Use adapter pattern, migrate gradually

5. **Skipping Tests**
   - ❌ Don't: Skip writing tests
   - ✅ Do: Write tests, especially for new code

6. **Ignoring Linter**
   - ❌ Don't: Leave linter errors
   - ✅ Do: Fix all linter errors before proceeding

## Quality Gates

Before marking a task complete, ensure:

- [ ] All code follows project conventions
- [ ] All tests pass
- [ ] No linter errors
- [ ] Documentation updated
- [ ] No breaking changes (or documented)
- [ ] Manual testing complete
- [ ] Related tasks identified

## Getting Help

If stuck:

1. **Re-read the task** - Maybe missed something
2. **Search codebase** - Similar code might exist
3. **Review patterns** - Check how similar things are done
4. **Check documentation** - Architecture docs, decisions log
5. **Break it down** - Maybe task is too large

## Remember

- **One task at a time**
- **Think before code**
- **Verify, don't assume**
- **Test incrementally**
- **Document decisions**

