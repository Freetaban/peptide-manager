# 🌍 Gestione Ambienti

## Uso Quotidiano

### Sviluppo (Default)
```powershell
# Usa database sviluppo
python gui.py
# O esplicitamente:
python gui.py --env development
```

### Produzione (Con Conferma)
```powershell
# Usa database produzione
python gui.py --env production
```

## Script Utili

### Copia Prod → Dev
```powershell
# Aggiorna DB sviluppo con dati produzione
python scripts\copy_prod_to_dev.py
```

### Backup Produzione
```powershell
# Backup manuale
python scripts\backup_production.py
```

## Workflow Feature

1. **Inizio Feature:**
```powershell
   git checkout -b feature/nome-feature
   python scripts\copy_prod_to_dev.py  # Dati freschi
   python gui.py  # Ambiente sviluppo
```

2. **Sviluppo:**
   - Lavora su `data/development/peptide_management.db`
   - Testa modifiche liberamente

3. **Feature Completa:**
```powershell
   # Test finale
   python gui.py --env development
   
   # Merge su master
   git checkout master
   git merge feature/nome-feature
   
   # Deploy (vedi guida deploy)
```

## Sicurezza

✅ Database produzione: **MAI** committato
✅ Backup automatici: Ogni giorno
✅ Conferma richiesta: Apertura produzione