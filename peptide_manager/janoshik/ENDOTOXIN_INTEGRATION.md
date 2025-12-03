# Integrazione Analisi Endotossine - Changelog

## Data: 3 Dicembre 2025

### Obiettivo
Estendere il sistema di scoring Janoshik per includere analisi endotossine come parametro di qualità.

---

## Motivazione

I Certificati di Analisi (CoA) Janoshik possono contenere multiple analisi per ogni prodotto:

1. **Purity (%)** - Purezza peptide (già implementata)
2. **Quantity (mg)** - Quantità nominale vs effettiva
3. **Heavy Metals** - Metalli pesanti
4. **Endotoxins (EU/mg)** - Endotossine batteriche ⭐ **NUOVO**
5. **Microbiology** - Test microbiologici

**Endotossine** sono critiche per peptidi iniettabili:
- FDA limit: tipicamente 5-10 EU/mg
- Causano reazioni infiammatorie/febbre
- Test endotossine indica QC avanzato
- Presenza test endotossine = trasparenza supplier

---

## Modifiche Database

### File: `migrations/008_janoshik_supplier_ranking.sql`

#### Tabella `janoshik_certificates`
```sql
-- Aggiunto campo per storage endotossine
endotoxin_level REAL,  -- EU/mg (Endotoxin Units per mg)
```

#### Tabella `supplier_rankings`
```sql
-- Aggiunti campi per metriche endotossine
avg_endotoxin_level REAL,  -- EU/mg
certs_with_endotoxin INTEGER DEFAULT 0,

-- Aggiunto campo per score endotossine
endotoxin_score REAL DEFAULT 0,
```

---

## Modifiche LLM Extraction

### File: `peptide_manager/janoshik/llm_providers.py`

#### Aggiornamento EXTRACTION_PROMPT
```python
IMPORTANT for Results:
- Extract EVERY parameter from Results table
- Include name, value, and unit
- Look for Purity (%), Quantity (mg), Endotoxins (EU/mg)  # ← NUOVO
- Examples: {"Retatrutide": "44.33 mg", "Purity": "99.720%", "Endotoxins": "<50 EU/mg"}
```

#### Esempio JSON output
```json
{
  "test_type": "Assessment of a peptide vial",
  "results": {
    "Retatrutide": "44.33 mg",
    "Purity": "99.720%",
    "Endotoxins": "<50 EU/mg"  // ← NUOVO
  },
  "comments": ""
}
```

**Handling valori**:
- `"<50 EU/mg"` → parse come `50.0`
- `"45.3 EU/mg"` → parse come `45.3`
- Supporta sia valori esatti che limiti superiori (`<`)

---

## Modifiche Scoring Algorithm

### File: `peptide_manager/janoshik/scorer.py`

#### 1. Aggiornamento Pesi (Totale = 1.0)
```python
WEIGHT_VOLUME = 0.25       # ↓ da 0.30 (-5%)
WEIGHT_QUALITY = 0.35      # = invariato
WEIGHT_CONSISTENCY = 0.15  # ↓ da 0.20 (-5%)
WEIGHT_RECENCY = 0.15      # = invariato
WEIGHT_ENDOTOXIN = 0.10    # ⭐ NUOVO (+10%)
```

**Rationale riduzione**:
- Volume: -5% (da 30% a 25%) - meno critico di qualità
- Consistency: -5% (da 20% a 15%) - già ben rappresentato da quality score

#### 2. Nuovo Metodo: `_extract_endotoxins()`
```python
def _extract_endotoxins(self, certs: pd.DataFrame) -> List[float]:
    """Estrae valori endotossine dai certificati (EU/mg)"""
    endotoxins = []
    
    for _, cert in certs.iterrows():
        # Cerca in endotoxin_level column
        if 'endotoxin_level' in cert and pd.notna(cert['endotoxin_level']):
            endotoxins.append(float(cert['endotoxin_level']))
            continue
        
        # Cerca in results dict
        results = cert.get('results', {})
        if isinstance(results, dict):
            for key, value in results.items():
                if 'endotoxin' in key.lower():
                    # Parse "<50 EU/mg" -> 50.0
                    endotox_str = str(value).replace('<', '').replace('EU/mg', '').strip()
                    try:
                        endotoxins.append(float(endotox_str))
                        break
                    except ValueError:
                        pass
    
    return endotoxins
```

#### 3. Nuovo Metodo: `_calculate_endotoxin_score()`
```python
def _calculate_endotoxin_score(self, avg_endotoxin: Optional[float], 
                                 certs_with_endotoxin: int) -> float:
    """
    Score basato su livello endotossine (0-100).
    
    Formula:
    - Nessun dato → 50 (neutro)
    - < 10 EU/mg → 100 (eccellente - limite FDA)
    - < 50 EU/mg → 80-99 (buono)
    - < 100 EU/mg → 60-79 (accettabile)
    - < 200 EU/mg → 40-59 (mediocre)
    - >= 200 EU/mg → 0-39 (scarso)
    
    Bonus: +5 se >= 5 certificati con test endotossine (trasparenza)
    """
```

