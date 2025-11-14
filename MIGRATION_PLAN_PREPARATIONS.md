# 📋 Piano Migrazione: Preparations Module

## 🎯 Obiettivo

Migrare il modulo **Preparations** da `models_legacy.py` alla nuova architettura modulare.

---

## 📊 Analisi Modulo Attuale

### Tabella Database:
```sql
CREATE TABLE preparations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id INTEGER NOT NULL,
    vials_used INTEGER NOT NULL,
    volume_ml REAL NOT NULL,
    diluent TEXT NOT NULL DEFAULT 'BAC Water',
    preparation_date DATE NOT NULL,
    expiry_date DATE,
    volume_remaining_ml REAL NOT NULL,
    storage_location TEXT,
    notes TEXT,
    deleted_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (batch_id) REFERENCES batches(id) ON DELETE CASCADE
);
```

### Metodi Esistenti in `models_legacy.py`:
- `add_preparation()` ✅ Usa fiale dal batch
- `get_preparations()` ✅ Filtri: batch_id, only_active
- `get_preparation_details()` ✅ Include peptidi e concentrazione
- `use_preparation()` ✅ Registra somministrazione
- `update_preparation()` ✅ Modifica campi
- `delete_preparation()` ⚠️ Con opzione restore_vials
- `get_expired_preparations()` ✅ Scadute
- `_recalculate_preparation_volume()` 🔧 Riconciliazione
- `reconcile_preparation_volumes()` 🔧 Batch riconciliazione

---

## 🏗️ Struttura Nuova Architettura

### File: `peptide_manager/models/preparation.py`

