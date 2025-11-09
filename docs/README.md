# 🧬 Peptide Management System - Refactored Architecture

Sistema modulare per la gestione di peptidi, fornitori, batch e protocolli.

## ✨ Caratteristiche

- ✅ **Architettura modulare** - Codice organizzato e manutenibile
- ✅ **Type-safe** - Python dataclasses con type hints
- ✅ **Testabile** - 22+ unit tests
- ✅ **Retrocompatibile** - Adapter per codice legacy
- ✅ **Dual environment** - Production/Development separati

---

## 📦 Struttura Progetto

```
peptide-management-system/
├── peptide_manager/              # Core package
│   ├── __init__.py              # Adapter retrocompatibilità
│   ├── database.py              # Database manager
│   │
│   ├── models/                  # Business logic
│   │   ├── base.py             # Classi base
│   │   ├── supplier.py         # Supplier model ✅
│   │   ├── peptide.py          # TODO
│   │   ├── batch.py            # TODO
│   │   └── ...
│   │
│   ├── ui/                      # GUI (Flet)
│   │   ├── main_window.py      # TODO
│   │   ├── tabs/               # Tab separate
│   │   ├── dialogs/            # Dialog riutilizzabili
│   │   └── widgets/            # Widget custom
│   │
│   ├── services/                # Business services
│   │   └── report_service.py   # TODO
│   │
│   └── utils/                   # Utilities
│       ├── validators.py       # TODO
│       └── formatters.py       # TODO
│
├── tests/                       # Test suite
│   ├── test_models/
│   │   └── test_supplier.py   # 16 tests ✅
│   ├── test_adapter.py         # 6 tests ✅
│   └── test_ui/                # TODO
│
├── scripts/
│   └── copy_prod_to_dev.py     # Environment management
│
├── gui.py                       # Entry point
└── MIGRATION_GUIDE.md          # Guida migrazione

```

---

## 🚀 Quick Start

### Installazione

```bash
# Clone repository
git clone <repo-url>
cd peptide-management-system

# Installa dipendenze
pip install flet

# Setup database
python -c "from peptide_manager.database import init_database; init_database()"
```

### Uso Base

```python
from peptide_manager.database import DatabaseManager
from peptide_manager.models import Supplier

# Connetti al database
db = DatabaseManager('peptide_management.db')

# Crea un fornitore
supplier = Supplier(
    name="Peptide Sciences",
    country="US",
    website="https://peptidesciences.com",
    reliability_rating=5
)

supplier_id = db.suppliers.create(supplier)
print(f"Supplier creato con ID: {supplier_id}")

# Recupera fornitori
suppliers = db.suppliers.get_all()
for s in suppliers:
    print(f"- {s.name} ({s.country})")

# Cerca fornitori
us_suppliers = db.suppliers.get_all(search="US")

# Aggiorna fornitore
supplier = db.suppliers.get_by_id(supplier_id)
supplier.reliability_rating = 4
db.suppliers.update(supplier)

# Elimina fornitore
success, message = db.suppliers.delete(supplier_id)
print(message)

# Chiudi connessione
db.close()
```

### Con Context Manager

```python
from peptide_manager.database import DatabaseManager
from peptide_manager.models import Supplier

with DatabaseManager('peptide_management.db') as db:
    # Crea supplier
    supplier = Supplier(name="Test")
    supplier_id = db.suppliers.create(supplier)
    
    # Usa database
    suppliers = db.suppliers.get_all()
    
    # Connessione chiusa automaticamente
```

---

## 🎨 GUI (Flet)

### Avvio Applicazione

```bash
# Development environment
python gui.py --env development

# Production environment
python gui.py --env production
```

### Retrocompatibilità

Il vecchio codice funziona ancora:

```python
from peptide_manager import PeptideManager

# Vecchia interfaccia (adapter)
manager = PeptideManager('peptide_management.db')

# Usa metodi come prima
manager.add_supplier("Test", country="IT", rating=5)
suppliers = manager.get_suppliers()
manager.update_supplier(1, name="Updated")
manager.delete_supplier(1)

manager.close()
```

---

## 🧪 Testing

### Run All Tests

```bash
# Tutti i test
python -m unittest discover tests -v

# Solo model tests
python -m unittest tests.test_models.test_supplier -v

# Solo adapter tests
python -m unittest tests.test_adapter -v
```

### Test Coverage

```bash
# Installa coverage
pip install coverage

# Run con coverage
coverage run -m unittest discover tests
coverage report
coverage html  # Genera report HTML
```

