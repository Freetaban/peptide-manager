# Analisi Comparativa: gui.py vs gui_modular/views/

**Branch:** `refactor/modular-gui-integration`  
**Data:** 5 Dicembre 2025  
**Scopo:** Identificare differenze funzionali prima del refactoring

---

## 📊 Stato Attuale

### gui.py (Monolitico)
- **Righe:** 4431
- **Dimensione:** 178.6 KB
- **Funzionalità:** COMPLETA con tutte le feature operative

### gui_modular/views/ (Modulare)
- **9 moduli** implementati
- **Pattern:** ft.Container con __init__(app)
- **Stato:** PARZIALE - mancano feature critiche

---

## 🔍 Confronto Dettagliato per Vista

### 1. Dashboard

#### ✅ gui.py (`build_dashboard` - linee 443-728)
**Funzionalità complete:**
- ✅ Statistiche inventario (batches, valore, scadenze)
- ✅ **SOMMINISTRAZIONI PROGRAMMATE OGGI** (checklist operativa)
  - Multi-prep distribution display
  - Ramp schedule indicator con settimana
  - Badge ciclo e status
  - Bottone "Registra" somministrazione
  - Gestione prep multi-peptide
- ✅ **Lista batches in scadenza (60 giorni)**
  - Colori warning (rosso <30gg, arancio <60gg)
  - Link dettagli batch
- ✅ **Bottone Riconciliazione Volumi**

#### ❌ gui_modular/views/dashboard.py (linee 1-73)
**Funzionalità limitate:**
- ✅ Statistiche base (conta peptidi, batches, suppliers, preparations)
- ❌ **MANCA: Somministrazioni programmate (CRITICO)**
- ❌ **MANCA: Batches in scadenza**
- ❌ **MANCA: Bottone riconciliazione**
- ❌ **MANCA: Tutta la logica operativa**

**Gap Stimato:** ~250 linee di codice mancanti  
**Impatto:** **ALTO - Dashboard non utilizzabile in produzione**

---

### 2. Batches

#### ✅ gui.py (`build_batches` + dialoghi - linee 729-1263)
**Funzionalità complete:**
- ✅ Tabella batches con colori scadenza
- ✅ Dialog dettagli batch completo
- ✅ Dialog aggiungi batch con composizione peptidi multi-select
- ✅ Dialog modifica batch completo
- ✅ Conferma eliminazione
- ✅ Validazione composizione peptidi
- ✅ Calcolo automatico mg_per_vial totale

#### ✅ gui_modular/views/batches.py (446 linee)
**Funzionalità complete:**
- ✅ Tabella batches con ricerca
- ✅ Dialog dettagli (completo)
- ✅ Dialog aggiungi (completo con composizione)
- ✅ Dialog modifica (completo)
- ✅ Conferma eliminazione
- ✅ Usa FormBuilder e DialogBuilder (pattern pulito)

**Gap:** **NESSUNO - Batches è equivalente**  
**Impatto:** BASSO - Può essere integrato subito

---

### 3. Peptides

#### ✅ gui.py (`build_peptides` - linee 1264-1457)
**Funzionalità:**
- ✅ Tabella peptidi
- ✅ Dialog dettagli
- ✅ Dialog aggiungi
- ✅ Dialog modifica
- ✅ Conferma eliminazione

#### Status gui_modular/views/peptides.py
**Da verificare** (analisi veloce necessaria)

---

### 4. Suppliers

#### ✅ gui.py (`build_suppliers` - linee 1458-1716)
**Funzionalità:**
- ✅ Tabella fornitori con rating (stelline)
- ✅ Dialog dettagli con statistiche (ordini, spesa, fiale)
- ✅ Dialog aggiungi con rating dropdown
- ✅ Dialog modifica
- ✅ Conferma eliminazione

#### Status gui_modular/views/suppliers.py
**Da verificare**

---

### 5. Preparations ⚠️

#### ✅ gui.py (`build_preparations` + dialoghi - linee 1717-2784)
**Funzionalità complete:**
- ✅ Tabella preparazioni con % rimanente
- ✅ **Dialog dettagli con WASTAGE completo:**
  - Wastage totale ml
  - Wastage reason/notes
  - **Storico wastage (lista completa eventi)**
  - Bottone "Registra Spreco" nel dialog
- ✅ **Dialog registra spreco (`_show_wastage_dialog`):**
  - Volume ml
  - Motivo (dropdown: spillage, measurement_error, contamination, other)
  - Note
  - Validazione volume <= rimanente
- ✅ **Dialog somministrazione (`show_administer_dialog` - line 2463)**
  - Pre-compilato da dashboard
  - Gestione multi-prep
  - Calcolo volume da dose mcg
- ✅ Dialog aggiungi preparazione (completo)
- ✅ Dialog modifica preparazione

#### ❌ gui_modular/views/preparations.py
**Da verificare se ha:**
- Wastage tracking?
- Dialog somministrazione?
- Dialog registra spreco?

**Impatto Potenziale:** **ALTO se manca wastage**

---

### 6. Protocols

#### ✅ gui.py (`build_protocols` - linee 2785-2861)
**Funzionalità:**
- ✅ Tabella protocolli con status attivo/inattivo
- ✅ Display peptidi + frequenza
- ✅ Schema ON/OFF days
- ✅ Dialog dettagli
- ✅ Dialog aggiungi
- ✅ Dialog modifica

