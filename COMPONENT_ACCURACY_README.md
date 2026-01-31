# Component-Level Accuracy Calculation for Blend Protocols

## Overview

Il sistema ora supporta il calcolo dell'accuratezza sia totale che per singolo componente per i certificati blend, usando le proporzioni standard dei protocolli conosciuti.

## Protocolli Supportati

### GLOW
- **Composizione**: BPC-157 + TB-500 + GHK-Cu
- **Proporzioni**: 1:1:5 (BPC:TB:GHK)
- **Esempio GLOW 70mg**:
  - BPC-157: 10mg nominale
  - TB-500: 10mg nominale
  - GHK-Cu: 50mg nominale

### KLOW
- **Composizione**: BPC-157 + TB-500 + KPV + GHK-Cu
- **Proporzioni**: 1:1:1:5 (BPC:TB:KPV:GHK)
- **Esempio KLOW 80mg**:
  - BPC-157: 10mg nominale
  - TB-500: 10mg nominale
  - KPV: 10mg nominale
  - GHK-Cu: 50mg nominale

### BPC+TB
- **Composizione**: BPC-157 + TB-500
- **Proporzioni**: 1:1
- **Esempio BPC+TB 20mg**:
  - BPC-157: 10mg nominale
  - TB-500: 10mg nominale

## Architettura Dati

### Database Structure
```sql
-- Certificato blend (record singolo)
task_number: "83568"
peptide_name_std: "BPC-157+TB500+GHK-Cu"
protocol_name: "GLOW"
is_blend: 1
quantity_nominal: 70.0
blend_components: '[
  {"peptide": "GHK-Cu", "quantity": 51.2, "unit": "mg"},
  {"peptide": "BPC157", "quantity": 12.97, "unit": "mg"},
  {"peptide": "TB500", "quantity": 11.41, "unit": "mg"}
]'
```

**Importante**: Un blend è salvato come **1 record singolo** con i componenti in un array JSON, non come record separati per ogni peptide.

### Calcolo Accuratezza

#### 1. Accuratezza Totale
```
Total Accuracy = (Total Measured / Total Nominal) × 100%
```

Esempio Task #83568:
- Totale misurato: 75.58mg (51.2 + 12.97 + 11.41)
- Totale nominale: 70.0mg
- Accuratezza: 107.97%

#### 2. Accuratezza per Componente

Per protocolli conosciuti, calcola l'accuratezza di ogni singolo componente usando le proporzioni standard:

```python
from peptide_manager.janoshik.blend_protocols import calculate_component_nominal_quantities

# Per GLOW 70mg
nominals = calculate_component_nominal_quantities("GLOW", 70.0)
# Returns: {'BPC157': 10.0, 'TB500': 10.0, 'GHK-Cu': 50.0}

# Accuratezza componente
accuracy = (measured / nominal) × 100%
```

Esempio Task #83568 (GLOW 70mg):

| Peptide | Nominale | Misurato | Accuratezza | Status |
|---------|----------|----------|-------------|--------|
| GHK-Cu  | 50.00mg  | 51.20mg  | 102.40%     | PASS   |
| BPC-157 | 10.00mg  | 12.97mg  | 129.70%     | WARN   |
| TB-500  | 10.00mg  | 11.41mg  | 114.10%     | WARN   |

**Soglie**:
- PASS: deviazione ≤10% dal nominale
- WARN: deviazione >10% dal nominale

## Files Implementati

### Core Module
- **`peptide_manager/janoshik/blend_protocols.py`**: Definizioni protocolli standard e calcolo quantità nominali

### Scripts di Test
- **`test_task_83568_accuracy.py`**: Verifica accuratezza Task #83568
- **`demo_component_accuracy.py`**: Demo completa con tutti i protocolli

### Enhanced Accuracy Calculation
- **`example_accuracy_calculation.py`**: Aggiornato per supportare component-level accuracy

## Utilizzo

