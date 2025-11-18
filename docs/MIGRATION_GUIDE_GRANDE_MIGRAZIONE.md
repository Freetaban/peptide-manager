**Guida alla "Grande Migrazione" — Treatment Cycles**

Scopo

## Dry-run eseguito (staging)

Ho eseguito un dry-run locale applicando le migrazioni su una copia del DB di produzione in `data/staging/peptide_management.db`.

- Copia DB produzione -> staging:

```powershell
Copy-Item data/production/peptide_management.db data/staging/peptide_management.db
```

- Applicazione migrazioni (esempio usato):

```powershell
- Fornire una checklist operativa e comandi precisi per migrare le funzionalità "treatment cycles" da ambiente di sviluppo a produzione.
- Garantire che la migrazione sia sicura, reversibile e tracciabile.

Prerequisiti
- Backup recente e verificato del DB di produzione (`data/production/peptide_management.db`).
- Ambiente di staging che replica struttura e dimensione dati di produzione.
```

- Risultati principali del dry-run:
   - `migrations/003_add_preparation_status.sql` è stata applicata (se alcune colonne esistevano già, lo script di migrazione è stato reso tollerante ai warning di colonne duplicate e ha registrato la migrazione come applicata in `schema_migrations`).
   - `migrations/004_add_administrations_cycle_id.sql` è stata applicata con successo su `data/staging/peptide_management.db` ed ora la tabella `administrations` include la colonna `cycle_id` (nullable).
   - Ho aggiunto il piccolo helper `scripts/apply_sql_to_db.py` per eseguire file SQL su un DB specifico in modo affidabile e compatibile con Windows.

- Comandi di verifica eseguiti:

```powershell
- Tutti i test unitari e di integrazione eseguiti e passati su `feature/treatment-cycles` branch.
- Accesso SSH/PowerShell alla macchina che ospita il DB di produzione.

```

- Note e raccomandazioni:
   - La migration `004_add_administrations_cycle_id.sql` è non-distruttiva (colonna nullable) ed è sicura per l'applicazione dopo backup.
   - Raccomando di eseguire lo stesso processo in uno staging che rispecchi i dati reali (dimensioni e casi edge) prima del cutover in produzione.

### Osservazioni emerse durante il dry-run

- In alcuni casi (DB di produzione aggiornato parzialmente), la tabella di tracking `schema_migrations` potrebbe non essere presente: questo accade quando si applicano file SQL manualmente (senza usare `migrations/migrate.py`). Se si preferisce usare `migrate.py` per tracciare le migrazioni, creare preventivamente la tabella `schema_migrations` oppure eseguire `migrate.py` direttamente puntando a un `.env` che risolva il `DB_PATH` di staging.

- Durante il mio dry-run ho applicato manualmente le migration su `data/staging/peptide_management.db` nell'ordine seguente: `003_add_preparation_status.sql`, `004_add_administrations_cycle_id.sql`, `002_add_cycles.sql`. Dopo l'applicazione la tabella `cycles` e la colonna `administrations.cycle_id` risultano presenti in staging. Nota: se si usa `migrate.py` queste operazioni vengono tracciate automaticamente in `schema_migrations`.

-- Raccomandazione operativa: preferire l'uso di `migrations/migrate.py --env <env>` quando possibile, perché inizializza e mantiene `schema_migrations`. Il deploy manuale di SQL è utile per interventi puntuali ma richiede attenzione al tracking e ai backup.

File e script rilevanti
- `migrations/002_add_cycles.sql` — tabelle cycles, treatment_plans, ecc.
- `migrations/003_add_preparation_status.sql` — status e campi wastage per `preparations`.
- `scripts/reconcile_wastage.py` — converte somministrazioni fittizie in wastage.
- `scripts/compare_schemas.py` — confronta schemi tra DB.
- `scripts/deploy_migrations.py` (da creare) — wrapper per applicare migration in ordine con logging.

Piano di azione (high-level)
1. Finalizzazione e test (DEV)
   - Completare UI/UX per templates e plans.
   - Eseguire `pytest` e test manuali GUI.
2. Dry-run su staging
   - Creare `data/staging/peptide_management.db` come copia produzione.
   - Applicare migrations in staging, eseguire reconcile scripts in DRY RUN.
   - Documentare tempo di esecuzione e problemi.
3. Preparazione produzione
   - Schedulare finestra di manutenzione.
   - Preparare backup full (file `.backup`) e checksum.
4. Cutover (migrazione live)
   - Fermare servizi che scrivono sul DB.
   - Eseguire backup definitivo.
   - Applicare migrations in ordine.
   - Eseguire reconciliation scripts (`reconcile_wastage.py --live`).
   - Eseguire smoke tests.
   - Riavviare servizi e monitorare.
5. Post-migration
   - Eseguire verifica completa e raccolta logs.
   - Comunicare agli utenti e smettere modalità di fallback.