```python
from dataclasses import dataclass
from typing import Optional
from datetime import date, datetime
from decimal import Decimal
from .base import BaseModel, Repository

@dataclass
class Preparation(BaseModel):
    """Rappresenta una preparazione (ricostituzione) da un batch."""
    batch_id: int
    vials_used: int
    volume_ml: Decimal
    diluent: str = 'BAC Water'
    preparation_date: date = None
    expiry_date: Optional[date] = None
    volume_remaining_ml: Decimal = None
    storage_location: Optional[str] = None
    notes: Optional[str] = None
    deleted_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Validazione e conversioni."""
        # Validazioni
        if self.batch_id is None:
            raise ValueError("Batch ID obbligatorio")
        if self.vials_used < 1:
            raise ValueError("Vials used deve essere >= 1")
        if self.volume_ml <= 0:
            raise ValueError("Volume deve essere > 0")
        
        # Conversioni Decimal
        if isinstance(self.volume_ml, (int, float, str)):
            self.volume_ml = Decimal(str(self.volume_ml))
        if self.volume_remaining_ml and isinstance(self.volume_remaining_ml, (int, float, str)):
            self.volume_remaining_ml = Decimal(str(self.volume_remaining_ml))
        
        # Default: volume_remaining = volume_ml se non specificato
        if self.volume_remaining_ml is None:
            self.volume_remaining_ml = self.volume_ml
        
        # Conversioni date
        if isinstance(self.preparation_date, str):
            self.preparation_date = date.fromisoformat(self.preparation_date)
        if isinstance(self.expiry_date, str):
            self.expiry_date = date.fromisoformat(self.expiry_date)
    
    def is_deleted(self) -> bool:
        """Verifica se eliminato (soft delete)."""
        return self.deleted_at is not None
    
    def is_depleted(self) -> bool:
        """Verifica se esaurito."""
        return self.volume_remaining_ml <= 0
    
    def is_expired(self) -> bool:
        """Verifica se scaduto."""
        if not self.expiry_date:
            return False
        return self.expiry_date < date.today()
    
    def calculate_concentration_mg_ml(self, batch_mg_per_vial: Decimal) -> Decimal:
        """
        Calcola concentrazione in mg/ml.
        
        Args:
            batch_mg_per_vial: mg per fiala del batch
        
        Returns:
            Concentrazione in mg/ml
        """
        total_mg = batch_mg_per_vial * self.vials_used
        return total_mg / self.volume_ml


class PreparationRepository(Repository):
    """Repository per operazioni CRUD sulle preparazioni."""
    
    def get_all(
        self,
        batch_id: Optional[int] = None,
        only_active: bool = False,
        include_deleted: bool = False
    ) -> List['Preparation']:
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
    
    def get_by_id(
        self, 
        prep_id: int, 
        include_deleted: bool = False
    ) -> Optional['Preparation']:
        """Recupera preparazione per ID."""
        query = 'SELECT * FROM preparations WHERE id = ?'
        
        if not include_deleted:
            query += ' AND deleted_at IS NULL'
        
        row = self._fetch_one(query, (prep_id,))
        return Preparation.from_row(row) if row else None
    
    def create(self, preparation: 'Preparation') -> int:
        """
        Crea nuova preparazione e decrementa fiale dal batch.
        
        Returns:
            ID della preparazione creata
        """
        # Validazione esistenza batch
        query = 'SELECT id, vials_remaining FROM batches WHERE id = ? AND deleted_at IS NULL'
        batch_row = self._fetch_one(query, (preparation.batch_id,))
        
        if not batch_row:
            raise ValueError(f"Batch #{preparation.batch_id} non trovato")
        
        vials_available = batch_row[1]
        if vials_available < preparation.vials_used:
            raise ValueError(
                f"Fiale insufficienti: disponibili {vials_available}, "
                f"richieste {preparation.vials_used}"
            )
        
        # Inserisci preparazione
        query = '''
            INSERT INTO preparations (
                batch_id, vials_used, volume_ml, diluent,
                preparation_date, expiry_date, volume_remaining_ml,
                storage_location, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''
        cursor = self._execute(query, (
            preparation.batch_id,
            preparation.vials_used,
            float(preparation.volume_ml),
            preparation.diluent,
            preparation.preparation_date,
            preparation.expiry_date,
            float(preparation.volume_remaining_ml),
            preparation.storage_location,
            preparation.notes
        ))
        
        prep_id = cursor.lastrowid
        
        # Decrementa fiale dal batch
        query = '''
            UPDATE batches 
            SET vials_remaining = vials_remaining - ?
            WHERE id = ?
        '''
        self._execute(query, (preparation.vials_used, preparation.batch_id))
        
        self._commit()
        return prep_id
    
    def update(self, preparation: 'Preparation') -> bool:
        """Aggiorna preparazione esistente."""
        if preparation.id is None:
            raise ValueError("ID preparazione necessario per update")
        
        query = '''
            UPDATE preparations 
            SET batch_id = ?, vials_used = ?, volume_ml = ?, diluent = ?,
                preparation_date = ?, expiry_date = ?, volume_remaining_ml = ?,
                storage_location = ?, notes = ?
            WHERE id = ?
        '''
        self._execute(query, (
            preparation.batch_id,
            preparation.vials_used,
            float(preparation.volume_ml),
            preparation.diluent,
            preparation.preparation_date,
            preparation.expiry_date,
            float(preparation.volume_remaining_ml),
            preparation.storage_location,
            preparation.notes,
            preparation.id
        ))
        
        self._commit()
        return True
    
    def delete(
        self, 
        prep_id: int, 
        restore_vials: bool = False,
        force: bool = False
    ) -> tuple[bool, str]:
        """
        Elimina preparazione (soft delete di default).
        
        Args:
            prep_id: ID preparazione
            restore_vials: Se True, riaggiunge fiale al batch
            force: Se True, elimina fisicamente (hard delete)
        
        Returns:
            (success: bool, message: str)
        """
        prep = self.get_by_id(prep_id, include_deleted=True)
        if not prep:
            return False, f"Preparazione #{prep_id} non trovata"
        
        if prep.is_deleted() and not force:
            return False, "Preparazione già eliminata"
        
        # Controlla somministrazioni
        query = '''
            SELECT COUNT(*) FROM administrations 
            WHERE preparation_id = ? AND deleted_at IS NULL
        '''
        row = self._fetch_one(query, (prep_id,))
        admin_count = row[0] if row else 0
        
        if admin_count > 0 and not force:
            return False, (
                f"Impossibile eliminare: ha {admin_count} somministrazioni. "
                f"Elimina prima le somministrazioni o usa force=True"
            )
        
        # Ripristina fiale se richiesto
        if restore_vials:
            query = '''
                UPDATE batches 
                SET vials_remaining = vials_remaining + ?
                WHERE id = ?
            '''
            self._execute(query, (prep.vials_used, prep.batch_id))
        
        if force:
            # Hard delete
            query = 'DELETE FROM preparations WHERE id = ?'
            self._execute(query, (prep_id,))
            self._commit()
            return True, "Preparazione eliminata definitivamente"
        else:
            # Soft delete
            query = 'UPDATE preparations SET deleted_at = CURRENT_TIMESTAMP WHERE id = ?'
            self._execute(query, (prep_id,))
            self._commit()
            return True, "Preparazione archiviata (soft delete)"
    
    def restore(self, prep_id: int) -> tuple[bool, str]:
        """Ripristina preparazione eliminata."""
        prep = self.get_by_id(prep_id, include_deleted=True)
        if not prep:
            return False, f"Preparazione #{prep_id} non trovata"
        
        if not prep.is_deleted():
            return False, "Preparazione non è eliminata"
        
        query = 'UPDATE preparations SET deleted_at = NULL WHERE id = ?'
        self._execute(query, (prep_id,))
        self._commit()
        
        return True, "Preparazione ripristinata"
    
    def use_volume(
        self, 
        prep_id: int, 
        ml_used: Decimal
    ) -> bool:
        """
        Decrementa volume usato.
        
        Args:
            prep_id: ID preparazione
            ml_used: Volume in ml da sottrarre
        
        Returns:
            True se successo
        """
        prep = self.get_by_id(prep_id)
        if not prep:
            raise ValueError(f"Preparazione #{prep_id} non trovata")
        
        if prep.volume_remaining_ml < ml_used:
            raise ValueError(
                f"Volume insufficiente: disponibile {prep.volume_remaining_ml}ml, "
                f"richiesto {ml_used}ml"
            )
        
        query = '''
            UPDATE preparations 
            SET volume_remaining_ml = volume_remaining_ml - ?
            WHERE id = ?
        '''
        self._execute(query, (float(ml_used), prep_id))
        self._commit()
        
        return True
    
    def recalculate_volume(self, prep_id: int) -> tuple[bool, str]:
        """
        Ricalcola volume basandosi su somministrazioni attive.
        
        Returns:
            (success: bool, message: str)
        """
        prep = self.get_by_id(prep_id)
        if not prep:
            return False, f"Preparazione #{prep_id} non trovata"
        
        # Somma dosi somministrazioni attive
        query = '''
            SELECT COALESCE(SUM(dose_ml), 0)
            FROM administrations
            WHERE preparation_id = ? AND deleted_at IS NULL
        '''
        row = self._fetch_one(query, (prep_id,))
        total_used = Decimal(str(row[0]))
        
        # Calcola volume corretto
        volume_correct = prep.volume_ml - total_used
        
        # Aggiorna
        query = '''
            UPDATE preparations
            SET volume_remaining_ml = ?
            WHERE id = ?
        '''
        self._execute(query, (float(volume_correct), prep_id))
        self._commit()
        
        message = (
            f"Prep #{prep_id}: Volume ricalcolato = {volume_correct:.2f}ml "
            f"(iniziale: {prep.volume_ml:.2f}ml, usato: {total_used:.2f}ml)"
        )
        
        return True, message
    
    def get_expired(self) -> List['Preparation']:
        """Recupera preparazioni scadute con volume residuo."""
        query = '''
            SELECT * FROM preparations
            WHERE deleted_at IS NULL
              AND expiry_date IS NOT NULL
              AND expiry_date < DATE('now')
              AND volume_remaining_ml > 0
            ORDER BY expiry_date
        '''
        rows = self._fetch_all(query)
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

## 🧪 Test da Scrivere

### File: `tests/test_models/test_preparation.py`

Test minimi necessari:
1. ✅ `test_preparation_creation()` - Creazione valida
2. ✅ `test_preparation_requires_batch()` - Validazione batch_id
3. ✅ `test_preparation_validates_vials()` - Validazione vials_used
4. ✅ `test_preparation_validates_volume()` - Validazione volume
5. ✅ `test_is_deleted()` - Metodo helper
6. ✅ `test_is_depleted()` - Metodo helper
7. ✅ `test_is_expired()` - Metodo helper
8. ✅ `test_calculate_concentration()` - Calcolo concentrazione
9. ✅ `test_create_preparation()` - Repository create
10. ✅ `test_create_decrements_batch_vials()` - Verifica decremento fiale
11. ✅ `test_get_by_id()` - Recupero per ID
12. ✅ `test_get_all()` - Recupero tutti
13. ✅ `test_get_all_filters()` - Filtri (batch_id, only_active)
14. ✅ `test_update_preparation()` - Aggiornamento
15. ✅ `test_soft_delete()` - Soft delete
16. ✅ `test_restore()` - Ripristino
17. ✅ `test_use_volume()` - Uso volume
18. ✅ `test_recalculate_volume()` - Riconciliazione
19. ✅ `test_get_expired()` - Preparazioni scadute
20. ✅ `test_count()` - Conteggio

---

## 🔗 Integrazione con Adapter

### Modifiche a `peptide_manager/__init__.py`:

```python
from .models import (
    # ... existing imports
    Preparation,
    PreparationRepository,
)

