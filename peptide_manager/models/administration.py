"""
Administration model - gestisce log somministrazioni peptidi.

Una administration registra ogni somministrazione di peptide da una preparazione,
tracciando dose, data/ora, sito iniezione, effetti collaterali, e collegamento
a un protocollo opzionale.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict
from datetime import datetime, date
from decimal import Decimal

from .base import BaseModel, Repository


@dataclass
class Administration(BaseModel):
    """Rappresenta una somministrazione di peptide."""
    
    # Campi obbligatori
    preparation_id: int = field(default=None)
    administration_datetime: datetime = field(default=None)
    dose_ml: Decimal = field(default=None)
    
    # Campi opzionali
    protocol_id: Optional[int] = None
    injection_site: Optional[str] = None
    injection_method: Optional[str] = None
    notes: Optional[str] = None
    side_effects: Optional[str] = None
    deleted_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Validazione dopo inizializzazione."""
        # Conversioni Decimal PRIMA della validazione
        if isinstance(self.dose_ml, (int, float, str)):
            self.dose_ml = Decimal(str(self.dose_ml))
        
        # Validazioni base
        if self.preparation_id is None:
            raise ValueError("Preparation ID obbligatorio")
        if self.dose_ml is None or self.dose_ml <= 0:
            raise ValueError("Dose deve essere > 0")
        
        # Conversioni datetime
        if self.administration_datetime is None:
            self.administration_datetime = datetime.now()
        elif isinstance(self.administration_datetime, str):
            self.administration_datetime = datetime.fromisoformat(self.administration_datetime)
        
        # Conversione deleted_at
        if self.deleted_at and isinstance(self.deleted_at, str):
            self.deleted_at = datetime.fromisoformat(self.deleted_at)
    
    def is_deleted(self) -> bool:
        """Verifica se eliminata (soft delete)."""
        return self.deleted_at is not None
    
    def has_protocol(self) -> bool:
        """Verifica se collegata a un protocollo."""
        return self.protocol_id is not None
    
    def has_side_effects(self) -> bool:
        """Verifica se sono stati registrati effetti collaterali."""
        return bool(self.side_effects and self.side_effects.strip())


