# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Sistema backup automatico database
- Export dati (CSV, Excel, JSON)
- Grafici utilizzo con matplotlib
- Notifiche scadenze (email/desktop)
- Web interface (Flask)

---

## [0.1.0] - 2025-01-XX

### 🎉 Initial Release

Prima release pubblica del Peptide Management System con funzionalità core complete.

### Added

#### Core Features
- **Database SQLite completo** con schema relazionale per gestione peptidi
- **Gestione Fornitori** con rating affidabilità e statistiche acquisti
- **Catalogo Peptidi** con anti-duplicati e normalizzazione nomi automatica
- **Gestione Batches** con tracking fiale, scadenze, e prezzi
- **Composizioni Multi-Peptide** supporto per blend di peptidi
- **Certificati COA** storage e tracking certificati di analisi
- **Preparazioni** sistema completo ricostituzione peptidi con diluente
- **Protocolli Dosaggio** schemi on/off con tracking aderenza
- **Somministrazioni** log completo con dosi, siti iniezione, e note

#### Interfacce Utente
- **TUI (Text User Interface)** interfaccia DOS-style immersiva con menu numerati
- **CLI Modulare** comandi Click per automazione (`peptide-manager <cmd>`)
- **Menu Tematici** sottomenu per peptides, suppliers, batches, preparations, protocols

#### Tools & Utilities
- **Calcolatore Diluizioni** 
  - Calcolo concentrazioni mg/ml
  - Conversioni mcg ↔ ml
  - Suggerimenti diluizione ottimale per dose target
  - Tabelle dosaggi multipli
  - Calcolo dosi disponibili da preparazione
- **Sistema Correzione Fiale** comando `adjust` per correggere conteggi errati
- **Alert Scadenze** visualizzazione batches in scadenza (60 giorni)
- **Merge Duplicati** unificazione peptidi duplicati con migrazione riferimenti
- **Inventario Completo** vista aggregata con filtri e ricerche

#### Commands (CLI)

**Suppliers:**
- `list` - Lista fornitori con rating
- `add` - Aggiungi fornitore (interattivo)
- `edit` - Modifica fornitore
- `show` - Dettagli e statistiche fornitore
- `search` - Cerca fornitori
- `stats` - Statistiche comparative
- `delete` - Elimina fornitore

**Peptides:**
- `list` - Lista catalogo peptidi
- `add` - Aggiungi peptide (con anti-duplicati)
- `edit` - Modifica peptide
- `show` - Dettagli peptide e utilizzo
- `search` - Cerca peptidi
- `duplicates` - Trova duplicati
- `merge` - Unisci peptidi duplicati
- `delete` - Elimina peptide

**Batches:**
- `list` - Lista batches disponibili
- `add` - Wizard registrazione acquisto
- `show` - Dettagli completi batch
- `edit` - Modifica batch
- `use` - Usa fiale da batch
- `adjust` - **NEW** Correggi conteggio fiale (+/-)
- `search` - Cerca batch con filtri
- `expiring` - Batches in scadenza
- `delete` - Elimina batch

**Preparations:**
- `list` - Lista preparazioni attive
- `add` - Wizard nuova preparazione con calcolatore
- `show` - Dettagli preparazione e somministrazioni
- `use` - Registra somministrazione
- `edit` - Modifica preparazione
- `expired` - Preparazioni scadute
- `calc` - Calcolatore diluizioni standalone
- `delete` - Elimina preparazione (opzione restore vials)

**Protocols:**
- `list` - Lista protocolli
- `add` - Wizard nuovo protocollo
- `show` - Dettagli protocollo
- `edit` - Modifica protocollo
- `activate` - Attiva protocollo
- `deactivate` - Disattiva protocollo
- `log` - Log somministrazioni
- `stats` - Statistiche aderenza
- `link-admin` - Collega somministrazione a protocollo
- `link-batch` - Collega multiple somministrazioni
- `delete` - Elimina protocollo

**Quick Commands:**
- `init` - Inizializza database
- `inventory` - Inventario completo
- `summary` - Riepilogo rapido sistema
- `tui` - Lancia TUI interattiva

#### Developer Features
- **Setup.py** installazione con `pip install -e .`
- **Click Framework** CLI modulare e estensibile
- **Row Factory** risultati query come dizionari
- **Error Handling** validazione input e messaggi utili
- **Docstrings** Google-style su tutte le funzioni
- **Type Hints** annotazioni tipo per funzioni principali

### Technical Details

#### Database Schema
- 10 tabelle relazionali con foreign keys
- Indici ottimizzati per query frequenti
- CASCADE delete per integrità referenziale
- CHECK constraints per validazione dati

#### Architecture
- **MVC Pattern** separazione logica/presentazione
- **Manager Class** `PeptideManager` per operazioni CRUD
- **Command Pattern** CLI commands indipendenti
- **Repository Pattern** accesso dati centralizzato

#### Dependencies
- Python 3.12+
- Click 8.0+
- SQLite3 (built-in)

### Fixed
- **SyntaxError in interactive.py** rimosso prefisso `python` errato da docstring
- **Validazione fiale** prevenzione valori negativi in `use_vials()`
- **Normalizzazione nomi** peptidi normalizzati automaticamente (BPC157 → BPC-157)

### Changed
- **Entry Point** `peptide-manager` senza argomenti ora lancia TUI (prima richiedeva comando)
- **Menu Structure** riorganizzati comandi in gruppi tematici
- **Error Messages** messaggi più chiari e actionable

### Security
- Database locale (no network exposure)
- No password/auth (single-user design)
- Dati sensibili in `.gitignore`

### Documentation
- README.md completo con esempi
- SESSION_LOG.md per continuità sviluppo
- GUIDA_CORREZIONE_FIALE.md per feature `adjust`
- Docstrings su tutte le funzioni pubbliche

---

## Release Notes - v0.1.0

### Highlights

🎯 **Sistema Completo**: Tutte le funzionalità core implementate e funzionanti  
🖥️ **TUI Immersiva**: Interfaccia DOS-style per uso quotidiano  
⚡ **CLI Potente**: Comandi scriptabili per automazione  
🧮 **Calcolatore Avanzato**: Tool matematico per diluizioni precise  
🔧 **Error Recovery**: Sistema correzione errori di registrazione  
📊 **Tracking Completo**: Da acquisto a somministrazione  

### Known Issues

- Shell.py corrotta (non utilizzata, TUI è sostituto)
- reports.py solo skeleton (funzioni base disponibili in altri moduli)
- Nessun test automatico (coverage 0%)

### Upgrade Path

Prima installazione - nessun upgrade necessario.

### Breaking Changes

Nessuno (prima release).

---

## Version History

- **0.1.0** (2025-01-XX) - Initial public release

---

## Links

- [GitHub Repository](https://github.com/yourusername/peptide-management-system)
- [Documentation](docs/)
- [Issues](https://github.com/yourusername/peptide-management-system/issues)
- [Releases](https://github.com/yourusername/peptide-management-system/releases)

---

[Unreleased]: https://github.com/yourusername/peptide-management-system/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/yourusername/peptide-management-system/releases/tag/v0.1.0
