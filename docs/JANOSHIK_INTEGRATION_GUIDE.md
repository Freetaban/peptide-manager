# Guida Integrazione Janoshik

## 📋 Riepilogo

Il sistema è **completamente configurato e funzionante** ✅

L'integrazione Janoshik permette di:
1. **Scrapare** automaticamente i certificati da janoshik.com/tests/
2. **Scaricare** le immagini dei CoA (Certificati di Analisi)
3. **Estrarre** i dati usando GPT-4o per leggere le immagini
4. **Calcolare** ranking e score dei supplier
5. **Aggiornare** il database e visualizzare nella GUI

---

## 🔍 Stato Attuale

**Database Development** (`data/development/peptide_management.db`):
- ✅ 452 certificati Janoshik già archiviati
- ✅ 82 supplier univoci
- ✅ 76 ranking calcolati

**Top 3 Supplier** (per qualità):
1. qinglishangmao.com: 86.50
2. cocerpeptides.com: 82.07
3. peptidegurus.com: 81.81

---

## 🛠️ Componenti Verificati

### 1. Database e Tabelle ✅
- Tabella `janoshik_certificates`: contiene certificati scaricati
- Tabella `supplier_rankings`: contiene ranking calcolati
- Colonne Janoshik in `suppliers`: cache dati per GUI

### 2. Scraper ✅
- **URL base**: https://janoshik.com/tests/
- **Storage**: `data/janoshik/images/`
- **Cache**: `data/janoshik/cache/`
- Scraping funziona e identifica nuovi certificati

### 3. LLM Extractor ✅
- **Provider**: GPT-4o
- **API Key**: Configurata in `.env.development`
- Estrae dati da immagini CoA

### 4. Supplier Scorer ✅
- Algoritmo scoring implementato
- Calcola 5 metriche:
  - Volume score (20%)
  - Quality score (25%)
  - Accuracy score (20%)
  - Consistency score (15%)
  - Recency score (10%)
  - Testing completeness (10%)

### 5. JanoshikManager ✅
- Orchestrator completo funzionante
- Coordina: scraping → extraction → scoring → storage
- Callbacks per progress tracking

### 6. Certificati Esistenti ✅
- 452 certificati già scaricati con immagini
- Esempio: Jilin Qijian Biotechnology (40741_cc145e68.png, 231KB)

---

## 🚀 Come Usare l'Integrazione

### Test Veloce di Verifica

Esegui prima un test per verificare che tutto funzioni:

```powershell
python scripts/verify_janoshik_integration.py
```

Questo test verifica tutti i componenti **senza** scaricare nuovi certificati.

---

### Aggiornamento Manuale Completo

Per scaricare **NUOVI** certificati e aggiornare il database:

```powershell
python scripts/update_janoshik_data.py
```

⚠️ **Attenzione**: Questo eseguirà:
1. Scraping di janoshik.com/tests/ (può richiedere 5-30 minuti)
2. Download nuove immagini CoA
3. Chiamate API a GPT-4o (costa $$$)
4. Aggiornamento database

**Opzioni consigliate**:
- Prima volta: Test veloce (1 pagina, 10 certificati)
- Aggiornamento settimanale: 2-3 pagine (~100-150 certificati)
- Aggiornamento completo: Tutto (può richiedere ore)

---

### Aggiornamento dalla GUI

**TODO**: Implementare pulsante "Aggiorna Janoshik" nella GUI che esegue:

```python
from peptide_manager.janoshik import JanoshikManager, LLMProvider

manager = JanoshikManager(
    db_path="data/production/peptide_management.db",
    llm_provider=LLMProvider.GPT4O
)

result = manager.run_full_update(
    max_pages=2,  # Limita a 2 pagine
    max_certificates=50,  # Massimo 50 nuovi certificati
    progress_callback=lambda stage, msg: print(f"{stage}: {msg}")
)

print(f"Nuovi certificati: {result['certificates_new']}")
print(f"Top supplier: {result['top_supplier']}")
```

---

## 📊 Workflow Completo

### 1. Scraping

```
janoshik.com/tests/ → identifica certificati nuovi → scarica immagini
```

**Logica**:
- Scraping paginato (50 certificati per pagina)
- Controlla `image_hash` per evitare duplicati
- Download solo nuove immagini non già archiviate

### 2. Extraction

```
Immagini CoA → GPT-4o → Dati strutturati JSON
```

**Campi estratti**:
- Supplier name
- Product name (peptide)
- Test date
- Purity % (purezza)
- Purity mg/vial
- Endotoxin EU/mg
- Quantity tested mg
- Heavy metals
- Microbiology (TAMC, TYMC)
- Batch number

### 3. Scoring

```
Certificati → Algoritmo scoring → Ranking supplier
```

**Metriche calcolate**:
- **Volume**: Numero certificati (attività)
- **Quality**: Purezza media
- **Accuracy**: Quantità dichiarata vs testata
- **Consistency**: Deviazione standard purezza
- **Recency**: Certificati recenti (90 giorni)
- **Testing completeness**: Presenza test endotoxin/heavy metals/microbiology

**Formula finale**:
```
Total Score = 
    0.20 * volume_score +
    0.25 * quality_score +
    0.20 * accuracy_score +
    0.15 * consistency_score +
    0.10 * recency_score +
    0.10 * testing_completeness_score
```

### 4. Storage

```
Dati estratti → Database → GUI refresh
```

**Tabelle aggiornate**:
- `janoshik_certificates`: Nuovi certificati
- `supplier_rankings`: Nuovi ranking
- `suppliers`: Colonne cache Janoshik

