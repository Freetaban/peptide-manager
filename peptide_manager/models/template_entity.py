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
