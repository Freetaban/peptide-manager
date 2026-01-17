# Treatment Planner - Rollback Summary

**Data:** 17 Gennaio 2026  
**Branch:** feature/treatment-planner  
**Operazione:** Rollback temporaneo + Preservazione modifica Janoshik URL

---

## ✅ Operazioni Completate

### 1. Backup Completo
Tutti i file del Treatment Planner salvati in:
```
backups/treatment_planner_wip/
```

**Contenuto:**
- ✅ gui.py (modificato)
- ✅ peptide_manager/models/base.py (modificato)
- ✅ peptide_manager/models/planner.py (modificato)
- ✅ gui_modular/views/treatment_planner.py (nuovo)
- ✅ docs/TREATMENT_PLANNER_WIZARD.md (nuovo)
- ✅ scripts/test_treatment_planner_wizard.py (nuovo)
- ✅ .github/prompts/plan-multiPhaseTreatmentCyclePlanner.prompt.md (nuovo)
- ✅ migrations/012_add_treatment_planner.sql (reference)
- ✅ README.md (documentazione backup)
- ✅ SCRAPER_URL_FIX.md (documentazione fix URL)

### 2. Rollback File Treatment Planner

**File Ripristinati (git restore):**
- ✅ gui.py
- ✅ peptide_manager/models/base.py
- ✅ peptide_manager/models/planner.py

**File Rimossi:**
- ✅ gui_modular/views/treatment_planner.py
- ✅ docs/TREATMENT_PLANNER_WIZARD.md
- ✅ scripts/test_treatment_planner_wizard.py
- ✅ .github/prompts/plan-multiPhaseTreatmentCyclePlanner.prompt.md

### 3. Preservazione Modifica Janoshik

**File Mantenuto:** `peptide_manager/janoshik/scraper.py`

**Modifica:**
```python
# Linea 26
BASE_URL = "https://public.janoshik.com/"  # ← Nuovo URL
```

**Motivo:** Janoshik ha cambiato l'URL pubblico dei certificati.

---

## 📊 Stato Finale

### Git Status
```
On branch feature/treatment-planner

Changes not staged for commit:
  modified:   migrations/012_add_treatment_planner.sql
  modified:   peptide_manager/janoshik/scraper.py

no changes added to commit
```

### Database
- ✅ Migration 012 applicata (tabelle esistono ma non usate)
- ✅ Nessun impatto sul funzionamento corrente
- ✅ Backwards compatible

### Applicazione
- ✅ Import PeptideManager: OK
- ✅ Scraper URL: https://public.janoshik.com/ (corretto)
- ✅ GUI: Funzionante (senza tab Treatment Planner)
- ✅ Nessun errore critico

---

## 🔄 Per Riprendere Sviluppo

### Opzione 1: Restore da Backup (Consigliato)

```powershell
# Dalla root del progetto
Copy-Item -Recurse "backups\treatment_planner_wip\gui.py" "." -Force
Copy-Item -Recurse "backups\treatment_planner_wip\peptide_manager" "peptide_manager" -Force
Copy-Item -Recurse "backups\treatment_planner_wip\gui_modular" "gui_modular" -Force
Copy-Item "backups\treatment_planner_wip\docs\TREATMENT_PLANNER_WIZARD.md" "docs\" -Force
Copy-Item "backups\treatment_planner_wip\scripts\test_treatment_planner_wizard.py" "scripts\" -Force

# Verifica
git status
python scripts\test_treatment_planner_wizard.py
```

### Opzione 2: Stash e Branch

Se vuoi committare lo stato attuale prima di riprendere:

```bash
# Salva stato corrente
git add migrations/012_add_treatment_planner.sql
git add peptide_manager/janoshik/scraper.py
git commit -m "Keep: migration 012 + Janoshik URL fix"

# Poi restore backup come sopra
```

---

## 📝 Note Importanti

### ✅ Cosa Funziona Ora
- Tutte le funzionalità esistenti (Peptidi, Batch, Preparazioni, Cicli, Amministrazioni, Calculator, Janoshik)
- Scraper Janoshik con URL aggiornato
- Database con tabelle Treatment Planner (vuote)

### ⚠️ Cosa NON È Disponibile
- Tab "Piani Trattamento" nella GUI
- Wizard creazione piani multi-fase
- Metodi backend: `create_treatment_plan()`, `activate_plan_phase()`, etc.
- Documentazione wizard

### 🗄️ Database Migration
La migration 012 rimane applicata. Le tabelle esistono ma non sono utilizzate:
- `treatment_plans`
- `plan_phases`
- `plan_resources`
- `plan_simulations`

Questo NON crea problemi perché:
- Tabelle vuote non impattano performance
- Nessun codice le referenzia dopo il rollback
- Backwards compatible al 100%

---

## 📚 Documentazione Disponibile

Nel backup `backups/treatment_planner_wip/`:
- **README.md**: Panoramica completa del lavoro fatto
- **SCRAPER_URL_FIX.md**: Dettagli modifica URL Janoshik
- **TREATMENT_PLANNER_WIZARD.md**: User guide completa (da docs/)
- **plan-multiPhaseTreatmentCyclePlanner.prompt.md**: Piano sviluppo originale

---

## 🎯 Prossimi Passi

Quando deciderai di riprendere lo sviluppo del Treatment Planner:

1. Restore files da backup (vedi sopra)
2. Completare implementazione backend:
   - `ResourcePlanner` in calculator.py
   - Metodi in PeptideManager
3. Testare wizard end-to-end
4. Aggiungere features avanzate (template, simulations, etc.)

---

**Rollback completato con successo!** ✅

Tutto il lavoro è al sicuro in `backups/treatment_planner_wip/` e può essere ripristinato in qualsiasi momento.
