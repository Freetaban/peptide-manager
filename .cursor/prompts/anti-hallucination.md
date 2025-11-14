# Anti-Hallucination Protocol

Rules to prevent making up code, APIs, or implementation details.

## Core Rules

### 1. Never Assume
- ❌ Don't assume a function exists
- ❌ Don't assume a file path is correct
- ❌ Don't assume an API signature
- ✅ Always verify by searching the codebase

### 2. Verify Before Referencing
Before using any code element:
- [ ] Search for the exact name in codebase
- [ ] Read the actual implementation
- [ ] Check the file path is correct
- [ ] Verify the function signature
- [ ] Confirm the import path

### 3. Use Only Existing Code
- ✅ Reference code that exists
- ✅ Show actual file paths and line numbers
- ✅ Use code references format: ```startLine:endLine:filepath
- ❌ Never invent function names
- ❌ Never make up file paths
- ❌ Never assume implementation details

### 4. When Uncertain, Search First
If you're not 100% certain:
1. **Stop** and search the codebase
2. Use semantic search for concepts
3. Use grep for exact names
4. Read the actual files
5. Then proceed

## Verification Checklist

### Before Referencing a Function
- [ ] Searched for function name
- [ ] Found the actual definition
- [ ] Read the implementation
- [ ] Verified parameters and return type
- [ ] Checked all call sites

### Before Referencing a File
- [ ] Verified file exists
- [ ] Checked the actual path
- [ ] Read relevant sections
- [ ] Confirmed it's the right file

### Before Referencing a Pattern
- [ ] Found similar implementations
- [ ] Read the actual code
- [ ] Understood the pattern
- [ ] Verified it's used consistently

## Red Flags - Stop and Verify

If you catch yourself:
- [ ] Using a function name you haven't seen
- [ ] Referencing a file path you're not sure about
- [ ] Assuming an API exists
- [ ] Making up implementation details
- [ ] Guessing at behavior

**STOP** and verify before proceeding.

## Safe Practices

### When Showing Code Examples
1. Use actual code from codebase
2. Use code references with line numbers
3. If showing new code, clearly mark it as "proposed"
4. Never mix real and invented code

### When Proposing Changes
1. Show current implementation first
2. Explain what needs to change
3. Propose specific changes
4. Reference actual files and functions

### When Explaining Behavior
1. Base explanation on actual code
2. If uncertain, say "I need to check"
3. Don't make up behavior
4. Verify by reading code

## Example: Safe vs Unsafe

### ❌ Unsafe (Hallucination)
```python
# Assuming a function exists
manager.get_all_suppliers_with_details()
```

### ✅ Safe (Verified)
```python
# After searching, found actual method
# From peptide_manager/__init__.py:90
suppliers = self.db.suppliers.get_all(search=search)
```

## Verification Workflow

1. **Need to use something?**
   → Search codebase first

2. **Found it?**
   → Read the actual implementation
   → Verify it does what you think

3. **Not found?**
   → Don't assume it exists
   → Propose creating it
   → Or find alternative approach

4. **Uncertain?**
   → State the uncertainty
   → Propose investigation
   → Don't guess

## Remember

> "When in doubt, search it out."

It's better to:
- Take time to verify
- Admit uncertainty
- Propose investigation

Than to:
- Make up code
- Assume behavior
- Create confusion

