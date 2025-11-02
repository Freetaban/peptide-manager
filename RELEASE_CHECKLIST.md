# Release Checklist v0.1.0

## Pre-Release Tasks

### Code
- [ ] Tutti i file aggiornati committati
- [ ] Branch `main` aggiornato
- [ ] Nessun TODO critico nel codice
- [ ] Version number aggiornato in setup.py (0.1.0)
- [ ] Version number aggiornato in main.py (0.1.0)

### Testing
- [ ] Test manuale TUI completo
- [ ] Test comandi CLI principali
- [ ] Database init/operations funzionanti
- [ ] Nessun crash su operazioni base
- [ ] Testato su Windows (se possibile)
- [ ] Testato su Linux (se possibile)

### Documentation
- [ ] README.md completo e accurato
- [ ] CHANGELOG.md aggiornato con v0.1.0
- [ ] CONTRIBUTING.md presente
- [ ] LICENSE presente (MIT)
- [ ] .gitignore completo
- [ ] SESSION_LOG.md aggiornato

### Files to Include
```
✅ README.md
✅ CHANGELOG.md
✅ CONTRIBUTING.md
✅ LICENSE
✅ .gitignore
✅ setup.py
✅ requirements.txt
✅ SESSION_LOG.md
✅ GUIDA_CORREZIONE_FIALE.md
```

### Files to Update in Repo
1. Replace `cli/utils/interactive.py` (fixed)
2. Replace `peptide_manager/models.py` (added adjust_vials)
3. Replace `cli/commands/batches.py` (added adjust command)
4. Replace `cli/main.py` (TUI integration)
5. Add `cli/tui.py` (new file)
6. Add/Update root files:
   - README.md
   - CHANGELOG.md
   - CONTRIBUTING.md
   - LICENSE
   - .gitignore

---

## GitHub Repository Setup

### Repository Settings
- [ ] Description: "Complete peptide management system with tracking, dilution calculator, and TUI"
- [ ] Topics/Tags: 
  - `python`
  - `cli`
  - `tui`
  - `peptides`
  - `health-tracking`
  - `sqlite`
  - `click`
- [ ] License: MIT
- [ ] README featured
- [ ] Issues enabled
- [ ] Discussions enabled (optional)
- [ ] Wiki disabled (use docs/)

### Branch Protection (optional)
- [ ] Protect `main` branch
- [ ] Require PR reviews
- [ ] Require status checks

---

## Creating Release

### Step 1: Tag Version
```bash
git tag -a v0.1.0 -m "Release v0.1.0 - Initial public release"
git push origin v0.1.0
```

### Step 2: Create GitHub Release

**Release Title:** `v0.1.0 - Initial Release`

**Tag:** `v0.1.0`

**Target:** `main`

**Release Notes Template:**

```markdown
# 🎉 Peptide Management System v0.1.0

First public release! Complete system for peptide tracking from purchase to administration.

## ✨ Highlights

- 🖥️ **DOS-Style TUI** - Immersive menu interface
- ⚡ **Powerful CLI** - Full command-line control
- 🧮 **Dilution Calculator** - Precise concentration calculations
- 📊 **Complete Tracking** - Suppliers, batches, preparations, protocols
- 🔧 **Error Recovery** - Vial count correction system

## 📦 Installation

```bash
pip install git+https://github.com/yourusername/peptide-management-system.git
```

Or clone and install:

```bash
git clone https://github.com/yourusername/peptide-management-system.git
cd peptide-management-system
pip install -e .
```

## 🚀 Quick Start

```bash
# Initialize database
peptide-manager init

# Launch TUI
peptide-manager

# Or use CLI
peptide-manager batches add
peptide-manager inventory
```

## 📚 Documentation

See [README.md](README.md) for complete documentation.

## 🐛 Known Issues

- Shell.py corrupted (use TUI instead)
- No automated tests yet

## 📝 Full Changelog

See [CHANGELOG.md](CHANGELOG.md) for detailed changes.

## 🙏 Acknowledgments

Thank you for trying out v0.1.0!

---

**Full Changelog**: https://github.com/yourusername/peptide-management-system/commits/v0.1.0
```

### Step 3: Attach Assets (optional)

No binaries for Python project, but could include:
- [ ] `peptide_management_schema.sql` (DB schema export)
- [ ] `QUICKSTART.pdf` (optional)

---

## Post-Release Tasks

### Announcement
- [ ] Post in GitHub Discussions (if enabled)
- [ ] Update project README with release link
- [ ] Share on relevant communities (if desired)

### Monitoring
- [ ] Watch for issues
- [ ] Respond to questions
- [ ] Collect feedback

### Next Steps
- [ ] Create `develop` branch for v0.2.0 work
- [ ] Add GitHub Issues for known TODOs
- [ ] Plan v0.2.0 features

---

## v0.2.0 Planning (Future)

**Target Date:** Q1 2025

**Planned Features:**
- Automated backup system
- Export to CSV/Excel/JSON
- Advanced reports
- Test suite (pytest)
- CI/CD pipeline (GitHub Actions)

---

## Rollback Plan

If critical issues found after release:

1. Create hotfix branch
2. Fix issue
3. Tag as v0.1.1
4. Release as patch
5. Update main

---

## Commands Reference

```bash
# Git operations
git status
git add .
git commit -m "Release v0.1.0"
git push origin main
git tag -a v0.1.0 -m "Release v0.1.0"
git push origin v0.1.0

# Verify installation
pip install -e .
peptide-manager --version
peptide-manager --help

# Test basic operations
peptide-manager init
peptide-manager summary
peptide-manager
```

---

## Checklist Summary

**Before Release:**
- ✅ All code committed
- ✅ Documentation complete  
- ✅ Manual testing done
- ✅ Version numbers updated

**During Release:**
- ✅ Tag created
- ✅ GitHub release published
- ✅ Release notes complete

**After Release:**
- ✅ Monitor feedback
- ✅ Plan next version
- ✅ Celebrate! 🎉

---

**Date Prepared:** 2025-01-XX  
**Release Manager:** [Your Name]  
**Status:** ⏳ Pending
