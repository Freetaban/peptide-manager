# Janoshik Supplier Scoring Algorithm

## Panoramica

Sistema di scoring per classificare supplier di peptidi basato su dati certificati Janoshik pubblici.

**Obiettivo**: Identificare supplier "hot" (affidabili, attivi, alta qualità) mediante analisi quantitativa multi-parametrica.

---

## Componenti Score (Totale = 100)

### 1. Volume Score (25%)
**Peso**: 0.25  
**Range**: 0-100

Valuta numero totale certificati e attività recente.

**Formula**:
- Base: `min(100, (total_certs / 30) * 100)`
- Bonus: +10 se ≥3 certificati negli ultimi 30 giorni

**Scala**:
- 0 certs → 0
- 1-5 certs → 20-40
- 6-15 certs → 41-70
- 16-30 certs → 71-90
- 30+ certs → 91-100

**Rationale**: Supplier con più certificati dimostrano maggiore trasparenza e volume business.

---

### 2. Quality Score (35%)
**Peso**: 0.35  
**Range**: 0-100

Valuta purezza media e minima dei peptidi testati.

**Formula**:
- avg ≥ 99% → 90-100
- avg ≥ 98% → 70-89
- avg ≥ 95% → 50-69
- avg < 95% → 0-49
- Penalty: -20 se min < 95%

**Rationale**: Purezza è parametro critico per efficacia e sicurezza. Penalty per outlier bassi.

---

### 3. Consistency Score (15%)
**Peso**: 0.15  
**Range**: 0-100

Valuta variabilità purezza e regolarità testing.

**Formula**:
- std < 0.5% → 95
- std < 1.0% → 80
- std < 2.0% → 60
- std ≥ 2.0% → 0-50
- Bonus: +10 se avg_gap < 60 giorni

**Rationale**: Consistenza indica controllo qualità robusto. Testing regolare indica commitment.

---

### 4. Recency Score (15%)
**Peso**: 0.15  
**Range**: 0-100

Valuta attività recente del supplier.

**Formula**:
- < 7 giorni → 100
- < 30 giorni → 70-99
- < 90 giorni → 40-69
- < 180 giorni → 10-39
- ≥ 180 giorni → 0-9
- Bonus: +15 se ≥2 cert negli ultimi 30 giorni

**Rationale**: Supplier attivi sono più affidabili. Inattività prolungata è red flag.

---

### 5. Endotoxin Score (10%)
**Peso**: 0.10  
**Range**: 0-100

Valuta livello endotossine nei certificati (quando disponibile).

**Formula**:
- Nessun dato → 50 (neutro)
- < 10 EU/mg → 100 (eccellente - limite FDA)
- < 50 EU/mg → 80-99 (buono)
- < 100 EU/mg → 60-79 (accettabile)
- < 200 EU/mg → 40-59 (mediocre)
- ≥ 200 EU/mg → 0-39 (scarso)
- Bonus: +5 se ≥5 certificati con test endotossine

**Note FDA**: 
- Limite tipico per peptidi iniettabili: 5-10 EU/mg
- Alcuni prodotti richiedono < 0.5 EU/mg (intratecali)

**Rationale**: Endotossine batteriche causano reazioni infiammatorie/febbre. Test endotossine indica QC avanzato.

---

## Calcolo Score Totale

```python
total_score = (
    volume_score * 0.25 +
    quality_score * 0.35 +
    consistency_score * 0.15 +
    recency_score * 0.15 +
    endotoxin_score * 0.10
)
```

**Range finale**: 0-100

---

## Interpretazione Score

### Score > 80: 🔥 HOT (Top tier)
- Alta qualità (>99% purity)
- Molto attivo (certificati recenti)
- Consistente (std < 1%)
- Endotossine basse (se disponibile)

### Score 60-80: ✅ Buono (Affidabile)
- Buona qualità (98-99% purity)
- Attivo (certificati < 90 giorni)
- Abbastanza consistente
- Endotossine accettabili

