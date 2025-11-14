# 📘 Guida alla Migrazione Entità - Repository Pattern

Questa guida ti permette di migrare autonomamente le entità rimanenti (Preparations, Protocols, Administrations, Certificates) seguendo il pattern già stabilito.

## 🎯 Obiettivo

Migrare un'entità da `models_legacy.py` a un nuovo modulo in `peptide_manager/models/{entity}.py` seguendo il pattern Repository.

---

## 📋 Pattern Generale

Ogni entità migrata segue questa struttura:

```
peptide_manager/models/{entity}.py
├── @dataclass {Entity}(BaseModel)    # Model con type hints
└── class {Entity}Repository(Repository)  # Repository con CRUD
    ├── get_all()                      # Lista con filtri
    ├── get_by_id()                    # Singolo elemento
    ├── create()                       # Crea nuovo
    ├── update()                       # Aggiorna esistente
    ├── delete()                       # Elimina (con controlli)
    └── [metodi custom se necessari]   # Es: get_expired(), etc.
```

---

## 🔄 Workflow Completo

### Fase 1: Analisi Pre-Migrazione

#### 1.1 Studia l'Entità Legacy

```python
# In peptide_manager/models_legacy.py
# Cerca tutti i metodi che iniziano con:
# - get_{entity}*
# - add_{entity}
# - update_{entity}
# - delete_{entity}
# - {entity}_* (metodi custom)
```

**Esempio per Preparations:**
- `add_preparation()`
- `get_preparations()`
- `get_preparation_details()`
- `update_preparation()`
- `delete_preparation()`
- `use_preparation()`
- `get_expired_preparations()`
- `reconcile_preparation_volumes()`

#### 1.2 Identifica Schema Database

Verifica la struttura della tabella nel database:

```python
# Query per vedere schema
cursor.execute("PRAGMA table_info(preparations)")
# Oppure
cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='preparations'")
```

**Campi tipici da identificare:**
- Campi obbligatori (NOT NULL)
- Campi opzionali (NULL)
- Foreign keys
- Tipi di dato (INTEGER, TEXT, REAL, DATE, TIMESTAMP)
- Valori di default

#### 1.3 Mappa Metodi Legacy → Nuovi Metodi

Crea una mappa mentale:

| Metodo Legacy | Nuovo Metodo Repository | Note |
|--------------|-------------------------|------|
| `get_preparations()` | `get_all()` | Con filtri opzionali |
| `get_preparation_details()` | `get_by_id()` + JOIN | O metodo custom |
| `add_preparation()` | `create()` | Con validazioni |
| `update_preparation()` | `update()` | Con validazioni |
| `delete_preparation()` | `delete()` | Con controlli FK |
| `use_preparation()` | `use_volume()` | Metodo custom |
| `get_expired_preparations()` | `get_expired()` | Metodo custom |

---

### Fase 2: Creazione Model e Repository

#### 2.1 Crea File `peptide_manager/models/{entity}.py`

**Template Base:**

