# 📘 Guida alla Migrazione - Refactoring Peptide Management System

## 🎯 Obiettivo

Migrare da architettura monolitica a modulare, **senza rompere il codice esistente**.

---

## 📊 Stato Attuale vs Target

### ❌ Prima (Monolitico)

```
peptide-management-system/
├── gui.py                    # 3,737 righe (GUI + Logic)
├── models.py                 # 1,904 righe (tutto il backend)
└── database.py               # 178 righe
```

**Problemi:**
- File giganti impossibili da navigare
- Accoppiamento stretto tra UI e business logic
- Testing impossibile (tutto integrato)
- Modifiche rischiose (un cambio rompe tutto)

### ✅ Dopo (Modulare)

```
peptide-management-system/
├── peptide_manager/
│   ├── __init__.py           # Adapter per retrocompatibilità
│   ├── database.py           # Database manager
│   ├── models/               # Business logic separata
│   │   ├── base.py
│   │   ├── supplier.py       # ~150 righe
│   │   ├── peptide.py        # ~150 righe
│   │   └── ...
│   ├── ui/                   # GUI separata
│   │   ├── main_window.py
│   │   └── tabs/
│   │       ├── suppliers_tab.py  # ~200 righe
│   │       └── ...
│   └── services/             # Business services
│       └── report_service.py
├── gui.py                    # ~50 righe (entry point)
└── tests/                    # Unit & integration tests
```

**Vantaggi:**
- File piccoli e focalizzati (~150-200 righe)
- Separazione chiara (models ≠ UI)
- Testabile (ogni modulo indipendente)
- Scalabile (aggiungi moduli senza toccare esistenti)

---

## 🚀 Strategia di Migrazione

### Fase 1: Backend Models ✅ **COMPLETATO**

**Cosa è stato fatto:**
- ✅ Creata architettura modulare in `peptide_manager/models/`
- ✅ Implementato `Supplier` model + repository
- ✅ Creato adapter `PeptideManager` per retrocompatibilità
- ✅ Scritti 22 unit tests (tutti passano)

**Risultato:**
- Vecchio codice funziona ancora (usa adapter)
- Nuovo codice è pulito e testato
- Possiamo migrare gradualmente

### Fase 2: Altri Models (In Corso)

**Da fare:**
1. `Peptide` model + repository
2. `Batch` model + repository
3. `Certificate` model + repository
4. `Preparation` model + repository
5. `Protocol` model + repository
6. `Administration` model + repository

**Timeline:** 1 modulo al giorno = 1 settimana

### Fase 3: Refactor GUI (Dopo)

**Da fare:**
1. Creare `ui/main_window.py`
2. Estrarre tabs in file separati
3. Estrarre dialogs comuni
4. Estrarre widgets custom

**Timeline:** 2 settimane

---

## 📖 Come Usare il Nuovo Codice

### Opzione A: Usa Adapter (Retrocompatibilità)

Il vecchio codice funziona **identicamente**:

```python
# gui.py (NESSUN CAMBIO NECESSARIO)
from peptide_manager import PeptideManager

manager = PeptideManager('db.db')

# Vecchia interfaccia funziona ancora
manager.add_supplier("Test", country="IT", rating=5)
suppliers = manager.get_suppliers()  # Restituisce list[dict]
manager.update_supplier(1, name="Updated")
manager.delete_supplier(1)
```

**Sotto il cofano:**
- Usa la nuova architettura modulare
- Tutto testato con unit tests
- Performance migliorate

### Opzione B: Usa Nuova Interfaccia (Consigliato)

Per nuovo codice o refactoring graduale:

```python
# Nuovo stile (più pulito)
from peptide_manager.database import DatabaseManager
from peptide_manager.models import Supplier

db = DatabaseManager('db.db')

# Crea supplier con dataclass
supplier = Supplier(
    name="Test",
    country="IT",
    reliability_rating=5
)

# CRUD con repository
supplier_id = db.suppliers.create(supplier)
supplier = db.suppliers.get_by_id(supplier_id)
supplier.name = "Updated"
db.suppliers.update(supplier)
db.suppliers.delete(supplier_id)

# Query avanzate
suppliers = db.suppliers.get_all(search="Test")
count = db.suppliers.count()
with_batches = db.suppliers.get_with_batch_count()
```