### Score 40-60: ⚠️ Mediocre (Da valutare)
- Qualità variabile (95-98% purity)
- Attività intermittente
- Bassa consistenza
- Endotossine elevate o mancanti

### Score < 40: ❌ Scarso (Red flag)
- Bassa qualità (< 95% purity)
- Inattivo (> 180 giorni)
- Molto inconsistente
- Endotossine elevate

---

## Dati Estratti da Certificati

### Campi Obbligatori
- `task_number` (unique)
- `supplier_name` (client/manufacturer/website)
- `peptide_name` (sample)
- `test_date` (analysis_conducted)
- `purity_percentage` (%)

### Campi Opzionali
- `quantity_tested_mg` (mg nominali vs mg effettivi)
- `endotoxin_level` (EU/mg)
- `batch_number`
- `testing_ordered`, `sample_received` (date)
- `test_type` (tipo analisi)
- `comments`, `verification_key`

### Parametri NON utilizzati per scoring
- Heavy metals (non rilevante per ranking generale)
- Microbiology (non standardizzato)
- Quantity (importante ma non per quality ranking)

---

## Normalizzazione Supplier

### Standardizzazione nomi
- Lowercase
- Trim whitespace
- Rimuovi `www.` prefix
- Priorità: `client` > `manufacturer` > `supplier_name`

### Esempi
```
"www.licensedpeptides.com" → "licensedpeptides.com"
"Peptide Sciences LLC" → "peptide sciences llc"
"  AmoPure.net  " → "amopure.net"
```

---

## Metriche Supplementari

### Tracking
- `total_certificates`: Totale certificati
- `recent_certificates`: Ultimi 90 giorni
- `certs_last_30d`: Ultimi 30 giorni
- `days_since_last_cert`: Giorni da ultimo certificato
- `avg_date_gap`: Gap medio tra certificati (giorni)
- `peptides_tested`: Lista peptidi testati (top 10)

### Endotossine
- `avg_endotoxin_level`: Media EU/mg
- `certs_with_endotoxin`: N. certificati con test endotossine

---

## Esempio Calcolo

### Supplier: "amopure.net"

**Dati input**:
- 18 certificati totali
- 4 certificati ultimi 30 giorni
- Avg purity: 99.65%
- Min purity: 98.80%
- Std purity: 0.42%
- Last cert: 5 giorni fa
- Avg gap: 45 giorni
- Avg endotoxin: 38.2 EU/mg (6 certificati)

**Calcolo**:
1. Volume: `(18/30)*100 + 10 = 70`
2. Quality: `90 + (99.65-99)*10 = 96.5`
3. Consistency: `95 + 10 = 100` (std<0.5%, gap<60)
4. Recency: `100 + 15 = 100` (< 7 giorni, ≥2 cert/30d)
5. Endotoxin: `80 + (50-38.2)/40*19 + 5 = 90.6` (< 50, ≥5 certs)

**Total Score**:
```
70*0.25 + 96.5*0.35 + 100*0.15 + 100*0.15 + 90.6*0.10
= 17.5 + 33.78 + 15 + 15 + 9.06
= 90.34 → 🔥 HOT
```

---

## Aggiornamenti Futuri

### Possibili estensioni
- [ ] Pesare certificati recenti più dei vecchi (time decay)
- [ ] Penalizzare gap lunghi tra certificati (inconsistenza)
- [ ] Bonus per variety peptidi testati (diversificazione)
- [ ] Tracking heavy metals se standardizzato
- [ ] Analisi trend nel tempo (miglioramento/peggioramento)
- [ ] Confidence score basato su sample size

### Tuning pesi
Pesi attuali basati su giudizio esperto. Possono essere ottimizzati con:
- A/B testing con utenti
- Correlazione con qualità reale reported dagli utenti
- Machine learning su feedback storico

---

*Versione: 1.0*  
*Data: Dicembre 2025*  
*Autore: Peptide Management System*