#### Status gui_modular/views/protocols.py
**Da verificare**

---

### 7. Cycles ✅

#### ✅ gui.py (`build_cycles` - linee 2862-2875)
**Stato:**
```python
# ALREADY INTEGRATED - usa modulo
try:
    from gui_modular.views.cycles import CyclesView
    return CyclesView(self)
except Exception:
    return fallback
```

#### ✅ gui_modular/views/cycles.py (1761 linee)
**Stato:** **COMPLETO e già integrato (emergency fix Dec 4)**

**Gap:** **NESSUNO - già funzionante**

---

### 8. Administrations

#### ✅ gui.py (`build_administrations` - linee 3232-3546)
**Funzionalità complete:**
- ✅ **Usa pandas DataFrame per filtri veloci**
- ✅ Filtri avanzati:
  - Ricerca testo nelle note
  - Range date (da/a)
  - Peptide (dropdown)
  - Sito iniezione (dropdown)
  - Metodo (dropdown)
  - Protocollo (dropdown)
- ✅ **Statistiche dinamiche filtrate:**
  - Somministrazioni count
  - Totale ml/mcg
  - Giorni unici
  - Prima/ultima data
  - Preparazioni/protocolli usati
- ✅ Tabella risultati con 11 colonne
- ✅ Bottoni azioni (dettagli, modifica, elimina)
- ✅ Dialog dettagli somministrazione
- ✅ Dialog modifica somministrazione

#### Status gui_modular/views/administrations.py
**Da verificare se ha:**
- Filtri completi?
- Statistiche dinamiche?
- Pandas integration?

**Impatto Potenziale:** **ALTO se mancano filtri/stats**

---

### 9. Calculator

#### ✅ gui.py (`build_calculator` - linee 3547-3850 circa)
**Funzionalità:**
- ✅ Dropdown preparazioni attive
- ✅ Info preparazione selezionata
- ✅ **Calcolatore mcg → ml**
- ✅ **Calcolatore ml → mcg**
- ✅ **Tabella conversioni comuni** (50, 100, 250, 500, 1000 mcg)
- ✅ Update automatico preparazione selezionata

#### Status gui_modular/views/calculator.py
**Da verificare**

---

## 🚨 Gap Critici Identificati

### 1. Dashboard (CRITICO)
**Mancano ~250 linee:**
- Somministrazioni programmate oggi (feature operativa principale)
- Batches in scadenza
- Bottone riconciliazione

**Azione:** Portare in gui_modular/views/dashboard.py

---

### 2. Preparations (DA VERIFICARE)
**Possibili mancanze:**
- Wastage tracking e dialog registra spreco
- Dialog somministrazione
- Storico wastage

**Azione:** Verificare e portare se mancante

---

### 3. Administrations (DA VERIFICARE)
**Possibili mancanze:**
- Filtri avanzati completi
- Statistiche dinamiche
- Pandas integration

**Azione:** Verificare e portare se mancante

---

## 📋 Piano d'Azione

### Fase 1: Verifica Approfondita
- [ ] Leggere e confrontare tutti i 6 moduli rimanenti (peptides, suppliers, preparations, protocols, administrations, calculator)
- [ ] Documentare gap precisi per ogni modulo
- [ ] Stimare righe di codice da portare

### Fase 2: Adeguamento Moduli
- [ ] **Dashboard:** Aggiungere somministrazioni programmate + batches scadenza
- [ ] **Preparations:** Aggiungere wastage (se mancante)
- [ ] **Administrations:** Aggiungere filtri avanzati (se mancanti)
- [ ] Altri moduli secondo necessità

### Fase 3: Test Pre-Integrazione
- [ ] Testare ogni modulo modificato standalone
- [ ] Verificare che i dialoghi si aprano correttamente
- [ ] Verificare interazione con PeptideManager

### Fase 4: Integrazione Progressiva
- [ ] Batches (già OK)
- [ ] Cycles (già integrato)
- [ ] Dashboard (dopo fix)
- [ ] Altri moduli uno alla volta
- [ ] Commit dopo ogni integrazione riuscita

### Fase 5: Pulizia
- [ ] Rimuovere metodi `build_*` obsoleti da gui.py
- [ ] Verificare reduction righe (target: ~300-500)
- [ ] Test regressione completo

---

## ⏱️ Stima Tempo

- **Verifica approfondita:** 30-45 min
- **Fix Dashboard:** 1-2 ore
- **Fix altri moduli:** 2-4 ore (se necessario)
- **Test e integrazione:** 2-3 ore
- **Pulizia finale:** 30 min

**Totale stimato:** 6-10 ore lavoro

---

## ✅ Conclusioni

**Non possiamo procedere con l'integrazione cieca.**

I moduli in `gui_modular/views/` sono stati implementati in passato ma **NON sono equivalenti funzionali** di gui.py. In particolare:

1. **Dashboard manca feature critiche** (somministrazioni programmate)
2. **Preparations potrebbe mancare wastage** (da verificare)
3. **Administrations potrebbe mancare filtri** (da verificare)

**Prossimo passo:** Completare verifica approfondita dei 6 moduli rimanenti prima di qualsiasi integrazione.

