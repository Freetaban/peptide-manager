"""
Supplier model - gestisce fornitori di peptidi.
"""

from dataclasses import dataclass
from typing import Optional, List
from .base import BaseModel, Repository


@dataclass
class Supplier(BaseModel):
    """Rappresenta un fornitore di peptidi."""
    name: str = ""
    country: Optional[str] = None
    website: Optional[str] = None
    email: Optional[str] = None
    notes: Optional[str] = None
    reliability_rating: Optional[int] = None
    
    def __post_init__(self):
        """Validazione dopo inizializzazione."""
        if self.reliability_rating is not None:
            if not 1 <= self.reliability_rating <= 5:
                raise ValueError("Rating deve essere tra 1 e 5")


class SupplierRepository(Repository):
    """Repository per operazioni CRUD sui fornitori."""
    
    def get_all(self, search: Optional[str] = None) -> List[Supplier]:
        """
        Recupera tutti i fornitori.
        
        Args:
            search: Filtro opzionale per nome o paese
            
        Returns:
            Lista di Supplier
        """
        if search:
            query = '''
                SELECT * FROM suppliers 
                WHERE name LIKE ? OR country LIKE ?
                ORDER BY name
            '''
            rows = self._fetch_all(query, (f'%{search}%', f'%{search}%'))
        else:
            query = 'SELECT * FROM suppliers ORDER BY name'
            rows = self._fetch_all(query)
        
        return [Supplier.from_row(row) for row in rows]
    
    def get_by_id(self, supplier_id: int) -> Optional[Supplier]:
        """
        Recupera un fornitore per ID.
        
        Args:
            supplier_id: ID del fornitore
            
        Returns:
            Supplier o None se non trovato
        """
        query = 'SELECT * FROM suppliers WHERE id = ?'
        row = self._fetch_one(query, (supplier_id,))
        return Supplier.from_row(row) if row else None
    
    def create(self, supplier: Supplier) -> int:
        """
        Crea un nuovo fornitore.
        
        Args:
            supplier: Oggetto Supplier da creare
            
        Returns:
            ID del fornitore creato
            
        Raises:
            ValueError: Se nome è vuoto o rating non valido
        """
        # Validazione
        if not supplier.name or not supplier.name.strip():
            raise ValueError("Nome fornitore obbligatorio")
        
        if supplier.reliability_rating is not None:
            if not 1 <= supplier.reliability_rating <= 5:
                raise ValueError("Rating deve essere tra 1 e 5")
        
        query = '''
            INSERT INTO suppliers (name, country, website, email, notes, reliability_rating)
            VALUES (?, ?, ?, ?, ?, ?)
        '''
        cursor = self._execute(query, (
            supplier.name,
            supplier.country,
            supplier.website,
            supplier.email,
            supplier.notes,
            supplier.reliability_rating
        ))
        
        self._commit()
        return cursor.lastrowid
    
    def update(self, supplier: Supplier) -> bool:
        """
        Aggiorna un fornitore esistente.
        
        Args:
            supplier: Oggetto Supplier con dati aggiornati (deve avere id)
            
        Returns:
            True se aggiornato, False altrimenti
            
        Raises:
            ValueError: Se id non specificato o dati non validi
        """
        if supplier.id is None:
            raise ValueError("ID fornitore necessario per update")
        
        if not supplier.name or not supplier.name.strip():
            raise ValueError("Nome fornitore obbligatorio")
        
        if supplier.reliability_rating is not None:
            if not 1 <= supplier.reliability_rating <= 5:
                raise ValueError("Rating deve essere tra 1 e 5")
        
        query = '''
            UPDATE suppliers 
            SET name = ?, country = ?, website = ?, email = ?, 
                notes = ?, reliability_rating = ?
            WHERE id = ?
        '''
        self._execute(query, (
            supplier.name,
            supplier.country,
            supplier.website,
            supplier.email,
            supplier.notes,
            supplier.reliability_rating,
            supplier.id
        ))
        
        self._commit()
        return True
    
    def delete(self, supplier_id: int, force: bool = False) -> tuple[bool, str]:
        """
        Elimina un fornitore.
        
        Args:
            supplier_id: ID del fornitore da eliminare
            force: Se True, elimina anche se ci sono batches associati
            
        Returns:
            (success: bool, message: str)
        """
        # Verifica esistenza
        supplier = self.get_by_id(supplier_id)
        if not supplier:
            return False, f"Fornitore #{supplier_id} non trovato"
        
        # Controlla batches associati
        query = 'SELECT COUNT(*) FROM batches WHERE supplier_id = ?'
        row = self._fetch_one(query, (supplier_id,))
        batch_count = row[0] if row else 0
        
        if batch_count > 0 and not force:
            return False, (
                f"Impossibile eliminare '{supplier.name}': "
                f"ha {batch_count} batch(es) associati. "
                f"Usa force=True per forzare l'eliminazione."
            )
        
        # Elimina
        query = 'DELETE FROM suppliers WHERE id = ?'
        self._execute(query, (supplier_id,))
        self._commit()
        
        return True, f"Fornitore '{supplier.name}' eliminato"
    
    def count(self) -> int:
        """Conta i fornitori totali."""
        query = 'SELECT COUNT(*) FROM suppliers'
        row = self._fetch_one(query)
        return row[0] if row else 0
    
    def get_with_batch_count(self) -> List[dict]:
        """
        Recupera fornitori con conteggio batches.
        
        Returns:
            Lista di dict con campi supplier + batch_count
        """
        query = '''
            SELECT s.*, COUNT(b.id) as batch_count
            FROM suppliers s
            LEFT JOIN batches b ON s.id = b.supplier_id
            GROUP BY s.id
            ORDER BY s.name
        '''
        rows = self._fetch_all(query)
        
        result = []
        for row in rows:
            data = dict(row)
            batch_count = data.pop('batch_count', 0)
            supplier = Supplier.from_row(data)
            result.append({
                'supplier': supplier,
                'batch_count': batch_count
            })
        
        return result