### Calcolo Accuratezza Singolo Certificato

```python
from peptide_manager.janoshik.repositories import JanoshikCertificateRepository
from peptide_manager.janoshik.blend_protocols import calculate_component_nominal_quantities

# Load certificate
repo = JanoshikCertificateRepository('data/production/peptide_management.db')
cert = repo.get_by_task_number('83568')

# Calculate component nominals if protocol known
if cert.protocol_name:
    nominals = calculate_component_nominal_quantities(
        cert.protocol_name,
        cert.quantity_nominal
    )

    # Calculate accuracy for each component
    components = cert.get_blend_components()
    for comp in components:
        peptide = comp['peptide']
        measured = comp['quantity']
        nominal = nominals.get(peptide)

        if nominal:
            accuracy = (measured / nominal) * 100
            print(f"{peptide}: {accuracy:.2f}%")
```

### Demo Completo

```bash
# Test Task #83568
python test_task_83568_accuracy.py

# Demo tutti i protocolli
python demo_component_accuracy.py
```

## Risultati Reprocessing

Dopo il riprocessamento di 155 certificati (2026-01-27):

- **Totale blend**: 61 certificati (11% del database)
- **Protocolli identificati**: 52 certificati (85% dei blend)
- **Top protocolli**:
  - KLOW: 9 certificati
  - GLOW: 8 certificati
  - BPC+TB: 5 certificati

### Certificati con Quantità Nominale

Non tutti i blend hanno `quantity_nominal` popolato. Questo valore viene estratto dal certificato solo se esplicitamente indicato (es. "GLOW 70mg").

Per certificati senza quantità nominale:
- Accuratezza totale: Non calcolabile
- Accuratezza componente: Non calcolabile
- Dati disponibili: Solo quantità misurate per componente

## Vantaggi Component-Level Accuracy

1. **Identificazione Problemi Specifici**: Un blend può avere accuratezza totale accettabile (es. 107%) ma componenti individuali fuori tolleranza (es. BPC-157 al 129%)

2. **Quality Control**: Permette di identificare problemi di dosaggio specifici per peptide

3. **Supplier Ranking**: Valutazione della precisione del supplier per peptidi specifici, non solo miscele totali

4. **Tracciabilità**: Storico performance per ogni peptide anche quando ordinato in blend

## Esempi Reali

### Task #93546 - GLOW 70mg
```
Overall: 115.2% (WARN)
Components:
  - GHK-Cu: 114.42% (WARN) - Deviazione: +14.4%
  - TB500: 113.60% (WARN) - Deviazione: +13.6%
  - BPC157: 120.70% (WARN) - Deviazione: +20.7%
```
**Analisi**: Tutti i componenti sono in eccesso, BPC-157 particolarmente sovradosato.

### Task #83568 - GLOW 70mg
```
Overall: 107.97% (WARN)
Components:
  - GHK-Cu: 102.40% (PASS) - Deviazione: +2.4%
  - BPC157: 129.70% (WARN) - Deviazione: +29.7%
  - TB500: 114.10% (WARN) - Deviazione: +14.1%
```
**Analisi**: L'accuratezza totale sembra accettabile, ma BPC-157 è significativamente sovradosato (+30%).

## Prossimi Step

1. **Popolare quantity_nominal**: Usare heuristics per dedurre quantità nominali da batch names
2. **Extend Protocols**: Aggiungere altri protocolli comuni al database
3. **UI Integration**: Visualizzazione grafica delle accuratezze per componente
4. **Alerting**: Notifiche automatiche per componenti fuori tolleranza
5. **Trend Analysis**: Tracking accuratezza componenti nel tempo per supplier

## Note Tecniche

- Il calcolo usa `Decimal` per precisione numerica
- Le proporzioni sono definite in codice (non database) per semplicità
- Matching case-insensitive per protocol names (GLOW = Glow = glow)
- Supporta varianti con suffissi (GLOW70, Klow80, etc.)
