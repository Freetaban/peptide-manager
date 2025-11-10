"""
Batch model - gestisce inventario fiale di peptidi.
"""

from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal
from .base import BaseModel, Repository


@dataclass
class Batch(BaseModel):
    """Rappresenta un batch (fiala) di peptide acquistato."""
    supplier_id: int = None
    product_name: str = ""
    batch_number: str = ""  # Può essere vuoto per dati legacy
    manufacturing_date: Optional[date] = None
    expiration_date: Optional[date] = None
    mg_per_vial: Optional[Decimal] = None
    vials_count: int = 1
    vials_remaining: int = 1
    purchase_date: Optional[date] = None
    price_per_vial: Optional[Decimal] = None
    storage_location: Optional[str] = None
    notes: Optional[str] = None
    coa_path: Optional[str] = None  # Certificate of Analysis path
    deleted_at: Optional[datetime] = None  # Soft delete timestamp
    
    def __post_init__(self):
        """Validazione dopo inizializzazione."""
        # Validazioni base
        if self.supplier_id is None:
            raise ValueError("Fornitore obbligatorio")
        if not self.product_name or not self.product_name.strip():
            raise ValueError("Nome prodotto obbligatorio")
        # NOTA: batch_number può essere vuoto/None per dati legacy esistenti
        # Solo per nuovi batch è obbligatorio (validato in create())
        if self.vials_count is not None and self.vials_count < 1:
            raise ValueError("Numero fiale deve essere >= 1")
        if self.vials_remaining is not None and self.vials_remaining < 0:
            raise ValueError("Fiale rimanenti non possono essere negative")
        # NOTA: Non validare vials_remaining > vials_count perché adjust_vials 
        # può aggiungere fiale (correzione errori) e superare il count originale
        
        # Converti stringhe date in date objects se necessario
        if isinstance(self.manufacturing_date, str):
            self.manufacturing_date = date.fromisoformat(self.manufacturing_date)
        if isinstance(self.expiration_date, str):
            self.expiration_date = date.fromisoformat(self.expiration_date)
        if isinstance(self.purchase_date, str):
            self.purchase_date = date.fromisoformat(self.purchase_date)
        
        # Converti stringhe Decimal in Decimal objects se necessario
        if isinstance(self.mg_per_vial, (int, float, str)):
            self.mg_per_vial = Decimal(str(self.mg_per_vial))
        if isinstance(self.price_per_vial, (int, float, str)):
            self.price_per_vial = Decimal(str(self.price_per_vial))
    
    def is_deleted(self) -> bool:
        """Verifica se il batch è stato eliminato (soft delete)."""
        return self.deleted_at is not None
    
    def is_depleted(self) -> bool:
        """Verifica se il batch è esaurito."""
        return self.vials_remaining == 0
    
    def is_expired(self, reference_date: Optional[date] = None) -> bool:
        """
        Verifica se il batch è scaduto.
        
        Args:
            reference_date: Data di riferimento (default: oggi)
        """
        if self.expiration_date is None:
            return False
        
        ref = reference_date or date.today()
        return self.expiration_date < ref
    
    def days_until_expiration(self, reference_date: Optional[date] = None) -> Optional[int]:
        """
        Calcola giorni rimanenti alla scadenza.
        
        Args:
            reference_date: Data di riferimento (default: oggi)
            
        Returns:
            Giorni rimanenti (negativo se scaduto, None se nessuna scadenza)
        """
        if self.expiration_date is None:
            return None
        
        ref = reference_date or date.today()
        return (self.expiration_date - ref).days


