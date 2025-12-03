# 📦 File Obsoleti - Peptide Management System

**Data spostamento:** 3 Dicembre 2025  
**Motivo:** Pulizia filesystem per mantenere solo file attivi e necessari

---

## 📂 Contenuti

### 1. **CLI (Command Line Interface)** - `cli/`
**Status:** Obsoleto - Non più utilizzato  
**Motivo:** Sostituito completamente da GUI Flet (gui.py)  
**Contenuto:**
- Interface TUI (Text User Interface) DOS-style
- Shell interattiva 
- Comandi modulari (batches, peptides, preparations, protocols, suppliers)
- Utilities interattive

### 2. **GUI Modular** - `gui_modular/`
**Status:** Progetto abbandonato  
**Motivo:** Approccio modulare non necessario per il progetto. Si usa `gui.py` monolitico.  
**Contenuto:**
- Tentativo di GUI modulare con views e components separati
- Thread-safe database wrapper
- Navigazione complessa

### 3. **Debug Scripts** - Root level
**Status:** File di debug temporanei  
**File:**
- `debug_compositions.py` - Debug batch compositions
- `debug_cycle_dashboard.py` - Debug cycle dashboard
- `debug_cycle_detail.py` - Debug cycle details
- `debug_preps.py` - Debug preparations
- `fix_prep6.py` - Fix specifico preparation #6
- `test_rampup.py` - Test ramp schedule

### 4. **Scripts Obsoleti** - `scripts/`
**Status:** Script di utility non più necessari  
**File:**
- `test_assign.py` - Test assignment
- `test_multiprep.py` - Test multi-preparation
- `purge_cycles.py` - Purge cycles (manuale)
- `purge_cycles_auto.py` - Purge cycles (automatico)
- `smoke_gui_actions.py` - Smoke test GUI actions (sostituito da smoke_test_gui.py)
- `import_from_csv.py` - Import dati da CSV (non più usato)
- `sync_prod_to_staging.py` - Sync production to staging (non più ambiente staging)
- `SYNC_GUIDE.md` - Guida sync branch
- `quick-sync.ps1` - PowerShell sync script
- `sync-feature-branch.ps1` - PowerShell feature branch sync

### 5. **Documentazione Obsoleta** - Root level
**Status:** Documentazione completata/superata  
**File:**
- `CLEANUP_PLAN.md` - Piano di cleanup (completato)
- `SESSION_LOG.md` - Log di sessione sviluppo (storico, info in Git)
- `GITHUB_TEMPLATES.md` - Templates GitHub (non necessari)
- `Makefile` - Makefile Unix (non usato su Windows)

### 6. **Documentazione Planning/Migration** - `docs/`
**Status:** Fasi completate  
**Cartelle:**
- `docs/planning/` - Documenti di planning (refactoring completato)
- `docs/migration/` - Guide migrazione (migrazione completata)
- `docs/demo.py` - File demo (test)

### 7. **Backups** - `backups/`
**Status:** Backup vecchia struttura  
**Motivo:** Si usa `data/backups/` struttura unificata  
**Contenuto:**
- `backups/production/` - Backup production obsoleti
- `backups/recovery/` - Recovery files

### 8. **Database File** - Root level
**Status:** File database in posizione errata  
**File:**
- `peptide_management.db` - Database nella root (usare `data/production/peptide_management.db`)

---

## ⚠️ Nota Importante

**NON ELIMINARE QUESTA CARTELLA** senza prima verificare che:
1. ✅ Il sistema funzioni correttamente senza questi file
2. ✅ Tutti i test passino (204/205 passing)
3. ✅ La GUI si avvii correttamente
4. ✅ Non ci siano riferimenti nel codice attivo

---

## 🔄 Ripristino

Se necessario ripristinare un file:
```powershell
# Esempio: ripristinare uno script
Copy-Item "file_obsoleti\scripts\nome_file.py" "scripts\" -Force
```

---

## 📅 Cronologia

### 3 Dicembre 2025
- **Cleanup iniziale**: Spostamento file obsoleti dopo refactoring completo
- **Test verifica**: 204/205 test passing post-cleanup
- **GUI verifica**: Import gui.py funzionante

---

## 📊 Statistiche Cleanup

- **File Python spostati:** ~15 file debug/test
- **Cartelle spostate:** 5 (cli, gui_modular, backups, docs/planning, docs/migration)
- **Script obsoleti:** 10 script
- **Documentazione:** 3 file markdown
- **Spazio recuperato:** ~50+ file organizzati

---

*Per domande o dubbi sul contenuto di questa cartella, consultare il commit Git corrispondente.*