class PeptideManager:
    # ...
    
    # ==================== PREPARATIONS (MIGRATO ✅) ====================
    
    def get_preparations(
        self,
        batch_id: int = None,
        only_active: bool = False
    ) -> List[Dict]:
        """Recupera preparazioni (usa nuova architettura)."""
        preps = self.db.preparations.get_all(
            batch_id=batch_id,
            only_active=only_active
        )
        
        # Converti in dict per retrocompatibilità GUI
        result = []
        for prep in preps:
            prep_dict = prep.to_dict()
            
            # Aggiungi info batch (JOIN)
            batch = self.db.batches.get_by_id(prep.batch_id)
            if batch:
                prep_dict['batch_product'] = batch.product_name
            
            result.append(prep_dict)
        
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
        """Crea nuova preparazione (usa nuova architettura)."""
        prep = Preparation(
            batch_id=batch_id,
            vials_used=vials_used,
            volume_ml=volume_ml,
            preparation_date=preparation_date,
            diluent=diluent,
            expiry_date=expiry_date,
            storage_location=storage_location,
            notes=notes
        )
        
        prep_id = self.db.preparations.create(prep)
        print(f"✅ Preparazione #{prep_id} creata")
        return prep_id
    
    def update_preparation(self, prep_id: int, **kwargs) -> bool:
        """Aggiorna preparazione (usa nuova architettura)."""
        prep = self.db.preparations.get_by_id(prep_id)
        if not prep:
            print(f"❌ Preparazione #{prep_id} non trovata")
            return False
        
        # Aggiorna campi
        allowed_fields = [
            'batch_id', 'vials_used', 'volume_ml', 'diluent',
            'preparation_date', 'expiry_date', 'volume_remaining_ml',
            'storage_location', 'notes'
        ]
        
        for key, value in kwargs.items():
            if key in allowed_fields:
                setattr(prep, key, value)
        
        try:
            self.db.preparations.update(prep)
            print(f"✅ Preparazione #{prep_id} aggiornata")
            return True
        except ValueError as e:
            print(f"❌ Errore: {e}")
            return False
    
    def soft_delete_preparation(self, prep_id: int) -> bool:
        """Elimina preparazione (usa nuova architettura)."""
        success, message = self.db.preparations.delete(prep_id, force=False)
        
        if success:
            print(f"✓ {message}")
        else:
            print(f"❌ {message}")
        
        return success
    
    def get_preparation_details(self, prep_id: int) -> Optional[Dict]:
        """Recupera dettagli preparazione completi."""
        prep = self.db.preparations.get_by_id(prep_id)
        if not prep:
            return None
        
        result = prep.to_dict()
        
        # Batch info
        batch = self.db.batches.get_by_id(prep.batch_id)
        if batch:
            result['product_name'] = batch.product_name
            result['mg_per_vial'] = float(batch.mg_per_vial)
            
            # Peptidi
            peptides = self.db.batch_composition.get_peptides_in_batch(batch.id)
            result['peptides'] = peptides
            
            # Concentrazione
            result['concentration_mg_ml'] = float(
                prep.calculate_concentration_mg_ml(batch.mg_per_vial)
            )
        
        # Somministrazioni
        query = '''
            SELECT COUNT(*), SUM(dose_ml)
            FROM administrations
            WHERE preparation_id = ? AND deleted_at IS NULL
        '''
        cursor = self.conn.cursor()
        cursor.execute(query, (prep_id,))
        admin_count, ml_used = cursor.fetchone()
        
        result['administrations_count'] = admin_count or 0
        result['ml_used'] = float(ml_used) if ml_used else 0.0
        
        return result
    
    def use_preparation(
        self,
        prep_id: int,
        ml_used: float,
        administration_datetime: str = None,
        injection_site: str = None,
        injection_method: str = 'SubQ',
        notes: str = None,
        protocol_id: int = None
    ) -> bool:
        """
        Usa preparazione e registra somministrazione.
        
        NOTA: Questo metodo usa ancora il vecchio manager per 
        registrare la somministrazione (modulo Administrations non ancora migrato).
        """
        # Usa volume (nuova architettura)
        try:
            self.db.preparations.use_volume(prep_id, ml_used)
        except ValueError as e:
            print(f"❌ {e}")
            return False
        
        # Registra somministrazione (vecchio manager - TODO: migrare)
        # Delega temporaneamente al vecchio manager
        return self._get_old_manager().use_preparation(
            prep_id=prep_id,
            ml_used=ml_used,
            administration_datetime=administration_datetime,
            injection_site=injection_site,
            injection_method=injection_method,
            notes=notes,
            protocol_id=protocol_id
        )
    
    def reconcile_preparation_volumes(self, prep_id: int = None) -> Dict:
        """Riconcilia volumi preparazioni (usa nuova architettura)."""
        stats = {
            'checked': 0,
            'fixed': 0,
            'total_diff': 0.0,
            'details': []
        }
        
        # Determina preparazioni da riconciliare
        if prep_id:
            preps = [self.db.preparations.get_by_id(prep_id)]
        else:
            preps = self.db.preparations.get_all()
        
        for prep in preps:
            if not prep:
                continue
            
            stats['checked'] += 1
            
            # Ricalcola
            success, message = self.db.preparations.recalculate_volume(prep.id)
            
            if 'ricalcolato' in message.lower():
                stats['fixed'] += 1
                # Parse differenza dal messaggio (opzionale)
                # ...
        
        return stats