**Vantaggi:**
- Type hints (autocompletamento IDE)
- Validazione automatica
- Codice più leggibile
- Testabile facilmente

---

## 🔄 Piano di Migrazione Graduale

### Week 1: Suppliers (✅ Fatto)

```bash
git checkout -b refactor/suppliers

# 1. Copia nuovo codice
cp -r peptide_refactor/peptide_manager/* peptide_manager/

# 2. Test che vecchio codice funziona
python gui.py --env development

# 3. Test unitari
python -m unittest tests.test_models.test_supplier

# 4. Se tutto OK, commit
git add .
git commit -m "refactor: modularize Supplier model with tests"
```

### Week 2: Peptides

```bash
git checkout -b refactor/peptides

# 1. Crea models/peptide.py (simile a supplier.py)
# 2. Aggiungi metodi in __init__.py adapter
# 3. Scrivi tests
# 4. Verifica vecchio codice funziona
# 5. Commit
```

### Week 3-4: Altri Models

Ripeti processo per:
- Batch
- Certificate
- Preparation
- Protocol
- Administration

### Week 5-6: GUI Refactor

```bash
git checkout -b refactor/gui-suppliers-tab

# 1. Estrai SupplierTab da gui.py
# 2. Test funzionalità
# 3. Commit
```

---

## 🧪 Testing Strategy

### Unit Tests (Isolati)

Ogni model ha i suoi test:

```python
# tests/test_models/test_supplier.py
class TestSupplierRepository(unittest.TestCase):
    def test_create_supplier(self):
        # Test SOLO la creazione
        supplier = Supplier(name="Test")
        supplier_id = repo.create(supplier)
        self.assertGreater(supplier_id, 0)
```

**Run:**
```bash
python -m unittest tests.test_models.test_supplier
```

### Integration Tests (Insieme)

Test che tutto funziona insieme:

```python
# tests/test_adapter.py
class TestPeptideManagerAdapter(unittest.TestCase):
    def test_old_interface_still_works(self):
        # Test che vecchia interfaccia funziona
        manager = PeptideManager('test.db')
        manager.add_supplier("Test")
        suppliers = manager.get_suppliers()
        self.assertEqual(len(suppliers), 1)
```

**Run:**
```bash
python -m unittest tests.test_adapter
```

### Manual Testing

Sempre testa GUI dopo ogni cambio:

```bash
# Test su development (sicuro)
python gui.py --env development

# Test su production (dopo verifiche)
python gui.py --env production
```

---

## ⚠️ Rischi e Mitigazioni

| Rischio | Mitigazione |
|---------|-------------|
| **Rompo codice esistente** | Usa adapter + test retrocompatibilità |
| **Perdo funzionalità** | Test manuali dopo ogni step |
| **Import circolari** | Models non importano mai UI |
| **Database corruption** | Sempre su `--env development` |
| **Troppo complesso** | Migra 1 modulo alla volta |

---

## 📋 Checklist per Ogni Modulo

Prima di committare, verifica:

- [ ] Unit tests scritti e passano
- [ ] Integration tests passano
- [ ] Vecchio codice funziona (adapter)
- [ ] GUI funziona su `--env development`
- [ ] Documentazione aggiornata
- [ ] Commit message descrittivo

---

## 🎓 Best Practices

### 1. Sempre su Branch Separato

```bash
git checkout -b refactor/module-name
# Lavora qui
git commit -am "refactor: module-name"
git checkout master
git merge refactor/module-name
```

### 2. Test Prima di Commit

```bash
# Test unitari
python -m unittest tests.test_models.test_X

# Test integration
python -m unittest tests.test_adapter

# Test GUI
python gui.py --env development
```

### 3. Small Commits

```bash
# ❌ Male: mega-commit
git commit -am "refactor everything"

# ✅ Bene: commit atomici
git commit -m "refactor: add Supplier dataclass"
git commit -m "refactor: add SupplierRepository"
git commit -m "test: add Supplier unit tests"
git commit -m "refactor: add adapter for Supplier"
```

### 4. Documentazione Inline