**Scala valutazione**:
| EU/mg | Score | Valutazione | Note |
|-------|-------|-------------|------|
| < 10 | 100 | Eccellente | Rispetta FDA limit |
| 10-49 | 80-99 | Buono | Sicuro per uso |
| 50-99 | 60-79 | Accettabile | Borderline |
| 100-199 | 40-59 | Mediocre | Preoccupante |
| ≥ 200 | 0-39 | Scarso | Non accettabile |
| No data | 50 | Neutro | Non penalizza assenza dati |

**Bonus trasparenza**: +5 punti se supplier ha ≥5 certificati con test endotossine.

#### 4. Aggiornamento Formula Score Totale
```python
total_score = (
    volume_score * self.WEIGHT_VOLUME +
    quality_score * self.WEIGHT_QUALITY +
    consistency_score * self.WEIGHT_CONSISTENCY +
    recency_score * self.WEIGHT_RECENCY +
    endotoxin_score * self.WEIGHT_ENDOTOXIN  # ⭐ NUOVO
)
```

#### 5. Aggiornamento Output Metriche
```python
return {
    # ... metriche esistenti ...
    'avg_endotoxin_level': round(avg_endotoxin, 3) if avg_endotoxin else None,
    'certs_with_endotoxin': certs_with_endotoxin,
    # ... score components ...
    'endotoxin_score': round(endotoxin_score, 2),
    'total_score': round(total_score, 2)
}
```

---

## Impatto su Ranking

### Esempio Comparativo

**Supplier A - Alta trasparenza endotossine**:
- 20 certificati, 15 con test endotossine
- Avg endotoxin: 8.5 EU/mg
- Endotoxin score: 100 (< 10 EU/mg) + 5 (bonus) = **100**
- Contributo total score: 100 * 0.10 = **+10 punti**

**Supplier B - Nessun test endotossine**:
- 20 certificati, 0 con test endotossine
- Avg endotoxin: None
- Endotoxin score: **50** (neutro)
- Contributo total score: 50 * 0.10 = **+5 punti**

**Delta**: Supplier A guadagna **+5 punti** rispetto a Supplier B per trasparenza endotossine.

---

## Testing

### Test Cases da Implementare

1. **Test estrazione endotossine**:
   ```python
   cert = {"results": {"Endotoxins": "<50 EU/mg"}}
   endotoxins = scorer._extract_endotoxins(pd.DataFrame([cert]))
   assert endotoxins == [50.0]
   ```

2. **Test score nessun dato**:
   ```python
   score = scorer._calculate_endotoxin_score(None, 0)
   assert score == 50.0
   ```

3. **Test score eccellente**:
   ```python
   score = scorer._calculate_endotoxin_score(8.5, 10)
   assert score == 105.0  # 100 + bonus
   ```

4. **Test score scarso**:
   ```python
   score = scorer._calculate_endotoxin_score(250.0, 3)
   assert score < 40.0
   ```

---

## Dependencies Aggiornate

### File: `requirements.txt`

```pip-requirements
# Janoshik Supplier Ranking (LLM providers)
openai>=1.0.0
anthropic>=0.40.0
google-generativeai>=0.8.0
requests>=2.31.0
beautifulsoup4>=4.12.0
pillow>=10.0.0
```

---

## Documentazione

### File: `peptide_manager/janoshik/SCORING_ALGORITHM.md`

Creato documento completo con:
- Spiegazione dettagliata algoritmo endotoxin scoring
- Riferimenti FDA limits
- Esempi calcolo
- Interpretazione score
- Rationale decisioni design

---

## Prossimi Passi

1. ✅ **Database schema** - aggiunto `endotoxin_level` column
2. ✅ **LLM extraction** - aggiornato prompt per estrarre endotossine
3. ✅ **Scoring algorithm** - implementato `_calculate_endotoxin_score()`
4. ✅ **Documentation** - creato SCORING_ALGORITHM.md
5. ✅ **Dependencies** - aggiornato requirements.txt
6. ⏳ **Testing** - da implementare unit tests
7. ⏳ **Scraper** - da implementare web scraping janoshik.com
8. ⏳ **GUI** - da integrare visualizzazione endotoxin scores

---

## Note Design

### Perché score neutro (50) se mancano dati?

**Alternative considerate**:
1. ❌ Score = 0 → Penalizza troppo supplier che non testano (unfair)
2. ❌ Score = 100 → Premia supplier che nascondono dati (pericoloso)
3. ✅ **Score = 50** → Neutro, non influenza significativamente total score

**Rationale**: 
- Non tutti i supplier testano endotossine (costoso)
- Assenza test ≠ alta contaminazione
- Presenza test = trasparenza (bonus)
- Score neutro mantiene neutralità algoritmo

### Perché peso 10%?

**Considerazioni**:
- Troppo alto (>15%) → Penalizza supplier senza dati
- Troppo basso (<5%) → Inefficace come incentivo
- **10%** → Bilanciato: significativo ma non dominante

**Test sensitivity**:
- Supplier con endotoxin score 100 vs 50 → +5 punti total score
- Può cambiare ranking se score molto vicini (es. 85.3 vs 85.8)
- Non stravolge ranking se differenze qualità significative

---

## Versioning

**Scoring Algorithm Version**: 1.1  
**Migration Version**: 008  
**Branch**: feature/janoshik-supplier-ranking

---

*Documento creato: 3 Dicembre 2025*  
*Autore: GitHub Copilot + User ftaba*
