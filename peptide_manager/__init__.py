"""
Adapter per retrocompatibilità con il vecchio PeptideManager.

Questo modulo permette al vecchio codice GUI di continuare a funzionare
mentre migriamo progressivamente alla nuova architettura.

Strategia:
- Suppliers, Peptides, Batches: usa nuova architettura (DatabaseManager + Repository)
- Altri moduli (Protocols, etc.): delega al vecchio models.py

Questo permette migrazione incrementale senza bloccare la GUI.
"""

from typing import List, Dict, Optional
from .database import DatabaseManager
from .models import (
    Supplier,
    SupplierRepository,
    Peptide,
    PeptideRepository,
    Batch,
    BatchRepository,
    BatchComposition,
    BatchCompositionRepository,
    Preparation,
    PreparationRepository
)


class PeptideManager:
    """
    Adapter ibrido: nuova architettura per moduli migrati + fallback per il resto.
    
    Moduli migrati (usa nuova architettura):
    - Suppliers ✅
    - Peptides ✅
    - Batches ✅
    - BatchComposition ✅
    
    Moduli non migrati (usa vecchio codice):
    - Certificates
    - Preparations
    - Protocols
    - Administrations
    """
    
    def __init__(self, db_path: str = 'peptide_management.db'):
        """
        Inizializza il manager (compatibile con vecchia interfaccia).
        
        Args:
            db_path: Percorso del database
        """
        self.db_path = db_path
        self.db = DatabaseManager(db_path)
        
        # Per retrocompatibilità
        self.conn = self.db.conn
        
        # Lazy loading del vecchio manager (solo se serve)
        self._old_manager = None
    
    def _get_old_manager(self):
        """
        Lazy load del vecchio PeptideManager per metodi non ancora migrati.
        
        Importa il vecchio models_legacy.py solo quando necessario.
        """
        if self._old_manager is None:
            try:
                # Importa vecchio PeptideManager da models_legacy.py (stesso package)
                from .models_legacy import PeptideManager as OldPeptideManager
                self._old_manager = OldPeptideManager(self.db_path)
                print("⚠️  Usando vecchio PeptideManager per moduli non ancora migrati")
            except ImportError as e:
                raise ImportError(
                    "Impossibile importare vecchio PeptideManager. "
                    "Assicurati che peptide_manager/models_legacy.py esista. "
                    f"Errore: {e}"
                )
        
        return self._old_manager
    
    def close(self):
        """Chiude le connessioni (compatibile con vecchia interfaccia)."""
        self.db.close()
        if self._old_manager:
            self._old_manager.close()
    
    # ==================== SUPPLIERS (MIGRATO ✅) ====================
    
    def get_suppliers(self, search: str = None) -> List[Dict]:
        """
        Recupera fornitori (usa nuova architettura).
        
        Args:
            search: Filtro ricerca (opzionale)
            
        Returns:
            Lista di dict (compatibile con vecchia interfaccia)
        """
        suppliers = self.db.suppliers.get_all(search=search)
        return [s.to_dict() for s in suppliers]
    
    def add_supplier(self, name: str, country: str = None, website: str = None,
                     email: str = None, notes: str = None, rating: int = None) -> int:
        """
        Aggiunge fornitore (usa nuova architettura).
        
        Args:
            name: Nome fornitore
            country: Paese (opzionale)
            website: Sito web (opzionale)
            email: Email (opzionale)
            notes: Note (opzionale)
            rating: Rating 1-5 (opzionale)
            
        Returns:
            ID del fornitore creato
        """
        supplier = Supplier(
            name=name,
            country=country,
            website=website,
            email=email,
            notes=notes,
            reliability_rating=rating
        )
        
        supplier_id = self.db.suppliers.create(supplier)
        print(f"Fornitore '{name}' aggiunto (ID: {supplier_id})")
        return supplier_id
    
    def update_supplier(self, supplier_id: int, **kwargs) -> bool:
        """
        Aggiorna fornitore (usa nuova architettura).
        
        Args:
            supplier_id: ID fornitore
            **kwargs: Campi da aggiornare
            
        Returns:
            True se aggiornato
        """
        supplier = self.db.suppliers.get_by_id(supplier_id)
        if not supplier:
            print(f"Fornitore #{supplier_id} non trovato")
            return False
        
        # Aggiorna campi
        allowed_fields = ['name', 'country', 'website', 'email', 'notes']
        for key, value in kwargs.items():
            if key in allowed_fields:
                setattr(supplier, key, value)
            elif key == 'rating':
                supplier.reliability_rating = value
        
        # Salva
        try:
            self.db.suppliers.update(supplier)
            print(f"Fornitore ID {supplier_id} aggiornato")
            return True
        except ValueError as e:
            print(f"Errore: {e}")
            return False
    
    def soft_delete_supplier(self, supplier_id: int) -> bool:
        """
        Elimina fornitore (usa nuova architettura).
        
        Args:
            supplier_id: ID fornitore
            
        Returns:
            True se eliminato
        """
        success, message = self.db.suppliers.delete(supplier_id, force=False)
        
        if success:
            print(f"✓ {message}")
        else:
            print(f"❌ {message}")
        
        return success
    
    # Alias per backward compatibility
    def delete_supplier(self, supplier_id: int, force: bool = False) -> bool:
        """Alias per soft_delete_supplier (backward compatibility con vecchi test)."""
        return self.db.suppliers.delete(supplier_id, force=force)[0]
    
    # ==================== PEPTIDES (MIGRATO ✅) ====================
    
    def get_peptides(self, search: str = None) -> List[Dict]:
        """
        Recupera peptidi (usa nuova architettura).
        
        Args:
            search: Filtro ricerca (opzionale)
            
        Returns:
            Lista di dict (compatibile con vecchia interfaccia)
        """
        peptides = self.db.peptides.get_all(search=search)
        return [p.to_dict() for p in peptides]
    
    def get_peptide_by_id(self, peptide_id: int) -> Optional[Dict]:
        """
        Recupera peptide per ID (usa nuova architettura).
        
        Args:
            peptide_id: ID del peptide
            
        Returns:
            Dict o None
        """
        peptide = self.db.peptides.get_by_id(peptide_id)
        return peptide.to_dict() if peptide else None
    
    def add_peptide(self, name: str, description: str = None,
                    common_uses: str = None, notes: str = None) -> int:
        """
        Aggiunge peptide (usa nuova architettura).
        
        Args:
            name: Nome peptide
            description: Descrizione (opzionale)
            common_uses: Usi comuni (opzionale)
            notes: Note (opzionale)
            
        Returns:
            ID del peptide creato
        """
        peptide = Peptide(
            name=name,
            description=description,
            common_uses=common_uses,
            notes=notes
        )
        
        peptide_id = self.db.peptides.create(peptide)
        print(f"Peptide '{name}' aggiunto al catalogo (ID: {peptide_id})")
        return peptide_id
    
    def update_peptide(self, peptide_id: int, **kwargs) -> bool:
        """
        Aggiorna peptide (usa nuova architettura).
        
        Args:
            peptide_id: ID peptide
            **kwargs: Campi da aggiornare
            
        Returns:
            True se aggiornato
        """
        peptide = self.db.peptides.get_by_id(peptide_id)
        if not peptide:
            print(f"Peptide #{peptide_id} non trovato")
            return False
        
        # Aggiorna campi
        allowed_fields = ['name', 'description', 'common_uses', 'notes']
        for key, value in kwargs.items():
            if key in allowed_fields:
                setattr(peptide, key, value)
        
        # Salva
        try:
            self.db.peptides.update(peptide)
            print(f"Peptide ID {peptide_id} aggiornato")
            return True
        except ValueError as e:
            print(f"Errore: {e}")
            return False
    
    def soft_delete_peptide(self, peptide_id: int) -> bool:
        """
        Elimina peptide (usa nuova architettura).
        
        Args:
            peptide_id: ID peptide
            
        Returns:
            True se eliminato
        """
        success, message = self.db.peptides.delete(peptide_id, force=False)
        
        if success:
            print(f"✓ {message}")
        else:
            print(f"❌ {message}")
        
        return success
    
    # Alias per backward compatibility
    def delete_peptide(self, peptide_id: int, force: bool = False) -> bool:
        """Alias per soft_delete_peptide (backward compatibility con vecchi test)."""
        return self.db.peptides.delete(peptide_id, force=force)[0]
    
    # ==================== BATCHES (MIGRATO ✅) ====================
    
    def get_batches(
        self,
        search: str = None,
        supplier_id: int = None,
        only_available: bool = False,
        only_depleted: bool = False,
        only_expired: bool = False
    ) -> List[Dict]:
        """
        Recupera batches con filtri opzionali.
        
        Args:
            search: Filtro ricerca (nome prodotto o batch number)
            supplier_id: Filtra per fornitore specifico
            only_available: Solo batches con fiale disponibili
            only_depleted: Solo batches esauriti
            only_expired: Solo batches scaduti
        
        Returns:
            Lista di dict batch (compatibile GUI)
        """
        batches = self.db.batches.get_all(
            search=search,
            supplier_id=supplier_id,
            only_available=only_available,
            only_depleted=only_depleted,
            only_expired=only_expired
        )
        
        # Aggiungi supplier_name a ogni batch
        result = []
        for batch in batches:
            batch_dict = batch.to_dict()
            
            # Aggiungi nome fornitore
            supplier = self.db.suppliers.get_by_id(batch.supplier_id)
            batch_dict['supplier_name'] = supplier.name if supplier else "Sconosciuto"
            
            result.append(batch_dict)
        
        return result
    
    def add_batch(
        self,
        supplier_id: int,
        product_name: str,
        batch_number: str,
        peptide_ids: List[int] = None,
        peptide_amounts: Dict[int, float] = None,
        **kwargs
    ) -> int:
        """
        Aggiunge un nuovo batch con composizione peptidi.
        
        Args:
            supplier_id: ID fornitore
            product_name: Nome prodotto
            batch_number: Numero batch
            peptide_ids: Lista ID peptidi (opzionale per blend)
            peptide_amounts: Dict {peptide_id: mg_amount} (opzionale)
            **kwargs: Altri campi batch
        
        Returns:
            ID del batch creato
        """
        # Crea batch
        batch = Batch(
            supplier_id=supplier_id,
            product_name=product_name,
            batch_number=batch_number,
            **kwargs
        )
        
        batch_id = self.db.batches.create(batch)
        
        # Aggiungi composizione se specificata
        if peptide_ids:
            for peptide_id in peptide_ids:
                mg_amount = None
                if peptide_amounts and peptide_id in peptide_amounts:
                    mg_amount = peptide_amounts[peptide_id]
                
                try:
                    self.db.batch_composition.add_peptide_to_batch(
                        batch_id=batch_id,
                        peptide_id=peptide_id,
                        mg_amount=mg_amount
                    )
                except ValueError as e:
                    print(f"⚠️  {e}")
        
        print(f"✅ Batch '{product_name}' aggiunto (ID: {batch_id})")
        return batch_id
    
    def update_batch(
        self, 
        batch_id: int,
        peptide_ids: List[int] = None,
        peptide_amounts: Dict[int, float] = None,
        **kwargs
    ) -> bool:
        """
        Aggiorna batch esistente.
        
        Args:
            batch_id: ID batch
            peptide_ids: Nuova lista peptidi (opzionale, sovrascrive composizione)
            peptide_amounts: Dict {peptide_id: mg_amount}
            **kwargs: Campi batch da aggiornare
        
        Returns:
            True se aggiornato
        """
        batch = self.db.batches.get_by_id(batch_id)
        if not batch:
            print(f"❌ Batch #{batch_id} non trovato")
            return False
        
        # Aggiorna campi batch
        allowed_fields = [
            'supplier_id', 'product_name', 'batch_number',
            'manufacturing_date', 'expiration_date', 'mg_per_vial',
            'vials_count', 'vials_remaining', 'purchase_date',
            'price_per_vial', 'storage_location', 'notes', 'coa_path'
        ]
        
        for key, value in kwargs.items():
            if key in allowed_fields:
                setattr(batch, key, value)
        
        # Salva batch
        try:
            self.db.batches.update(batch)
        except ValueError as e:
            print(f"❌ Errore: {e}")
            return False
        
        # Aggiorna composizione se specificata
        if peptide_ids is not None:
            # Rimuovi composizione esistente
            self.db.batch_composition.clear_batch_composition(batch_id)
            
            # Aggiungi nuova composizione
            for peptide_id in peptide_ids:
                mg_amount = None
                if peptide_amounts and peptide_id in peptide_amounts:
                    mg_amount = peptide_amounts[peptide_id]
                
                try:
                    self.db.batch_composition.add_peptide_to_batch(
                        batch_id=batch_id,
                        peptide_id=peptide_id,
                        mg_amount=mg_amount
                    )
                except ValueError as e:
                    print(f"⚠️  {e}")
        
        print(f"✅ Batch ID {batch_id} aggiornato")
        return True
    
    def soft_delete_batch(self, batch_id: int) -> bool:
        """
        Elimina batch (soft delete).
        
        Args:
            batch_id: ID batch
        
        Returns:
            True se eliminato
        """
        success, message = self.db.batches.delete(batch_id, force=False)
        
        if success:
            print(f"✓ {message}")
        else:
            print(f"✗ {message}")
        
        return success
    
    def delete_batch(self, batch_id: int, force: bool = False) -> bool:
        """Alias per soft_delete_batch."""
        return self.db.batches.delete(batch_id, force=force)[0]
    
    def get_batch_details(self, batch_id: int) -> Optional[Dict]:
        """
        Recupera dettagli batch completi per GUI.
        
        Returns:
            Dict con:
            - Tutti i campi batch
            - 'composition': lista peptidi [{id, name, mg_amount}, ...]
            - 'preparations': lista preparazioni
            - 'supplier_name': nome fornitore
        """
        batch = self.db.batches.get_by_id(batch_id)
        if not batch:
            return None
        
        # 1. Dati batch base
        result = batch.to_dict()
        
        # 2. Composizione peptidi
        peptides = self.db.batch_composition.get_peptides_in_batch(batch_id)
        result['composition'] = peptides
        
        # 3. Preparazioni (usa vecchio manager - TODO: migrare)
        preparations = self._get_old_manager().get_preparations(batch_id=batch_id)
        result['preparations'] = preparations
        
        # 4. Nome fornitore (JOIN)
        supplier = self.db.suppliers.get_by_id(batch.supplier_id)
        result['supplier_name'] = supplier.name if supplier else "Sconosciuto"
        
        return result
    
    def get_expiring_batches(self, days: int = 60, limit: int = 5) -> List[Dict]:
        """
        Recupera batches in scadenza entro N giorni.
        
        Args:
            days: Giorni di anticipo (default: 60)
            limit: Numero massimo risultati
        
        Returns:
            Lista di dict batch in scadenza
        """
        batches = self.db.batches.get_expiring_soon(days=days)
        
        # Converti a dict e limita risultati
        result = [b.to_dict() for b in batches[:limit]]
        
        return result
    
    def adjust_batch_vials(
        self, 
        batch_id: int, 
        adjustment: int, 
        reason: str = None
    ) -> bool:
        """
        Corregge conteggio fiale batch.
        
        Args:
            batch_id: ID batch
            adjustment: Numero fiale da aggiungere (+) o rimuovere (-)
            reason: Motivo correzione (opzionale)
        
        Returns:
            True se successo
        """
        success, message = self.db.batches.adjust_vials(
            batch_id, 
            adjustment, 
            reason
        )
        
        if success:
            print(f"✅ {message}")
        else:
            print(f"❌ {message}")
        
        return success
    
    def get_inventory_summary(self) -> Dict:
        """Calcola statistiche inventario complete per dashboard."""
        # 1. Statistiche batches
        batch_stats = self.db.batches.get_inventory_summary()
        
        # 2. Peptidi unici
        unique_peptides = self.db.peptides.count()
        
        # 3. Valore totale inventario
        query = '''
            SELECT SUM(vials_remaining * COALESCE(price_per_vial, 0))
            FROM batches WHERE deleted_at IS NULL AND vials_remaining > 0
        '''
        cursor = self.conn.cursor()
        cursor.execute(query)
        row = cursor.fetchone()
        total_value = float(row[0]) if row and row[0] else 0.0
        
        # 4. Batches in scadenza (entro 60 giorni)
        expiring = self.db.batches.get_expiring_soon(days=60)
        expiring_soon = len(expiring)
        
        # Combina
        return {
            **batch_stats,
            'unique_peptides': unique_peptides,
            'total_value': total_value,
            'expiring_soon': expiring_soon,
        }
    
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
    
    def add_preparation(
        self,
        batch_id: int,
        vials_used: int,
        volume_ml: float,
        preparation_date: str = None,
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
            preparation_date: Data preparazione (YYYY-MM-DD), default oggi
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
            diluent=diluent,
            preparation_date=date.fromisoformat(preparation_date) if preparation_date else None,
            expiry_date=date.fromisoformat(expiry_date) if expiry_date else None,
            storage_location=storage_location,
            notes=notes
        )
        
        prep_id = self.db.preparations.create(preparation)
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
            return False
        
        # Aggiorna campi permessi
        allowed_fields = {
            'volume_remaining_ml': lambda v: Decimal(str(v)),
            'expiry_date': lambda v: date.fromisoformat(v) if v and isinstance(v, str) else v,
            'storage_location': lambda v: v,
            'notes': lambda v: v,
            'diluent': lambda v: v
        }
        
        from datetime import date
        from decimal import Decimal
        
        for key, value in kwargs.items():
            if key in allowed_fields:
                converter = allowed_fields[key]
                setattr(preparation, key, converter(value))
        
        return self.db.preparations.update(preparation)
    
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
        return success
    
    def get_preparation_details(self, prep_id: int) -> Optional[Dict]:
        """
        Recupera dettagli preparazione con informazioni batch (usa nuova architettura).
        
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
            result['batch_supplier_id'] = batch.supplier_id
            
            # Aggiungi composizione peptidi dal batch
            compositions = self.db.batch_composition.get_compositions_for_batch(preparation.batch_id)
            result['peptides'] = []
            for comp in compositions:
                peptide = self.db.peptides.get_by_id(comp.peptide_id)
                if peptide:
                    result['peptides'].append({
                        'peptide_id': peptide.id,
                        'name': peptide.name,
                        'mg_per_vial': float(comp.mg_per_vial) if comp.mg_per_vial else 0
                    })
        
        return result
    
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
        success, message = self.db.preparations.use_volume(prep_id, ml_used)
        
        if not success:
            return False
        
        # TODO: Quando migri administrations, crea record qui
        # if administration_datetime:
        #     self.db.administrations.create(...)
        
        return True
    
    def reconcile_preparation_volumes(self, prep_id: int = None) -> Dict:
        """
        Riconcilia volumi preparazioni (usa nuova architettura).
        
        Args:
            prep_id: ID preparazione specifica (None = tutte)
            
        Returns:
            Dict con statistiche riconciliazione
        """
        discrepancies = []
        reconciled = 0
        
        if prep_id:
            # Riconcilia singola preparazione
            success, message = self.db.preparations.recalculate_volume(prep_id)
            if success:
                reconciled += 1
            else:
                discrepancies.append({
                    'prep_id': prep_id,
                    'error': message
                })
        else:
            # Riconcilia tutte le preparazioni
            preparations = self.db.preparations.get_all(only_active=True)
            for prep in preparations:
                success, message = self.db.preparations.recalculate_volume(prep.id)
                if success:
                    reconciled += 1
                else:
                    discrepancies.append({
                        'prep_id': prep.id,
                        'error': message
                    })
        
        return {
            'status': 'ok',
            'reconciled': reconciled,
            'discrepancies': discrepancies
        }
    
    # ==================== NON ANCORA MIGRATI (FALLBACK) ====================
    
    def get_protocols(self, **kwargs) -> List[Dict]:
        """Delega al vecchio manager (TODO: migrare)."""
        return self._get_old_manager().get_protocols(**kwargs)
    
    def add_protocol(self, *args, **kwargs) -> int:
        """Delega al vecchio manager (TODO: migrare)."""
        return self._get_old_manager().add_protocol(*args, **kwargs)
    
    def update_protocol(self, *args, **kwargs) -> bool:
        """Delega al vecchio manager (TODO: migrare)."""
        return self._get_old_manager().update_protocol(*args, **kwargs)
    
    def soft_delete_protocol(self, *args, **kwargs) -> bool:
        """Delega al vecchio manager (TODO: migrare)."""
        return self._get_old_manager().soft_delete_protocol(*args, **kwargs)
    
    def get_protocol_details(self, *args, **kwargs):
        """Delega al vecchio manager (TODO: migrare)."""
        return self._get_old_manager().get_protocol_details(*args, **kwargs)
    
    def update_administration(self, *args, **kwargs) -> bool:
        """Delega al vecchio manager (TODO: migrare)."""
        return self._get_old_manager().update_administration(*args, **kwargs)
    
    def soft_delete_administration(self, *args, **kwargs) -> bool:
        """Delega al vecchio manager (TODO: migrare)."""
        return self._get_old_manager().soft_delete_administration(*args, **kwargs)
    
    def get_all_administrations_df(self, *args, **kwargs):
        """Delega al vecchio manager (TODO: migrare)."""
        return self._get_old_manager().get_all_administrations_df(*args, **kwargs)
    
    def check_data_integrity(self, *args, **kwargs):
        """Delega al vecchio manager (TODO: migrare)."""
        return self._get_old_manager().check_data_integrity(*args, **kwargs)


# Per mantenere il vecchio import path
__all__ = [
    'PeptideManager',
    'DatabaseManager',
    'Supplier',
    'SupplierRepository',
    'Peptide',
    'PeptideRepository',
    'Batch',
    'BatchRepository',
    'BatchComposition',
    'BatchCompositionRepository',
]
