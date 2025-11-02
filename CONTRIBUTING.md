# Contributing to Peptide Management System

First off, thank you for considering contributing to Peptide Management System! 🎉

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Coding Standards](#coding-standards)
- [Commit Guidelines](#commit-guidelines)
- [Pull Request Process](#pull-request-process)

---

## Code of Conduct

This project adheres to a simple code of conduct: be respectful, constructive, and professional.

---

## How Can I Contribute?

### 🐛 Reporting Bugs

Before creating bug reports, please check existing issues. When creating a bug report, include:

- **Clear title** and description
- **Steps to reproduce** the behavior
- **Expected vs actual** behavior
- **System information** (OS, Python version)
- **Database state** if relevant (without sensitive data)
- **Logs or screenshots** if applicable

**Template:**
```markdown
**Environment:**
- OS: Windows 11 / Ubuntu 22.04 / macOS 13
- Python: 3.12.0
- Version: 0.1.0

**Steps to Reproduce:**
1. Run command '...'
2. Enter data '...'
3. See error

**Expected:** Should show inventory
**Actual:** Raises ValueError

**Logs:**
```
[paste error here]
```
```

### 💡 Suggesting Enhancements

Enhancement suggestions are welcome! Please provide:

- **Use case**: Why is this enhancement needed?
- **Proposed solution**: How should it work?
- **Alternatives**: What other solutions were considered?
- **Impact**: Who benefits from this?

### 📝 Documentation Improvements

- Fix typos or unclear explanations
- Add examples or use cases
- Improve docstrings
- Translate documentation (future)

### 🔨 Code Contributions

1. Pick an issue or create one
2. Fork the repository
3. Create a feature branch
4. Make your changes
5. Submit a pull request

---

## Development Setup

### Prerequisites

- Python 3.12+
- Git
- Virtual environment tool

### Installation

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/peptide-management-system.git
cd peptide-management-system

# Add upstream remote
git remote add upstream https://github.com/ORIGINAL_OWNER/peptide-management-system.git

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install in development mode with dev dependencies
pip install -e ".[dev]"
```

### Development Dependencies

```bash
# Install development tools
pip install black flake8 pytest pytest-cov mypy
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=peptide_manager --cov-report=html

# Run specific test file
pytest tests/test_models.py
```

### Database Testing

```bash
# Use test database (not main db)
peptide-manager --db test.db init
peptide-manager --db test.db inventory
```

---

## Coding Standards

### Style Guide

- **PEP 8** compliance
- **Black** for formatting: `black .`
- **Flake8** for linting: `flake8 .`
- **Type hints** on public functions
- **Docstrings** Google-style

### Example

```python
def calculate_concentration(mg_peptide: float, volume_ml: float) -> float:
    """
    Calcola la concentrazione risultante.
    
    Args:
        mg_peptide: Quantità di peptide in mg
        volume_ml: Volume di diluente in ml
        
    Returns:
        Concentrazione in mg/ml
        
    Raises:
        ValueError: Se volume <= 0
        
    Examples:
        >>> calculate_concentration(5.0, 2.0)
        2.5
    """
    if volume_ml <= 0:
        raise ValueError("Il volume deve essere maggiore di 0")
    
    return mg_peptide / volume_ml
```

### Code Organization

```python
# Order:
# 1. Standard library imports
import os
import sys
from datetime import datetime

# 2. Third-party imports
import click
from typing import Dict, List

# 3. Local imports
from peptide_manager import PeptideManager
from peptide_manager.calculator import DilutionCalculator
```

### Naming Conventions

- **Functions/Variables**: `snake_case`
- **Classes**: `PascalCase`
- **Constants**: `UPPER_SNAKE_CASE`
- **Private**: `_leading_underscore`

### Database

- Use **parameterized queries** (no string interpolation)
- Close connections in `finally` blocks
- Commit after successful operations
- Rollback on errors

```python
def safe_operation(self, data):
    """Example of safe DB operation."""
    cursor = self.conn.cursor()
    
    try:
        cursor.execute('INSERT INTO table (col) VALUES (?)', (data,))
        self.conn.commit()
        return cursor.lastrowid
    except Exception as e:
        self.conn.rollback()
        raise
    finally:
        # Connection closed by manager
        pass
```

---

## Commit Guidelines

### Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation only
- **style**: Formatting (no code change)
- **refactor**: Code restructuring
- **test**: Adding tests
- **chore**: Maintenance

### Examples

```bash
# Good commits
feat(batches): add adjust command for vial correction
fix(tui): handle keyboard interrupt gracefully
docs(readme): add quick start section
refactor(calculator): simplify dilution logic

# Bad commits (avoid)
update
fix bug
changes
asdf
```

### Scope

- **batches** - Batch management
- **peptides** - Peptide catalog
- **preparations** - Preparation handling
- **protocols** - Protocol management
- **suppliers** - Supplier handling
- **tui** - TUI interface
- **cli** - CLI commands
- **db** - Database
- **calc** - Calculator
- **core** - Core logic

---

## Pull Request Process

### Before Submitting

1. ✅ **Update from upstream**
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. ✅ **Run tests**
   ```bash
   pytest
   black .
   flake8 .
   ```

3. ✅ **Update documentation**
   - Update CHANGELOG.md
   - Update README.md if needed
   - Add docstrings to new functions

4. ✅ **Self-review**
   - Check diff for debug code
   - Remove commented code
   - Verify no sensitive data

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Manual testing done
- [ ] No regression

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-reviewed
- [ ] Commented complex code
- [ ] Updated documentation
- [ ] No new warnings
- [ ] Added tests

## Related Issues
Closes #123
```

### Review Process

1. **Automated checks** must pass (when CI/CD setup)
2. **Code review** by maintainer
3. **Discussion** if needed
4. **Approval** and merge

### After Merge

- Delete your feature branch
- Update your fork
- Celebrate! 🎉

---

## Project Structure

```
peptide-management-system/
├── cli/                    # User interface
│   ├── main.py            # Entry point
│   ├── tui.py             # TUI interface
│   ├── commands/          # CLI commands
│   └── utils/             # CLI utilities
├── peptide_manager/        # Core logic
│   ├── models.py          # Database operations
│   ├── database.py        # Schema
│   ├── calculator.py      # Dilution calculator
│   ├── reports.py         # Reports (TODO)
│   └── utils.py           # Utilities
├── tests/                  # Test suite
│   ├── test_models.py
│   ├── test_calculator.py
│   └── test_database.py
├── docs/                   # Documentation
├── data/                   # User data (gitignored)
├── examples/               # Example scripts
└── scripts/                # Utility scripts
```

---

## Questions?

- 💬 **Discussions**: Use GitHub Discussions for questions
- 🐛 **Issues**: Report bugs via GitHub Issues
- 📧 **Contact**: [maintainer email]

---

## Recognition

Contributors will be:
- Listed in CONTRIBUTORS.md
- Mentioned in release notes
- Forever appreciated! ❤️

---

Thank you for contributing! 🚀
