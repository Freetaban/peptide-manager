# 🛡️ Sistema Anti-Regressioni - Quick Reference

## Setup Iniziale (1 volta)
```powershell
python scripts/install_hooks.py
```

## Prima di Ogni Commit

### 1️⃣ Se hai modificato GUI:
```powershell
python scripts/smoke_test_gui.py
```

### 2️⃣ Esegui test:
```powershell
python -m pytest tests/ -v
```

### 3️⃣ Commit (validazione automatica):
```powershell
git add .
git commit -m "Fix: descrizione chiara"
# Il pre-commit hook farà validazione automatica
```

## Cosa Fa il Sistema

### ✅ Pre-commit Hook Automatico
- Verifica sintassi Python
- Controlla che dialog GUI siano completi
- Avvisa se commit >200 righe

### ✅ Test Dialog GUI
- Verifica che ogni `show_*_dialog()` crei AlertDialog
- Verifica che dialog chiamino `page.update()`
- Previene regressioni come commit `9817859`

### ✅ Smoke Test GUI
- Testa inizializzazione app
- Testa caricamento views
- Verifica esistenza metodi dialog

## Saltare Validazione (Solo Emergenze)
```powershell
git commit --no-verify -m "Emergency fix"
```

## Help
- **Guida completa**: [DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md)
- **Lessons learned**: [LESSONS_LEARNED.md](LESSONS_LEARNED.md)
- **Test location**: `tests/test_gui_dialogs.py`
- **Scripts**: `scripts/pre_commit_check.py`, `scripts/smoke_test_gui.py`
