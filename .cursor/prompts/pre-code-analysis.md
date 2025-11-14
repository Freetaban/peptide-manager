# Pre-Code Analysis Checklist

Before writing ANY code, complete this analysis.

## 1. Understand the Task

- [ ] Read the TODO item completely
- [ ] Understand what "done" looks like
- [ ] Identify acceptance criteria
- [ ] Note any constraints or requirements

## 2. Explore Current Codebase

### Search for Related Code
- [ ] Semantic search for concepts
- [ ] Grep for exact function/class names
- [ ] Check imports and dependencies
- [ ] Find similar implementations

### Read Relevant Files
- [ ] Read the ENTIRE file, not snippets
- [ ] Understand the context
- [ ] Note patterns and conventions
- [ ] Identify dependencies

### Map the System
- [ ] What files are affected?
- [ ] What functions/classes are involved?
- [ ] What are the data flows?
- [ ] What are the dependencies?

## 3. Identify Alternatives

### Approach A
- Description:
- Pros:
- Cons:
- Complexity:
- Risk:

### Approach B
- Description:
- Pros:
- Cons:
- Complexity:
- Risk:

### Recommended Approach
- [ ] Which approach? Why?
- [ ] What are the trade-offs?
- [ ] Is this the simplest solution?

## 4. Plan Implementation

### Break Down into Steps
1. [ ] Step 1: [description]
2. [ ] Step 2: [description]
3. [ ] Step 3: [description]

### Identify Test Points
- [ ] Where can I test incrementally?
- [ ] What tests need to be written?
- [ ] How to verify each step?

### Consider Edge Cases
- [ ] What if input is None?
- [ ] What if input is empty?
- [ ] What if input is invalid?
- [ ] What if database operation fails?
- [ ] What if file doesn't exist?

## 5. Risk Assessment

### What Can Break?
- [ ] List potential breaking changes
- [ ] Identify fragile dependencies
- [ ] Note areas of uncertainty

### Rollback Plan
- [ ] How to undo if something goes wrong?
- [ ] What backups are needed?
- [ ] How to verify rollback works?

### Safety Checks
- [ ] Is production data at risk?
- [ ] Are destructive operations confirmed?
- [ ] Can I test safely first?

## 6. Verification Strategy

### How Will I Know It Works?
- [ ] Unit tests to write
- [ ] Integration tests to update
- [ ] Manual testing steps
- [ ] Success criteria

### How Will I Know It's Safe?
- [ ] No regressions
- [ ] Existing tests still pass
- [ ] No data loss
- [ ] Error handling works

## 7. Documentation Needs

- [ ] What docstrings need updating?
- [ ] What README sections need changes?
- [ ] What architecture docs need updates?
- [ ] What decisions need to be logged?

## 8. Final Check Before Coding

- [ ] Do I fully understand the current code?
- [ ] Have I considered all alternatives?
- [ ] Is my plan clear and incremental?
- [ ] Do I have a rollback plan?
- [ ] Can I test this safely?
- [ ] Am I ready to code?

---

**Only proceed to coding after completing this analysis.**

If any item is unclear or uncertain, investigate further before proceeding.

