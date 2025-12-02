# Lessons Learned - Regressioni Accidentali

## Data: 1 Dicembre 2025

### Problema Rilevato
**Dialog "Aggiungi Preparazione" non funzionante**

### Root Cause
Commit `9817859` (30 Nov 2025, 22:57) ha accidentalmente rimosso 13 righe di codice dalla funzione `show_add_preparation_dialog()` durante un refactoring multi-file.

```python
# Codice rimosso per errore:
dialog = ft.AlertDialog(
    title=ft.Text("Nuova Preparazione"),
    content=ft.Column([...]),
    actions=[...],
)
self.page.overlay.append(dialog)
dialog.open = True
self.page.update()
```

### Impatto
- Feature critica (creazione preparazioni) completamente non funzionante
- Bug introdotto durante fix di altro bug (multi-prep registration)
- Nessun test ha rilevato il problema prima del deploy
- Codice rimasto rotto per ~12 ore (22:57 → 11:00)

### Processo che ha causato la regressione
1. Commit `9817859` aveva multiple modifiche (gui.py -176 righe, __init__.py, administration.py)
2. Focus del commit: multi-prep FIFO + floating point + dashboard
3. Refactoring aggressivo di gui.py senza validazione manuale/automatica
4. Probabile copy-paste incompleto o merge mal gestito

### Prevenzione Futura

#### 1. Test Automatizzati (PRIORITÀ ALTA)
```python
# tests/test_gui_dialogs.py
def test_add_preparation_dialog_opens():
    """Verifica che il dialog Aggiungi Preparazione si apra correttamente."""
    app = PeptideManagementGUI()
    # Simula click su "Aggiungi Preparazione"
    # Verifica che page.overlay contenga AlertDialog
    # Verifica che dialog.open == True
```

#### 2. Pre-commit Hooks
```bash
# .git/hooks/pre-commit
# Verifica che funzioni critiche non siano incomplete
python scripts/check_dialog_completeness.py
```

#### 3. Code Review Checklist
- [ ] Ogni modifica a dialog include test
- [ ] Refactoring con -100+ righe richiede review
- [ ] Multi-file commit richiede validazione manuale
- [ ] Modifiche a funzioni con pattern `def show_*_dialog` richiedono smoke test GUI

#### 4. Smoke Tests Manuali
Prima di ogni commit che tocca GUI:
```bash
python gui.py
# Verifica manualmente:
# 1. Dashboard si apre
# 2. Ogni dialog si apre cliccando pulsanti
# 3. Nessun crash
```

#### 5. Git Discipline
- **UN COMMIT = UN PROBLEMA**: Evitare commit multi-fix
- Commit separati per:
  1. Multi-prep logic (backend)
  2. Dashboard refactoring (gui.py)
  3. Floating point fix (models)
- Commit message deve listare file modificati e scope

#### 6. Backup & Recovery
- ✅ Già implementato: backup automatico al close
- ✅ Git commit frequency: ogni feature/fix
- ⚠️ Aggiungere: snapshot pre-refactoring

### Metrics
- **Detection Time**: ~12 ore (commit → segnalazione utente)
- **Fix Time**: ~15 minuti (diagnosi: 10 min, fix: 5 min)
- **Affected Users**: 1 (solo utente production)
- **Data Loss**: Nessuna (solo feature disabilitata temporaneamente)

### Conclusione
Questo tipo di regressione è **prevenibile** con:
1. Test GUI automatizzati
2. Smoke test manuali pre-commit
3. Discipline: 1 commit = 1 problema
4. Code review per refactoring massicci

**La fretta è nemica della qualità**: commit `9817859` ha toccato 3 file e introdotto ~10 modifiche diverse. Meglio 3 commit separati.

---

## Azioni Immediate
- [x] Fix dialog code
- [ ] Creare test per tutti i dialog
- [ ] Implementare pre-commit hook
- [ ] Documentare checklist review
- [ ] Aggiungere smoke test script