```python
"""
{Entity} model - gestisce {descrizione entità}.
"""

from dataclasses import dataclass
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal
from .base import BaseModel, Repository


@dataclass
class {Entity}(BaseModel):
    """Rappresenta un/a {entità}."""
    
    # Campi obbligatori
    campo_obbligatorio: str = ""
    
    # Foreign keys
    foreign_key_id: int = None  # Es: batch_id, protocol_id
    
    # Campi opzionali
    campo_opzionale: Optional[str] = None
    data_campo: Optional[date] = None
    decimal_campo: Optional[Decimal] = None
    
    # Soft delete (se supportato)
    deleted_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Validazione dopo inizializzazione."""
        # Validazioni base
        if not self.campo_obbligatorio or not self.campo_obbligatorio.strip():
            raise ValueError("Campo obbligatorio non può essere vuoto")
        
        # Validazioni range/valori
        if self.decimal_campo is not None and self.decimal_campo < 0:
            raise ValueError("Valore non può essere negativo")
        
        # Conversioni automatiche
        if isinstance(self.data_campo, str):
            self.data_campo = date.fromisoformat(self.data_campo)
        if isinstance(self.decimal_campo, (int, float, str)):
            self.decimal_campo = Decimal(str(self.decimal_campo))
    
    def is_deleted(self) -> bool:
        """Verifica se eliminato (soft delete)."""
        return self.deleted_at is not None
    
    def is_expired(self, reference_date: Optional[date] = None) -> bool:
        """Verifica se scaduto (se applicabile)."""
        if self.expiry_date is None:
            return False
        ref = reference_date or date.today()
        return self.expiry_date < ref


class {Entity}Repository(Repository):
    """Repository per operazioni CRUD su {entity}."""
    
    def get_all(
        self,
        search: Optional[str] = None,
        foreign_key_id: Optional[int] = None,  # Es: batch_id
        only_active: bool = False,
        include_deleted: bool = False
    ) -> List[{Entity}]:
        """
        Recupera tutti gli elementi con filtri opzionali.
        
        Args:
            search: Filtro ricerca (nome/descrizione)
            foreign_key_id: Filtra per FK specifica
            only_active: Solo elementi attivi (es: volume > 0)
            include_deleted: Include eliminati (soft delete)
            
        Returns:
            Lista di {Entity}
        """
        query = 'SELECT * FROM {table_name} WHERE 1=1'
        params = []
        
        # Filtro soft delete
        if not include_deleted:
            query += ' AND deleted_at IS NULL'
        
        # Filtro ricerca
        if search:
            query += ' AND (campo_ricercabile LIKE ? OR altro_campo LIKE ?)'
            params.extend([f'%{search}%', f'%{search}%'])
        
        # Filtro foreign key
        if foreign_key_id:
            query += ' AND foreign_key_id = ?'
            params.append(foreign_key_id)
        
        # Filtro attivi
        if only_active:
            query += ' AND volume_remaining_ml > 0'  # Esempio
        
        query += ' ORDER BY created_at DESC'  # O altro campo
        
        rows = self._fetch_all(query, tuple(params))
        return [{Entity}.from_row(row) for row in rows]
    
    def get_by_id(
        self, 
        entity_id: int, 
        include_deleted: bool = False
    ) -> Optional[{Entity}]:
        """
        Recupera elemento per ID.
        
        Args:
            entity_id: ID elemento
            include_deleted: Include anche se eliminato
            
        Returns:
            {Entity} o None se non trovato
        """
        query = 'SELECT * FROM {table_name} WHERE id = ?'
        
        if not include_deleted:
            query += ' AND deleted_at IS NULL'
        
        row = self._fetch_one(query, (entity_id,))
        return {Entity}.from_row(row) if row else None
    
    def create(self, entity: {Entity}) -> int:
        """
        Crea nuovo elemento.
        
        Args:
            entity: Oggetto {Entity} da creare
            
        Returns:
            ID elemento creato
            
        Raises:
            ValueError: Se dati non validi o FK non esiste
        """
        # Validazione
        if not entity.campo_obbligatorio or not entity.campo_obbligatorio.strip():
            raise ValueError("Campo obbligatorio necessario")
        
        # Verifica foreign key esiste
        if entity.foreign_key_id:
            fk_query = 'SELECT id FROM {fk_table} WHERE id = ?'
            if not self._fetch_one(fk_query, (entity.foreign_key_id,)):
                raise ValueError(f"{FK} #{entity.foreign_key_id} non trovato")
        
        # Query INSERT
        query = '''
            INSERT INTO {table_name} (
                campo_obbligatorio, foreign_key_id,
                campo_opzionale, data_campo, decimal_campo
            )
            VALUES (?, ?, ?, ?, ?)
        '''
        
        cursor = self._execute(query, (
            entity.campo_obbligatorio,
            entity.foreign_key_id,
            entity.campo_opzionale,
            entity.data_campo,
            float(entity.decimal_campo) if entity.decimal_campo else None
        ))
        
        self._commit()
        return cursor.lastrowid
    
    def update(self, entity: {Entity}) -> bool:
        """
        Aggiorna elemento esistente.
        
        Args:
            entity: Oggetto {Entity} con dati aggiornati (deve avere id)
            
        Returns:
            True se aggiornato
            
        Raises:
            ValueError: Se id non specificato o dati non validi
        """
        if entity.id is None:
            raise ValueError("ID necessario per update")
        
        # Validazione (stessa di create)
        if not entity.campo_obbligatorio or not entity.campo_obbligatorio.strip():
            raise ValueError("Campo obbligatorio necessario")
        
        query = '''
            UPDATE {table_name} 
            SET campo_obbligatorio = ?, campo_opzionale = ?,
                data_campo = ?, decimal_campo = ?
            WHERE id = ?
        '''
        
        self._execute(query, (
            entity.campo_obbligatorio,
            entity.campo_opzionale,
            entity.data_campo,
            float(entity.decimal_campo) if entity.decimal_campo else None,
            entity.id
        ))
        
        self._commit()
        return True
    
    def delete(
        self, 
        entity_id: int, 
        force: bool = False
    ) -> tuple[bool, str]:
        """
        Elimina elemento (soft delete di default).
        
        Args:
            entity_id: ID elemento
            force: Se True, elimina fisicamente (hard delete)
            
        Returns:
            (success: bool, message: str)
        """
        # Verifica esistenza
        entity = self.get_by_id(entity_id, include_deleted=True)
        if not entity:
            return False, f"{Entity} #{entity_id} non trovato"
        
        if entity.is_deleted() and not force:
            return False, f"{Entity} già eliminato"
        
        # Controlla riferimenti (se applicabile)
        # Es: query = 'SELECT COUNT(*) FROM child_table WHERE entity_id = ?'
        # row = self._fetch_one(query, (entity_id,))
        # ref_count = row[0] if row else 0
        # if ref_count > 0 and not force:
        #     return False, f"Impossibile eliminare: {ref_count} riferimenti"
        
        if force:
            # Hard delete
            query = 'DELETE FROM {table_name} WHERE id = ?'
            self._execute(query, (entity_id,))
            self._commit()
            return True, f"{Entity} eliminato definitivamente"
        else:
            # Soft delete
            query = 'UPDATE {table_name} SET deleted_at = CURRENT_TIMESTAMP WHERE id = ?'
            self._execute(query, (entity_id,))
            self._commit()
            return True, f"{Entity} archiviato (soft delete)"
    
    def count(self, include_deleted: bool = False) -> int:
        """Conta elementi totali."""
        query = 'SELECT COUNT(*) FROM {table_name}'
        if not include_deleted:
            query += ' WHERE deleted_at IS NULL'
        
        row = self._fetch_one(query)
        return row[0] if row else 0
    
    # ========== METODI CUSTOM (se necessari) ==========
    
    def get_expired(self, reference_date: Optional[date] = None) -> List[{Entity}]:
        """
        Recupera elementi scaduti (esempio).
        
        Args:
            reference_date: Data riferimento (default: oggi)
            
        Returns:
            Lista elementi scaduti
        """
        ref = reference_date or date.today()
        query = '''
            SELECT * FROM {table_name}
            WHERE deleted_at IS NULL
              AND expiry_date IS NOT NULL
              AND expiry_date < ?
            ORDER BY expiry_date
        '''
        rows = self._fetch_all(query, (ref,))
        return [{Entity}.from_row(row) for row in rows]
```

