"""
Modulo Preparations - Gestione preparazioni (ricostituzioni).

Una preparazione rappresenta la ricostituzione di una o più fiale da un batch
con un diluente (es. BAC Water) per creare una soluzione pronta all'uso.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple
from datetime import date, datetime
from decimal import Decimal

from .base import BaseModel, Repository


@dataclass
class Preparation(BaseModel):
    """Rappresenta una preparazione (ricostituzione) da un batch."""
    
    # Campi obbligatori - usiamo field() per evitare conflitto con BaseModel
    batch_id: int = field(default=None)
    vials_used: int = field(default=None)
    volume_ml: Decimal = field(default=None)
    
    # Campi opzionali
    diluent: str = 'BAC Water'
    preparation_date: Optional[date] = None
    expiry_date: Optional[date] = None
    volume_remaining_ml: Optional[Decimal] = None
    storage_location: Optional[str] = None
    notes: Optional[str] = None
    deleted_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Validazione e conversioni dopo inizializzazione."""
        # Validazioni base
        if self.batch_id is None:
            raise ValueError("Batch ID obbligatorio")
        if self.vials_used < 1:
            raise ValueError("Vials used deve essere >= 1")
        if self.volume_ml <= 0:
            raise ValueError("Volume deve essere > 0")
        
        # Conversioni Decimal
        if isinstance(self.volume_ml, (int, float, str)):
            self.volume_ml = Decimal(str(self.volume_ml))
        
        if self.volume_remaining_ml is not None:
            if isinstance(self.volume_remaining_ml, (int, float, str)):
                self.volume_remaining_ml = Decimal(str(self.volume_remaining_ml))
        else:
            # Default: volume_remaining = volume_ml se non specificato
            self.volume_remaining_ml = self.volume_ml
        
        # Conversioni date
        if self.preparation_date is None:
            self.preparation_date = date.today()
        elif isinstance(self.preparation_date, str):
            self.preparation_date = date.fromisoformat(self.preparation_date)
        
        if self.expiry_date and isinstance(self.expiry_date, str):
            self.expiry_date = date.fromisoformat(self.expiry_date)
        
        # Conversione deleted_at
        if self.deleted_at and isinstance(self.deleted_at, str):
            self.deleted_at = datetime.fromisoformat(self.deleted_at)
    
    def is_deleted(self) -> bool:
        """Verifica se eliminato (soft delete)."""
        return self.deleted_at is not None
    
    def is_depleted(self) -> bool:
        """Verifica se esaurito (volume rimanente <= 0)."""
        return self.volume_remaining_ml <= 0
    
    def is_expired(self) -> bool:
        """Verifica se scaduto."""
        if not self.expiry_date:
            return False
        return self.expiry_date < date.today()
    
    def is_active(self) -> bool:
        """Verifica se attiva (non eliminata, non esaurita, non scaduta)."""
        return not self.is_deleted() and not self.is_depleted() and not self.is_expired()
    
    def calculate_concentration_mg_ml(self, batch_mg_per_vial: Decimal) -> Decimal:
        """
        Calcola concentrazione in mg/ml.
        
        Args:
            batch_mg_per_vial: mg per fiala del batch
        
        Returns:
            Concentrazione in mg/ml
        
        Example:
            >>> prep = Preparation(batch_id=1, vials_used=2, volume_ml=4.0)
            >>> prep.calculate_concentration_mg_ml(Decimal('5.0'))
            Decimal('2.5')  # (2 vials * 5mg) / 4ml = 2.5 mg/ml
        """
        if isinstance(batch_mg_per_vial, (int, float, str)):
            batch_mg_per_vial = Decimal(str(batch_mg_per_vial))
        
        total_mg = batch_mg_per_vial * self.vials_used
        return total_mg / self.volume_ml