---

## 🔧 Configurazione Avanzata

### Cambiare Provider LLM

Nel codice, modifica:

```python
# Usa GPT-4o (migliore qualità, più costoso)
llm_provider = LLMProvider.GPT4O

# Usa GPT-4o-mini (più economico, buona qualità)
llm_provider = LLMProvider.GPT4O_MINI

# Usa Claude Sonnet (alternativa)
llm_provider = LLMProvider.CLAUDE_SONNET

# Usa Gemini Flash (gratuito ma quota limitata)
llm_provider = LLMProvider.GEMINI_FLASH
```

### Configurare API Keys

Modifica `.env.development`:

```env
# OpenAI (per GPT-4o/GPT-4o-mini)
OPENAI_API_KEY=sk-proj-...

# Anthropic (per Claude)
ANTHROPIC_API_KEY=sk-ant-...

# Google (per Gemini)
GEMINI_API_KEY=AIza...
```

### Limitare Scraping

```python
# Solo 1 pagina (50 certificati)
max_pages = 1

# Massimo 20 nuovi certificati
max_certificates = 20
```

---

## 📁 Struttura File

```
data/janoshik/
├── images/              # Immagini CoA scaricate
│   ├── 40741_cc145e68.png
│   ├── 89403_d1229a7a.png
│   └── ...
├── cache/               # Cache HTML pagine scraping
│   └── ...
└── exports/             # Export CSV/Excel (opzionale)

peptide_manager/janoshik/
├── scraper.py           # Scraping janoshik.com
├── extractor.py         # Estrazione dati da immagini
├── scorer.py            # Algoritmo ranking
├── manager.py           # Orchestrator completo
├── llm_providers.py     # Integrazione LLM (GPT-4o, Claude, Gemini)
├── models/
│   ├── janoshik_certificate.py
│   └── supplier_ranking.py
└── repositories/
    ├── certificate_repository.py
    └── ranking_repository.py
```

---

## 🧪 Testing

### Test Componenti

```powershell
# Verifica tutti i componenti (no download)
python scripts/verify_janoshik_integration.py
```

### Test Completo (con download)

```powershell
# Test veloce (10 certificati, GPT-4o)
python scripts/test_janoshik_full_workflow.py
# Scegli opzione 1
```

### Test Unitari

```powershell
# Test scraper
pytest tests/test_janoshik_scraper.py -v

# Test extractor
pytest tests/test_janoshik_extractor.py -v

# Test scorer
pytest tests/test_janoshik_scorer.py -v

# Test completo
pytest tests/test_janoshik_*.py -v
```

---

## ⚠️ Note Importanti

### Costi API

**GPT-4o** (consigliato):
- Input: $5.00 / 1M tokens
- Output: $15.00 / 1M tokens
- ~$0.02-0.05 per certificato

**Stima costi**:
- 10 certificati: ~$0.20-0.50
- 50 certificati: ~$1.00-2.50
- 500 certificati: ~$10.00-25.00

### Rate Limits

**Gemini** (gratuito):
- 15 richieste/minuto
- 1500 richieste/giorno
- ⚠️ Quota limitata!

**GPT-4o**:
- 5000 richieste/minuto (tier 1)
- 10000 richieste/minuto (tier 2+)

### Tempo Esecuzione

- **Scraping**: ~30-60 secondi per pagina (50 certificati)
- **Download immagini**: ~5-10 secondi per immagine
- **Extraction LLM**: ~2-5 secondi per certificato
- **Scoring**: ~1-2 secondi totale

**Totale**:
- 10 certificati: ~2-3 minuti
- 50 certificati: ~5-10 minuti
- 500 certificati: ~30-60 minuti

---

## 🎯 Prossimi Passi

### Per l'Utente

1. ✅ **Verifica funzionamento**: Eseguito con successo
2. 🔄 **Test con nuovi certificati**: Opzionale (costa API credits)
3. 🚀 **Integrazione GUI**: Pulsante "Aggiorna Janoshik"
4. 📅 **Scheduling**: Aggiornamento automatico settimanale

### Per lo Sviluppatore

1. ✅ **Verificare componenti**: Test superati (6/6)
2. ⏳ **Implementare GUI update button**: TODO
3. ⏳ **Aggiungere cron job/scheduler**: TODO
4. ⏳ **Implementare webhook Janoshik**: TODO (se disponibile)

---

## 📚 Risorse

### Documentazione

- [README.md](../peptide_manager/janoshik/README.md) - Overview completo
- [SCORING_ALGORITHM.md](../peptide_manager/janoshik/SCORING_ALGORITHM.md) - Dettagli algoritmo
- [ENDOTOXIN_INTEGRATION.md](../peptide_manager/janoshik/ENDOTOXIN_INTEGRATION.md) - Gestione endotoxin

### Script Utili

```powershell
# Verifica tabelle Janoshik
python scripts/janoshik/check_schema.py

# Conta certificati
python scripts/janoshik/count_janoshik_certs.py

# Controlla raw data
python scripts/janoshik/check_raw_data.py
```

---

## ✅ Checklist Deployment

Prima di usare in produzione:

- [x] Test componenti superati
- [x] API keys configurate
- [x] Database development OK
- [ ] Test con nuovi certificati (opzionale)
- [ ] Backup database prima di update
- [ ] GUI button implementato
- [ ] Documentazione utente finale
- [ ] Training utente sull'uso

---

**Ultimo aggiornamento**: 29 Dicembre 2025  
**Stato**: ✅ Sistema verificato e funzionante  
**Contatto**: Verifica superata con 6/6 test