#### 2.2 Esempio Concreto: Preparations

**Schema tabella `preparations` (verifica nel tuo DB):**
```sql
CREATE TABLE preparations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id INTEGER NOT NULL,
    vials_used INTEGER NOT NULL,
    volume_ml REAL NOT NULL,
    volume_remaining_ml REAL NOT NULL,
    diluent TEXT DEFAULT 'BAC Water',
    preparation_date DATE NOT NULL,
    expiry_date DATE,
    storage_location TEXT,
    notes TEXT,
    deleted_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (batch_id) REFERENCES batches(id)
)
```

**Model Preparations (esempio completo):**

```python
@dataclass
class Preparation(BaseModel):
    """Rappresenta una preparazione (ricostituzione) di peptide."""
    batch_id: int = None
    vials_used: int = 1
    volume_ml: Decimal = None
    volume_remaining_ml: Decimal = None
    diluent: str = 'BAC Water'
    preparation_date: Optional[date] = None
    expiry_date: Optional[date] = None
    storage_location: Optional[str] = None
    notes: Optional[str] = None
    deleted_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Validazione dopo inizializzazione."""
        if self.batch_id is None:
            raise ValueError("Batch ID obbligatorio")
        if self.vials_used < 1:
            raise ValueError("Numero fiale deve essere >= 1")
        if self.volume_ml is not None and self.volume_ml <= 0:
            raise ValueError("Volume deve essere > 0")
        
        # Conversioni
        if isinstance(self.preparation_date, str):
            self.preparation_date = date.fromisoformat(self.preparation_date)
        if isinstance(self.expiry_date, str):
            self.expiry_date = date.fromisoformat(self.expiry_date)
        if isinstance(self.volume_ml, (int, float, str)):
            self.volume_ml = Decimal(str(self.volume_ml))
        if isinstance(self.volume_remaining_ml, (int, float, str)):
            self.volume_remaining_ml = Decimal(str(self.volume_remaining_ml))
    
    def is_depleted(self) -> bool:
        """Verifica se preparazione esaurita."""
        return self.volume_remaining_ml == 0
    
    def is_expired(self, reference_date: Optional[date] = None) -> bool:
        """Verifica se scaduta."""
        if self.expiry_date is None:
            return False
        ref = reference_date or date.today()
        return self.expiry_date < ref
```

**Repository Preparations (esempio completo):**