```python
# ✅ Bene
class SupplierRepository(Repository):
    """
    Repository per operazioni CRUD sui fornitori.
    
    Fornisce metodi per creare, leggere, aggiornare ed eliminare
    fornitori nel database.
    """
    
    def create(self, supplier: Supplier) -> int:
        """
        Crea un nuovo fornitore.
        
        Args:
            supplier: Oggetto Supplier da creare
            
        Returns:
            ID del fornitore creato
            
        Raises:
            ValueError: Se nome vuoto o rating invalido
        """
```

---

## 💡 Esempi Pratici

### Esempio 1: Vecchio → Nuovo (Suppliers)

**PRIMA (gui.py, 3737 righe):**
```python
def load_suppliers(self):
    # 50 righe di codice UI + SQL mescolato
    cursor = self.manager.conn.cursor()
    cursor.execute("SELECT * FROM suppliers...")
    rows = cursor.fetchall()
    # ... altro codice UI ...
```

**DOPO (ui/tabs/suppliers_tab.py, ~150 righe):**
```python
def load_suppliers(self):
    # UI pulita
    suppliers = self.db.suppliers.get_all(search=self.search_box.value)
    self.update_table(suppliers)
```

### Esempio 2: Testing

**PRIMA:** Impossibile testare (tutto integrato)

**DOPO:**
```python
# Test isolato
def test_create_supplier():
    supplier = Supplier(name="Test")
    supplier_id = repo.create(supplier)
    assert supplier_id > 0

# Test integrazione
def test_gui_suppliers_tab():
    tab = SuppliersTab(db)
    tab.add_supplier("Test", "IT", 5)
    suppliers = tab.get_suppliers()
    assert len(suppliers) == 1
```

---

## 📞 FAQ

**Q: Il vecchio codice continuerà a funzionare?**
A: Sì! L'adapter mantiene la vecchia interfaccia identica.

**Q: Devo riscrivere tutto subito?**
A: No! Migra 1 modulo alla volta. Vecchio e nuovo coesistono.

**Q: Cosa faccio se rompo qualcosa?**
A: `git checkout master` e riparti dal branch.

**Q: I test sono obbligatori?**
A: Fortemente consigliati! Prevengono regressioni.

**Q: Quanto tempo ci vuole?**
A: ~3-4 settimane migrando 1-2 moduli al giorno.

---

## 🎯 Quick Start

### Setup per Nuovo Sviluppo

```bash
# 1. Copia nuovo codice nel progetto
cd C:\Users\ftaba\source\peptide-management-system

# 2. Crea branch
git checkout -b refactor/suppliers

# 3. Copia moduli refactored
# (manualmente o script)

# 4. Test
python -m unittest tests.test_models.test_supplier
python gui.py --env development

# 5. Se OK, commit
git add .
git commit -m "refactor: modularize Supplier model"
git push origin refactor/suppliers
```

### Uso Quotidiano

```python
# Vecchio stile (funziona ancora)
from peptide_manager import PeptideManager
manager = PeptideManager('db.db')
manager.add_supplier("Test")

# Nuovo stile (consigliato per nuovo codice)
from peptide_manager.database import DatabaseManager
from peptide_manager.models import Supplier

db = DatabaseManager('db.db')
supplier = Supplier(name="Test")
db.suppliers.create(supplier)
```

---

## ✅ Next Steps

1. **Review Codice Refactored:** Leggi `peptide_manager/models/supplier.py`
2. **Run Tests:** `python -m unittest tests.test_models.test_supplier -v`
3. **Pianifica Migrazione:** Decidi ordine moduli (consiglio: Peptide → Batch → etc.)
4. **Crea Branch:** `git checkout -b refactor/peptides`
5. **Inizia Refactor:** Usa `supplier.py` come template

---

## 📚 Risorse

- **Git Workflow:** Vedi `WORKFLOW_GIT_BRANCHES.md`
- **Python Dataclasses:** https://docs.python.org/3/library/dataclasses.html
- **Repository Pattern:** https://martinfowler.com/eaaCatalog/repository.html
- **Unit Testing:** https://docs.python.org/3/library/unittest.html

---

**Buon refactoring! 🚀**
