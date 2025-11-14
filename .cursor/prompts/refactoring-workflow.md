# Refactoring Workflow

Step-by-step process for safe, incremental refactoring.

## Phase 1: Preparation

### 1.1 Understand Current State
```
1. Read the TODO item carefully
2. Search codebase for all related code
3. Identify all files that will be affected
4. Understand current patterns and conventions
5. Check for existing tests
```

### 1.2 Analyze Dependencies
```
1. Map import dependencies
2. Identify circular dependencies (if any)
3. List all call sites of code to be changed
4. Check for external dependencies
```

### 1.3 Risk Assessment
```
1. What can break?
2. What data could be lost?
3. What APIs will change?
4. How to rollback?
```

## Phase 2: Design

### 2.1 Propose Approach
```
1. Document current implementation
2. Propose new structure
3. List all changes needed
4. Consider alternatives
5. Get confirmation (if major change)
```

### 2.2 Create Implementation Plan
```
1. Break down into atomic steps
2. Order steps by dependency
3. Identify test points
4. Plan validation at each step
```

## Phase 3: Implementation

### 3.1 Create New Code (if needed)
```
1. Write new implementation
2. Add type hints
3. Add docstrings
4. Write tests FIRST (TDD if possible)
5. Ensure it compiles/runs
```

### 3.2 Integrate Gradually
```
1. Add adapter/wrapper for backward compatibility
2. Update one call site at a time
3. Test after each change
4. Keep old code until fully migrated
```

### 3.3 Validate Continuously
```
1. Run linter after each file
2. Run tests after each logical change
3. Check for regressions
4. Verify functionality manually
```

## Phase 4: Cleanup

### 4.1 Remove Old Code
```
1. Ensure all call sites migrated
2. Remove old implementation
3. Remove adapter (if temporary)
4. Clean up unused imports
```

### 4.2 Documentation
```
1. Update docstrings
2. Update README if needed
3. Update CHANGELOG if breaking change
4. Update architecture docs if structural change
```

### 4.3 Final Validation
```
1. All tests pass
2. No linter errors
3. Manual testing complete
4. Documentation updated
5. TODO marked complete
```

## Red Flags - Stop and Reassess

If you encounter any of these, STOP and reassess:

- [ ] Multiple unrelated files need changes
- [ ] Breaking changes to public APIs
- [ ] Tests are failing and unclear why
- [ ] Circular dependencies introduced
- [ ] Code becomes more complex, not simpler
- [ ] Uncertain about approach

## Questions to Ask Before Coding

1. **Do I fully understand the current code?**
   - If no: Read more, search more, ask questions

2. **Is this the simplest solution?**
   - If no: Consider alternatives

3. **What will break if I make this change?**
   - If unclear: Analyze dependencies first

4. **Can I test this incrementally?**
   - If no: Break it down further

5. **Do I have a rollback plan?**
   - If no: Create one before starting

6. **Is this the right time for this change?**
   - If dependencies aren't ready: Wait or adjust plan