```python
class PreparationRepository(Repository):
    """Repository per operazioni CRUD su preparazioni."""
    
    def get_all(
        self,
        batch_id: Optional[int] = None,
        only_active: bool = False,
        include_deleted: bool = False
    ) -> List[Preparation]:
        """Recupera preparazioni con filtri."""
        query = 'SELECT * FROM preparations WHERE 1=1'
        params = []
        
        if not include_deleted:
            query += ' AND deleted_at IS NULL'
        
        if batch_id:
            query += ' AND batch_id = ?'
            params.append(batch_id)
        
        if only_active:
            query += ' AND volume_remaining_ml > 0'
        
        query += ' ORDER BY preparation_date DESC'
        
        rows = self._fetch_all(query, tuple(params))
        return [Preparation.from_row(row) for row in rows]
    
    def get_by_id(self, prep_id: int, include_deleted: bool = False) -> Optional[Preparation]:
        """Recupera preparazione per ID."""
        query = 'SELECT * FROM preparations WHERE id = ?'
        if not include_deleted:
            query += ' AND deleted_at IS NULL'
        
        row = self._fetch_one(query, (prep_id,))
        return Preparation.from_row(row) if row else None
    
    def create(self, preparation: Preparation) -> int:
        """Crea nuova preparazione."""
        # Validazione
        if preparation.batch_id is None:
            raise ValueError("Batch ID obbligatorio")
        
        # Verifica batch esiste
        batch_query = 'SELECT id, vials_remaining FROM batches WHERE id = ?'
        batch_row = self._fetch_one(batch_query, (preparation.batch_id,))
        if not batch_row:
            raise ValueError(f"Batch #{preparation.batch_id} non trovato")
        
        # Verifica fiale disponibili
        vials_remaining = batch_row[1] if hasattr(batch_row, '__getitem__') else batch_row['vials_remaining']
        if vials_remaining < preparation.vials_used:
            raise ValueError(
                f"Fiale insufficienti (disponibili: {vials_remaining}, "
                f"richieste: {preparation.vials_used})"
            )
        
        # Inserisci preparazione
        query = '''
            INSERT INTO preparations (
                batch_id, vials_used, volume_ml, volume_remaining_ml,
                diluent, preparation_date, expiry_date,
                storage_location, notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''
        cursor = self._execute(query, (
            preparation.batch_id,
            preparation.vials_used,
            float(preparation.volume_ml) if preparation.volume_ml else None,
            float(preparation.volume_remaining_ml) if preparation.volume_remaining_ml else None,
            preparation.diluent,
            preparation.preparation_date,
            preparation.expiry_date,
            preparation.storage_location,
            preparation.notes
        ))
        
        prep_id = cursor.lastrowid
        
        # Decrementa fiale dal batch
        update_batch_query = '''
            UPDATE batches SET vials_remaining = vials_remaining - ?
            WHERE id = ?
        '''
        self._execute(update_batch_query, (preparation.vials_used, preparation.batch_id))
        
        self._commit()
        return prep_id
    
    def update(self, preparation: Preparation) -> bool:
        """Aggiorna preparazione."""
        if preparation.id is None:
            raise ValueError("ID preparazione necessario per update")
        
        query = '''
            UPDATE preparations 
            SET volume_remaining_ml = ?, expiry_date = ?,
                storage_location = ?, notes = ?
            WHERE id = ?
        '''
        self._execute(query, (
            float(preparation.volume_remaining_ml) if preparation.volume_remaining_ml else None,
            preparation.expiry_date,
            preparation.storage_location,
            preparation.notes,
            preparation.id
        ))
        
        self._commit()
        return True
    
    def delete(self, prep_id: int, force: bool = False, restore_vials: bool = False) -> tuple[bool, str]:
        """Elimina preparazione."""
        preparation = self.get_by_id(prep_id, include_deleted=True)
        if not preparation:
            return False, f"Preparazione #{prep_id} non trovata"
        
        # Controlla amministrazioni collegate
        admin_query = 'SELECT COUNT(*) FROM administrations WHERE preparation_id = ?'
        admin_row = self._fetch_one(admin_query, (prep_id,))
        admin_count = admin_row[0] if admin_row else 0
        
        if admin_count > 0 and not force:
            return False, (
                f"Impossibile eliminare: {admin_count} somministrazione(i) collegata(e). "
                f"Usa force=True per forzare."
            )
        
        # Restore vials se richiesto
        if restore_vials and not preparation.is_deleted():
            restore_query = '''
                UPDATE batches SET vials_remaining = vials_remaining + ?
                WHERE id = ?
            '''
            self._execute(restore_query, (preparation.vials_used, preparation.batch_id))
        
        if force:
            query = 'DELETE FROM preparations WHERE id = ?'
            self._execute(query, (prep_id,))
            self._commit()
            return True, f"Preparazione eliminata definitivamente"
        else:
            query = 'UPDATE preparations SET deleted_at = CURRENT_TIMESTAMP WHERE id = ?'
            self._execute(query, (prep_id,))
            self._commit()
            return True, f"Preparazione archiviata (soft delete)"
    
    def use_volume(
        self,
        prep_id: int,
        ml_used: Decimal,
        administration_datetime: Optional[datetime] = None
    ) -> tuple[bool, str]:
        """
        Usa volume da preparazione (metodo custom).
        
        Args:
            prep_id: ID preparazione
            ml_used: ML da usare
            administration_datetime: Data/ora somministrazione
            
        Returns:
            (success: bool, message: str)
        """
        preparation = self.get_by_id(prep_id)
        if not preparation:
            return False, f"Preparazione #{prep_id} non trovata"
        
        new_volume = preparation.volume_remaining_ml - ml_used
        
        if new_volume < 0:
            return False, (
                f"Volume insufficiente (disponibile: {preparation.volume_remaining_ml}ml, "
                f"richiesto: {ml_used}ml)"
            )
        
        query = 'UPDATE preparations SET volume_remaining_ml = ? WHERE id = ?'
        self._execute(query, (float(new_volume), prep_id))
        self._commit()
        
        return True, f"Volume aggiornato: {preparation.volume_remaining_ml}ml → {new_volume}ml"
    
    def get_expired(self, reference_date: Optional[date] = None) -> List[Preparation]:
        """Recupera preparazioni scadute."""
        ref = reference_date or date.today()
        query = '''
            SELECT * FROM preparations
            WHERE deleted_at IS NULL
              AND expiry_date IS NOT NULL
              AND expiry_date < ?
              AND volume_remaining_ml > 0
            ORDER BY expiry_date
        '''
        rows = self._fetch_all(query, (ref,))
        return [Preparation.from_row(row) for row in rows]
    
    def count(self, include_deleted: bool = False) -> int:
        """Conta preparazioni totali."""
        query = 'SELECT COUNT(*) FROM preparations'
        if not include_deleted:
            query += ' WHERE deleted_at IS NULL'
        
        row = self._fetch_one(query)
        return row[0] if row else 0
```

---

