# Guida all'uso

## Workflow tipico

1. Aggiungi fornitori
2. Registra acquisti (batch)
3. Carica certificati COA
4. Crea preparazioni
5. Definisci protocolli
6. Log somministrazioni
7. Genera report

## Esempi

### Aggiungere un batch blend

```python
manager.add_batch(
    supplier_name='SwissChems',
    product_name='BPC-157 + TB-500 Blend',
    vials_count=10,
    mg_per_vial=10.0,
    total_price=180.00,
    purchase_date='2024-10-30',
    composition=[
        ('BPC-157', 5.0),
        ('TB-500', 5.0)
    ]
)
```

### Calcolare diluizione

```python
from peptide_manager import DilutionCalculator

calc = DilutionCalculator()
volume = calc.calculate_dilution(5.0, 2.5)  # 5mg in 2.5mg/ml
print(f"Volume necessario: {volume}ml")
```
