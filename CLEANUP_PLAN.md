# 🧹 Cleanup e Riorganizzazione Documentazione

**Data:** 14 Novembre 2025  
**Stato Progetto:** Post-refactoring completo (8 entità migrate a Repository pattern)

---

## 📊 ANALISI FILE OBSOLETI

### File da ELIMINARE (Obsoleti)

#### 1. **Backup Models Legacy**
```
peptide_manager/models_legacy_BACKUP.py          # Duplicato non necessario
peptide_manager/models_legacy_FULL_BACKUP.py     # Backup pre-cleanup
```
**Motivo:** `models_legacy.py` attuale (90 righe) è sufficiente. I backup completi sono in Git.

#### 2. **Database File Multipli**
```
peptide_dev.db                                   # Usare data/development/
peptide_management.db                            # Usare data/production/
peptide_management.db.backup_20251106_175102     # Vecchio backup
peptide_management_backup.db                     # Duplicato
test_db.db                                       # Test file isolato
```
**Motivo:** Centralizzare DB in `data/production/` e `data/development/`

#### 3. **Documentazione Ridondante** 
```
MIGRATION_PLAN_PREPARATIONS.md                  # Completata (vedere PEPTIDE_MODULE_COMPLETED.md)
REFACTORING_ISOLATION_PLAN.md                   # Completato refactoring
WORKFLOW_GIT_BRANCHES.md                        # Workflow semplice su master
```
**Motivo:** Refactoring completato, info storica disponibile in Git

#### 4. **File Temporanei/Cache**
```
__pycache__/                                    # Git ignore già presente
.pytest_cache/                                  # Git ignore già presente  
*.pyc                                           # Git ignore già presente
```
**Motivo:** File generati automaticamente

---

## 📁 RIORGANIZZAZIONE DOCUMENTAZIONE

### Struttura ATTUALE (Disorganizzata)
```
/
├── ARCHITECTURE.md
├── CHANGELOG.md
├── CONTRIBUTING.md
├── DECISIONS.md
├── GITHUB_TEMPLATES.md
├── MIGRATION_GUIDE.md
├── MIGRATION_PLAN_PREPARATIONS.md   ❌ OBSOLETO
├── README.md
├── README_ENVIRONMENTS.md
├── REFACTORING_GUIDE.md
├── REFACTORING_ISOLATION_PLAN.md    ❌ OBSOLETO
├── RELEASE_CHECKLIST.md
├── SESSION_LOG.md
├── WORKFLOW.md
├── WORKFLOW_GIT_BRANCHES.md         ❌ OBSOLETO
└── docs/
    ├── API.md
    ├── MIGRATION_GUIDE.md           ❌ DUPLICATO
    ├── MIGRATION_GUIDE_ENTITIES.md
    ├── PEPTIDE_MODULE_COMPLETED.md
    ├── QUICK_START.md
    ├── README.md
    ├── REFACTORING_SUMMARY.md
    ├── USAGE.md
    └── database_structure.sql
```

### Struttura PROPOSTA (Organizzata)
```
/
├── README.md                        # Main readme
├── LICENSE
├── .gitignore
├── requirements.txt
├── setup.py
├── pytest.ini
├── Makefile
│
├── docs/
│   ├── README.md                    # Index documentazione
│   ├── getting-started/
│   │   ├── QUICK_START.md           # Setup rapido
│   │   ├── USAGE.md                 # Guida uso quotidiano
│   │   └── ENVIRONMENTS.md          # (merge README_ENVIRONMENTS.md)
│   │
│   ├── architecture/
│   │   ├── ARCHITECTURE.md          # Design generale
│   │   ├── DECISIONS.md             # Architecture Decision Records
│   │   ├── DATABASE_SCHEMA.md       # (da database_structure.sql)
│   │   └── API.md                   # API reference
│   │
│   ├── development/
│   │   ├── CONTRIBUTING.md          # Come contribuire
│   │   ├── WORKFLOW.md              # Workflow Git
│   │   └── RELEASE_CHECKLIST.md     # Processo release
│   │
│   ├── migration/                   # Storia refactoring (archiviata)
│   │   ├── REFACTORING_SUMMARY.md   # Panoramica completamento
│   │   ├── MIGRATION_GUIDE_ENTITIES.md  # Dettagli tecnici migrazione
│   │   └── PEPTIDE_MODULE_COMPLETED.md  # Storia peptide module
│   │
│   └── planning/                    # ⚠️ IMPORTANTE - PROSSIMI CAMBIAMENTI
│       └── PROTOCOL_EVOLUTION.md    # 🔥 NUOVO - Protocolli vs Piani vs Cicli
│
├── CHANGELOG.md                     # Root level (importante)
└── SESSION_LOG.md                   # Root level (log sviluppo)
```