class AdministrationRepository(Repository):
    """Repository per operazioni CRUD su somministrazioni."""
    
    def get_all(
        self,
        protocol_id: Optional[int] = None,
        preparation_id: Optional[int] = None,
        days_back: Optional[int] = None,
        include_deleted: bool = False
    ) -> List[Administration]:
        """
        Recupera somministrazioni con filtri opzionali.
        
        Args:
            protocol_id: Filtra per protocollo specifico
            preparation_id: Filtra per preparazione specifica
            days_back: Filtra ultimi N giorni
            include_deleted: Include somministrazioni eliminate
            
        Returns:
            Lista di Administration
        """
        query = 'SELECT * FROM administrations WHERE 1=1'
        params = []
        
        # Filtro soft delete
        if not include_deleted:
            query += ' AND deleted_at IS NULL'
        
        # Filtro protocollo
        if protocol_id is not None:
            query += ' AND protocol_id = ?'
            params.append(protocol_id)
        
        # Filtro preparazione
        if preparation_id is not None:
            query += ' AND preparation_id = ?'
            params.append(preparation_id)
        
        # Filtro giorni recenti
        if days_back is not None:
            query += ' AND administration_datetime >= datetime("now", ?)'
            params.append(f'-{days_back} days')
        
        query += ' ORDER BY administration_datetime DESC'
        
        rows = self._fetch_all(query, tuple(params))
        return [Administration.from_row(row) for row in rows]
    
    def get_by_id(
        self, 
        admin_id: int, 
        include_deleted: bool = False
    ) -> Optional[Administration]:
        """
        Recupera somministrazione per ID.
        
        Args:
            admin_id: ID somministrazione
            include_deleted: Include anche se eliminata
            
        Returns:
            Administration o None se non trovata
        """
        query = 'SELECT * FROM administrations WHERE id = ?'
        
        if not include_deleted:
            query += ' AND deleted_at IS NULL'
        
        row = self._fetch_one(query, (admin_id,))
        return Administration.from_row(row) if row else None
    
    def create(self, administration: Administration) -> int:
        """
        Crea nuova somministrazione.
        
        Args:
            administration: Oggetto Administration da creare
            
        Returns:
            ID somministrazione creata
            
        Raises:
            ValueError: Se dati non validi o preparation/protocol non esistono
        """
        # Validazione preparazione
        if administration.preparation_id is None:
            raise ValueError("Preparation ID obbligatorio")
        
        # Verifica preparazione esiste
        prep_query = 'SELECT id, volume_remaining_ml FROM preparations WHERE id = ? AND deleted_at IS NULL'
        prep_row = self._fetch_one(prep_query, (administration.preparation_id,))
        if not prep_row:
            raise ValueError(f"Preparazione #{administration.preparation_id} non trovata")
        
        # Verifica volume disponibile
        # Arrotonda a 2 decimali per evitare errori floating point e consentire solo unità registrabili
        volume_remaining = Decimal(str(prep_row[1]))
        if round(float(volume_remaining), 2) < round(float(administration.dose_ml), 2):
            raise ValueError(
                f"Volume insufficiente (disponibile: {volume_remaining}ml, "
                f"richiesto: {administration.dose_ml}ml)"
            )
        
        # Verifica protocollo se specificato
        if administration.protocol_id is not None:
            protocol_query = 'SELECT id FROM protocols WHERE id = ? AND deleted_at IS NULL'
            if not self._fetch_one(protocol_query, (administration.protocol_id,)):
                raise ValueError(f"Protocollo #{administration.protocol_id} non trovato")
        
        # Inserisci somministrazione
        query = '''
            INSERT INTO administrations (
                preparation_id, protocol_id, administration_datetime,
                dose_ml, injection_site, injection_method,
                notes, side_effects
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        '''
        
        cursor = self._execute(query, (
            administration.preparation_id,
            administration.protocol_id,
            administration.administration_datetime,
            float(administration.dose_ml),
            administration.injection_site,
            administration.injection_method,
            administration.notes,
            administration.side_effects
        ))
        
        admin_id = cursor.lastrowid
        
        # Decrementa volume dalla preparazione
        update_prep_query = '''
            UPDATE preparations 
            SET volume_remaining_ml = volume_remaining_ml - ?
            WHERE id = ?
        '''
        self._execute(update_prep_query, (
            float(administration.dose_ml),
            administration.preparation_id
        ))
        
        self._commit()
        return admin_id
    
    def update(self, administration: Administration) -> bool:
        """
        Aggiorna somministrazione esistente.
        
        Args:
            administration: Oggetto Administration con dati aggiornati (deve avere id)
            
        Returns:
            True se aggiornato
            
        Raises:
            ValueError: Se id non specificato o dati non validi
        """
        if administration.id is None:
            raise ValueError("ID somministrazione necessario per update")
        
        # Validazione
        if administration.dose_ml <= 0:
            raise ValueError("Dose deve essere > 0")
        
        # NOTA: Update NON modifica dose_ml (per evitare inconsistenze volume)
        # Se serve cambiare dose, eliminare e ricreare
        
        query = '''
            UPDATE administrations 
            SET protocol_id = ?, administration_datetime = ?,
                injection_site = ?, injection_method = ?,
                notes = ?, side_effects = ?
            WHERE id = ?
        '''
        
        self._execute(query, (
            administration.protocol_id,
            administration.administration_datetime,
            administration.injection_site,
            administration.injection_method,
            administration.notes,
            administration.side_effects,
            administration.id
        ))
        
        self._commit()
        return True
    
    def delete(
        self, 
        admin_id: int, 
        force: bool = False,
        restore_volume: bool = False
    ) -> tuple[bool, str]:
        """
        Elimina somministrazione (soft delete di default).
        
        Args:
            admin_id: ID somministrazione
            force: Se True, elimina fisicamente (hard delete)
            restore_volume: Se True, ripristina volume alla preparazione
            
        Returns:
            (success: bool, message: str)
        """
        # Verifica esistenza
        administration = self.get_by_id(admin_id, include_deleted=True)
        if not administration:
            return False, f"Somministrazione #{admin_id} non trovata"
        
        if administration.is_deleted() and not force:
            return False, f"Somministrazione già eliminata"
        
        # Ripristina volume se richiesto
        if restore_volume and not administration.is_deleted():
            restore_query = '''
                UPDATE preparations 
                SET volume_remaining_ml = volume_remaining_ml + ?
                WHERE id = ?
            '''
            self._execute(restore_query, (
                float(administration.dose_ml),
                administration.preparation_id
            ))
        
        if force:
            # Hard delete
            query = 'DELETE FROM administrations WHERE id = ?'
            self._execute(query, (admin_id,))
            self._commit()
            return True, f"Somministrazione eliminata definitivamente"
        else:
            # Soft delete
            query = 'UPDATE administrations SET deleted_at = CURRENT_TIMESTAMP WHERE id = ?'
            self._execute(query, (admin_id,))
            self._commit()
            return True, f"Somministrazione archiviata (soft delete)"
    
    def count(
        self,
        protocol_id: Optional[int] = None,
        preparation_id: Optional[int] = None,
        include_deleted: bool = False
    ) -> int:
        """
        Conta somministrazioni con filtri opzionali.
        
        Args:
            protocol_id: Filtra per protocollo
            preparation_id: Filtra per preparazione
            include_deleted: Include eliminate
            
        Returns:
            Numero somministrazioni
        """
        query = 'SELECT COUNT(*) FROM administrations WHERE 1=1'
        params = []
        
        if not include_deleted:
            query += ' AND deleted_at IS NULL'
        
        if protocol_id is not None:
            query += ' AND protocol_id = ?'
            params.append(protocol_id)
        
        if preparation_id is not None:
            query += ' AND preparation_id = ?'
            params.append(preparation_id)
        
        row = self._fetch_one(query, tuple(params))
        return row[0] if row else 0
    
    # ========== METODI CUSTOM ==========
    
    def get_with_details(
        self,
        protocol_id: Optional[int] = None,
        preparation_id: Optional[int] = None,
        days_back: Optional[int] = None,
        include_deleted: bool = False
    ) -> List[Dict]:
        """
        Recupera somministrazioni con dettagli completi (JOIN).
        
        Args:
            protocol_id: Filtra per protocollo
            preparation_id: Filtra per preparazione
            days_back: Filtra ultimi N giorni
            include_deleted: Include eliminate
            
        Returns:
            Lista di dict con dettagli somministrazioni
        """
        query = '''
            SELECT 
                a.*,
                pr.name as protocol_name,
                prep.batch_id,
                b.product_name as batch_product,
                GROUP_CONCAT(p.name, ', ') as peptide_names
            FROM administrations a
            LEFT JOIN protocols pr ON a.protocol_id = pr.id
            LEFT JOIN preparations prep ON a.preparation_id = prep.id
            LEFT JOIN batches b ON prep.batch_id = b.id
            LEFT JOIN batch_composition bc ON b.id = bc.batch_id
            LEFT JOIN peptides p ON bc.peptide_id = p.id
            WHERE 1=1
        '''
        params = []
        
        if not include_deleted:
            query += ' AND a.deleted_at IS NULL'
        
        if protocol_id is not None:
            query += ' AND a.protocol_id = ?'
            params.append(protocol_id)
        
        if preparation_id is not None:
            query += ' AND a.preparation_id = ?'
            params.append(preparation_id)
        
        if days_back is not None:
            query += ' AND a.administration_datetime >= datetime("now", ?)'
            params.append(f'-{days_back} days')
        
        query += ' GROUP BY a.id ORDER BY a.administration_datetime DESC'
        
        rows = self._fetch_all(query, tuple(params))
        return [dict(row) for row in rows]
    
    def get_statistics(self, protocol_id: Optional[int] = None) -> Dict:
        """
        Calcola statistiche somministrazioni.
        
        Args:
            protocol_id: ID protocollo (None = tutte)
            
        Returns:
            Dict con statistiche (count, total_ml, avg_dose, first_date, last_date)
        """
        query = '''
            SELECT 
                COUNT(*) as count,
                SUM(dose_ml) as total_ml,
                AVG(dose_ml) as avg_dose,
                MIN(administration_datetime) as first_date,
                MAX(administration_datetime) as last_date
            FROM administrations
            WHERE deleted_at IS NULL
        '''
        params = []
        
        if protocol_id is not None:
            query += ' AND protocol_id = ?'
            params.append(protocol_id)
        
        row = self._fetch_one(query, tuple(params))
        
        if not row or row[0] == 0:
            return {
                'count': 0,
                'total_ml': 0,
                'avg_dose': 0,
                'first_date': None,
                'last_date': None
            }
        
        return {
            'count': row[0],
            'total_ml': float(row[1]) if row[1] else 0,
            'avg_dose': float(row[2]) if row[2] else 0,
            'first_date': row[3],
            'last_date': row[4]
        }
    
    def link_to_protocol(self, admin_id: int, protocol_id: int) -> tuple[bool, str]:
        """
        Collega somministrazione a un protocollo.
        
        Args:
            admin_id: ID somministrazione
            protocol_id: ID protocollo
            
        Returns:
            (success: bool, message: str)
        """
        # Verifica somministrazione
        admin = self.get_by_id(admin_id)
        if not admin:
            return False, f"Somministrazione #{admin_id} non trovata"
        
        # Verifica protocollo
        protocol_query = 'SELECT id FROM protocols WHERE id = ? AND deleted_at IS NULL'
        if not self._fetch_one(protocol_query, (protocol_id,)):
            return False, f"Protocollo #{protocol_id} non trovato"
        
        # Aggiorna
        query = 'UPDATE administrations SET protocol_id = ? WHERE id = ?'
        self._execute(query, (protocol_id, admin_id))
        self._commit()
        
        return True, f"Somministrazione collegata a protocollo #{protocol_id}"
    
    def unlink_from_protocol(self, admin_id: int) -> tuple[bool, str]:
        """
        Scollega somministrazione da protocollo.
        
        Args:
            admin_id: ID somministrazione
            
        Returns:
            (success: bool, message: str)
        """
        admin = self.get_by_id(admin_id)
        if not admin:
            return False, f"Somministrazione #{admin_id} non trovata"
        
        if not admin.has_protocol():
            return False, "Somministrazione non collegata a nessun protocollo"
        
        query = 'UPDATE administrations SET protocol_id = NULL WHERE id = ?'
        self._execute(query, (admin_id,))
        self._commit()
        
        return True, "Somministrazione scollegata da protocollo"
    
    def calculate_multi_prep_distribution(
        self,
        required_ml: float,
        available_preps: List[Dict]
    ) -> tuple[bool, List[Dict], str]:
        """
        Calcola come distribuire una dose su più preparazioni.
        
        Strategia: usa preparazioni in ordine di scadenza (FIFO) finché
        non raggiungi la dose richiesta.
        
        Args:
            required_ml: Dose totale richiesta in ml
            available_preps: Lista preparazioni disponibili
                             [{'id': int, 'volume_remaining_ml': float, 'expiry_date': str}, ...]
        
        Returns:
            Tuple (success, distribution, message)
            - success: True se dose realizzabile
            - distribution: [{'prep_id': int, 'ml': float}, ...]
            - message: Messaggio descrittivo
        
        Example:
            >>> preps = [
            ...     {'id': 1, 'volume_remaining_ml': 0.3, 'expiry_date': '2025-12-01'},
            ...     {'id': 2, 'volume_remaining_ml': 0.5, 'expiry_date': '2025-12-15'}
            ... ]
            >>> repo.calculate_multi_prep_distribution(0.6, preps)
            (True, [{'prep_id': 1, 'ml': 0.3}, {'prep_id': 2, 'ml': 0.3}], '2 preparazioni')
        """
        from decimal import Decimal
        
        required_ml = Decimal(str(required_ml))
        
        # Ordina per scadenza (FIFO)
        sorted_preps = sorted(
            available_preps,
            key=lambda p: (p.get('expiry_date') or '9999-12-31', p['id'])
        )
        
        # Calcola volume totale disponibile
        total_available = sum(
            Decimal(str(p['volume_remaining_ml'])) for p in sorted_preps
        )
        
        if total_available < required_ml:
            return False, [], f"Volume insufficiente: richiesti {required_ml}ml, disponibili {total_available}ml"
        
        # Distribuzione greedy (FIFO)
        distribution = []
        remaining = required_ml
        
        for prep in sorted_preps:
            if remaining <= 0:
                break
            
            available = Decimal(str(prep['volume_remaining_ml']))
            to_use = min(available, remaining)
            
            distribution.append({
                'prep_id': prep['id'],
                'ml': float(to_use),
                'prep_info': prep  # Informazioni complete per GUI
            })
            
            remaining -= to_use
        
        num_preps = len(distribution)
        message = f"{num_preps} preparazion{'e' if num_preps > 1 else 'i'} necessarie"
        
        return True, distribution, message
    
    def create_multi_prep_administration(
        self,
        distribution: List[Dict],
        administration_datetime: datetime,
        protocol_id: Optional[int] = None,
        cycle_id: Optional[int] = None,
        injection_site: Optional[str] = None,
        injection_method: Optional[str] = None,
        notes: Optional[str] = None,
        side_effects: Optional[str] = None
    ) -> tuple[bool, List[int], str]:
        """
        Crea somministrazioni multiple da più preparazioni (dose split).
        
        Args:
            distribution: Output di calculate_multi_prep_distribution()
                          [{'prep_id': int, 'ml': float}, ...]
            administration_datetime: Data/ora somministrazione
            protocol_id: ID protocollo (opzionale)
            cycle_id: ID ciclo (opzionale)
            injection_site: Sito iniezione
            injection_method: Metodo iniezione
            notes: Note
            side_effects: Effetti collaterali
        
        Returns:
            Tuple (success, admin_ids, message)
            - success: True se tutto ok
            - admin_ids: Lista ID somministrazioni create
            - message: Messaggio descrittivo
        
        Raises:
            ValueError: Se volume insufficiente in una preparazione
        """
        admin_ids = []
        
        try:
            for item in distribution:
                prep_id = item['prep_id']
                ml = item['ml']
                
                # Crea somministrazione per questa preparazione
                admin = Administration(
                    preparation_id=prep_id,
                    dose_ml=ml,
                    administration_datetime=administration_datetime,
                    protocol_id=protocol_id,
                    injection_site=injection_site,
                    injection_method=injection_method,
                    notes=f"Multi-prep {len(distribution)} totale. {notes}" if notes else f"Multi-prep {len(distribution)} preparazioni",
                    side_effects=side_effects
                )
                
                admin_id = self.create(admin)
                admin_ids.append(admin_id)
                
                # Assegna a ciclo se specificato
                if cycle_id:
                    from .cycle import CycleRepository
                    cycle_repo = CycleRepository(self.conn)
                    cycle_repo.record_administration(cycle_id, admin_id)
            
            total_ml = sum(item['ml'] for item in distribution)
            message = f"{len(admin_ids)} somministrazioni create ({total_ml:.2f}ml totali)"
            
            return True, admin_ids, message
            
        except Exception as e:
            # Rollback in caso di errore
            for admin_id in admin_ids:
                try:
                    self.delete(admin_id, force=True, restore_volume=True)
                except:
                    pass
            
            return False, [], f"Errore: {str(e)}"
