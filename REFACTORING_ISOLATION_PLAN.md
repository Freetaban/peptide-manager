# 🛡️ Piano di Isolamento per Refactoring

## 🎯 Obiettivo

Isolare completamente il lavoro di refactoring dal codice di produzione, permettendo:
- ✅ Uso quotidiano sicuro della versione stabile
- ✅ Sviluppo refactoring senza rischi
- ✅ Migrazione dati semplice quando pronto

## 📁 Struttura Proposta

```
C:\Users\ftaba\
├── source\
│   └── peptide-management-system\     # REPO GIT (sviluppo/refactoring)
│       ├── .git\
│       ├── peptide_manager\
│       ├── gui.py (in refactoring)
│       ├── data\
│       │   ├── development\          # DB sviluppo
│       │   └── production\            # DB produzione (condiviso)
│       └── ...
│
└── peptide-production\                 # DIRECTORY SEPARATA (produzione stabile)
    ├── peptide_manager\
    ├── gui.py (versione stabile)
    ├── cli\
    ├── scripts\
    ├── data\
    │   └── production\                # DB produzione (link simbolico o copia)
    └── requirements.txt
```

## 🔄 Workflow

### Fase 1: Setup Iniziale (Una Tantum)

#### 1.1 Crea Branch Stable
```powershell
cd C:\Users\ftaba\source\peptide-management-system

# Assicurati che master sia pulito e funzionante
git status
# Se ci sono modifiche, committale o stash

# Crea branch stable dal master corrente
git checkout -b stable
git push -u origin stable

# Torna a master per refactoring
git checkout master
```

#### 1.2 Crea Directory Produzione
```powershell
# Crea directory produzione (fuori dal repo)
New-Item -ItemType Directory -Path "C:\Users\ftaba\peptide-production"

# Copia file essenziali (script lo farà automaticamente)
```

#### 1.3 Crea Script di Sincronizzazione
```powershell
# Esegui script per copiare versione stabile
python scripts\create_production_copy.py --from-branch stable
```

### Fase 2: Uso Quotidiano (Produzione)

```powershell
# Vai nella directory produzione
cd C:\Users\ftaba\peptide-production

# Avvia GUI produzione (versione stabile, sempre funzionante)
python gui.py --env production

# Oppure usa shortcut sul desktop
```

**Vantaggi:**
- ✅ Codice stabile, mai cambia
- ✅ Nessun rischio di aprire branch sbagliato
- ✅ Database produzione sempre accessibile
- ✅ Nessuna interferenza con sviluppo

### Fase 3: Sviluppo Refactoring

```powershell
# Vai nel repo sviluppo
cd C:\Users\ftaba\source\peptide-management-system

# Assicurati di essere su master (o branch refactoring)
git checkout master
# oppure
git checkout -b refactoring/database-migration

# Lavora normalmente
# - Modifica codice
# - Testa su data/development/
# - Commit frequenti
```

**Vantaggi:**
- ✅ Isolato dalla produzione
- ✅ Puoi sperimentare liberamente
- ✅ Git traccia tutto
- ✅ Puoi rollback facilmente

### Fase 4: Aggiornamento Database Sviluppo

Durante il refactoring, quando serve testare con dati freschi:

```powershell
# Aggiorna database sviluppo con dati produzione
# (solo quando serve, non automatico)
python scripts\copy_prod_to_dev.py
```

**Nota:** Il database produzione NON viene mai toccato durante lo sviluppo. Solo il database sviluppo viene aggiornato quando serve.

### Fase 5: Migrazione Finale

Quando il refactoring è completo e testato:

```powershell
# 1. Test completo su sviluppo
cd C:\Users\ftaba\source\peptide-management-system
python gui.py --env development
# Verifica tutto funziona

# 2. Merge su stable
git checkout stable
git merge master
# Risolvi conflitti se necessario

# 3. Aggiorna directory produzione
python scripts\create_production_copy.py --from-branch stable

# 4. Test produzione
cd C:\Users\ftaba\peptide-production
python gui.py --env production
# Verifica tutto funziona

# 5. Migra dati (se schema cambiato)
python scripts\migrate_production_data.py
```

## 📋 File da Copiare in Produzione

### Essenziali (Sempre)
- `peptide_manager/` (tutto)
- `gui.py`
- `requirements.txt`
- `setup.py`
- `scripts/` (tutti tranne quelli di sviluppo)

### Opzionali
- `cli/` (solo se usi CLI/TUI, non necessario per GUI)

### Configurazione
- `.env.production` (se esiste)
- `pytest.ini` (opzionale)