### Fase 3: Aggiornare Export e DatabaseManager

#### 3.1 Aggiorna `peptide_manager/models/__init__.py`

Aggiungi export del nuovo model e repository:

```python
from .base import BaseModel, Repository
from .supplier import Supplier, SupplierRepository
from .peptide import Peptide, PeptideRepository
from .batch import Batch, BatchRepository
from .batch_composition import BatchComposition, BatchCompositionRepository
from .preparation import Preparation, PreparationRepository  # ← NUOVO

__all__ = [
    'BaseModel',
    'Repository',
    'Supplier',
    'SupplierRepository',
    'Peptide',
    'PeptideRepository',
    'Batch',
    'BatchRepository',
    'BatchComposition',
    'BatchCompositionRepository',
    'Preparation',              # ← NUOVO
    'PreparationRepository',     # ← NUOVO
]
```

#### 3.2 Aggiorna `peptide_manager/database.py`

Aggiungi import e inizializza repository:

```python
from .models.supplier import SupplierRepository
from .models.peptide import PeptideRepository
from .models.batch import BatchRepository
from .models.batch_composition import BatchCompositionRepository
from .models.preparation import PreparationRepository  # ← NUOVO

class DatabaseManager:
    def __init__(self, db_path: str = 'peptide_management.db'):
        # ...
        # Inizializza repository
        self.suppliers = SupplierRepository(self.conn)
        self.peptides = PeptideRepository(self.conn)
        self.batches = BatchRepository(self.conn)
        self.batch_composition = BatchCompositionRepository(self.conn)
        self.preparations = PreparationRepository(self.conn)  # ← NUOVO
```

---

### Fase 4: Implementare Adapter in `peptide_manager/__init__.py`

#### 4.1 Sostituisci Metodi Legacy con Nuova Implementazione

Trova la sezione `# ==================== NON ANCORA MIGRATI (FALLBACK) ====================` e sostituisci i metodi.

**Prima (delega legacy):**

```python
def get_preparations(self, **kwargs) -> List[Dict]:
    """Delega al vecchio manager (TODO: migrare)."""
    return self._get_old_manager().get_preparations(**kwargs)
```

**Dopo (usa nuovo repository):**