Comandi consigliati (PowerShell)
- Creare backup (consigliato prima di ogni operazione):
```powershell
# crea file di backup SQLite (raw copy)
Copy-Item data/production/peptide_management.db data/backups/peptide_management.pre_migration_$(Get-Date -Format yyyyMMdd_HHmmss).db

# opzione: dump SQL (sqlite3 must be available)
sqlite3 data/production/peptide_management.db ".backup data/backups/peptide_management.pre_migration_$(Get-Date -Format yyyyMMdd_HHmmss).backup"
```

- Applicare migration singola (staging/test):
```powershell
# applica migration (esempio manuale)
# apri sqlite e esegui
sqlite3 data/staging/peptide_management.db < migrations/002_add_cycles.sql
sqlite3 data/staging/peptide_management.db < migrations/003_add_preparation_status.sql
```

- Eseguire reconciliation (dry run):
```powershell
python scripts/reconcile_wastage.py --db data/staging/peptide_management.db
```

- Eseguire reconciliation (live):
```powershell
python scripts/reconcile_wastage.py --db data/production/peptide_management.db --live
```

- Eseguire test automatici:
```powershell
.\venv\Scripts\Activate.ps1 ; python -m pytest tests/ -q
```

Checklist tecnica dettagliata (passo-passo)
1. Verifica readiness
   - `git checkout feature/treatment-cycles`
   - `pytest` verde
   - UI/UX funzionale in `gui_modular`
2. Creazione staging
   - Copia DB produzione -> `data/staging/` (file-based copy)
3. Dry-run migrations
   - Esegui i `.sql` su staging
   - Esegui `scripts/reconcile_wastage.py` in dry-run
   - Controlla differenze con `scripts/compare_schemas.py`
4. Correzioni
   - Se emergono errori, correggere codice/migration e ricominciare dry-run
5. Backup production definitivo
   - Come da comandi backup
6. Pause servizi (cutover)
   - Avvisa utenti; fermare servizi che scrivono su DB
7. Applicare migrations in produzione
   - Eseguire in ordine `002`, `003` (e eventuali altre)
   - Registrare output in `logs/migration_YYYYmmdd_HHMMSS.log`
8. Riconciliazione dati
   - Eseguire `scripts/reconcile_wastage.py --live` e altri script di mapping
9. Smoke tests
   - Verifiche rapide: login, elenco preparazioni, creare somministrazione, segnare esaurita
10. Riavvio servizi e monitor
   - Riavviare servizi GUI e job in background; monitorare errori 30–60 minuti
11. Verifiche estese (post-migrazione)
   - Eseguire test integrati e verifiche su KPI: conteggi record, report inventario
12. Comunicazione e documentazione
   - Aggiornare `docs/` e inviare nota agli utenti

Query di verifica SQL (esempi)
- Controllo conteggi principali:
```sql
SELECT COUNT(*) FROM preparations;
SELECT COUNT(*) FROM administrations WHERE deleted_at IS NULL;
SELECT COUNT(*) FROM treatment_plans;
SELECT COUNT(*) FROM protocol_templates;
```

- Controllo colonne nuove in `preparations`:
```sql
PRAGMA table_info(preparations);
```

- Verifica preparazioni esaurite e wastage:
```sql
SELECT id, batch_id, volume_ml, volume_remaining_ml, status, wastage_ml, actual_depletion_date
FROM preparations
WHERE status = 'depleted' OR wastage_ml IS NOT NULL
ORDER BY actual_depletion_date DESC
LIMIT 50;
```

Rollback (se necessario)
1. Se i problemi sono bloccanti, fermare nuovi scritti e ripristinare backup:
```powershell
Copy-Item data/backups/peptide_management.pre_migration_YYYYmmdd_HHMMSS.db data/production/peptide_management.db -Force
```
2. Riavviare servizi e aprire issue per investigazione.

Stime tempistiche (indicative)
- Dry-run su staging: 30–120 min (dipende dati e problemi)
- Backup produzione: 5–30 min (dimensione DB)
- Applicazione migrations: 1–30 min
- Riconciliazione dati: variabile (da pochi minuti a ore)
- Smoke tests + monitoraggio iniziale: 30–60 min

Punti di attenzione / rischi
- Migrations non idempotenti: assicurarsi che SQL sia safe per ripetizioni o usare `schema_migrations` per tracciare.
- Script di riconciliazione: testare in staging in DRY RUN e revisionare edge cases.
- GUI: feature incomplete possono confondere utenti; preferire modalità opt-in per abilitare cycles.
- Backup inconsistente: sempre verificare checksum e apertura del backup prima del cutover.

Contatti e responsabilità
- Sviluppo: [tu] (owner feature)
- QA: persona/role QA
- Operazioni/Deployment: persona/role ops

Allegati utili
- `docs/planning/PROTOCOL_EVOLUTION.md` (design e decisioni)
- `migrations/` (SQL files)
- `scripts/reconcile_wastage.py` (conversione legacy)
- `scripts/compare_schemas.py` (verifica differenze)

---
Nota: mantenere questa guida aggiornata man mano che emergono passi specifici durante i test. Buona preparazione alla migrazione!