### Test Risultati

```
Ran 22 tests in 0.6s
OK

✅ 16 tests - Supplier model & repository
✅ 6 tests - PeptideManager adapter
```

---

## 📖 Documentazione

### Models

#### Supplier

```python
from peptide_manager.models import Supplier, SupplierRepository

# Dataclass con validazione
supplier = Supplier(
    name="Test Supplier",          # Required
    country="IT",                  # Optional
    website="https://test.com",    # Optional
    email="test@test.com",         # Optional
    notes="Test notes",            # Optional
    reliability_rating=5           # Optional (1-5)
)

# Repository pattern
repo = SupplierRepository(connection)

# CRUD operations
supplier_id = repo.create(supplier)
supplier = repo.get_by_id(supplier_id)
suppliers = repo.get_all(search="test")
repo.update(supplier)
success, msg = repo.delete(supplier_id, force=False)

# Utility methods
count = repo.count()
with_batches = repo.get_with_batch_count()
```

**Validazione automatica:**
- Nome obbligatorio (non vuoto)
- Rating 1-5 (se specificato)
- Eliminazione protetta (se ha batches associati)

---

## 🔄 Migration

Vedi [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) per:
- Strategia di migrazione completa
- Piano settimanale
- Esempi pratici
- Best practices
- FAQ

---

## 🏗️ Architettura

### Design Patterns

**Repository Pattern:**
```python
# Business logic separata da data access
class SupplierRepository(Repository):
    def create(self, supplier: Supplier) -> int:
        # SQL + validation
    
    def get_all(self, search=None) -> List[Supplier]:
        # Query + mapping
```

**Adapter Pattern:**
```python
# Vecchia interfaccia → Nuova architettura
class PeptideManager:  # Adapter
    def __init__(self, db_path):
        self.db = DatabaseManager(db_path)  # Nuova architettura
    
    def add_supplier(self, name, **kwargs):  # Vecchia interfaccia
        supplier = Supplier(name=name, **kwargs)
        return self.db.suppliers.create(supplier)  # Nuova logica
```

**Dataclass Pattern:**
```python
# Type-safe, immutable-ish, validation
@dataclass
class Supplier(BaseModel):
    name: str = ""
    country: Optional[str] = None
    
    def __post_init__(self):
        # Validazione
```

### Separazione Responsabilità

| Layer | Responsabilità | Esempio |
|-------|----------------|---------|
| **Models** | Business logic + Data | `Supplier`, `SupplierRepository` |
| **Database** | Connection management | `DatabaseManager` |
| **UI** | User interface | `SuppliersTab`, `SupplierDialog` |
| **Services** | Cross-cutting concerns | `ReportService`, `ExportService` |
| **Utils** | Helper functions | `validators`, `formatters` |

---

## 🎯 Roadmap

### ✅ Fase 1 - Suppliers (Completato)

- [x] Supplier model + repository
- [x] Unit tests (16 tests)
- [x] Adapter per retrocompatibilità
- [x] Integration tests (6 tests)
- [x] Documentazione

### 🚧 Fase 2 - Altri Models (In Corso)

- [ ] Peptide model + repository
- [ ] Batch model + repository
- [ ] Certificate model + repository
- [ ] Preparation model + repository
- [ ] Protocol model + repository
- [ ] Administration model + repository

### 📅 Fase 3 - GUI Refactor (Pianificato)

- [ ] Extract main window
- [ ] Separate tabs
- [ ] Common dialogs
- [ ] Custom widgets

### 🎨 Fase 4 - Polish (Futuro)

- [ ] REST API (FastAPI)
- [ ] CLI tools
- [ ] Export/Import services
- [ ] Advanced reporting

---

## 🤝 Contributing

### Workflow Git

```bash
# 1. Crea feature branch
git checkout -b refactor/module-name

# 2. Implementa + test
# ... coding ...

# 3. Run tests
python -m unittest discover tests -v

# 4. Commit
git add .
git commit -m "refactor: add Module model"

# 5. Push & PR
git push origin refactor/module-name
```

### Coding Standards

- **Type hints** ovunque
- **Docstrings** Google style
- **Tests** per ogni modulo (>80% coverage)
- **Max 200 righe** per file
- **PEP 8** compliant

---

## 📄 License

[MIT License](LICENSE)

---

## 📞 Support

- **Issues:** GitHub Issues
- **Email:** ftaba@example.com
- **Docs:** [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)

---

**Built with ❤️ using Python, Flet, and good architecture principles.**
