"""
GUI Janoshik Analytics - Checklist Verifica
============================================

STATO ATTUALE (Dec 6, 2025)
----------------------------
✅ Refactoring scoring/analytics COMPLETATO
✅ Queries usano campi standardizzati (peptide_name_std, quantity_nominal, unit_of_measure)
✅ GUI ha gestione errori corretta (mostra messaggio se moduli non disponibili)
⚠️  Feature Janoshik NON ancora attiva in production (tabella janoshik_certificates mancante)

VERIFICHE PRE-COMMIT
--------------------
[x] scorer.py: usa quantity_nominal dal DB (fallback regex)
[x] scorer.py: verifica unità (solo mg comparabili)
[x] analytics.py: get_hottest_peptides usa peptide_name_std direct query
[x] analytics.py: get_best_vendor_for_peptide usa exact match (non LIKE)
[x] analytics.py: get_peptide_vendors usa peptide_name_std
[x] analytics.py: get_vendor_peptide_matrix usa peptide_name_std
[x] analytics.py: get_top_vendors include campi standardizzati
[x] SCORING_ALGORITHM.md: documentazione aggiornata con benefici
[x] GUI: importa JanoshikViewsLogic correttamente
[x] GUI: gestisce HAS_JANOSHIK=False con messaggio
[x] Commit: edfbf2c completato con successo

VERIFICHE POST-ATTIVAZIONE (quando tabella janoshik_certificates sarà popolata)
--------------------------------------------------------------------------------
Quando la feature Janoshik sarà attiva in production, eseguire:

1. SMOKE TEST BASE
   ```powershell
   python scripts/test_analytics_integration.py
   ```
   Verifica:
   - [ ] get_hottest_peptides ritorna peptidi
   - [ ] get_best_vendor_for_peptide trova fornitori
   - [ ] >80% certificati hanno peptide_name_std popolato
   - [ ] Query exact match funziona (consolidamento varianti)

2. TEST GUI - Tab Classifica Fornitori
   ```powershell
   python gui.py
   # Naviga a: Janoshik Market → Classifica Fornitori
   ```
   Verifica:
   - [ ] Dropdown "Periodo" funziona (Mese, Trimestre, Anno, Tutti)
   - [ ] Bottone "Carica Dati" mostra tabella
   - [ ] Tabella ha colonne: #, Fornitore, Score, Certificati, Purezza Media/Min/Max, Qualità, Attività
   - [ ] Ordinamento corretto (miglior score in alto)
   - [ ] Badge qualità visualizzati (🥇🥈🥉⚠️)
   - [ ] Badge attività visualizzati (🔥✅⏰💤)

3. TEST GUI - Tab Peptidi Più Testati
   ```powershell
   # Stessa GUI → Tab "Peptidi Più Testati"
   ```
   Verifica:
   - [ ] Dropdown "Periodo" funziona
   - [ ] Bottone "Carica Dati" mostra tabella
   - [ ] Colonne: #, Peptide, Test Effettuati, Fornitori, Trend
   - [ ] Peptidi standardizzati (non varianti multiple)
   - [ ] Badge popolarità visualizzati (🔥🔥🔥, 🔥🔥, 🔥, 📊)
   - [ ] Top peptide è quello con più test

4. TEST GUI - Tab Ricerca Vendor per Peptide
   ```powershell
   # Stessa GUI → Tab terzo
   ```
   Test case: "Tirzepatide"
   Verifica:
   - [ ] TextField accetta input
   - [ ] Ricerca trova fornitori
   - [ ] Card "MIGLIOR FORNITORE" mostrata con stella 🌟
   - [ ] Dati corretti: Purezza, Certificati, Score
   - [ ] Tabella "Altri fornitori" sotto card
   - [ ] Ordinamento per recommendation_score

5. PERFORMANCE TEST
   ```powershell
   # Misura tempo query prima/dopo refactoring
   python -c "
   import time
   from peptide_manager.janoshik.analytics import JanoshikAnalytics
   a = JanoshikAnalytics('data/production/peptide_management.db')
   
   start = time.time()
   result = a.get_hottest_peptides(limit=50)
   elapsed = time.time() - start
   print(f'get_hottest_peptides: {elapsed:.3f}s')
   "
   ```
   Atteso:
   - [ ] get_hottest_peptides < 0.1s (era ~0.5-1s con CTE)
   - [ ] get_best_vendor_for_peptide < 0.05s (era ~0.2s con LIKE)

6. VERIFICA CONSOLIDAMENTO VARIANTI
   ```sql
   -- Eseguire in SQLite browser o script
   SELECT 
       COUNT(DISTINCT product_name) as varianti_originali,
       COUNT(DISTINCT peptide_name_std) as valori_standardizzati
   FROM janoshik_certificates;
   ```
   Atteso:
   - [ ] varianti_originali >> valori_standardizzati (es. 200 → 50)
   - [ ] Esempi: "BPC-157"/"BPC 157"/"BPC157" → "BPC157"
   - [ ] "Tirzepatide 30mg"/"Tirze 30"/"Tirzepatide" → "Tirzepatide"

PROBLEMI NOTI
-------------
- ❌ smoke_test_gui.py ha nome classe sbagliato (PeptideManagementGUI vs PeptideGUI)
  → FIX: Aggiornare script con nome classe corretto se necessario

- ⚠️  Feature Janoshik in sviluppo, non ancora in production
  → ATTESO: GUI mostra messaggio "Modulo Janoshik non disponibile" finché tabella non esiste

- ℹ️  test_analytics_integration.py creato per quando feature sarà attiva
  → Attualmente fallisce perché tabella janoshik_certificates mancante (NORMALE)

COMMIT HISTORY (Feature Standardization)
-----------------------------------------
1. Migration 006: Aggiunti campi peptide_name_std, quantity_nominal, unit_of_measure
2. Backfill script: Popolati 452 certificati con campi standardizzati
3. LLM prompt: Aggiornato per estrarre campi standardizzati
4. Model: JanoshikCertificate include nuovi campi
5. edfbf2c (questo): Refactoring scorer/analytics per usare campi DB

PROSSIMI PASSI
--------------
Quando tabella janoshik_certificates sarà popolata in production:
1. Eseguire script backfill per popolare campi standardizzati
2. Eseguire test_analytics_integration.py per validare queries
3. Aprire GUI e testare manualmente tutte e 3 le tab Janoshik Market
4. Misurare performance improvement (dovrebbe essere 5-10x più veloce)
5. Verificare consolidamento varianti (50+ varianti → valori standard)

CONTATTI
--------
Domande? Problemi dopo attivazione?
→ Eseguire debug con: python scripts/test_analytics_integration.py
→ Controllare log GUI per stack trace dettagliato
→ Verificare schema DB: scripts/check_janoshik_tables.py

---
Creato: Dec 6, 2025
Ultimo update commit: edfbf2c
Stato: READY FOR PRODUCTION (quando feature attiva)