---

## 🔥 DOCUMENTAZIONE PROSSIMI CAMBIAMENTI

### PROTOCOL_EVOLUTION.md (DA CREARE)

**Contenuto importante da preservare/creare:**

#### Problema Attuale
Il sistema attuale ha una sola tabella `protocols` che mescola concetti diversi:
- **Protocollo Teorico**: Schema di dosaggio generico (es: "Melanotan II - Schema Estivo")
- **Piano di Trattamento**: Istanza specifica per un ciclo (es: "MT2 Ciclo Giugno 2025")
- **Registrazione Effettiva**: Somministrazioni reali collegate

#### Evoluzione Proposta: 3 Livelli

```
┌─────────────────────────────────────┐
│   PROTOCOLLO (Template)             │  ← Teorico, riutilizzabile
│   - Nome schema                     │
│   - Dosi standard                   │
│   - Peptidi coinvolti               │
│   - Schema giorni ON/OFF            │
└─────────────┬───────────────────────┘
              │ crea istanza
              ▼
┌─────────────────────────────────────┐
│   PIANO DI TRATTAMENTO              │  ← Istanza specifica
│   - Riferimento protocollo          │
│   - Date inizio/fine effettive      │
│   - Preparazioni assegnate          │
│   - Goal personalizzati             │
└─────────────┬───────────────────────┘
              │ esecuzione
              ▼
┌─────────────────────────────────────┐
│   CICLO/SOMMINISTRAZIONI            │  ← Registrazioni reali
│   - Riferimento piano                │
│   - Somministrazioni effettive      │
│   - Note/effetti osservati          │
│   - Progress tracking                │
└─────────────────────────────────────┘
```

#### Schema Database Proposto

**Tabella: `protocol_templates` (nuovo)**
```sql
CREATE TABLE protocol_templates (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    dose_ml REAL,
    frequency_per_day INTEGER,
    days_on INTEGER,
    days_off INTEGER,
    cycle_duration_weeks INTEGER,
    created_at TIMESTAMP,
    is_template INTEGER DEFAULT 1  -- sempre 1 (template)
);

CREATE TABLE protocol_template_peptides (
    id INTEGER PRIMARY KEY,
    template_id INTEGER REFERENCES protocol_templates(id),
    peptide_id INTEGER REFERENCES peptides(id),
    target_dose_mcg REAL
);
```

**Tabella: `treatment_plans` (nuovo)**
```sql
CREATE TABLE treatment_plans (
    id INTEGER PRIMARY KEY,
    protocol_template_id INTEGER REFERENCES protocol_templates(id),
    name TEXT NOT NULL,  -- es: "MT2 Ciclo Estate 2025"
    start_date DATE,
    end_date DATE,
    status TEXT CHECK(status IN ('planned', 'active', 'paused', 'completed')),
    notes TEXT,
    created_at TIMESTAMP
);

CREATE TABLE treatment_plan_preparations (
    id INTEGER PRIMARY KEY,
    plan_id INTEGER REFERENCES treatment_plans(id),
    preparation_id INTEGER REFERENCES preparations(id)
);
```

**Tabella: `administrations` (modificata)**
```sql
-- Aggiungere colonna:
ALTER TABLE administrations ADD COLUMN treatment_plan_id INTEGER REFERENCES treatment_plans(id);
-- Mantenere protocol_id per retrocompatibilità temporanea
```

#### Vantaggi

1. **Riusabilità**: Template protocollo usato per più cicli
2. **Tracking**: Statistiche per piano specifico (es: "Quanto consumato nel ciclo giugno?")
3. **Flessibilità**: Piano può deviare dal template senza modificarlo
4. **Analytics**: Confronto efficacia tra cicli diversi
5. **Planning**: Pianificare cicli futuri senza iniziarli

