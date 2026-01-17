# Decisione Algoritmo Scoring Janoshik

**Data**: 17 Gennaio 2026  
**Contesto**: Discrepanza tra due sistemi di scoring per fornitori Janoshik

## Problema Identificato

Esistevano **due algoritmi di scoring** diversi per i fornitori Janoshik:

### 1. Algoritmo Semplice (SCELTO ✓)
- **Campo**: `janoshik_quality_score` in tabella `suppliers`
- **Calcolo**: Script `scripts/janoshik/sync_suppliers.py`
- **Formula**: 
  - 60% purezza media
  - 30% consistenza (bassa variabilità = score alto)
  - 10% volume (numero certificati)
- **Range**: 0-100
- **Pre-calcolato**: Salvato nel database

**Top 3:**
1. Qinglishangmao: 96.0
2. Peptide Gurus: 94.5
3. Modern Research: 93.7

### 2. Algoritmo Complesso (Scartato)
- **Campo**: `composite_score` (calcolato al volo)
- **Calcolo**: `peptide_manager/janoshik/scorer.py` → `SupplierScorer.calculate_rankings()`
- **Formula**: 6 componenti
  - 20% volume (numero certificati + attività recente)
  - 25% quality (purezza media e minima)
  - 20% accuracy (quantità dichiarata vs testata)
  - 15% consistency (variabilità purezza)
  - 10% recency (attività recente)
  - 10% testing completeness (endotossine, metalli, micro)
- **Range**: 0-100
- **Dinamico**: Calcolato ogni volta dalla GUI

**Top 3:**
1. Peptide Gurus: 89.9
2. Reta Peptide: 86.5
3. Modern Research: 84.8

## Decisione: Algoritmo Semplice

**Motivi**:
1. **Coerenza**: Stesso score in tutta l'applicazione (tabella Fornitori + classifica Janoshik)
2. **Performance**: Pre-calcolato nel database, non ricalcolato ogni volta
3. **Semplicità**: Formula più intuitiva (60% purezza + 30% consistenza + 10% volume)
4. **Rating allineato**: `reliability_rating` (1-5 stelle) deriva da questo score
5. **Manutenibilità**: Un solo algoritmo da mantenere

## Implementazione

### Modifiche effettuate:
1. **GUI Janoshik** (`gui_modular/views/janoshik.py`):
   - Query diretta a `janoshik_quality_score` invece di `composite_score`
   - Rimosso filtro temporale (score pre-calcolato su tutti i certificati)
   - Aggiornato testo formula

2. **Tabella Fornitori** (`gui_modular/views/suppliers.py`):
   - Sostituito colonna "Rating" (stelle) con "Score Janoshik" (numerico)
   - Visualizza `janoshik_quality_score` con 1 decimale

3. **DataTable Component** (`gui_modular/components/data_table.py`):
   - Rimossa conversione automatica rating → stelle
   - Aggiunto formato speciale per `janoshik_quality_score` (1 decimale)

### File coinvolti:
- ✅ `scripts/janoshik/sync_suppliers.py` - Calcola `janoshik_quality_score`
- ✅ `scripts/janoshik/populate_reliability_rating.py` - Converte score → rating 1-5
- ✅ `gui_modular/views/janoshik.py` - Classifica fornitori
- ✅ `gui_modular/views/suppliers.py` - Tabella fornitori
- ✅ `gui_modular/components/data_table.py` - Componente tabella

### Formula dettagliata (algoritmo semplice):

```python
def calculate_quality_score(supplier_stats):
    """
    Score finale 0-100:
    - 60% Purity Score
    - 30% Consistency Score  
    - 10% Volume Score
    """
    # Purity Score (0-100)
    avg_purity = supplier_stats['avg_purity']
    purity_score = avg_purity  # Already 0-100
    
    # Consistency Score (0-100)
    # Bassa variabilità = score alto
    std_purity = supplier_stats['std_purity']
    if std_purity <= 1.0:
        consistency_score = 100
    elif std_purity <= 2.0:
        consistency_score = 90
    elif std_purity <= 3.0:
        consistency_score = 80
    elif std_purity <= 5.0:
        consistency_score = 70
    else:
        consistency_score = max(0, 60 - (std_purity - 5) * 5)
    
    # Volume Score (0-100)
    total_certificates = supplier_stats['total_certificates']
    if total_certificates >= 20:
        volume_score = 100
    elif total_certificates >= 15:
        volume_score = 90
    elif total_certificates >= 10:
        volume_score = 80
    elif total_certificates >= 5:
        volume_score = 70
    else:
        volume_score = 50
    
    # Final Score
    quality_score = (
        purity_score * 0.6 +
        consistency_score * 0.3 +
        volume_score * 0.1
    )
    
    return round(quality_score, 1)
```

### Conversione Rating (1-5 stelle):

```python
def quality_score_to_rating(score):
    """Converte quality_score (0-100) in reliability_rating (1-5)"""
    if score >= 90:
        return 5  # ⭐⭐⭐⭐⭐
    elif score >= 80:
        return 4  # ⭐⭐⭐⭐
    elif score >= 70:
        return 3  # ⭐⭐⭐
    elif score >= 60:
        return 2  # ⭐⭐
    else:
        return 1  # ⭐
```

## Nota Futura

**Possibile ritorno all'algoritmo complesso:**
- L'algoritmo a 6 componenti (`SupplierScorer`) è più sofisticato
- Include metriche avanzate: accuracy quantità, testing completeness, recency
- Potrebbe essere preferibile per analisi più profonde
- Mantenuto in `peptide_manager/janoshik/scorer.py` per uso futuro

**Come riabilitarlo:**
1. Modificare `scripts/janoshik/sync_suppliers.py` per usare `SupplierScorer`
2. Aggiornare campo `janoshik_quality_score` con `composite_score`
3. Ricalcolare rating con soglie adeguate (considerare che gli score sono più bassi)
4. Testare impatto su classifiche esistenti

## Conclusione

Per ora, **algoritmo semplice** garantisce coerenza e performance.  
L'algoritmo complesso resta disponibile per future evoluzioni.

---

*Ultimo aggiornamento: 17/01/2026*
