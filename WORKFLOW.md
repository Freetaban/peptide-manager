# 🔄 Workflow Completo Sviluppo → Produzione

## 1️⃣ Inizio Nuova Feature
```powershell
# Crea branch feature
git checkout -b feature/nome-feature

# Copia dati produzione in sviluppo (dati freschi!)
python scripts\copy_prod_to_dev.py

# Apri ambiente sviluppo
python gui.py
```

## 2️⃣ Sviluppo Feature

- Lavora su `data/development/peptide_management.db`
- Modifica codice (`gui.py`, `models.py`, ecc.)
- Testa liberamente

## 3️⃣ Modifiche Schema Database

Se la feature richiede modifiche al database:
```powershell
# Crea file migrazione
# File: migrations/003_nome_feature.sql

-- Descrizione feature
CREATE TABLE IF NOT EXISTS nuova_tabella (...);
ALTER TABLE esistente ADD COLUMN nuova_colonna ...;
```

Applica in sviluppo:
```powershell
python migrations\migrate.py --env development
```

## 4️⃣ Test e Commit
```powershell
# Test completo
python gui.py --env development

# Commit codice
git add .
git commit -m "feat: descrizione feature"

# Commit migrazione (se presente)
git add migrations/003_nome_feature.sql
git commit -m "feat: add migration for nome-feature"
```

## 5️⃣ Merge su Master
```powershell
# Torna su master
git checkout master

# Merge feature
git merge feature/nome-feature

# Push
git push origin master
```

## 6️⃣ Deploy Produzione

### Opzione A: Deploy Automatico (Sicuro)
```powershell
# Dry run (simula)
python scripts\deploy_to_production.py --dry-run

# Deploy reale
python scripts\deploy_to_production.py
```

### Opzione B: Deploy Manuale
```powershell
# 1. Backup produzione
python scripts\backup_production.py

# 2. Applica migrazioni (se presenti)
python migrations\migrate.py --env production

# 3. Test
python gui.py --env production
```

## 7️⃣ Verifica Produzione
```powershell
# Apri produzione e verifica feature
python gui.py --env production

# Se OK, fatto!
# Se problemi, ripristina da backup:
copy backups\production\backup_*.db data\production\peptide_management.db
```

---

## 🚨 Situazioni Particolari

### Rollback Deploy Fallito
```powershell
# Trova ultimo backup
dir backups\production

# Ripristina
copy backups\production\pre_deploy_TIMESTAMP.db data\production\peptide_management.db
```

### Sincronizzazione Database Dopo Deploy
```powershell
# Dopo deploy produzione, aggiorna anche sviluppo
python scripts\copy_prod_to_dev.py
```

### Test Migrazione su Copia
```powershell
# Copia DB in temp
copy data\development\peptide_management.db test_migration.db

# Testa migrazione
python migrations\migrate.py --env development  # usa test_migration
```