```python
# ==================== PREPARATIONS (MIGRATO ✅) ====================

def get_preparations(
    self,
    batch_id: int = None,
    only_active: bool = False
) -> List[Dict]:
    """
    Recupera preparazioni (usa nuova architettura).
    
    Args:
        batch_id: Filtra per batch specifico
        only_active: Solo preparazioni con volume rimanente > 0
        
    Returns:
        Lista di dict (compatibile con vecchia interfaccia)
    """
    preparations = self.db.preparations.get_all(
        batch_id=batch_id,
        only_active=only_active
    )
    return [p.to_dict() for p in preparations]

def get_preparation_details(self, prep_id: int) -> Optional[Dict]:
    """
    Recupera dettagli preparazione (usa nuova architettura).
    
    Args:
        prep_id: ID preparazione
        
    Returns:
        Dict con dettagli completi o None
    """
    preparation = self.db.preparations.get_by_id(prep_id)
    if not preparation:
        return None
    
    result = preparation.to_dict()
    
    # Aggiungi informazioni batch (JOIN)
    batch = self.db.batches.get_by_id(preparation.batch_id)
    if batch:
        result['batch_product'] = batch.product_name
        result['batch_number'] = batch.batch_number
    
    # Aggiungi composizione peptidi dal batch
    peptides = self.db.batch_composition.get_peptides_in_batch(preparation.batch_id)
    result['composition'] = peptides
    
    return result

def add_preparation(
    self,
    batch_id: int,
    vials_used: int,
    volume_ml: float,
    preparation_date: str,
    diluent: str = 'BAC Water',
    expiry_date: str = None,
    storage_location: str = None,
    notes: str = None
) -> int:
    """
    Aggiunge preparazione (usa nuova architettura).
    
    Args:
        batch_id: ID batch
        vials_used: Numero fiale usate
        volume_ml: Volume totale ml
        preparation_date: Data preparazione (YYYY-MM-DD)
        diluent: Tipo diluente
        expiry_date: Data scadenza (opzionale)
        storage_location: Posizione conservazione
        notes: Note
        
    Returns:
        ID preparazione creata
    """
    from datetime import date
    from decimal import Decimal
    
    preparation = Preparation(
        batch_id=batch_id,
        vials_used=vials_used,
        volume_ml=Decimal(str(volume_ml)),
        volume_remaining_ml=Decimal(str(volume_ml)),  # Inizialmente uguale
        diluent=diluent,
        preparation_date=date.fromisoformat(preparation_date) if preparation_date else None,
        expiry_date=date.fromisoformat(expiry_date) if expiry_date else None,
        storage_location=storage_location,
        notes=notes
    )
    
    prep_id = self.db.preparations.create(preparation)
    print(f"Preparazione #{prep_id} creata")
    return prep_id

def update_preparation(self, prep_id: int, **kwargs) -> bool:
    """
    Aggiorna preparazione (usa nuova architettura).
    
    Args:
        prep_id: ID preparazione
        **kwargs: Campi da aggiornare
        
    Returns:
        True se aggiornato
    """
    preparation = self.db.preparations.get_by_id(prep_id)
    if not preparation:
        print(f"Preparazione #{prep_id} non trovata")
        return False
    
    # Aggiorna campi
    allowed_fields = [
        'volume_remaining_ml', 'expiry_date',
        'storage_location', 'notes'
    ]
    
    for key, value in kwargs.items():
        if key in allowed_fields:
            if key == 'volume_remaining_ml':
                from decimal import Decimal
                value = Decimal(str(value))
            elif key == 'expiry_date' and value:
                from datetime import date
                value = date.fromisoformat(value)
            setattr(preparation, key, value)
    
    # Salva
    try:
        self.db.preparations.update(preparation)
        print(f"Preparazione ID {prep_id} aggiornata")
        return True
    except ValueError as e:
        print(f"Errore: {e}")
        return False

def soft_delete_preparation(self, prep_id: int, restore_vials: bool = False) -> bool:
    """
    Elimina preparazione (usa nuova architettura).
    
    Args:
        prep_id: ID preparazione
        restore_vials: Se True, ripristina fiale al batch
        
    Returns:
        True se eliminato
    """
    success, message = self.db.preparations.delete(
        prep_id,
        force=False,
        restore_vials=restore_vials
    )
    
    if success:
        print(f"[OK] {message}")
    else:
        print(f"[ERROR] {message}")
    
    return success

def use_preparation(
    self,
    prep_id: int,
    ml_used: float,
    administration_datetime: str = None,
    injection_site: str = None,
    notes: str = None,
    protocol_id: int = None
) -> bool:
    """
    Usa volume da preparazione (usa nuova architettura).
    
    Args:
        prep_id: ID preparazione
        ml_used: ML da usare
        administration_datetime: Data/ora somministrazione
        injection_site: Sito iniezione
        notes: Note
        protocol_id: ID protocollo (opzionale)
        
    Returns:
        True se successo
    """
    from decimal import Decimal
    
    success, message = self.db.preparations.use_volume(
        prep_id,
        Decimal(str(ml_used)),
        administration_datetime
    )
    
    if success:
        # Crea amministrazione (se necessario)
        # TODO: implementare quando migri administrations
        print(f"[OK] {message}")
        return True
    else:
        print(f"[ERROR] {message}")
        return False

def get_expired_preparations(self) -> List[Dict]:
    """
    Recupera preparazioni scadute (usa nuova architettura).
    
    Returns:
        Lista di dict preparazioni scadute
    """
    preparations = self.db.preparations.get_expired()
    return [p.to_dict() for p in preparations]

def reconcile_preparation_volumes(self, prep_id: int = None) -> Dict:
    """
    Riconcilia volumi preparazioni (usa nuova architettura).
    
    Args:
        prep_id: ID preparazione specifica (None = tutte)
        
    Returns:
        Dict con statistiche riconciliazione
    """
    # Implementa logica riconciliazione
    # Calcola volume teorico vs volume rimanente
    # Segnala discrepanze
    
    if prep_id:
        preparation = self.db.preparations.get_by_id(prep_id)
        if not preparation:
            return {'error': f"Preparazione #{prep_id} non trovata"}
        
        # Logica riconciliazione singola
        # ...
    else:
        # Logica riconciliazione tutte
        # ...
    
    return {'status': 'ok', 'reconciled': 0, 'discrepancies': []}
```

#### 4.2 Rimuovi Deleghe Legacy

Dopo aver implementato tutti i metodi, **rimuovi** le deleghe al vecchio manager:

```python
# RIMUOVI queste righe:
def get_preparations(self, **kwargs) -> List[Dict]:
    """Delega al vecchio manager (TODO: migrare)."""
    return self._get_old_manager().get_preparations(**kwargs)
```

---

### Fase 5: Scrivere Test

#### 5.1 Crea `tests/test_models/test_{entity}.py`

Segui il pattern di `test_supplier.py`:

```python
"""
Test per {Entity} model e {Entity}Repository.
"""

import pytest
import sqlite3
from datetime import date
from decimal import Decimal
from peptide_manager.models.{entity} import {Entity}, {Entity}Repository


@pytest.fixture
def db_connection():
    """Crea database in-memory per test."""
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    
    # Crea schema
    conn.execute('''
        CREATE TABLE {table_name} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            campo_obbligatorio TEXT NOT NULL,
            foreign_key_id INTEGER NOT NULL,
            campo_opzionale TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (foreign_key_id) REFERENCES {fk_table}(id)
        )
    ''')
    
    # Crea tabelle dipendenti se necessario
    # ...
    
    yield conn
    conn.close()


class Test{Entity}Model:
    """Test per {Entity} dataclass."""
    
    def test_create_valid(self):
        """Test creazione valida."""
        entity = {Entity}(
            campo_obbligatorio="Test",
            foreign_key_id=1
        )
        assert entity.campo_obbligatorio == "Test"
        assert entity.foreign_key_id == 1
    
    def test_validation_empty_field(self):
        """Test validazione campo obbligatorio."""
        with pytest.raises(ValueError, match="obbligatorio"):
            {Entity}(campo_obbligatorio="")


class Test{Entity}Repository:
    """Test per {Entity}Repository."""
    
    def test_create(self, db_connection):
        """Test creazione elemento."""
        repo = {Entity}Repository(db_connection)
        
        entity = {Entity}(
            campo_obbligatorio="Test",
            foreign_key_id=1
        )
        
        entity_id = repo.create(entity)
        assert entity_id > 0
        
        # Verifica creato
        retrieved = repo.get_by_id(entity_id)
        assert retrieved is not None
        assert retrieved.campo_obbligatorio == "Test"
    
    def test_get_all(self, db_connection):
        """Test recupero lista."""
        repo = {Entity}Repository(db_connection)
        
        # Crea elementi di test
        # ...
        
        all_entities = repo.get_all()
        assert len(all_entities) >= 2
    
    def test_update(self, db_connection):
        """Test aggiornamento."""
        repo = {Entity}Repository(db_connection)
        
        # Crea elemento
        entity = {Entity}(campo_obbligatorio="Test", foreign_key_id=1)
        entity_id = repo.create(entity)
        
        # Aggiorna
        entity.id = entity_id
        entity.campo_obbligatorio = "Updated"
        success = repo.update(entity)
        
        assert success is True
        
        # Verifica aggiornato
        updated = repo.get_by_id(entity_id)
        assert updated.campo_obbligatorio == "Updated"
    
    def test_delete(self, db_connection):
        """Test eliminazione."""
        repo = {Entity}Repository(db_connection)
        
        # Crea elemento
        entity = {Entity}(campo_obbligatorio="Test", foreign_key_id=1)
        entity_id = repo.create(entity)
        
        # Elimina (soft delete)
        success, message = repo.delete(entity_id, force=False)
        
        assert success is True
        
        # Verifica eliminato (non visibile)
        deleted = repo.get_by_id(entity_id)
        assert deleted is None
        
        # Verifica ancora presente (con include_deleted)
        deleted = repo.get_by_id(entity_id, include_deleted=True)
        assert deleted is not None
        assert deleted.is_deleted() is True
```

#### 5.2 Esegui Test

```bash
pytest tests/test_models/test_{entity}.py -v
```

---

### Fase 6: Validazione e Cleanup

#### 6.1 Checklist Validazione

- [ ] **Model creato correttamente**
  - [ ] Dataclass estende `BaseModel`
  - [ ] Tutti i campi hanno type hints
  - [ ] `__post_init__` valida e converte dati
  - [ ] Metodi helper (es: `is_deleted()`, `is_expired()`) se necessari

- [ ] **Repository implementato**
  - [ ] Estende `Repository`
  - [ ] `get_all()` con filtri opzionali
  - [ ] `get_by_id()` funziona
  - [ ] `create()` valida e inserisce
  - [ ] `update()` aggiorna correttamente
  - [ ] `delete()` gestisce soft/hard delete
  - [ ] Metodi custom implementati

- [ ] **Export e DatabaseManager**
  - [ ] Aggiunto a `models/__init__.py`
  - [ ] Aggiunto a `database.py`
  - [ ] Repository inizializzato in `DatabaseManager.__init__()`

- [ ] **Adapter PeptideManager**
  - [ ] Tutti i metodi legacy sostituiti
  - [ ] Metodi restituiscono dict (compatibilità)
  - [ ] Gestione errori corretta
  - [ ] Deleghe legacy rimosse

- [ ] **Test scritti e passano**
  - [ ] Test model validazione
  - [ ] Test repository CRUD
  - [ ] Test edge cases
  - [ ] Test error conditions

- [ ] **Integrazione GUI/CLI**
  - [ ] GUI funziona con nuovo codice
  - [ ] CLI funziona con nuovo codice
  - [ ] Nessuna regressione

#### 6.2 Test Manuale

```python
# Test rapido in Python REPL
from peptide_manager import PeptideManager

manager = PeptideManager('test.db')

# Test creazione
prep_id = manager.add_preparation(
    batch_id=1,
    vials_used=2,
    volume_ml=10.0,
    preparation_date='2025-01-15'
)
print(f"Creata preparazione #{prep_id}")

# Test recupero
preparations = manager.get_preparations()
print(f"Trovate {len(preparations)} preparazioni")

# Test dettagli
details = manager.get_preparation_details(prep_id)
print(f"Dettagli: {details}")

manager.close()
```

#### 6.3 Rimuovi Codice Legacy (DOPO validazione completa)

**NON rimuovere subito!** Aspetta che tutto funzioni perfettamente.

Quando sei sicuro:
1. Rimuovi metodi da `models_legacy.py` (opzionale, puoi lasciarli)
2. Rimuovi import `_get_old_manager()` se non serve più
3. Aggiorna commenti in `peptide_manager/__init__.py`

---

## 📝 Pattern Comuni e Casi Speciali

### Pattern 1: Foreign Key Validation

```python
def create(self, entity: {Entity}) -> int:
    # Verifica FK esiste
    fk_query = 'SELECT id FROM {fk_table} WHERE id = ?'
    if not self._fetch_one(fk_query, (entity.foreign_key_id,)):
        raise ValueError(f"{FK} #{entity.foreign_key_id} non trovato")
    
    # Continua con INSERT...
```

### Pattern 2: Soft Delete

