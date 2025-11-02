# GitHub Issue Templates

Create these files in `.github/ISSUE_TEMPLATE/` directory:

---

## 1. Bug Report

**File:** `.github/ISSUE_TEMPLATE/bug_report.md`

```markdown
---
name: Bug Report
about: Create a report to help us improve
title: '[BUG] '
labels: bug
assignees: ''
---

**Describe the bug**
A clear and concise description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:
1. Run command '...'
2. Enter data '...'
3. See error

**Expected behavior**
A clear and concise description of what you expected to happen.

**Screenshots**
If applicable, add screenshots to help explain your problem.

**Environment:**
 - OS: [e.g. Windows 11, Ubuntu 22.04]
 - Python Version: [e.g. 3.12.0]
 - Project Version: [e.g. 0.1.0]

**Additional context**
Add any other context about the problem here.

**Logs**
```
Paste relevant error messages or logs here
```
```

---

## 2. Feature Request

**File:** `.github/ISSUE_TEMPLATE/feature_request.md`

```markdown
---
name: Feature Request
about: Suggest an idea for this project
title: '[FEATURE] '
labels: enhancement
assignees: ''
---

**Is your feature request related to a problem? Please describe.**
A clear and concise description of what the problem is. Ex. I'm always frustrated when [...]

**Describe the solution you'd like**
A clear and concise description of what you want to happen.

**Describe alternatives you've considered**
A clear and concise description of any alternative solutions or features you've considered.

**Use Case**
Describe how this feature would be used and who would benefit from it.

**Additional context**
Add any other context or screenshots about the feature request here.

**Priority**
- [ ] Critical (blocking work)
- [ ] High (important)
- [ ] Medium (nice to have)
- [ ] Low (future consideration)
```

---

## 3. Question

**File:** `.github/ISSUE_TEMPLATE/question.md`

```markdown
---
name: Question
about: Ask a question about usage or functionality
title: '[QUESTION] '
labels: question
assignees: ''
---

**Your question**
What would you like to know?

**Context**
What are you trying to accomplish?

**What you've tried**
What have you already attempted?

**Environment:**
 - OS: [e.g. Windows 11]
 - Python Version: [e.g. 3.12.0]
 - Project Version: [e.g. 0.1.0]

**Additional information**
Any other details that might help us answer your question.
```

---

## 4. Documentation

**File:** `.github/ISSUE_TEMPLATE/documentation.md`

```markdown
---
name: Documentation
about: Suggest improvements to documentation
title: '[DOCS] '
labels: documentation
assignees: ''
---

**What needs to be documented?**
Which area of documentation needs improvement?

**Current state**
What's wrong or missing with current documentation?

**Suggested improvement**
How should it be improved?

**Affected files**
- [ ] README.md
- [ ] CHANGELOG.md
- [ ] Code docstrings
- [ ] Other: ___________

**Additional context**
Add any other context about the documentation request here.
```

---

## Setup Instructions

1. Create directory structure:
```bash
mkdir -p .github/ISSUE_TEMPLATE
```

2. Create each file:
```bash
touch .github/ISSUE_TEMPLATE/bug_report.md
touch .github/ISSUE_TEMPLATE/feature_request.md
touch .github/ISSUE_TEMPLATE/question.md
touch .github/ISSUE_TEMPLATE/documentation.md
```

3. Copy content above into respective files

4. Commit and push:
```bash
git add .github/
git commit -m "Add issue templates"
git push
```

---

## Labels to Create

Create these labels in GitHub Issues settings:

- `bug` (red) - Something isn't working
- `enhancement` (blue) - New feature or request
- `documentation` (green) - Improvements or additions to documentation
- `question` (yellow) - Further information is requested
- `help wanted` (purple) - Extra attention is needed
- `good first issue` (green) - Good for newcomers
- `duplicate` (gray) - This issue or pull request already exists
- `invalid` (gray) - This doesn't seem right
- `wontfix` (gray) - This will not be worked on
- `priority: high` (orange) - High priority
- `priority: low` (light blue) - Low priority

---

## Pull Request Template

**File:** `.github/PULL_REQUEST_TEMPLATE.md`

```markdown
## Description
Brief description of what this PR does

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Code refactoring
- [ ] Performance improvement

## Related Issues
Closes #(issue number)

## Testing
Describe the tests you ran and how to reproduce them:
- [ ] Unit tests pass (`pytest`)
- [ ] Manual testing completed
- [ ] No regression in existing features

## Checklist
- [ ] My code follows the style guidelines of this project
- [ ] I have performed a self-review of my own code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes
- [ ] Any dependent changes have been merged and published

## Screenshots (if applicable)
Add screenshots to help explain your changes

## Additional Notes
Any additional information that reviewers should know
```

Setup:
```bash
touch .github/PULL_REQUEST_TEMPLATE.md
# Copy content above
git add .github/PULL_REQUEST_TEMPLATE.md
git commit -m "Add PR template"
git push
```