### Database
- **NON copiare** il database fisico produzione
- **Creare link simbolico** a `data/production/` del repo
- Il database produzione rimane in: `peptide-management-system/data/production/peptide_management.db`
- La directory produzione punta allo stesso file tramite link
- Il database sviluppo (`data/development/`) è separato e NON viene copiato nella directory produzione

### NON Copiare
- `tests/` (non serve in produzione)
- `docs/` (opzionale)
- `.cursor/` (solo sviluppo)
- `.cursorrules` (solo sviluppo)
- `ARCHITECTURE.md`, `DECISIONS.md` (solo sviluppo)
- File di sviluppo temporanei
- `data/production/` (link simbolico invece di copia)

## 🔐 Sicurezza

### Protezioni
1. **Directory produzione read-only** (opzionale)
   - Previene modifiche accidentali
   - Solo script può aggiornare

2. **Backup automatico prima di aggiornamento**
   - Script crea backup prima di copiare
   - Rollback possibile

3. **Verifica hash file**
   - Script verifica integrità dopo copia
   - Assicura copia corretta

## 🚀 Script da Creare

### 1. `scripts/create_production_copy.py`
Crea/aggiorna directory produzione da branch git.

### 2. `scripts/sync_production_data.py`
Sincronizza dati produzione → sviluppo (opzionale).

### 3. `scripts/migrate_production_data.py`
Migra dati quando refactoring completo (futuro).

## ✅ Vantaggi di Questo Approccio

1. **Isolamento Completo**
   - Produzione mai toccata da refactoring
   - Sviluppo può rompersi senza conseguenze

2. **Sicurezza**
   - Nessun rischio di aprire branch sbagliato
   - Database produzione protetto

3. **Flessibilità**
   - Puoi lavorare su refactoring per mesi
   - Produzione continua a funzionare

4. **Semplicità**
   - Directory produzione = versione stabile
   - Nessuna confusione

5. **Migrazione Facile**
   - Quando pronto, script aggiorna tutto
   - Dati migrati automaticamente

## ⚠️ Considerazioni

### Database Produzione: Posizione e Strategia

**Raccomandazione: Database Condiviso (Link Simbolico)**

Il database produzione **rimane nella posizione originale** nel repo:
```
C:\Users\ftaba\source\peptide-management-system\data\production\peptide_management.db
```

La directory produzione crea un **link simbolico** che punta allo stesso file:
```
C:\Users\ftaba\peptide-production\data\production\ → (link) → C:\Users\ftaba\source\peptide-management-system\data\production\
```

**Flusso Dati:**
- **Produzione**: Database modificato solo durante uso quotidiano in produzione
- **Sviluppo**: Database separato (`data/development/`), aggiornato periodicamente da produzione
- **Direzione**: Solo produzione → sviluppo (mai il contrario!)

**Vantaggi:**
- ✅ **Un solo database produzione** - nessuna duplicazione
- ✅ **Nessun rischio di divergenza** - entrambe le directory (repo e produzione) usano lo stesso file
- ✅ **Backup automatici** continuano a funzionare (puntano al file originale)
- ✅ **Semplice da gestire** - nessuna sincronizzazione necessaria

**Come funziona:**
1. Il database fisico produzione è in: `peptide-management-system/data/production/`
2. Lo script crea un link simbolico in: `peptide-production/data/production/`
3. Entrambe le directory accedono allo stesso file fisico
4. Le modifiche in produzione sono immediatamente visibili da entrambe
5. Il database sviluppo (`data/development/`) è separato e viene aggiornato da produzione quando serve tramite `copy_prod_to_dev.py`

**Nota Windows:**
- Link simbolici su Windows richiedono privilegi admin o "Developer Mode" abilitato
- Se non disponibile, lo script copia la directory (fallback)
- In questo caso, entrambe le directory avranno una copia, ma solo quella nel repo viene usata/modificata

## 📝 Checklist Setup

- [x] Crea branch `stable` da master corrente
- [x] Crea directory `C:\Users\ftaba\peptide-production`
- [x] Crea script `create_production_copy.py`
- [x] Esegui script per copiare versione stabile
- [x] Crea venv nella directory produzione
- [x] Installa dipendenze nel venv
- [ ] Testa produzione nella nuova directory
- [ ] Crea shortcut desktop per produzione (opzionale)
- [x] Documenta processo nel README

## 🎯 Prossimi Passi

1. **Ora:** Crea script e directory produzione
2. **Durante refactoring:** Lavora nel repo, usa produzione separata
3. **Quando pronto:** Migra tutto in una volta

