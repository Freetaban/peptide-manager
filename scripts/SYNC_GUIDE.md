# Script di Sincronizzazione Feature Branch

Questi script ti aiutano a mantenere la feature branch sincronizzata con master.

## 📜 Script Disponibili

### 1. `sync-feature-branch.ps1` (Completo)
Script dettagliato con gestione errori, stash automatico e feedback.

**Uso base (rebase)**:
```powershell
.\scripts\sync-feature-branch.ps1
```

**Uso con merge invece di rebase**:
```powershell
.\scripts\sync-feature-branch.ps1 -UseMerge
```

**Uso con branch diversa**:
```powershell
.\scripts\sync-feature-branch.ps1 -FeatureBranch "feature/my-feature"
```

**Caratteristiche**:
- ✅ Salva automaticamente modifiche non committate (stash)
- ✅ Gestione errori e conflitti
- ✅ Supporta sia rebase che merge
- ✅ Push automatico con --force-with-lease (sicuro)
- ✅ Ripristina modifiche stashed

---

### 2. `quick-sync.ps1` (Veloce)
Versione rapida per sync frequenti.

**Uso**:
```powershell
.\scripts\quick-sync.ps1
```

**Cosa fa**:
1. `git checkout master`
2. `git pull`
3. `git checkout feature/wastage-and-multiprep`
4. `git rebase master`
5. `git push --force-with-lease`

---

## 🔄 Quando Sincronizzare

### Sync Consigliato
- **Ogni 1-2 settimane** se lavori poco su master
- **Dopo ogni fix/improvement importante** su master
- **Prima di merge finale** della feature in master

### Workflow Tipico

```powershell
# 1. Lavoro su master (produzione)
git checkout master
# ... fai modifiche ...
git add -A
git commit -m "Fix importante"
git push

# 2. Sincronizza feature branch
.\scripts\sync-feature-branch.ps1

# 3. Continua sviluppo feature
git checkout feature/wastage-and-multiprep
# ... sviluppo ...
```

---

## ⚠️ Gestione Conflitti

Se durante il sync ci sono conflitti:

### Con Rebase
```powershell
# 1. Risolvi conflitti nei file
# 2. Aggiungi file risolti
git add <file-risolto>

# 3. Continua rebase
git rebase --continue

# 4. Push con force
git push --force-with-lease

# OPPURE annulla tutto
git rebase --abort
```

### Con Merge
```powershell
# 1. Risolvi conflitti nei file
# 2. Aggiungi file risolti
git add <file-risolto>

# 3. Completa merge
git commit

# 4. Push normale
git push

# OPPURE annulla tutto
git merge --abort
```

---

## 🎯 Best Practices

1. **Usa rebase per sync periodici** → storia lineare
2. **Usa merge per integrazioni importanti** → preserva contesto
3. **Sincronizza frequentemente** → meno conflitti
4. **Testa dopo ogni sync** → assicurati che tutto funzioni
5. **Committa prima di sync** → evita complicazioni

---

## 🔍 Comandi Utili

```powershell
# Visualizza storia branch
git log --oneline --graph --all -20

# Vedi differenze tra master e feature
git diff master..feature/wastage-and-multiprep

# Vedi file modificati
git diff --name-only master..feature/wastage-and-multiprep

# Vedi quando è stato l'ultimo sync
git log --oneline --all | Select-String "Merge master"

# Torna su master
git checkout master
```

---

## 🚨 Troubleshooting

### "Push rejected" dopo rebase
```powershell
# Normale dopo rebase, usa force-with-lease (sicuro)
git push --force-with-lease origin feature/wastage-and-multiprep
```

### Hai modifiche non salvate
```powershell
# Salva temporaneamente
git stash

# Sincronizza
.\scripts\sync-feature-branch.ps1

# Ripristina
git stash pop
```

### Vuoi annullare un rebase in corso
```powershell
git rebase --abort
```

### Hai pushato ma vuoi tornare indietro
```powershell
# Attenzione: pericoloso se altri lavorano sulla stessa branch
git reset --hard origin/master
git push --force-with-lease
```
