# 💊 Peptide Management System

[![Version](https://img.shields.io/badge/version-0.1.0-blue.svg)](https://github.com/freetaban/peptide-management-system)
[![Python](https://img.shields.io/badge/python-3.12+-green.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-orange.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

Sistema completo di gestione peptidi per uso personale con tracking di acquisti, inventario, preparazioni, protocolli di dosaggio e somministrazioni.

![Screenshot](docs/screenshots/tui-main.png)

---

## ✨ Caratteristiche

### 📦 Gestione Completa
- **Fornitori** - Database fornitori con rating affidabilità
- **Peptidi** - Catalogo con anti-duplicati e normalizzazione automatica
- **Batches** - Inventario fiale con tracking scadenze e certificati COA
- **Preparazioni** - Ricostituzione con calcolatore diluizioni integrato
- **Protocolli** - Schemi di dosaggio con statistiche aderenza
- **Somministrazioni** - Log completo con dosaggi e note

### 🎯 Interfacce Multiple
- **TUI (Text User Interface)** - Interfaccia DOS-style immersiva con menu navigabili
- **CLI Modulare** - Comandi Click per automazione e scripting
- **Output Formattati** - Report e inventari leggibili

### 🧮 Strumenti Avanzati
- **Calcolatore Diluizioni** - Calcoli automatici concentrazioni e dosaggi
- **Correzione Errori** - Sistema per ripristinare fiale registrate per errore
- **Alert Scadenze** - Notifiche batch in scadenza
- **Merge Duplicati** - Unificazione peptidi duplicati

---

## 🚀 Quick Start

### Installazione

```bash
# Clone repository
git clone https://github.com/yourusername/peptide-management-system.git
cd peptide-management-system

# Crea virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# oppure
venv\Scripts\activate     # Windows

# Installa dipendenze
pip install -e .

# Inizializza database
peptide-manager init
```

### Primo Utilizzo

```bash
# Lancia interfaccia TUI interattiva
peptide-manager

# Oppure usa comandi diretti
peptide-manager suppliers add    # Aggiungi fornitore
peptide-manager batches add      # Registra acquisto
peptide-manager inventory        # Mostra inventario
```

---

## 📚 Documentazione

### Interfaccia TUI

Lancia `peptide-manager` senza argomenti per accedere all'interfaccia DOS-style:

```
╔════════════════════════════════════════════════════════════╗
║          PEPTIDE MANAGEMENT SYSTEM v0.1.0                  ║
╚════════════════════════════════════════════════════════════╝

  [1] Gestione Peptidi
  [2] Gestione Fornitori
  [3] Gestione Batches
  [4] Gestione Preparazioni
  [5] Gestione Protocolli
  [6] Inventario Completo
  [7] Riepilogo Sistema

  [0] Esci
```

### Comandi CLI

#### Gestione Fornitori
```bash
peptide-manager suppliers list           # Lista fornitori
peptide-manager suppliers add            # Aggiungi fornitore
peptide-manager suppliers show <id>      # Dettagli fornitore
peptide-manager suppliers stats          # Statistiche comparative
```

#### Gestione Batches
```bash
peptide-manager batches list             # Lista batches disponibili
peptide-manager batches add              # Wizard nuovo acquisto
peptide-manager batches show <id>        # Dettagli completi batch
peptide-manager batches use <id> <qty>   # Usa fiale
peptide-manager batches adjust <id> +/-  # Correggi conteggio fiale
peptide-manager batches expiring         # Batches in scadenza
```

#### Gestione Preparazioni
```bash
peptide-manager preparations list        # Lista preparazioni attive
peptide-manager preparations add         # Nuova preparazione (wizard)
peptide-manager preparations use <id>    # Registra somministrazione
peptide-manager preparations calc        # Calcolatore diluizioni
peptide-manager preparations expired     # Preparazioni scadute
```

#### Gestione Protocolli
```bash
peptide-manager protocols list           # Lista protocolli
peptide-manager protocols add            # Nuovo protocollo
peptide-manager protocols stats <id>     # Statistiche aderenza
peptide-manager protocols activate <id>  # Attiva protocollo
```

---

## 🧮 Calcolatore Diluizioni

### Esempio Pratico

```bash
# Hai 5mg di peptide, vuoi dose da 250mcg in 0.2ml
peptide-manager preparations calc --mg 5 --dose 250

# Output:
💡 SUGGERIMENTO:
  Volume diluente: 2.0ml
  Concentrazione: 2.5mg/ml
  Volume per dose (250mcg): 0.1ml
  Dosi disponibili: 20
```

### Funzionalità
- Calcolo concentrazione da mg + volume
- Suggerimento diluizione ottimale per dose target
- Conversione mcg ↔ ml
- Tabelle dosaggi multipli
- Calcolo dosi disponibili

---

## 🔧 Correzione Errori

Sistema integrato per correggere errori di registrazione:

```bash
# Hai registrato per errore l'uso di 1 fiala
peptide-manager batches show 1           # Verifica stato attuale
peptide-manager batches adjust 1 +1 --reason "Fiala registrata per errore"

# Output:
✓ Batch #1 'BPC-157 5mg':
  Fiale aggiunte: 1
  3 → 4 fiale
  Motivo: Fiala registrata per errore
```

---

## 📊 Database Schema

```sql
suppliers           # Fornitori
  ├── id, name, country, website
  ├── reliability_rating (1-5)
  └── notes

peptides            # Catalogo peptidi
  ├── id, name, description
  ├── common_uses
  └── notes

batches             # Inventario acquisti
  ├── id, supplier_id, product_name
  ├── vials_count, vials_remaining
  ├── mg_per_vial, total_price
  ├── purchase_date, expiry_date
  └── storage_location

batch_composition   # Composizione multi-peptide
  ├── batch_id, peptide_id
  └── mg_per_vial

preparations        # Ricostituzione
  ├── id, batch_id, vials_used
  ├── volume_ml, volume_remaining_ml
  ├── diluent, preparation_date
  └── expiry_date

protocols           # Schemi dosaggio
  ├── id, name, dose_ml
  ├── frequency_per_day
  ├── days_on, days_off
  └── cycle_duration_weeks

administrations     # Somministrazioni
  ├── id, preparation_id, protocol_id
  ├── administration_datetime
  ├── dose_ml, injection_site
  └── notes, side_effects

certificates        # COA
  ├── id, batch_id, certificate_type
  ├── lab_name, purity_percentage
  └── test_date, file_path
```

---

## 🛠️ Sviluppo

### Setup Ambiente

```bash
# Clone e setup
git clone https://github.com/yourusername/peptide-management-system.git
cd peptide-management-system
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"

# Formattazione codice
black .
flake8 .

# Test (TODO)
pytest
```

### Struttura Progetto

```
peptide-management-system/
├── cli/                    # Interfaccia utente
│   ├── main.py            # Entry point
│   ├── tui.py             # TUI DOS-style
│   └── commands/          # Comandi CLI modulari
│       ├── batches.py
│       ├── peptides.py
│       ├── preparations.py
│       ├── protocols.py
│       └── suppliers.py
├── peptide_manager/        # Core logic
│   ├── models.py          # CRUD operations
│   ├── database.py        # Schema DB
│   ├── calculator.py      # Calcolatore diluizioni
│   ├── reports.py         # Report generator
│   └── utils.py           # Utilities
├── data/                   # Dati utente
│   ├── backups/
│   ├── certificates/
│   └── exports/
├── docs/                   # Documentazione
├── tests/                  # Test suite
└── setup.py               # Package config
```

---

## 🎯 Roadmap

### v0.2.0 (Q1 2025)
- [ ] Sistema backup automatico
- [ ] Export dati (CSV, Excel, JSON)
- [ ] Report avanzati con statistiche
- [ ] Test coverage > 80%

### v0.3.0 (Q2 2025)
- [ ] Grafici utilizzo (matplotlib)
- [ ] Notifiche scadenze (email/desktop)
- [ ] Import dati da CSV

### v1.0.0 (Q3 2025)
- [ ] Web interface (Flask)
- [ ] API REST
- [ ] Multi-user support
- [ ] Cloud sync opzionale

---

## 🤝 Contributing

Le contribuzioni sono benvenute! Per favore:

1. Fork il progetto
2. Crea un branch per la feature (`git checkout -b feature/AmazingFeature`)
3. Commit le modifiche (`git commit -m 'Add AmazingFeature'`)
4. Push al branch (`git push origin feature/AmazingFeature`)
5. Apri una Pull Request

### Linee Guida
- Usa **black** per formattazione
- Aggiungi docstrings Google-style
- Scrivi test per nuove funzionalità
- Aggiorna CHANGELOG.md

---

## 📝 License

Questo progetto è rilasciato sotto licenza MIT. Vedi file [LICENSE](LICENSE) per dettagli.

---

## ⚠️ Disclaimer

Questo software è fornito "così com'è" senza garanzie. Non sostituisce consulenza medica professionale. L'utente è responsabile dell'uso corretto e della verifica di tutte le informazioni inserite.

---

## 🙏 Acknowledgments

- Ispirato dalla necessità di tracking personale peptidi
- Interfaccia TUI ispirata a software DOS classici
- Calcolatore diluizioni basato su best practices farmaceutiche

---

## 📧 Contatti

- **Issues:** [GitHub Issues](https://github.com/yourusername/peptide-management-system/issues)
- **Discussions:** [GitHub Discussions](https://github.com/yourusername/peptide-management-system/discussions)

---

## 🌟 Star History

Se trovi utile questo progetto, considera di dargli una stella ⭐

[![Star History Chart](https://api.star-history.com/svg?repos=yourusername/peptide-management-system&type=Date)](https://star-history.com/#yourusername/peptide-management-system&Date)

---

<p align="center">Made with ❤️ for personal peptide management</p>