class BatchRepository(Repository):
    """Repository per operazioni CRUD sui batches."""
    
    def get_all(
        self, 
        search: Optional[str] = None,
        supplier_id: Optional[int] = None,
        include_deleted: bool = False,
        only_available: bool = False,
        only_depleted: bool = False,
        only_expired: bool = False
    ) -> List[Batch]:
        """
        Recupera tutti i batches con filtri opzionali.
        
        Args:
            search: Filtro per nome prodotto o batch number
            supplier_id: Filtra per fornitore
            include_deleted: Include batches eliminati (soft delete)
            only_available: Solo batches con fiale disponibili
            only_depleted: Solo batches esauriti
            only_expired: Solo batches scaduti
            
        Returns:
            Lista di Batch
        """
        query = 'SELECT * FROM batches WHERE 1=1'
        params = []
        
        # Filtro soft delete
        if not include_deleted:
            query += ' AND deleted_at IS NULL'
        
        # Filtro ricerca
        if search:
            query += ' AND (product_name LIKE ? OR batch_number LIKE ?)'
            params.extend([f'%{search}%', f'%{search}%'])
        
        # Filtro fornitore
        if supplier_id:
            query += ' AND supplier_id = ?'
            params.append(supplier_id)
        
        # Filtro disponibilità
        if only_available:
            query += ' AND vials_remaining > 0'
        
        if only_depleted:
            query += ' AND vials_remaining = 0'
        
        # Filtro scadenza
        if only_expired:
            query += ' AND expiration_date < DATE("now")'
        
        query += ' ORDER BY product_name'
        
        rows = self._fetch_all(query, tuple(params))
        return [Batch.from_row(row) for row in rows]
    
    def get_by_id(self, batch_id: int, include_deleted: bool = False) -> Optional[Batch]:
        """
        Recupera un batch per ID.
        
        Args:
            batch_id: ID del batch
            include_deleted: Include anche se eliminato (soft delete)
            
        Returns:
            Batch o None se non trovato
        """
        query = 'SELECT * FROM batches WHERE id = ?'
        
        if not include_deleted:
            query += ' AND deleted_at IS NULL'
        
        row = self._fetch_one(query, (batch_id,))
        return Batch.from_row(row) if row else None
    
    def create(self, batch: Batch) -> int:
        """
        Crea un nuovo batch.
        
        Args:
            batch: Oggetto Batch da creare
            
        Returns:
            ID del batch creato
            
        Raises:
            ValueError: Se dati non validi
        """
        # Validazione per nuovi batch (più rigida che per dati legacy)
        if not batch.batch_number or not batch.batch_number.strip():
            raise ValueError("batch_number obbligatorio per nuovi batch")
        
        query = '''
            INSERT INTO batches (
                supplier_id, product_name, batch_number,
                manufacturing_date, expiration_date, mg_per_vial,
                vials_count, vials_remaining, purchase_date,
                price_per_vial, storage_location, notes, coa_path
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''
        cursor = self._execute(query, (
            batch.supplier_id,
            batch.product_name,
            batch.batch_number,
            batch.manufacturing_date,
            batch.expiration_date,
            float(batch.mg_per_vial) if batch.mg_per_vial else None,
            batch.vials_count,
            batch.vials_remaining,
            batch.purchase_date,
            float(batch.price_per_vial) if batch.price_per_vial else None,
            batch.storage_location,
            batch.notes,
            batch.coa_path
        ))
        
        self._commit()
        return cursor.lastrowid
    
    def update(self, batch: Batch) -> bool:
        """
        Aggiorna un batch esistente.
        
        Args:
            batch: Oggetto Batch con dati aggiornati (deve avere id)
            
        Returns:
            True se aggiornato
            
        Raises:
            ValueError: Se id non specificato o dati non validi
        """
        if batch.id is None:
            raise ValueError("ID batch necessario per update")
        
        # Validazione (già fatta in __post_init__)
        
        query = '''
            UPDATE batches 
            SET supplier_id = ?, product_name = ?, batch_number = ?,
                manufacturing_date = ?, expiration_date = ?, mg_per_vial = ?,
                vials_count = ?, vials_remaining = ?, purchase_date = ?,
                price_per_vial = ?, storage_location = ?, notes = ?, coa_path = ?
            WHERE id = ?
        '''
        self._execute(query, (
            batch.supplier_id,
            batch.product_name,
            batch.batch_number,
            batch.manufacturing_date,
            batch.expiration_date,
            float(batch.mg_per_vial) if batch.mg_per_vial else None,
            batch.vials_count,
            batch.vials_remaining,
            batch.purchase_date,
            float(batch.price_per_vial) if batch.price_per_vial else None,
            batch.storage_location,
            batch.notes,
            batch.coa_path,
            batch.id
        ))
        
        self._commit()
        return True
    
    def delete(self, batch_id: int, force: bool = False) -> tuple[bool, str]:
        """
        Elimina un batch (soft delete di default).
        
        Args:
            batch_id: ID del batch da eliminare
            force: Se True, elimina fisicamente (hard delete)
            
        Returns:
            (success: bool, message: str)
        """
        # Verifica esistenza
        batch = self.get_by_id(batch_id, include_deleted=True)
        if not batch:
            return False, f"Batch #{batch_id} non trovato"
        
        if batch.is_deleted() and not force:
            return False, f"Batch '{batch.product_name}' già eliminato"
        
        # Controlla preparazioni collegate
        query = 'SELECT COUNT(*) FROM preparations WHERE batch_id = ?'
        row = self._fetch_one(query, (batch_id,))
        prep_count = row[0] if row else 0
        
        if prep_count > 0 and not force:
            return False, (
                f"Impossibile eliminare batch '{batch.product_name}': "
                f"ha {prep_count} preparazione(i) collegata(e). "
                f"Usa force=True per eliminazione forzata."
            )
        
        if force:
            # Hard delete - elimina fisicamente
            query = 'DELETE FROM batches WHERE id = ?'
            self._execute(query, (batch_id,))
            self._commit()
            return True, f"Batch '{batch.product_name}' eliminato definitivamente"
        else:
            # Soft delete - marca come eliminato
            query = 'UPDATE batches SET deleted_at = CURRENT_TIMESTAMP WHERE id = ?'
            self._execute(query, (batch_id,))
            self._commit()
            return True, f"Batch '{batch.product_name}' archiviato (soft delete)"
    
    def restore(self, batch_id: int) -> tuple[bool, str]:
        """
        Ripristina un batch eliminato (soft delete).
        
        Args:
            batch_id: ID del batch da ripristinare
            
        Returns:
            (success: bool, message: str)
        """
        # Verifica esistenza (include deleted)
        batch = self.get_by_id(batch_id, include_deleted=True)
        if not batch:
            return False, f"Batch #{batch_id} non trovato"
        
        if not batch.is_deleted():
            return False, f"Batch '{batch.product_name}' non è eliminato"
        
        # Ripristina
        query = 'UPDATE batches SET deleted_at = NULL WHERE id = ?'
        self._execute(query, (batch_id,))
        self._commit()
        
        return True, f"Batch '{batch.product_name}' ripristinato"
    
    def adjust_vials(
        self, 
        batch_id: int, 
        adjustment: int, 
        reason: Optional[str] = None
    ) -> tuple[bool, str]:
        """
        Corregge il conteggio fiale (positivo o negativo).
        
        Args:
            batch_id: ID del batch
            adjustment: Numero fiale da aggiungere (+) o rimuovere (-)
            reason: Motivo della correzione (opzionale)
            
        Returns:
            (success: bool, message: str)
        """
        batch = self.get_by_id(batch_id)
        if not batch:
            return False, f"Batch #{batch_id} non trovato"
        
        new_vials = batch.vials_remaining + adjustment
        
        # Validazione
        if new_vials < 0:
            return False, f"Impossibile: fiale diventerebbero negative ({new_vials})"
        
        # Aggiorna
        query = 'UPDATE batches SET vials_remaining = ? WHERE id = ?'
        self._execute(query, (new_vials, batch_id))
        self._commit()
        
        action = "aggiunte" if adjustment > 0 else "rimosse"
        message = (
            f"Batch #{batch_id} '{batch.product_name}': "
            f"Fiale {action}: {abs(adjustment)} "
            f"({batch.vials_remaining} → {new_vials})"
        )
        
        if reason:
            message += f" - Motivo: {reason}"
        
        return True, message
    
    def get_expiring_soon(self, days: int = 30) -> List[Batch]:
        """
        Recupera batches in scadenza entro N giorni.
        
        Args:
            days: Giorni di anticipo (default: 30)
            
        Returns:
            Lista di Batch in scadenza
        """
        query = '''
            SELECT * FROM batches 
            WHERE deleted_at IS NULL
              AND vials_remaining > 0
              AND expiration_date IS NOT NULL
              AND expiration_date <= DATE('now', '+' || ? || ' days')
            ORDER BY expiration_date
        '''
        rows = self._fetch_all(query, (days,))
        return [Batch.from_row(row) for row in rows]
    
    def get_inventory_summary(self) -> dict:
        """
        Calcola statistiche inventario batches.
        
        Returns:
            Dict con statistiche
        """
        query = '''
            SELECT 
                COUNT(*) as total_batches,
                SUM(CASE WHEN vials_remaining > 0 THEN 1 ELSE 0 END) as available_batches,
                SUM(CASE WHEN vials_remaining = 0 THEN 1 ELSE 0 END) as depleted_batches,
                SUM(vials_remaining) as total_vials_remaining,
                SUM(CASE WHEN expiration_date < DATE('now') AND vials_remaining > 0 
                    THEN 1 ELSE 0 END) as expired_batches
            FROM batches
            WHERE deleted_at IS NULL
        '''
        row = self._fetch_one(query)
        
        if not row:
            return {
                'total_batches': 0,
                'available_batches': 0,
                'depleted_batches': 0,
                'total_vials_remaining': 0,
                'expired_batches': 0
            }
        
        return {
            'total_batches': row[0] or 0,
            'available_batches': row[1] or 0,
            'depleted_batches': row[2] or 0,
            'total_vials_remaining': row[3] or 0,
            'expired_batches': row[4] or 0
        }
    
    def count(self, include_deleted: bool = False) -> int:
        """Conta i batches totali."""
        query = 'SELECT COUNT(*) FROM batches'
        if not include_deleted:
            query += ' WHERE deleted_at IS NULL'
        
        row = self._fetch_one(query)
        return row[0] if row else 0