```python
def get_all(self, include_deleted: bool = False) -> List[{Entity}]:
    query = 'SELECT * FROM {table} WHERE 1=1'
    if not include_deleted:
        query += ' AND deleted_at IS NULL'
    # ...
```

### Pattern 3: Operazioni Multi-Tabella (Transazioni)

Se devi modificare più tabelle in una operazione:

```python
def create_with_side_effects(self, entity: {Entity}) -> int:
    """Crea entità e aggiorna tabelle correlate."""
    try:
        # 1. Inserisci entità principale
        cursor = self._execute(query1, params1)
        entity_id = cursor.lastrowid
        
        # 2. Aggiorna tabella correlata
        self._execute(query2, (entity_id, param2))
        
        # 3. Commit tutto insieme
        self._commit()
        return entity_id
    except Exception as e:
        # Rollback automatico se errore
        self.conn.rollback()
        raise
```

### Pattern 4: Metodi Custom con JOIN

```python
def get_with_related_info(self, entity_id: int) -> Optional[dict]:
    """Recupera entità con informazioni correlate (JOIN)."""
    query = '''
        SELECT 
            e.*,
            r.name as related_name,
            r.field as related_field
        FROM {table} e
        JOIN {related_table} r ON e.foreign_key_id = r.id
        WHERE e.id = ?
    '''
    row = self._fetch_one(query, (entity_id,))
    
    if not row:
        return None
    
    # Estrai dati entità principale
    entity_data = {k: v for k, v in dict(row).items() 
                   if k not in ['related_name', 'related_field']}
    entity = {Entity}.from_row(entity_data)
    
    # Costruisci risultato
    return {
        'entity': entity,
        'related_name': row['related_name'],
        'related_field': row['related_field']
    }
```

### Pattern 5: Conversioni Decimal/Date

```python
# In __post_init__
if isinstance(self.decimal_field, (int, float, str)):
    self.decimal_field = Decimal(str(self.decimal_field))

# In create/update (per INSERT/UPDATE SQL)
float(self.decimal_field) if self.decimal_field else None

# Date
if isinstance(self.date_field, str):
    self.date_field = date.fromisoformat(self.date_field)
```

---

## ⚠️ Errori Comuni da Evitare

1. **Dimenticare conversioni Decimal → float per SQL**
   ```python
   # ❌ SBAGLIATO
   cursor.execute(query, (entity.decimal_field,))
   
   # ✅ CORRETTO
   cursor.execute(query, (float(entity.decimal_field) if entity.decimal_field else None,))
   ```

2. **Non validare Foreign Keys**
   ```python
   # ❌ SBAGLIATO - assume FK esiste
   cursor.execute(insert_query, (entity.fk_id,))
   
   # ✅ CORRETTO - verifica prima
   if not self._fetch_one('SELECT id FROM fk_table WHERE id = ?', (entity.fk_id,)):
       raise ValueError(f"FK #{entity.fk_id} non trovato")
   ```

3. **Dimenticare commit dopo modifiche**
   ```python
   # ❌ SBAGLIATO
   self._execute(query, params)
   # Manca commit!
   
   # ✅ CORRETTO
   self._execute(query, params)
   self._commit()
   ```

4. **Non gestire soft delete nei filtri**
   ```python
   # ❌ SBAGLIATO - mostra anche eliminati
   query = 'SELECT * FROM table'
   
   # ✅ CORRETTO
   query = 'SELECT * FROM table WHERE deleted_at IS NULL'
   ```

5. **Dimenticare export in `__init__.py`**
   - Se non esporti, altri moduli non possono importare
   - Verifica sempre `models/__init__.py` e `database.py`

---

## 📊 Checklist Finale per Entità Migrata

Prima di considerare completata la migrazione:

- [ ] File `peptide_manager/models/{entity}.py` creato
- [ ] Model `{Entity}` con validazioni
- [ ] Repository `{Entity}Repository` con CRUD completo
- [ ] Export in `models/__init__.py`
- [ ] Repository in `database.py`
- [ ] Metodi adapter in `peptide_manager/__init__.py`
- [ ] Deleghe legacy rimosse
- [ ] Test scritti e passano
- [ ] Test manuale GUI/CLI funziona
- [ ] Nessuna regressione
- [ ] Documentazione aggiornata (opzionale)

---

## 🔗 Riferimenti

- **Esempio Supplier**: `peptide_manager/models/supplier.py`
- **Esempio Peptide**: `peptide_manager/models/peptide.py`
- **Esempio Batch**: `peptide_manager/models/batch.py`
- **Base Classes**: `peptide_manager/models/base.py`
- **Adapter Pattern**: `peptide_manager/__init__.py` (sezioni migrate)

---

## 💡 Suggerimenti

1. **Inizia semplice**: Implementa prima `get_all()`, `get_by_id()`, `create()`, poi aggiungi il resto
2. **Testa incrementale**: Dopo ogni metodo, testa che funzioni
3. **Usa esempi esistenti**: Copia pattern da `supplier.py` o `peptide.py`
4. **Verifica database**: Controlla sempre schema reale nel DB
5. **Mantieni compatibilità**: I metodi adapter devono restituire `List[Dict]` come prima

---

**Buona migrazione! 🚀**