class PreparationRepository(Repository):
    """Repository per operazioni CRUD sulle preparazioni."""
    
    def get_all(
        self,
        batch_id: Optional[int] = None,
        only_active: bool = False,
        include_deleted: bool = False
    ) -> List[Preparation]:
        """
        Recupera preparazioni con filtri opzionali.
        
        Args:
            batch_id: Filtra per batch specifico
            only_active: Solo preparazioni attive (volume > 0)
            include_deleted: Include preparazioni eliminate
        
        Returns:
            Lista di preparazioni
        """
        query = 'SELECT * FROM preparations WHERE 1=1'
        params = []
        
        if not include_deleted:
            query += ' AND deleted_at IS NULL'
        
        if batch_id:
            query += ' AND batch_id = ?'
            params.append(batch_id)
        
        if only_active:
            query += ' AND volume_remaining_ml > 0'
        
        query += ' ORDER BY preparation_date DESC, id DESC'
        
        rows = self._fetch_all(query, tuple(params))
        return [Preparation.from_row(row) for row in rows]
    
    def get_by_id(
        self, 
        prep_id: int, 
        include_deleted: bool = False
    ) -> Optional[Preparation]:
        """
        Recupera preparazione per ID.
        
        Args:
            prep_id: ID preparazione
            include_deleted: Include se eliminata
        
        Returns:
            Preparazione o None se non trovata
        """
        query = 'SELECT * FROM preparations WHERE id = ?'
        
        if not include_deleted:
            query += ' AND deleted_at IS NULL'
        
        row = self._fetch_one(query, (prep_id,))
        return Preparation.from_row(row) if row else None
    
    def create(self, preparation: Preparation) -> int:
        """
        Crea nuova preparazione e decrementa fiale dal batch.
        
        Args:
            preparation: Oggetto Preparation da creare
        
        Returns:
            ID della preparazione creata
        
        Raises:
            ValueError: Se batch non esiste o fiale insufficienti
        """
        # Validazione esistenza batch e fiale disponibili
        query = 'SELECT id, vials_remaining FROM batches WHERE id = ? AND deleted_at IS NULL'
        batch_row = self._fetch_one(query, (preparation.batch_id,))
        
        if not batch_row:
            raise ValueError(f"Batch #{preparation.batch_id} non trovato")
        
        vials_available = batch_row[1]
        if vials_available < preparation.vials_used:
            raise ValueError(
                f"Fiale insufficienti nel batch #{preparation.batch_id}: "
                f"disponibili {vials_available}, richieste {preparation.vials_used}"
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
            preparation.preparation_date.isoformat() if preparation.preparation_date else None,
            preparation.expiry_date.isoformat() if preparation.expiry_date else None,
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
    
    def update(self, preparation: Preparation) -> bool:
        """
        Aggiorna preparazione esistente.
        
        Args:
            preparation: Oggetto Preparation con modifiche
        
        Returns:
            True se aggiornamento riuscito
        
        Raises:
            ValueError: Se ID preparazione mancante
        """
        if preparation.id is None:
            raise ValueError("ID preparazione necessario per update")
        
        query = '''
            UPDATE preparations 
            SET batch_id = ?, vials_used = ?, volume_ml = ?, diluent = ?,
                preparation_date = ?, expiry_date = ?, volume_remaining_ml = ?,
                storage_location = ?, notes = ?
            WHERE id = ? AND deleted_at IS NULL
        '''
        self._execute(query, (
            preparation.batch_id,
            preparation.vials_used,
            float(preparation.volume_ml),
            preparation.diluent,
            preparation.preparation_date.isoformat() if preparation.preparation_date else None,
            preparation.expiry_date.isoformat() if preparation.expiry_date else None,
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
    ) -> Tuple[bool, str]:
        """
        Elimina preparazione (soft delete o hard delete).
        
        Args:
            prep_id: ID preparazione da eliminare
            restore_vials: Se True, ripristina fiale nel batch
            force: Se True, hard delete (eliminazione permanente)
        
        Returns:
            Tuple (successo, messaggio)
        """
        prep = self.get_by_id(prep_id, include_deleted=True)
        if not prep:
            return False, f"Preparazione #{prep_id} non trovata"
        
        if prep.is_deleted() and not force:
            return False, f"Preparazione #{prep_id} già eliminata"
        
        # Ripristina fiale nel batch se richiesto
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
            return True, f"Preparazione #{prep_id} eliminata permanentemente"
        else:
            # Soft delete
            query = '''
                UPDATE preparations 
                SET deleted_at = ?
                WHERE id = ?
            '''
            self._execute(query, (datetime.now().isoformat(), prep_id))
            self._commit()
            
            vials_msg = f" (fiale ripristinate: +{prep.vials_used})" if restore_vials else ""
            return True, f"Preparazione #{prep_id} eliminata{vials_msg}"
    
    def restore(self, prep_id: int) -> Tuple[bool, str]:
        """
        Ripristina preparazione eliminata.
        
        Args:
            prep_id: ID preparazione da ripristinare
        
        Returns:
            Tuple (successo, messaggio)
        """
        prep = self.get_by_id(prep_id, include_deleted=True)
        if not prep:
            return False, f"Preparazione #{prep_id} non trovata"
        
        if not prep.is_deleted():
            return False, f"Preparazione #{prep_id} non è eliminata"
        
        query = '''
            UPDATE preparations 
            SET deleted_at = NULL
            WHERE id = ?
        '''
        self._execute(query, (prep_id,))
        self._commit()
        
        return True, f"Preparazione #{prep_id} ripristinata"
    
    def use_volume(self, prep_id: int, ml_to_use: float) -> Tuple[bool, str]:
        """
        Usa volume dalla preparazione (decrementa volume_remaining_ml).
        
        Args:
            prep_id: ID preparazione
            ml_to_use: Volume in ml da utilizzare
        
        Returns:
            Tuple (successo, messaggio)
        
        Raises:
            ValueError: Se volume insufficiente o preparazione non valida
        """
        prep = self.get_by_id(prep_id)
        if not prep:
            raise ValueError(f"Preparazione #{prep_id} non trovata")
        
        if prep.is_deleted():
            raise ValueError(f"Preparazione #{prep_id} è eliminata")
        
        ml_to_use = Decimal(str(ml_to_use))
        
        if ml_to_use <= 0:
            raise ValueError("Volume da usare deve essere > 0")
        
        if prep.volume_remaining_ml < ml_to_use:
            raise ValueError(
                f"Volume insufficiente: richiesto {ml_to_use} ml, "
                f"disponibile {prep.volume_remaining_ml} ml"
            )
        
        new_volume = prep.volume_remaining_ml - ml_to_use
        
        query = '''
            UPDATE preparations 
            SET volume_remaining_ml = ?
            WHERE id = ?
        '''
        self._execute(query, (float(new_volume), prep_id))
        self._commit()
        
        status = "esaurita" if new_volume <= 0 else f"rimanente: {new_volume} ml"
        return True, f"Usati {ml_to_use} ml dalla preparazione #{prep_id} ({status})"
    
    def recalculate_volume(self, prep_id: int) -> Tuple[bool, str]:
        """
        Ricalcola volume rimanente basandosi sulle somministrazioni effettive.
        
        Args:
            prep_id: ID preparazione
        
        Returns:
            Tuple (successo, messaggio)
        """
        prep = self.get_by_id(prep_id)
        if not prep:
            return False, f"Preparazione #{prep_id} non trovata"
        
        # Calcola volume usato dalle somministrazioni
        query = '''
            SELECT COALESCE(SUM(dose_ml), 0)
            FROM administrations
            WHERE preparation_id = ? AND deleted_at IS NULL
        '''
        row = self._fetch_one(query, (prep_id,))
        volume_used = Decimal(str(row[0])) if row else Decimal('0')
        
        # Calcola volume atteso
        expected_remaining = prep.volume_ml - volume_used
        
        # Confronta con volume attuale
        current_remaining = prep.volume_remaining_ml
        difference = abs(expected_remaining - current_remaining)
        
        if difference < Decimal('0.01'):  # Tolleranza 0.01 ml
            return True, f"Preparazione #{prep_id}: volume già corretto ({current_remaining} ml)"
        
        # Aggiorna volume
        query = '''
            UPDATE preparations 
            SET volume_remaining_ml = ?
            WHERE id = ?
        '''
        self._execute(query, (float(expected_remaining), prep_id))
        self._commit()
        
        return True, (
            f"Preparazione #{prep_id}: volume ricalcolato da {current_remaining} ml "
            f"a {expected_remaining} ml (differenza: {difference} ml)"
        )
    
    def get_expired(self) -> List[Preparation]:
        """
        Recupera tutte le preparazioni scadute.
        
        Returns:
            Lista di preparazioni scadute
        """
        today = date.today().isoformat()
        query = '''
            SELECT * FROM preparations 
            WHERE deleted_at IS NULL 
            AND expiry_date IS NOT NULL 
            AND expiry_date < ?
            ORDER BY expiry_date ASC
        '''
        rows = self._fetch_all(query, (today,))
        return [Preparation.from_row(row) for row in rows]
    
    def count(
        self,
        batch_id: Optional[int] = None,
        only_active: bool = False,
        include_deleted: bool = False
    ) -> int:
        """
        Conta preparazioni con filtri opzionali.
        
        Args:
            batch_id: Filtra per batch specifico
            only_active: Solo preparazioni attive
            include_deleted: Include preparazioni eliminate
        
        Returns:
            Numero di preparazioni
        """
        query = 'SELECT COUNT(*) FROM preparations WHERE 1=1'
        params = []
        
        if not include_deleted:
            query += ' AND deleted_at IS NULL'
        
        if batch_id:
            query += ' AND batch_id = ?'
            params.append(batch_id)
        
        if only_active:
            query += ' AND volume_remaining_ml > 0'
        
        row = self._fetch_one(query, tuple(params))
        return row[0] if row else 0