#### Migrazione Graduale

1. **Fase 1**: Creare nuove tabelle `protocol_templates` e `treatment_plans`
2. **Fase 2**: Migrare protocolli esistenti come template
3. **Fase 3**: Creare piani dai template per somministrazioni esistenti
4. **Fase 4**: Aggiornare GUI per gestire 3 livelli
5. **Fase 5**: Deprecare tabella `protocols` vecchia

---

## ✅ AZIONI IMMEDIATE

### 1. Eliminare File Obsoleti
```powershell
# Backup models legacy
Remove-Item peptide_manager/models_legacy_BACKUP.py
Remove-Item peptide_manager/models_legacy_FULL_BACKUP.py

# Database duplicati
Remove-Item peptide_dev.db
Remove-Item peptide_management.db
Remove-Item peptide_management.db.backup_20251106_175102
Remove-Item peptide_management_backup.db
Remove-Item test_db.db

# Documentazione obsoleta
Remove-Item MIGRATION_PLAN_PREPARATIONS.md
Remove-Item REFACTORING_ISOLATION_PLAN.md
Remove-Item WORKFLOW_GIT_BRANCHES.md
Remove-Item docs/MIGRATION_GUIDE.md  # Duplicato
```

### 2. Riorganizzare Documentazione
```powershell
# Creare nuove directory
New-Item -ItemType Directory -Path docs/getting-started
New-Item -ItemType Directory -Path docs/architecture
New-Item -ItemType Directory -Path docs/development
New-Item -ItemType Directory -Path docs/migration
New-Item -ItemType Directory -Path docs/planning

# Spostare file
Move-Item QUICK_START.md docs/getting-started/
Move-Item docs/USAGE.md docs/getting-started/
Move-Item README_ENVIRONMENTS.md docs/getting-started/ENVIRONMENTS.md

Move-Item ARCHITECTURE.md docs/architecture/
Move-Item DECISIONS.md docs/architecture/
Move-Item docs/API.md docs/architecture/
# Convertire database_structure.sql in DATABASE_SCHEMA.md

Move-Item CONTRIBUTING.md docs/development/
Move-Item WORKFLOW.md docs/development/
Move-Item RELEASE_CHECKLIST.md docs/development/

Move-Item docs/REFACTORING_SUMMARY.md docs/migration/
Move-Item docs/MIGRATION_GUIDE_ENTITIES.md docs/migration/
Move-Item docs/PEPTIDE_MODULE_COMPLETED.md docs/migration/
```

### 3. Creare Nuovo Documento
```powershell
# IMPORTANTE - Documentare evoluzione protocolli
New-Item docs/planning/PROTOCOL_EVOLUTION.md
# Contenuto: vedere sezione sopra
```

### 4. Aggiornare README Principale
Aggiungere sezione:
```markdown
## 📚 Documentazione

- **Quick Start**: [docs/getting-started/QUICK_START.md](docs/getting-started/QUICK_START.md)
- **Architecture**: [docs/architecture/](docs/architecture/)
- **Development**: [docs/development/](docs/development/)
- **Future Plans**: [docs/planning/](docs/planning/)
```

---

## 📊 METRICHE POST-CLEANUP

### Prima del Cleanup
- **File totali root**: 17 markdown
- **File obsoleti**: 6 (35%)
- **Database duplicati**: 5
- **Organizzazione**: Caotica

### Dopo il Cleanup
- **File root**: 3 markdown (README, CHANGELOG, SESSION_LOG)
- **Docs organizzati**: 4 cartegorie logiche
- **Database**: Centralizzati in data/
- **Organizzazione**: Strutturata e navigabile

---

## 🎯 PROSSIMI STEP (Dopo Cleanup)

1. **Implementare UI/UX Improvements** (dalle 3 proposte)
2. **Creare schema Protocol Evolution** (PROTOCOL_EVOLUTION.md)
3. **Design database per treatment plans**
4. **Prototipo GUI per gestione 3 livelli**
5. **Migrazione dati protocols → templates + plans**

---

**Nota:** Questo documento sarà archiviato in `docs/migration/` dopo l'esecuzione del cleanup.
