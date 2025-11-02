# Peptide Management System

Sistema completo per la gestione di peptidi.

## Features

- Gestione inventario batch (singoli e blend)
- Tracking fornitori e certificati COA
- Calcoli diluizione automatici
- Protocolli di dosaggio
- Log somministrazioni
- Report e statistiche

## Installazione

```bash
pip install -r requirements.txt
python -m peptide_manager init
```

## Uso rapido

```python
from peptide_manager import PeptideManager

manager = PeptideManager()
manager.print_inventory()
```

## CLI

```bash
# Inizializza database
peptide-manager init

# Mostra inventario
peptide-manager inventory

# Calcola diluizione
peptide-manager dilute 5.0 2.5
```
