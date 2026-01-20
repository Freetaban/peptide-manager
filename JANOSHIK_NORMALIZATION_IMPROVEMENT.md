# Miglioramento Normalizzazione Database Janoshik

## Problema Rilevato

Nel database Janoshik erano presenti **duplicati e sinonimi** per peptidi e vendor, causati da:
1. Variazioni ortografiche (BPC-157 vs BPC157)
2. Nomi commerciali vs generici (GLP vs Semaglutide)
3. Codici vs nomi completi (GLP-2TZ vs Tirzepatide)
4. Variazioni URL/domini vs nomi brand (www.mandybio.com vs Mandy Bio)
5. Variazioni case-sensitivity (PEPTIDEGURUS.COM vs Peptide Gurus)

## Soluzione Implementata

### 1. Peptide Normalizer (`peptide_manager/janoshik/peptide_normalizer.py`)

**Nuovo modulo** che standardizza i nomi dei peptidi:

#### Mappings Aggiunti:
- **GLP-1 Agonists**: 
  - GLP, GLP-1, glp1, sema → `Semaglutide`
  - GLP-2TZ, glp2tz, tirz → `Tirzepatide`
  - GLP-3RT, glp3rt, reta → `Retatrutide`
  
- **Repair Peptides**:
  - BPC-157, BPC157, bpc 157, bpc → `BPC157`
  - TB-500, TB500, tb 500, tb4, thymosin → `TB500`
  
- **Growth Hormones**:
  - HGH, somatropin, qitrope → `HGH`
  - CJC-1295, CJC1295, cjc 1295 → `CJC-1295`
  
- **Altri Peptidi**: 70+ varianti mappate per peptidi comuni

#### Funzionalità:
- Rimuove automaticamente dosaggi dai nomi (es: "BPC-157 5mg" → "BPC157")
- Gestisce blends (es: "BPC-157 + TB-500" → "BPC157+TB500")
- Normalizza acronimi e numeri (preserva maiuscole per acronimi come KPV, DSIP, VIP)
- Fornisce statistiche su duplicati rilevati

### 2. Supplier Normalizer (`peptide_manager/janoshik/supplier_normalizer.py`)

**Modulo aggiornato** con nuovi mappings:

#### Mappings Aggiunti/Aggiornati:
- **Mandy Bio**: `mandy bio`, `www.mandybio.com`, `mandybio.com` → `Mandy Bio`
- **Peptide Gurus**: `peptidegurus.com`, `peptidegurus`, `peptide gurus` → `Peptide Gurus`
- Preservazione maiuscole per acronimi: MTM, UWA, US, HK, SH, ZLZ, ZZTAI
- Fix "Of" → "of" per titoli (es: "Peptides Of London" → "Peptides of London")

### 3. Applicazione Automatica nei Certificati

**Modificato** `peptide_manager/janoshik/models/janoshik_certificate.py`:

```python
# Ora applica automaticamente i normalizzatori quando i dati vengono estratti dall'LLM
from peptide_manager.janoshik.supplier_normalizer import SupplierNormalizer
from peptide_manager.janoshik.peptide_normalizer import PeptideNormalizer

raw_supplier = extracted.get('manufacturer') or extracted.get('client') or 'unknown'
normalized_supplier = SupplierNormalizer.normalize(raw_supplier)

normalized_peptide = PeptideNormalizer.normalize(peptide_name_std)
```

**Beneficio**: Tutti i nuovi certificati importati saranno automaticamente normalizzati.

### 4. Script di Normalizzazione Database

**Nuovo script** `scripts/janoshik/normalize_database.py`:

#### Funzionalità:
- Analizza tutti i certificati esistenti nel database
- Applica normalizzatori a `supplier_name` e `peptide_name_std`
- Modalità dry-run (default) per preview sicura
- Modalità `--apply` per applicare modifiche
- Statistiche dettagliate su duplicati eliminati
- Verifica finale su duplicati rimanenti

#### Utilizzo:
```bash
# Dry run (solo analisi)
python scripts/janoshik/normalize_database.py

# Applica modifiche
python scripts/janoshik/normalize_database.py --apply

# Database specifico
python scripts/janoshik/normalize_database.py --db path/to/db.db --apply
```

## Risultati

### Database Development (Jan 17, 2026)

**Prima della normalizzazione:**
- Certificati: 491
- Duplicati peptidi: ~25 varianti non standardizzate
- Duplicati supplier: ~15 varianti non standardizzate

**Dopo la normalizzazione:**
- ✅ **69 modifiche applicate**
  - 2 supplier normalizzati
  - 67 peptidi normalizzati
  
- ✅ **Duplicati eliminati:**
  - `GLP` → `Semaglutide` (unificato)
  - `GLP-2TZ` → `Tirzepatide` (unificato)
  - `GLP-3RT` → `Retatrutide` (unificato)
  - `BPC-157` → `BPC157` (unificato)
  - Mandy Bio varianti → unificati
  - Peptide Gurus varianti → unificati

## Vantaggi

1. **Database più pulito**: Eliminati sinonimi e duplicati
2. **Query più affidabili**: Nomi standardizzati migliorano ricerche e analisi
3. **Statistiche accurate**: Ranking supplier e analytics peptidi non disturbati da duplicati
4. **Automatico per il futuro**: Tutti i nuovi certificati saranno normalizzati automaticamente
5. **Manutenibilità**: Facile aggiungere nuovi mapping quando necessario

## Manutenzione Futura

### Aggiungere Nuovi Mapping

**Per peptidi** (file: `peptide_normalizer.py`):
```python
MANUAL_MAPPINGS = {
    # ... esistenti ...
    "nuovo_alias": "Nome Standard",
}
```

**Per supplier** (file: `supplier_normalizer.py`):
```python
MANUAL_MAPPINGS = {
    # ... esistenti ...
    "variante.com": "Nome Standard",
}
```

### Rieseguire Normalizzazione
Dopo aver aggiunto nuovi mapping, rieseguire:
```bash
python scripts/janoshik/normalize_database.py --apply
```

## Note Tecniche

- **Preservazione dati originali**: Il campo `raw_data` (JSON) contiene sempre i dati originali estratti dall'LLM
- **Retrocompatibilità**: I certificati esistenti non vengono corrotti, solo i campi `supplier_name` e `peptide_name_std` vengono aggiornati
- **Sicurezza**: Script con dry-run di default per evitare modifiche accidentali
- **Performance**: Normalizzazione O(1) grazie a dict lookup

## Testing

Per verificare la normalizzazione su nuovi certificati:
```python
from peptide_manager.janoshik.peptide_normalizer import PeptideNormalizer
from peptide_manager.janoshik.supplier_normalizer import SupplierNormalizer

# Test peptide
print(PeptideNormalizer.normalize("BPC-157 5mg"))  # → "BPC157"
print(PeptideNormalizer.normalize("GLP"))  # → "Semaglutide"

# Test supplier
print(SupplierNormalizer.normalize("www.mandybio.com"))  # → "Mandy Bio"
print(SupplierNormalizer.normalize("peptidegurus"))  # → "Peptide Gurus"
```

## Conclusione

✅ **Problema risolto**: I duplicati e sinonimi segnalati (BPC-157/BPC157, GLP/Semaglutide, GLP-2TZ/Tirzepatide, GLP-3RT/Retatrutide, Mandy Bio varianti, Peptide Gurus varianti) sono stati **eliminati** e **unificati**.

✅ **Prevenzione futura**: Il sistema ora normalizza automaticamente tutti i nuovi certificati importati.

✅ **Facilmente estendibile**: Basta aggiungere nuovi mapping ai normalizzatori per gestire future varianti.