```

---

## ✅ Checklist Migrazione

- [ ] Creare `peptide_manager/models/preparation.py`
- [ ] Aggiungere import in `peptide_manager/models/__init__.py`
- [ ] Aggiornare `peptide_manager/database.py` (aggiungere `self.preparations`)
- [ ] Scrivere test in `tests/test_models/test_preparation.py`
- [ ] Eseguire test: `python -m pytest tests/test_models/test_preparation.py -v`
- [ ] Aggiornare adapter in `peptide_manager/__init__.py`
- [ ] Test integrazione con GUI: `python gui.py --env development`
- [ ] Commit: `git commit -m "refactor: migrate Preparations to modular architecture"`

---

## 🎯 Tempo Stimato

- Creazione model: **1 ora**
- Scrittura test: **1 ora**
- Integrazione adapter: **30 min**
- Test e debug: **1 ora**

**Totale: ~3.5 ore**

---

## 📝 Note Importanti

⚠️ **Dipendenza Circolare**: Il metodo `use_preparation()` registra somministrazioni, ma il modulo **Administrations** non è ancora migrato. 

**Soluzione temporanea**: Delegare solo la parte `administrations` al vecchio manager, mentre la parte `preparations` usa la nuova architettura.

**Soluzione definitiva**: Migrare anche **Administrations** (priorità 2).
