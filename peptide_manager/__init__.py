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
from datetime import datetime
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
    PreparationRepository,
    Protocol,
    ProtocolRepository,
    Administration,
    AdministrationRepository
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
                # Silenzioso: usato solo per check_data_integrity()
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
        supplier_id: int = None,
        product_name: str = None,
        batch_number: str = None,
        peptide_ids: List[int] = None,
        peptide_amounts: Dict[int, float] = None,
        supplier_name: str = None,  # Legacy: nome invece di ID
        composition: List = None,  # Legacy: List[Tuple[name, mg]]
        vials_count: int = None,
        mg_per_vial: float = None,
        total_price: float = None,
        purchase_date: str = None,
        expiry_date: str = None,
        storage_location: str = None,
        **kwargs
    ) -> int:
        """
        Aggiunge un nuovo batch con composizione peptidi.
        
        Supporta sia nuova API che vecchia per compatibilità.
        
        Args:
            supplier_id: ID fornitore (nuovo)
            supplier_name: Nome fornitore (legacy)
            product_name: Nome prodotto
            batch_number: Numero batch
            peptide_ids: Lista ID peptidi (nuovo)
            peptide_amounts: Dict {peptide_id: mg_amount} (nuovo)
            composition: List[Tuple[name, mg]] (legacy)
            vials_count: Numero fiale
            mg_per_vial: Mg per fiala
            total_price: Prezzo totale
            purchase_date: Data acquisto
            expiry_date: Data scadenza
            storage_location: Posizione storage
            **kwargs: Altri campi batch
        
        Returns:
            ID del batch creato
        """
        # Compatibilità backward: converti supplier_name in supplier_id
        if supplier_name and not supplier_id:
            suppliers = self.db.suppliers.get_all()
            supplier = next((s for s in suppliers if s.name == supplier_name), None)
            if not supplier:
                raise ValueError(f"Supplier '{supplier_name}' non trovato")
            supplier_id = supplier.id
        
        # Se non c'è batch_number, genera uno automatico
        if not batch_number:
            from datetime import datetime
            batch_number = f"BATCH-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        # Compatibilità backward: converti composition in peptide_ids/amounts
        if composition and not peptide_ids:
            peptide_ids = []
            peptide_amounts = {}
            
            for item in composition:
                if isinstance(item, tuple) and len(item) == 2:
                    peptide_name, mg_amount = item
                    # Cerca peptide per nome
                    peptides = self.db.peptides.get_all()
                    peptide = next((p for p in peptides if p.name == peptide_name), None)
                    if peptide:
                        peptide_ids.append(peptide.id)
                        peptide_amounts[peptide.id] = float(mg_amount)
        
        # Prepara kwargs per Batch
        batch_kwargs = {}
        if vials_count is not None:
            batch_kwargs['vials_count'] = vials_count
            batch_kwargs['vials_remaining'] = vials_count  # Inizialmente tutti disponibili
        if mg_per_vial is not None:
            batch_kwargs['mg_per_vial'] = mg_per_vial
        if total_price is not None:
            # Mantieni total_price per compatibilità DB
            batch_kwargs['total_price'] = total_price
            if vials_count:
                # Calcola anche price_per_vial
                batch_kwargs['price_per_vial'] = total_price / vials_count
        if purchase_date:
            batch_kwargs['purchase_date'] = purchase_date
        if expiry_date:
            batch_kwargs['expiration_date'] = expiry_date
        if storage_location:
            batch_kwargs['storage_location'] = storage_location
        
        # Merge con altri kwargs (escludendo total_price se già gestito)
        for k, v in kwargs.items():
            if k not in batch_kwargs:
                batch_kwargs[k] = v
        
        # Crea batch
        batch = Batch(
            supplier_id=supplier_id,
            product_name=product_name,
            batch_number=batch_number,
            **batch_kwargs
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
        # Aggiungi alias 'name' per compatibilità GUI (defensive)
        for peptide in peptides:
            # Prefer explicit keys if present, otherwise fallback safely
            peptide_name = peptide.get('peptide_name') or peptide.get('name') or peptide.get('peptide_id')
            peptide['name'] = peptide_name
            # Normalize mg amount: prefer existing mg_amount, else mg_per_vial
            if peptide.get('mg_amount') is None and peptide.get('mg_per_vial') is not None:
                peptide['mg_amount'] = peptide['mg_per_vial']  # Alias per compatibilità
        result['composition'] = peptides
        
        # 3. Preparazioni (usa nuova architettura)
        preparations = self.get_preparations(batch_id=batch_id)
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
        
        # Arricchisci con informazioni batch per compatibilità GUI
        result = []
        for p in preparations:
            prep_dict = p.to_dict()
            
            # Aggiungi info batch
            batch = self.db.batches.get_by_id(p.batch_id)
            if batch:
                prep_dict['batch_product'] = batch.product_name
                prep_dict['batch_number'] = batch.batch_number
                prep_dict['supplier_id'] = batch.supplier_id
            else:
                prep_dict['batch_product'] = 'N/A'
                prep_dict['batch_number'] = 'N/A'
                prep_dict['supplier_id'] = None
            
            result.append(prep_dict)
        
        return result
    
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
        
        # Converti Decimal in float per compatibilità GUI
        from decimal import Decimal
        for key, value in result.items():
            if isinstance(value, Decimal):
                result[key] = float(value)
        
        # Aggiungi informazioni batch (JOIN)
        batch = self.db.batches.get_by_id(preparation.batch_id)
        if batch:
            result['batch_product'] = batch.product_name
            result['product_name'] = batch.product_name  # Alias per compatibilità GUI
            result['batch_number'] = batch.batch_number
            result['batch_supplier_id'] = batch.supplier_id
            
            # Calcola concentrazione se abbiamo mg_per_vial
            if batch.mg_per_vial and preparation.volume_ml:
                total_mg = float(batch.mg_per_vial) * preparation.vials_used
                concentration = total_mg / float(preparation.volume_ml)
                result['concentration_mg_ml'] = concentration
            
            # Aggiungi composizione peptidi dal batch (defensive keys)
            compositions = self.db.batch_composition.get_peptides_in_batch(preparation.batch_id)
            result['peptides'] = []
            for comp in compositions:
                peptide_name = comp.get('peptide_name') or comp.get('name') or comp.get('peptide_id')
                # mg may be stored as 'mg_per_vial' or 'mg_amount'
                mg_value = None
                if comp.get('mg_per_vial') is not None:
                    mg_value = comp.get('mg_per_vial')
                elif comp.get('mg_amount') is not None:
                    mg_value = comp.get('mg_amount')

                try:
                    mg_float = float(mg_value) if mg_value is not None else 0.0
                except Exception:
                    mg_float = 0.0

                result['peptides'].append({
                    'peptide_id': comp.get('peptide_id'),
                    'name': peptide_name,
                    'mg_per_vial': mg_float
                })
        
        # Conta somministrazioni per questa preparazione
        admin_count = self.db.conn.execute(
            'SELECT COUNT(*) FROM administrations WHERE preparation_id = ? AND deleted_at IS NULL',
            (prep_id,)
        ).fetchone()[0]
        result['administrations_count'] = admin_count
        
        return result
    
    def use_preparation(
        self,
        prep_id: int,
        ml_used: float,
        administration_datetime: str = None,
        injection_site: str = None,
        notes: str = None,
        protocol_id: int = None,
        injection_method: str = None,
        side_effects: str = None
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
            injection_method: Metodo iniezione (compatibilità)
            side_effects: Effetti collaterali (compatibilità)
            
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
    
    def record_wastage(
        self,
        prep_id: int,
        volume_ml: float,
        reason: str = 'spillage',
        notes: str = None
    ) -> tuple:
        """
        Registra spreco su preparazione (usa nuova architettura).
        
        Args:
            prep_id: ID preparazione
            volume_ml: Volume sprecato in ml
            reason: Motivo (measurement_error, spillage, contamination, other)
            notes: Note aggiuntive
            
        Returns:
            Tuple (successo, messaggio)
        """
        return self.db.preparations.record_wastage(prep_id, volume_ml, reason, notes)
    
    def get_wastage_history(self, prep_id: int) -> List[Dict]:
        """
        Recupera storico wastage di una preparazione.
        
        Parsa il campo wastage_notes che contiene le registrazioni nel formato:
        "YYYY-MM-DD: X.XX ml - motivo/note"
        
        Args:
            prep_id: ID preparazione
            
        Returns:
            Lista di dict con: date, volume_ml, reason, notes
        """
        prep = self.db.preparations.get_by_id(prep_id)
        if not prep or not prep.wastage_notes:
            return []
        
        history = []
        lines = prep.wastage_notes.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            try:
                # Parse formato: "YYYY-MM-DD: X.XX ml - note"
                parts = line.split(':', 1)
                if len(parts) < 2:
                    continue
                
                date_str = parts[0].strip()
                rest = parts[1].strip()
                
                # Estrai volume (cerca "X.XX ml")
                import re
                volume_match = re.search(r'([\d.]+)\s*ml', rest)
                volume_ml = float(volume_match.group(1)) if volume_match else 0.0
                
                # Estrai note (tutto dopo " - ")
                notes_part = rest.split(' - ', 1)
                notes = notes_part[1] if len(notes_part) > 1 else rest
                
                history.append({
                    'date': date_str,
                    'volume_ml': volume_ml,
                    'reason': prep.wastage_reason or 'other',
                    'notes': notes
                })
            except Exception:
                # Skip righe malformate
                continue
        
        return history
    
    def reconcile_preparation_volumes(self, prep_id: int = None) -> Dict:
        """
        Riconcilia volumi preparazioni (usa nuova architettura).
        
        Args:
            prep_id: ID preparazione specifica (None = tutte)
            
        Returns:
            Dict con statistiche riconciliazione compatibile con GUI:
            {
                'checked': int,
                'fixed': int,
                'total_diff': float,
                'details': [...]
            }
        """
        cursor = self.conn.cursor()
        
        # Ottieni tutte le preparazioni da controllare
        if prep_id:
            cursor.execute('''
                SELECT p.id, p.volume_ml, p.volume_remaining_ml, b.product_name
                FROM preparations p
                JOIN batches b ON p.batch_id = b.id
                WHERE p.id = ? AND p.deleted_at IS NULL
            ''', (prep_id,))
        else:
            cursor.execute('''
                SELECT p.id, p.volume_ml, p.volume_remaining_ml, b.product_name
                FROM preparations p
                JOIN batches b ON p.batch_id = b.id
                WHERE p.deleted_at IS NULL
            ''')
        
        preparations = cursor.fetchall()
        
        checked = 0
        fixed = 0
        total_diff = 0.0
        details = []
        
        for prep_id_item, volume_initial, volume_current, product_name in preparations:
            checked += 1
            
            # Recupera wastage registrato per questa preparazione
            cursor.execute('''
                SELECT COALESCE(wastage_ml, 0), status
                FROM preparations
                WHERE id = ?
            ''', (prep_id_item,))
            
            wastage_result = cursor.fetchone()
            wastage_ml = wastage_result[0] if wastage_result else 0
            prep_status = wastage_result[1] if wastage_result else 'active'
            
            # Calcola volume atteso basandosi sulle somministrazioni attive E wastage
            cursor.execute('''
                SELECT COALESCE(SUM(dose_ml), 0)
                FROM administrations
                WHERE preparation_id = ? AND deleted_at IS NULL
            ''', (prep_id_item,))
            
            total_used = cursor.fetchone()[0]
            volume_expected = volume_initial - total_used - wastage_ml
            
            # Se preparazione è depleted con wastage, il volume rimanente deve essere 0
            if prep_status == 'depleted' and wastage_ml > 0:
                volume_expected = 0.0
            
            difference = volume_current - volume_expected
            
            # Se c'è una differenza significativa, correggi
            if abs(difference) > 0.001:
                fixed += 1
                total_diff += abs(difference)
                
                # Aggiorna il volume (e status se necessario)
                cursor.execute('''
                    UPDATE preparations
                    SET volume_remaining_ml = ?,
                        status = CASE 
                            WHEN ? <= 0 THEN 'depleted'
                            ELSE status
                        END
                    WHERE id = ?
                ''', (volume_expected, volume_expected, prep_id_item))
                
                details.append({
                    'prep_id': prep_id_item,
                    'product_name': product_name,
                    'old_volume': volume_current,
                    'new_volume': volume_expected,
                    'difference': difference
                })
        
        self.conn.commit()
        
        return {
            'checked': checked,
            'fixed': fixed,
            'total_diff': total_diff,
            'details': details
        }
    
    # ==================== PROTOCOLS (MIGRATO ✅) ====================
    
    def get_protocols(self, active_only: bool = True) -> List[Dict]:
        """
        Recupera protocolli (usa nuova architettura).
        
        Args:
            active_only: Solo protocolli attivi
        
        Returns:
            Lista di dict (compatibile con vecchia interfaccia)
        """
        protocols = self.db.protocols.get_all(active_only=active_only)
        result = []
        
        for p in protocols:
            protocol_dict = p.to_dict()
            
            # Recupera peptidi e dosi per questo protocollo
            cursor = self.conn.cursor()
            peptides_info = cursor.execute('''
                SELECT pep.name, pp.target_dose_mcg
                FROM protocol_peptides pp
                JOIN peptides pep ON pp.peptide_id = pep.id
                WHERE pp.protocol_id = ?
                ORDER BY pep.name
            ''', (p.id,)).fetchall()
            
            # Aggiungi info peptidi formattate (es: "Ipamorelin 250mcg, BPC-157 500mcg")
            if peptides_info:
                peptides_str = ", ".join([f"{name} {int(dose)}mcg" for name, dose in peptides_info])
                protocol_dict['peptides_display'] = peptides_str
                # Prendi la prima dose come dose rappresentativa (per retrocompatibilità)
                protocol_dict['first_dose_mcg'] = peptides_info[0][1]
            else:
                protocol_dict['peptides_display'] = "N/A"
                protocol_dict['first_dose_mcg'] = None
            
            result.append(protocol_dict)
        
        return result
    
    def add_protocol(
        self,
        name: str,
        frequency_per_day: int = 1,
        dose_ml: float = None,
        days_on: int = None,
        days_off: int = 0,
        cycle_duration_weeks: int = None,
        peptides: List = None,  # List[Tuple[str, float]] o List[Tuple[int, float]]
        description: str = None,
        notes: str = None
    ) -> int:
        """
        Crea nuovo protocollo (usa nuova architettura).
        
        Args:
            name: Nome protocollo
            dose_ml: Dose in ml per somministrazione
            frequency_per_day: Frequenza al giorno
            days_on: Giorni ON del ciclo
            days_off: Giorni OFF del ciclo
            cycle_duration_weeks: Durata ciclo in settimane
            peptides: Lista di (peptide_name/id, target_dose_mcg)
            description: Descrizione
            notes: Note
        
        Returns:
            ID protocollo creato
        """
        from decimal import Decimal
        
        protocol = Protocol(
            name=name,
            description=description,
            dose_ml=Decimal(str(dose_ml)) if dose_ml else None,
            frequency_per_day=frequency_per_day,
            days_on=days_on,
            days_off=days_off,
            cycle_duration_weeks=cycle_duration_weeks,
            notes=notes,
            active=True
        )
        
        protocol_id = self.db.protocols.create(protocol)
        
        # Aggiungi peptidi se specificati
        if peptides:
            for peptide_ref, target_dose_mcg in peptides:
                # Se è una stringa, cerca il peptide per nome
                if isinstance(peptide_ref, str):
                    # Cerca peptide esistente
                    all_peptides = self.db.peptides.get_all()
                    peptide = next((p for p in all_peptides if p.name == peptide_ref), None)
                    
                    if not peptide:
                        # Crea nuovo peptide se non esiste
                        from .models import Peptide
                        new_peptide = Peptide(name=peptide_ref)
                        peptide_id = self.db.peptides.create(new_peptide)
                    else:
                        peptide_id = peptide.id
                else:
                    # Assume sia un ID
                    peptide_id = peptide_ref
                
                # Aggiungi al protocollo
                self.db.protocols.add_peptide_to_protocol(
                    protocol_id,
                    peptide_id,
                    float(target_dose_mcg)
                )
        
        return protocol_id
    
    def update_protocol(self, protocol_id: int, **kwargs) -> bool:
        """
        Aggiorna protocollo (usa nuova architettura).
        
        Args:
            protocol_id: ID protocollo
            **kwargs: Campi da aggiornare
        
        Returns:
            True se aggiornato
        """
        protocol = self.db.protocols.get_by_id(protocol_id)
        if not protocol:
            return False
        
        # Campi permessi
        allowed_fields = {
            'name': lambda v: v,
            'description': lambda v: v,
            'dose_ml': lambda v: Decimal(str(v)),
            'frequency_per_day': lambda v: int(v),
            'days_on': lambda v: int(v) if v is not None else None,
            'days_off': lambda v: int(v),
            'cycle_duration_weeks': lambda v: int(v) if v is not None else None,
            'notes': lambda v: v,
            'active': lambda v: bool(v)
        }
        
        from decimal import Decimal
        
        for key, value in kwargs.items():
            if key in allowed_fields:
                converter = allowed_fields[key]
                setattr(protocol, key, converter(value))
        
        return self.db.protocols.update(protocol)
    
    def soft_delete_protocol(
        self,
        protocol_id: int,
        unlink_administrations: bool = True
    ) -> bool:
        """
        Elimina protocollo (usa nuova architettura).
        
        Args:
            protocol_id: ID protocollo
            unlink_administrations: Se True, scollega amministrazioni
        
        Returns:
            True se eliminato
        """
        success, message = self.db.protocols.delete(
            protocol_id,
            force=False,
            unlink_administrations=unlink_administrations
        )
        return success
    
    def get_protocol_details(self, protocol_id: int) -> Optional[Dict]:
        """
        Recupera dettagli protocollo con peptidi e statistiche (usa nuova architettura).
        
        Args:
            protocol_id: ID protocollo
        
        Returns:
            Dict con dettagli completi o None
        """
        protocol = self.db.protocols.get_by_id(protocol_id)
        if not protocol:
            return None
        
        result = protocol.to_dict()
        
        # Aggiungi peptidi
        result['peptides'] = self.db.protocols.get_peptides_for_protocol(protocol_id)
        
        # Aggiungi statistiche
        stats = self.db.protocols.get_statistics(protocol_id)
        if stats:
            result['administrations_count'] = stats['count']
            result['first_administration'] = stats['first_date']
            result['last_administration'] = stats['last_date']
            result['total_ml_administered'] = stats['total_ml']
        
        return result
    
    def activate_protocol(self, protocol_id: int) -> bool:
        """
        Attiva protocollo (usa nuova architettura).
        
        Args:
            protocol_id: ID protocollo
        
        Returns:
            True se attivato
        """
        success, message = self.db.protocols.activate(protocol_id)
        return success
    
    def deactivate_protocol(self, protocol_id: int) -> bool:
        """
        Disattiva protocollo (usa nuova architettura).
        
        Args:
            protocol_id: ID protocollo
        
        Returns:
            True se disattivato
        """
        success, message = self.db.protocols.deactivate(protocol_id)
        return success
    
    def get_protocol_statistics(self, protocol_id: int) -> Dict:
        """
        Recupera statistiche protocollo (usa nuova architettura).
        
        Args:
            protocol_id: ID protocollo
        
        Returns:
            Dict con statistiche
        """
        stats = self.db.protocols.get_statistics(protocol_id)
        return stats if stats else {}
    
    # ==================== ADMINISTRATIONS ====================
    
    def add_administration(
        self,
        preparation_id: int,
        dose_ml: float,
        administration_datetime: Optional[datetime] = None,
        protocol_id: Optional[int] = None,
        injection_site: Optional[str] = None,
        injection_method: Optional[str] = None,
        notes: Optional[str] = None,
        side_effects: Optional[str] = None
    ) -> int:
        """
        Registra una somministrazione di peptide.
        
        Args:
            preparation_id: ID preparazione
            dose_ml: Dose somministrata in ml
            administration_datetime: Data/ora somministrazione (default: ora corrente)
            protocol_id: ID protocollo opzionale
            injection_site: Sito iniezione
            injection_method: Metodo iniezione
            notes: Note
            side_effects: Effetti collaterali
            
        Returns:
            ID somministrazione creata
            
        Raises:
            ValueError: Se dati non validi o volume insufficiente
        """
        from .models.administration import Administration
        
        admin = Administration(
            preparation_id=preparation_id,
            dose_ml=dose_ml,
            administration_datetime=administration_datetime or datetime.now(),
            protocol_id=protocol_id,
            injection_site=injection_site,
            injection_method=injection_method,
            notes=notes,
            side_effects=side_effects
        )
        
        return self.db.administrations.create(admin)
    
    def get_administrations(
        self,
        protocol_id: Optional[int] = None,
        preparation_id: Optional[int] = None,
        days_back: Optional[int] = None,
        include_deleted: bool = False
    ) -> list[dict]:
        """
        Recupera somministrazioni con dettagli completi.
        
        Args:
            protocol_id: Filtra per protocollo
            preparation_id: Filtra per preparazione
            days_back: Filtra ultimi N giorni
            include_deleted: Include eliminate
            
        Returns:
            Lista di dict con dettagli somministrazioni
        """
        return self.db.administrations.get_with_details(
            protocol_id=protocol_id,
            preparation_id=preparation_id,
            days_back=days_back,
            include_deleted=include_deleted
        )
    
    def update_administration(
        self,
        admin_id: int,
        protocol_id: Optional[int] = None,
        administration_datetime: Optional[datetime] = None,
        injection_site: Optional[str] = None,
        injection_method: Optional[str] = None,
        notes: Optional[str] = None,
        side_effects: Optional[str] = None
    ) -> bool:
        """
        Aggiorna somministrazione esistente.
        
        NOTA: Non permette modifica dose_ml per evitare inconsistenze volume.
        
        Args:
            admin_id: ID somministrazione
            protocol_id: Nuovo ID protocollo
            administration_datetime: Nuova data/ora
            injection_site: Nuovo sito iniezione
            injection_method: Nuovo metodo iniezione
            notes: Nuove note
            side_effects: Nuovi effetti collaterali
            
        Returns:
            True se aggiornato con successo
        """
        # Recupera somministrazione esistente
        admin = self.db.administrations.get_by_id(admin_id)
        if not admin:
            raise ValueError(f"Somministrazione #{admin_id} non trovata")
        
        # Aggiorna solo campi specificati
        if protocol_id is not None:
            admin.protocol_id = protocol_id
        if administration_datetime is not None:
            admin.administration_datetime = administration_datetime
        if injection_site is not None:
            admin.injection_site = injection_site
        if injection_method is not None:
            admin.injection_method = injection_method
        if notes is not None:
            admin.notes = notes
        if side_effects is not None:
            admin.side_effects = side_effects
        
        return self.db.administrations.update(admin)
    
    def soft_delete_administration(
        self,
        admin_id: int,
        restore_volume: bool = False
    ) -> tuple[bool, str]:
        """
        Elimina somministrazione (soft delete).
        
        Args:
            admin_id: ID somministrazione
            restore_volume: Se True, ripristina volume alla preparazione
            
        Returns:
            (success: bool, message: str)
        """
        return self.db.administrations.delete(
            admin_id=admin_id,
            force=False,
            restore_volume=restore_volume
        )
    
    def delete_administration(
        self,
        admin_id: int,
        restore_volume: bool = False
    ) -> tuple[bool, str]:
        """
        Alias per soft_delete_administration (backward compatibility).
        """
        return self.soft_delete_administration(admin_id, restore_volume)
    
    def calculate_multi_prep_distribution(
        self,
        required_ml: float,
        available_preps: list
    ) -> tuple[bool, list, str]:
        """
        Calcola distribuzione dose su più preparazioni (FIFO per scadenza).
        
        Args:
            required_ml: Volume richiesto (ml)
            available_preps: Lista preparazioni disponibili (dict con id, remaining_volume_ml, expiry_date)
        
        Returns:
            (success, distribution, message)
            - success: bool se distribuzione possibile
            - distribution: lista [{'prep_id': int, 'volume_ml': float}, ...]
            - message: messaggio esplicativo
        """
        from decimal import Decimal
        return self.db.administrations.calculate_multi_prep_distribution(
            Decimal(str(required_ml)),
            available_preps
        )
    
    def create_multi_prep_administration(
        self,
        distribution: list,
        protocol_id: int,
        administration_datetime: str,
        injection_site: str,
        injection_method: str,
        notes: str = None,
        side_effects: str = None,
        cycle_id: int = None
    ) -> tuple[bool, str]:
        """
        Crea somministrazione multi-preparazione (transazionale).
        
        Args:
            distribution: Lista [{'prep_id': int, 'ml': float}, ...] (output di calculate_multi_prep_distribution)
            protocol_id: ID protocollo
            administration_datetime: Data/ora somministrazione (ISO format)
            injection_site: Sito iniezione
            injection_method: Metodo iniezione
            notes: Note opzionali
            side_effects: Effetti collaterali
            cycle_id: ID ciclo (opzionale)
        
        Returns:
            (success, admin_ids, message) - admin_ids è la lista degli ID creati
        """
        from decimal import Decimal
        
        # Converti distribution in Decimal per backend
        distribution_decimal = [
            {'prep_id': d['prep_id'], 'ml': Decimal(str(d['ml']))}
            for d in distribution
        ]
        
        success, admin_ids, message = self.db.administrations.create_multi_prep_administration(
            distribution=distribution_decimal,
            protocol_id=protocol_id,
            administration_datetime=administration_datetime,
            injection_site=injection_site,
            injection_method=injection_method,
            notes=notes,
            side_effects=side_effects,
            cycle_id=cycle_id
        )
        
        return success, admin_ids, message
    
    def get_all_administrations_df(self):
        """
        Recupera tutte le somministrazioni come DataFrame.
        
        Returns:
            pandas.DataFrame con tutte le somministrazioni
        """
        import pandas as pd
        from datetime import datetime
        
        administrations = self.db.administrations.get_with_details()
        
        if not administrations:
            # DataFrame vuoto con colonne corrette
            return pd.DataFrame(columns=[
                'id', 'preparation_id', 'preparation_display', 'protocol_id', 'protocol_name',
                'administration_datetime', 'dose_ml', 'dose_mcg', 'date',
                'injection_site', 'injection_method', 'notes', 'side_effects',
                'batch_product', 'peptide_names'
            ])
        
        df = pd.DataFrame(administrations)
        
        # Aggiungi colonna date (solo data senza ora)
        # Usa format='mixed' per gestire datetime con/senza microsecondi
        df['date'] = pd.to_datetime(df['administration_datetime'], format='mixed').dt.date
        
        # Aggiungi colonna time (solo ora senza data)
        df['time'] = pd.to_datetime(df['administration_datetime'], format='mixed').dt.time
        
        # Calcola dose_mcg: devo recuperare mg_per_vial dalla preparazione
        # Per ora uso una stima basata su batch_product (TODO: migliorare)
        # Assumo dose_ml * concentrazione_tipica (es. 1mg/ml = 1000mcg/ml)
        # La GUI legacy usava preparazione con mg totali / volume
        # Per compatibility, calcolo da preparations
        df['dose_mcg'] = df.apply(lambda row: self._calculate_dose_mcg(
            row['preparation_id'], row['dose_ml']
        ), axis=1)
        
        # Aggiungi colonna preparation_display con info leggibili
        df['preparation_display'] = df.apply(lambda row: self._format_preparation_display(
            row['preparation_id']
        ), axis=1)
        
        return df
    
    def _calculate_dose_mcg(self, preparation_id: int, dose_ml: float) -> float:
        """
        Calcola dose in microgrammi per una somministrazione.
        
        Args:
            preparation_id: ID preparazione
            dose_ml: Dose in millilitri
            
        Returns:
            Dose in microgrammi
        """
        try:
            # Recupera preparazione per calcolare concentrazione
            prep = self.db.preparations.get_by_id(preparation_id)
            if not prep:
                return 0.0
            
            # Recupera batch per mg_per_vial
            batch = self.db.batches.get_by_id(prep.batch_id)
            if not batch or not batch.mg_per_vial:
                return 0.0
            
            # Calcola concentrazione: (mg_per_vial * vials_used) / volume_ml
            total_mg = float(batch.mg_per_vial) * prep.vials_used
            concentration_mg_per_ml = total_mg / float(prep.volume_ml)
            
            # Dose in mcg = dose_ml * concentration_mg_per_ml * 1000
            dose_mcg = dose_ml * concentration_mg_per_ml * 1000
            
            return float(dose_mcg)
        except Exception:
            return 0.0
    
    def _format_preparation_display(self, preparation_id: int) -> str:
        """
        Formatta informazioni preparazione per visualizzazione.
        
        Args:
            preparation_id: ID preparazione
            
        Returns:
            Stringa formattata (es: "Prep #10: 2.5mg/ml")
        """
        try:
            prep = self.db.preparations.get_by_id(preparation_id)
            if not prep:
                return f"Prep #{preparation_id}"
            
            batch = self.db.batches.get_by_id(prep.batch_id)
            if not batch or not batch.mg_per_vial:
                return f"Prep #{prep.id}"
            
            # Calcola concentrazione
            total_mg = float(batch.mg_per_vial) * prep.vials_used
            concentration = total_mg / float(prep.volume_ml)
            
            return f"Prep #{prep.id}: {concentration:.1f}mg/ml"
        except Exception:
            return f"Prep #{preparation_id}"

    def get_scheduled_administrations(self, target_date=None) -> list[dict]:
        """
        Recupera le somministrazioni DA FARE oggi basandosi sui cicli attivi e schedule.
        
        **WORKFLOW FLESSIBILE**: 
        - Calcola quando è PREVISTA la prossima dose basandosi su ultima somministrazione
        - Mostra dosi previste per oggi + dosi in ritardo
        - Permette all'utente di somministrare fuori schedule (sistema si adatta)

        Args:
            target_date: `datetime.date` o stringa ISO (YYYY-MM-DD). Se None usa oggi.

        Returns:
            Lista di dict con chiavi:
            - peptide_id: ID peptide
            - peptide_name: Nome peptide
            - target_dose_mcg: Dose target in mcg (dal protocollo ciclo)
            - suggested_dose_ml: Dose suggerita in ml (calcolata da prep disponibile)
            - preparation_id: ID preparazione suggerita (None se non disponibile)
            - preparation: Dettagli preparazione
            - protocol_name: Nome protocollo
            - cycle_id: ID ciclo
            - cycle_name: Nome ciclo
            - status: 'ready' | 'no_prep'
            - schedule_status: 'due_today' | 'overdue' | 'future' | 'completed'
            - next_due_date: Data prossima dose prevista (None se oggi)
            - days_overdue: Giorni di ritardo (0 se in orario)
        """
        from datetime import date, datetime, timedelta
        import json

        if target_date is None:
            target_date = date.today()
        elif isinstance(target_date, str):
            target_date = date.fromisoformat(target_date)

        # 1. Recupera TUTTE le somministrazioni del database (per calcolare schedule)
        all_admins = self.db.administrations.get_with_details(include_deleted=False)
        
        # Mappa: (cycle_id, peptide_id) -> ultima somministrazione
        last_admin_map = {}
        completed_today = set()  # Set di (cycle_id, peptide_id) già somministrati oggi
        
        for a in all_admins:
            adm_dt = a.get('administration_datetime')
            cycle_id = a.get('cycle_id')
            
            if adm_dt is None:
                continue

            # Normalize to datetime
            if isinstance(adm_dt, str):
                try:
                    adm_dt_obj = datetime.fromisoformat(adm_dt)
                except Exception:
                    try:
                        adm_dt_obj = datetime.strptime(adm_dt, '%Y-%m-%d %H:%M:%S')
                    except Exception:
                        continue
            else:
                adm_dt_obj = adm_dt

            adm_date = adm_dt_obj.date()
            
            # Trova peptidi in questa somministrazione
            prep = self.get_preparation_details(a.get('preparation_id'))
            if prep and prep.get('peptides'):
                for pep_comp in prep['peptides']:
                    peptide_id = pep_comp['peptide_id']
                    key = (cycle_id, peptide_id) if cycle_id else (None, peptide_id)
                    
                    # Aggiorna ultima somministrazione per questo peptide/ciclo
                    if key not in last_admin_map or adm_date > last_admin_map[key]['date']:
                        last_admin_map[key] = {
                            'date': adm_date,
                            'datetime': adm_dt_obj
                        }
                    
                    # Se somministrazione oggi, marca come completato
                    if adm_date == target_date and cycle_id:
                        completed_today.add(key)

        # 2. Recupera cicli attivi e genera schedule
        to_do = []
        try:
            active_cycles = self.get_cycles(active_only=False)
            active_cycles = [c for c in active_cycles if c.get('status') == 'active']
        except Exception:
            return to_do
        
        for cycle in active_cycles:
            cycle_id = cycle.get('id')
            cycle_name = cycle.get('name', f'Ciclo #{cycle_id}')
            protocol_snapshot = cycle.get('protocol_snapshot')
            
            if not protocol_snapshot:
                continue
            
            # Parse JSON snapshot
            if isinstance(protocol_snapshot, str):
                try:
                    proto = json.loads(protocol_snapshot)
                except Exception:
                    continue
            else:
                proto = protocol_snapshot
            
            # Estrai parametri schedule dal protocollo
            frequency_per_day = proto.get('frequency_per_day', 1)
            days_on = proto.get('days_on')
            days_off = proto.get('days_off', 0)
            
            # Calcola intervallo tra dosi (in giorni)
            if days_on and days_off and days_on > 0:
                # Pattern ON/OFF definito: usa somma come ciclo completo
                cycle_length = days_on + days_off
            elif frequency_per_day and frequency_per_day >= 1:
                # Frequenza giornaliera: dose ogni giorno
                cycle_length = 1
            else:
                # Default settimanale
                cycle_length = 7
            
            # Estrai peptidi dal protocollo
            peptides = proto.get('peptides', [])
            custom_doses = proto.get('custom_doses', {})
            
            for pep in peptides:
                peptide_id = pep.get('peptide_id')
                peptide_name = pep.get('name') or pep.get('peptide_name', f'Peptide #{peptide_id}')
                key = (cycle_id, peptide_id)
                
                # Se già somministrato oggi, skippa
                if key in completed_today:
                    continue
                
                # Dose target (base, senza ramp)
                if custom_doses and str(peptide_id) in custom_doses:
                    target_dose_mcg = float(custom_doses[str(peptide_id)])
                else:
                    target_dose_mcg = float(pep.get('target_dose_mcg', 0))
                
                # Applica ramp-up se configurato
                ramp_percentage = 1.0  # Default 100%
                current_week = 1
                ramp_info = None
                
                if cycle.get('ramp_schedule'):
                    from .models.cycle import Cycle
                    # Crea oggetto Cycle temporaneo per usare helper
                    cycle_obj = Cycle(
                        start_date=date.fromisoformat(cycle['start_date']) if cycle.get('start_date') and isinstance(cycle['start_date'], str) else cycle.get('start_date'),
                        ramp_schedule=cycle.get('ramp_schedule')
                    )
                    current_week = cycle_obj.get_current_week(target_date)
                    
                    # Try to get exact dose first (new format)
                    exact_dose = cycle_obj.get_ramp_dose(peptide_id, target_date)
                    if exact_dose is not None:
                        # Use exact dose from ramp schedule
                        ramped_dose_mcg = exact_dose
                        ramp_info = {
                            'week': current_week,
                            'dose_mcg': exact_dose,
                            'type': 'exact'
                        }
                    else:
                        # Fallback to percentage (legacy)
                        ramp_percentage = cycle_obj.get_ramp_percentage(target_date)
                        ramped_dose_mcg = target_dose_mcg * ramp_percentage
                        ramp_info = {
                            'week': current_week,
                            'percentage': int(ramp_percentage * 100),
                            'type': 'percentage'
                        }
                else:
                    # No ramp schedule
                    ramped_dose_mcg = target_dose_mcg
                
                # Calcola prossima data prevista basandosi su ultima somministrazione
                last_admin = last_admin_map.get(key)
                schedule_status = 'due_today'
                next_due_date = None
                days_overdue = 0
                
                if last_admin:
                    last_date = last_admin['date']
                    next_due_date = last_date + timedelta(days=cycle_length)
                    
                    if next_due_date < target_date:
                        schedule_status = 'overdue'
                        days_overdue = (target_date - next_due_date).days
                    elif next_due_date > target_date:
                        schedule_status = 'future'
                    else:
                        schedule_status = 'due_today'
                else:
                    # Prima dose del ciclo: usa start_date del ciclo
                    start_date = cycle.get('start_date')
                    if start_date:
                        if isinstance(start_date, str):
                            start_date = date.fromisoformat(start_date)
                        next_due_date = start_date
                        
                        if next_due_date < target_date:
                            schedule_status = 'overdue'
                            days_overdue = (target_date - next_due_date).days
                        elif next_due_date > target_date:
                            schedule_status = 'future'
                        else:
                            schedule_status = 'due_today'
                
                # Mostra solo dosi previste per oggi o in ritardo
                if schedule_status not in ['due_today', 'overdue']:
                    continue
                
                # Trova preparazione attiva e calcola dose ml (usa dose ramped)
                suitable_prep = None
                suggested_dose_ml = None
                status = 'no_prep'
                
                all_preps = self.get_preparations(only_active=True)
                
                for prep in all_preps:
                    prep_details = self.get_preparation_details(prep['id'])
                    if not prep_details or not prep_details.get('peptides'):
                        continue
                    
                    for pep_comp in prep_details['peptides']:
                        if pep_comp.get('peptide_id') == peptide_id:
                            suitable_prep = prep_details
                            status = 'ready'
                            
                            mg_amount = pep_comp.get('mg_amount') or pep_comp.get('mg_per_vial') or 0
                            volume_ml = prep_details.get('volume_ml', 1)
                            if volume_ml > 0 and mg_amount > 0:
                                concentration_mcg_per_ml = (mg_amount / volume_ml) * 1000
                                # Usa dose ramped per calcolo ml
                                suggested_dose_ml = ramped_dose_mcg / concentration_mcg_per_ml
                            break
                    
                    if suitable_prep:
                        break
                
                to_do.append({
                    'peptide_id': peptide_id,
                    'peptide_name': peptide_name,
                    'target_dose_mcg': target_dose_mcg,  # Dose target originale
                    'ramped_dose_mcg': ramped_dose_mcg,  # Dose effettiva con ramp
                    'ramp_info': ramp_info,  # Info settimana e percentuale
                    'suggested_dose_ml': suggested_dose_ml,
                    'preparation_id': suitable_prep.get('id') if suitable_prep else None,
                    'preparation': suitable_prep,
                    'protocol_name': proto.get('name'),
                    'cycle_id': cycle_id,
                    'cycle_name': cycle_name,
                    'status': status,
                    'schedule_status': schedule_status,
                    'next_due_date': next_due_date,
                    'days_overdue': days_overdue,
                })

        # 3. Ordina: prima ritardi, poi previste oggi, poi per nome
        to_do.sort(key=lambda x: (0 if x['schedule_status'] == 'overdue' else 1, x['peptide_name']))
        
        return to_do
    
    def link_administration_to_protocol(
        self,
        admin_id: int,
        protocol_id: int
    ) -> tuple[bool, str]:
        """
        Collega somministrazione a un protocollo.
        
        Args:
            admin_id: ID somministrazione
            protocol_id: ID protocollo
            
        Returns:
            (success: bool, message: str)
        """
        return self.db.administrations.link_to_protocol(admin_id, protocol_id)
    
    def get_administration_statistics(
        self,
        protocol_id: Optional[int] = None
    ) -> dict:
        """
        Calcola statistiche somministrazioni.
        
        Args:
            protocol_id: ID protocollo (None = tutte)
            
        Returns:
            Dict con statistiche
        """
        return self.db.administrations.get_statistics(protocol_id)
    
    # ==================== CERTIFICATES ====================
    
    def add_certificate(
        self,
        batch_id: int,
        certificate_type: str,
        lab_name: str = None,
        test_date: str = None,
        file_path: str = None,
        file_name: str = None,
        purity_percentage: float = None,
        endotoxin_level: str = None,
        notes: str = None,
        details: List[Dict] = None
    ) -> int:
        """
        Aggiunge un certificato di analisi a un batch.
        
        Args:
            batch_id: ID batch
            certificate_type: 'manufacturer', 'third_party', o 'personal'
            lab_name: Nome laboratorio
            test_date: Data test
            file_path: Percorso file certificato
            file_name: Nome file
            purity_percentage: Percentuale purezza
            endotoxin_level: Livello endotossine
            notes: Note
            details: Lista di dict con test dettagliati
                    [{'parameter': 'Purity', 'value': '98.5', 'unit': '%', 
                      'specification': '>95%', 'pass_fail': 'pass'}, ...]
        
        Returns:
            ID del certificato creato
        """
        from .models.certificate import Certificate, CertificateDetail
        
        # Create certificate object
        cert = Certificate(
            batch_id=batch_id,
            certificate_type=certificate_type,
            lab_name=lab_name,
            test_date=test_date,
            file_path=file_path,
            file_name=file_name,
            purity_percentage=purity_percentage,
            endotoxin_level=endotoxin_level,
            notes=notes
        )
        
        # Add details if present
        if details:
            cert.details = [
                CertificateDetail(
                    certificate_id=0,  # Will be set after cert creation
                    test_parameter=d.get('parameter'),
                    result_value=d.get('value'),
                    unit=d.get('unit'),
                    specification=d.get('specification'),
                    pass_fail=d.get('pass_fail')
                )
                for d in details
            ]
        
        # Create certificate with details
        created_cert = self.db.certificates.create(cert)
        
        type_label = {
            'manufacturer': 'Produttore',
            'third_party': 'Third-party',
            'personal': 'Personale'
        }.get(certificate_type, certificate_type)
        
        print(f"Certificato [{type_label}] aggiunto al batch {batch_id} (ID: {created_cert.id})")
        return created_cert.id
    
    def get_certificates(self, batch_id: int) -> List[Dict]:
        """
        Recupera tutti i certificati di un batch con i loro dettagli.
        
        Args:
            batch_id: ID batch
            
        Returns:
            Lista di dict con certificati e dettagli
        """
        certificates = self.db.certificates.get_by_batch(batch_id)
        
        # Convert to dict format for backward compatibility
        result = []
        for cert in certificates:
            cert_dict = {
                'id': cert.id,
                'batch_id': cert.batch_id,
                'certificate_type': cert.certificate_type,
                'lab_name': cert.lab_name,
                'test_date': cert.test_date,
                'file_path': cert.file_path,
                'file_name': cert.file_name,
                'purity_percentage': float(cert.purity_percentage) if cert.purity_percentage else None,
                'endotoxin_level': cert.endotoxin_level,
                'notes': cert.notes,
                'created_at': cert.created_at,
                'details': [
                    {
                        'id': d.id,
                        'certificate_id': d.certificate_id,
                        'parameter': d.test_parameter,
                        'value': d.result_value,
                        'unit': d.unit,
                        'specification': d.specification,
                        'pass_fail': d.pass_fail
                    }
                    for d in cert.details
                ]
            }
            result.append(cert_dict)
        
        return result
    
    # ==================== PROTOCOL TEMPLATES (NUOVO ✅) ====================
    
    def add_protocol_template(
        self,
        name: str,
        description: str = None,
        dose_ml: float = None,
        frequency_per_day: int = 1,
        days_on: int = None,
        days_off: int = 0,
        cycle_duration_weeks: int = None,
        notes: str = None,
        tags: str = None
    ) -> int:
        """
        Aggiunge un nuovo template di protocollo.
        
        Args:
            name: Nome del template
            description: Descrizione
            dose_ml: Dose in ml per somministrazione
            frequency_per_day: Somministrazioni al giorno
            days_on: Giorni ON del ciclo
            days_off: Giorni OFF del ciclo
            cycle_duration_weeks: Durata totale ciclo in settimane
            notes: Note
            tags: Tags (separati da virgola)
            
        Returns:
            ID del template creato
        """
        from .models import ProtocolTemplate, ProtocolTemplateRepository
        
        template = ProtocolTemplate(
            name=name,
            description=description,
            dose_ml=dose_ml,
            frequency_per_day=frequency_per_day,
            days_on=days_on,
            days_off=days_off,
            cycle_duration_weeks=cycle_duration_weeks,
            notes=notes,
            tags=tags
        )
        
        repo = ProtocolTemplateRepository(self.conn)
        return repo.create(template)
    
    def get_protocol_templates(self, active_only: bool = True) -> List[Dict]:
        """
        Recupera templates di protocolli.
        
        Args:
            active_only: Se True, solo templates attivi
            
        Returns:
            Lista di dict con dati templates
        """
        from .models import ProtocolTemplateRepository
        
        repo = ProtocolTemplateRepository(self.conn)
        
        if active_only:
            templates = repo.get_active_templates()
        else:
            templates = repo.get_all()
        
        return [template.__dict__ for template in templates]
    
    def get_protocol_template(self, template_id: int) -> Optional[Dict]:
        """
        Recupera un template specifico.
        
        Args:
            template_id: ID del template
            
        Returns:
            Dict con dati del template o None
        """
        from .models import ProtocolTemplateRepository
        
        repo = ProtocolTemplateRepository(self.conn)
        template = repo.get_by_id(template_id)
        
        return template.__dict__ if template else None
    
    def update_protocol_template(self, template_id: int, **kwargs) -> bool:
        """
        Aggiorna un template.
        
        Args:
            template_id: ID del template
            **kwargs: Campi da aggiornare
            
        Returns:
            True se successo
        """
        from .models import ProtocolTemplateRepository
        
        repo = ProtocolTemplateRepository(self.conn)
        return repo.update(template_id, **kwargs)
    
    def delete_protocol_template(self, template_id: int) -> bool:
        """
        Elimina (soft delete) un template.
        
        Args:
            template_id: ID del template
            
        Returns:
            True se successo
        """
        from .models import ProtocolTemplateRepository
        
        repo = ProtocolTemplateRepository(self.conn)
        return repo.soft_delete(template_id)
    
    def search_protocol_templates(self, query: str) -> List[Dict]:
        """
        Cerca templates per nome.
        
        Args:
            query: Stringa di ricerca
            
        Returns:
            Lista di dict con templates trovati
        """
        from .models import ProtocolTemplateRepository
        
        repo = ProtocolTemplateRepository(self.conn)
        templates = repo.search_by_name(query)
        
        return [template.__dict__ for template in templates]
    
    # ==================== TREATMENT PLANS (NUOVO ✅) ====================
    
    def add_treatment_plan(
        self,
        name: str,
        start_date: str,
        protocol_template_id: int = None,
        description: str = None,
        reason: str = None,
        planned_end_date: str = None,
        total_planned_days: int = None,
        status: str = 'active',
        notes: str = None
    ) -> int:
        """
        Crea un nuovo piano di trattamento.
        
        Args:
            name: Nome del piano
            start_date: Data inizio (YYYY-MM-DD)
            protocol_template_id: ID del template (opzionale)
            description: Descrizione
            reason: Motivo del trattamento
            planned_end_date: Data fine pianificata
            total_planned_days: Giorni totali pianificati
            status: Status ('active', 'planned', 'paused', 'completed', 'abandoned')
            notes: Note
            
        Returns:
            ID del piano creato
        """
        from .models import TreatmentPlan, TreatmentPlanRepository
        from datetime import date
        
        plan = TreatmentPlan(
            name=name,
            start_date=date.fromisoformat(start_date),
            protocol_template_id=protocol_template_id,
            description=description,
            reason=reason,
            planned_end_date=date.fromisoformat(planned_end_date) if planned_end_date else None,
            total_planned_days=total_planned_days,
            status=status,
            notes=notes
        )
        
        repo = TreatmentPlanRepository(self.conn)
        return repo.create(plan)
    
    def get_treatment_plans(
        self,
        status: str = None,
        template_id: int = None
    ) -> List[Dict]:
        """
        Recupera piani di trattamento.
        
        Args:
            status: Filtra per status ('active', 'planned', 'completed', etc.)
            template_id: Filtra per template
            
        Returns:
            Lista di dict con dati dei piani
        """
        from .models import TreatmentPlanRepository
        
        repo = TreatmentPlanRepository(self.conn)
        
        if status == 'active':
            plans = repo.get_active_plans()
        elif status == 'planned':
            plans = repo.get_planned_plans()
        elif status == 'completed':
            plans = repo.get_completed_plans()
        elif template_id:
            plans = repo.get_by_template(template_id)
        else:
            plans = repo.get_all()
        
        return [plan.__dict__ for plan in plans]
    
    def get_treatment_plan(self, plan_id: int) -> Optional[Dict]:
        """
        Recupera un piano specifico.
        
        Args:
            plan_id: ID del piano
            
        Returns:
            Dict con dati del piano o None
        """
        from .models import TreatmentPlanRepository
        
        repo = TreatmentPlanRepository(self.conn)
        plan = repo.get_by_id(plan_id)
        
        return plan.__dict__ if plan else None
    
    def update_treatment_plan(self, plan_id: int, **kwargs) -> bool:
        """
        Aggiorna un piano di trattamento.
        
        Args:
            plan_id: ID del piano
            **kwargs: Campi da aggiornare
            
        Returns:
            True se successo
        """
        from .models import TreatmentPlanRepository
        
        repo = TreatmentPlanRepository(self.conn)
        return repo.update(plan_id, **kwargs)
    
    def pause_treatment_plan(self, plan_id: int) -> bool:
        """
        Mette in pausa un piano.
        
        Args:
            plan_id: ID del piano
            
        Returns:
            True se successo
        """
        from .models import TreatmentPlanRepository
        
        repo = TreatmentPlanRepository(self.conn)
        return repo.change_status(plan_id, 'paused')
    
    def resume_treatment_plan(self, plan_id: int) -> bool:
        """
        Riprende un piano in pausa.
        
        Args:
            plan_id: ID del piano
            
        Returns:
            True se successo
        """
        from .models import TreatmentPlanRepository
        
        repo = TreatmentPlanRepository(self.conn)
        return repo.change_status(plan_id, 'active')
    
    def complete_treatment_plan(self, plan_id: int) -> bool:
        """
        Completa un piano di trattamento.
        
        Args:
            plan_id: ID del piano
            
        Returns:
            True se successo
        """
        from .models import TreatmentPlanRepository
        
        repo = TreatmentPlanRepository(self.conn)
        return repo.change_status(plan_id, 'completed')
    
    def abandon_treatment_plan(self, plan_id: int) -> bool:
        """
        Abbandona un piano di trattamento.
        
        Args:
            plan_id: ID del piano
            
        Returns:
            True se successo
        """
        from .models import TreatmentPlanRepository
        
        repo = TreatmentPlanRepository(self.conn)
        return repo.change_status(plan_id, 'abandoned')
    
    def update_plan_adherence(self, plan_id: int, adherence: float) -> bool:
        """
        Aggiorna percentuale di aderenza.
        
        Args:
            plan_id: ID del piano
            adherence: Percentuale (0-100)
            
        Returns:
            True se successo
        """
        from .models import TreatmentPlanRepository
        from decimal import Decimal
        
        repo = TreatmentPlanRepository(self.conn)
        return repo.update_adherence(plan_id, Decimal(str(adherence)))
    
    def increment_plan_days(self, plan_id: int) -> bool:
        """
        Incrementa contatore giorni completati.
        
        Args:
            plan_id: ID del piano
            
        Returns:
            True se successo
        """
        from .models import TreatmentPlanRepository
        
        repo = TreatmentPlanRepository(self.conn)
        return repo.increment_days_completed(plan_id)
    
    def link_preparation_to_plan(
        self,
        plan_id: int,
        preparation_id: int,
        peptide_id: int = None,
        actual_dose_mcg: float = None,
        actual_dose_ml: float = None,
        frequency: str = None,
        notes: str = None
    ) -> int:
        """
        Associa una preparazione a un piano.
        
        Args:
            plan_id: ID del piano
            preparation_id: ID della preparazione
            peptide_id: ID del peptide (opzionale)
            actual_dose_mcg: Dose effettiva in mcg
            actual_dose_ml: Dose effettiva in ml
            frequency: Frequenza somministrazione
            notes: Note
            
        Returns:
            ID dell'associazione creata
        """
        from .models import TreatmentPlanPreparation, TreatmentPlanPreparationRepository
        
        link = TreatmentPlanPreparation(
            plan_id=plan_id,
            preparation_id=preparation_id,
            peptide_id=peptide_id,
            actual_dose_mcg=actual_dose_mcg,
            actual_dose_ml=actual_dose_ml,
            frequency=frequency,
            notes=notes
        )
        
        repo = TreatmentPlanPreparationRepository(self.conn)
        return repo.create(link)
    
    def get_plan_preparations(self, plan_id: int, active_only: bool = True) -> List[Dict]:
        """
        Recupera preparazioni di un piano.
        
        Args:
            plan_id: ID del piano
            active_only: Se True, solo preparazioni attive
            
        Returns:
            Lista di dict con associazioni
        """
        from .models import TreatmentPlanPreparationRepository
        
        repo = TreatmentPlanPreparationRepository(self.conn)
        
        if active_only:
            links = repo.get_active_preparations(plan_id)
        else:
            links = repo.get_by_plan(plan_id)
        
        return [link.__dict__ for link in links]

    # ==================== CYCLES (NUOVO) ====================

    def start_cycle(
        self,
        protocol_id: int,
        name: str = None,
        start_date: str = None,
        planned_end_date: str = None,
        days_on: int = None,
        days_off: int = 0,
        cycle_duration_weeks: int = None,
        ramp_schedule: list = None,
        status: str = 'active',
    ) -> int:
        """
        Avvia un nuovo cycle (istanza di trattamento) a partire da un protocol template.

        Salva uno snapshot del protocol corrente e opzionalmente un ramp_schedule.
        Returns the created cycle id.
        """
        from .models.cycle import Cycle, CycleRepository
        from datetime import date

        proto = self.get_protocol_details(protocol_id)
        if not proto:
            raise ValueError(f"Protocol #{protocol_id} non trovato")

        # Build snapshot from protocol details
        protocol_snapshot = proto

        cycle = Cycle(
            protocol_id=protocol_id,
            name=name or f"Cycle for {proto.get('name')}",
            description=proto.get('description'),
            start_date=date.fromisoformat(start_date) if start_date else None,
            planned_end_date=date.fromisoformat(planned_end_date) if planned_end_date else None,
            days_on=days_on if days_on is not None else proto.get('days_on'),
            days_off=days_off if days_off is not None else proto.get('days_off', 0),
            cycle_duration_weeks=cycle_duration_weeks if cycle_duration_weeks is not None else proto.get('cycle_duration_weeks'),
            protocol_snapshot=protocol_snapshot,
            ramp_schedule=ramp_schedule,
            status=status,
        )

        repo = CycleRepository(self.conn)
        cycle_id = repo.create(cycle)
        return cycle_id

    def get_cycles(self, active_only: bool = True) -> List[Dict]:
        """Recupera cicli esistenti."""
        from .models.cycle import CycleRepository

        repo = CycleRepository(self.conn)
        return repo.get_all(active_only=active_only)

    def get_cycle_details(self, cycle_id: int) -> Optional[Dict]:
        """Recupera dettagli di un ciclo."""
        from .models.cycle import CycleRepository

        repo = CycleRepository(self.conn)
        return repo.get_by_id(cycle_id)

    def update_cycle(self, cycle_id: int, **kwargs) -> bool:
        """
        Aggiorna un ciclo esistente.
        
        Args:
            cycle_id: ID del ciclo
            **kwargs: Campi da aggiornare (name, description, start_date, planned_end_date,
                     days_on, days_off, cycle_duration_weeks, ramp_schedule, status)
        
        Returns:
            True se aggiornato con successo
        """
        from .models.cycle import CycleRepository
        
        repo = CycleRepository(self.conn)
        return repo.update(cycle_id, **kwargs)

    def record_cycle_administration(self, cycle_id: int, administration_id: int) -> bool:
        """Associa una somministrazione esistente a un ciclo."""
        from .models.cycle import CycleRepository

        repo = CycleRepository(self.conn)
        return repo.record_administration(cycle_id, administration_id)

    def assign_administrations_to_cycle(self, admin_ids: list, cycle_id: int) -> int:
        """Assegna retroattivamente somministrazioni esistenti a un ciclo."""
        from .models.cycle import CycleRepository

        repo = CycleRepository(self.conn)
        return repo.assign_administrations(admin_ids, cycle_id)

    def update_cycle_ramp_schedule(self, cycle_id: int, ramp_schedule: list) -> bool:
        """Aggiorna il ramp_schedule di un ciclo (wrapper su CycleRepository)."""
        from .models.cycle import CycleRepository

        repo = CycleRepository(self.conn)
        return repo.update_ramp_schedule(cycle_id, ramp_schedule)

    def suggest_doses_from_inventory(self, cycle_id: int) -> Dict:
        """Stub: suggerisce dosi possibili in base all'inventario per un ciclo.

        Implementazione iniziale: ritorna struttura minimale. Verrà estesa con logica
        di matching batch/preparations.
        """
        from decimal import Decimal, ROUND_FLOOR
        from .models.cycle import CycleRepository

        repo = CycleRepository(self.conn)
        cycle = repo.get_by_id(cycle_id)
        if not cycle:
            raise ValueError(f"Cycle #{cycle_id} non trovato")

        # Extract targets from protocol_snapshot if present, otherwise try to load protocol
        targets = []
        proto = cycle.get('protocol_snapshot') or {}
        
        # Check for custom_doses first (from personalized cycle creation)
        custom_doses = {}
        if proto and isinstance(proto, dict) and proto.get('custom_doses'):
            custom_doses = proto.get('custom_doses', {})
        
        if proto and isinstance(proto, dict) and proto.get('peptides'):
            for p in proto.get('peptides'):
                peptide_id = p.get('peptide_id')
                # Use custom dose if available, otherwise template dose
                if custom_doses and str(peptide_id) in custom_doses:
                    planned_mcg = Decimal(str(custom_doses[str(peptide_id)]))
                else:
                    planned_mcg = Decimal(str(p.get('target_dose_mcg') or 0))
                
                targets.append({
                    'peptide_id': peptide_id,
                    'name': p.get('name'),
                    'planned_mcg': planned_mcg
                })
        else:
            # Fallback to current protocol
            if cycle.get('protocol_id'):
                protocol = self.get_protocol_details(cycle['protocol_id'])
                for p in protocol.get('peptides', []):
                    targets.append({
                        'peptide_id': p.get('peptide_id'),
                        'name': p.get('name'),
                        'planned_mcg': Decimal(str(p.get('target_dose_mcg') or 0))
                    })

        # Build a map for quick lookup of planned doses
        target_map = {t['peptide_id']: t for t in targets}

        # Compute available mcg per peptide from active preparations (reconstituted solutions)
        available = {}
        preps = self.db.preparations.get_all(only_active=True)
        for prep in preps:
            batch_id = prep.batch_id
            vials_used = prep.vials_used
            try:
                volume_remaining = Decimal(str(prep.volume_remaining_ml))
            except Exception:
                volume_remaining = Decimal('0')

            if volume_remaining <= 0:
                continue

            comps = self.db.batch_composition.get_by_batch(batch_id)
            for comp in comps:
                pid = comp.peptide_id
                # BatchComposition dataclass usa mg_amount
                mg_per_vial = comp.mg_amount
                if mg_per_vial is None:
                    continue

                total_mg = Decimal(str(mg_per_vial)) * Decimal(str(vials_used))
                try:
                    conc_mg_ml = total_mg / Decimal(str(prep.volume_ml))
                except Exception:
                    conc_mg_ml = Decimal('0')

                available_mcg = conc_mg_ml * volume_remaining * Decimal('1000')
                available[pid] = available.get(pid, Decimal('0')) + available_mcg

        # Compute available mcg per peptide from dry batches (vials)
        mixes = []  # collect mix batches info to report dependencies
        batches = self.db.batches.get_all(only_available=True)
        for batch in batches:
            if not getattr(batch, 'vials_remaining', 0):
                continue

            comps = self.db.batch_composition.get_by_batch(batch.id)
            if not comps:
                continue

            # Record mix info if batch contains multiple peptides
            if len(comps) > 1:
                comp_entries = []
                for comp in comps:
                    pid = comp.peptide_id
                    mg_per_vial = getattr(comp, 'mg_amount', None) or getattr(comp, 'mg_per_vial', None)
                    comp_entries.append({
                        'peptide_id': pid,
                        'mg_per_vial': float(Decimal(str(mg_per_vial))) if mg_per_vial is not None else None
                    })

                # Determine if this mix maps to cycle targets; compute how many administrations
                supported_admins = None
                batch_peptide_ids = [c.peptide_id for c in comps]
                if all(pid in target_map for pid in batch_peptide_ids):
                    # For each peptide, compute how many admins the batch can support for that peptide
                    per_pep_admins = []
                    for comp in comps:
                        pid = comp.peptide_id
                        mg_per_vial = getattr(comp, 'mg_amount', None) or getattr(comp, 'mg_per_vial', None)
                        if mg_per_vial is None:
                            per_pep_admins.append(0)
                            continue
                        total_mcg = Decimal(str(mg_per_vial)) * Decimal(str(batch.vials_remaining)) * Decimal('1000')
                        planned = target_map.get(pid, {}).get('planned_mcg') or Decimal('0')
                        try:
                            if planned <= 0:
                                per_pep_admins.append(0)
                            else:
                                per_pep_admins.append((total_mcg / planned).to_integral_value(rounding=ROUND_FLOOR))
                        except Exception:
                            per_pep_admins.append(0)

                    supported_admins = int(min(per_pep_admins)) if per_pep_admins else 0

                mixes.append({
                    'batch_id': batch.id,
                    'product_name': getattr(batch, 'product_name', None),
                    'vials_remaining': int(getattr(batch, 'vials_remaining', 0)),
                    'composition': comp_entries,
                    'supported_admins_for_cycle': supported_admins,
                })

            # Add batch contributions to availability per peptide
            for comp in comps:
                pid = comp.peptide_id
                mg_per_vial = getattr(comp, 'mg_amount', None) or getattr(comp, 'mg_per_vial', None)
                if mg_per_vial is None:
                    continue

                total_mg = Decimal(str(mg_per_vial)) * Decimal(str(batch.vials_remaining))
                # convert mg -> mcg
                total_mcg = total_mg * Decimal('1000')
                available[pid] = available.get(pid, Decimal('0')) + total_mcg

        # Build suggestion results
        suggestions = {}
        for t in targets:
            pid = t['peptide_id']
            planned = t.get('planned_mcg') or Decimal('0')
            avail = available.get(pid, Decimal('0'))
            # Find mixes that include this peptide
            related_mixes = [m for m in mixes if any(c['peptide_id'] == pid for c in m['composition'])]

            suggestions[pid] = {
                'peptide_id': pid,
                'name': t.get('name'),
                'planned_mcg': float(planned),
                'available_mcg': float(avail),
                'can_meet_planned_today': float(avail) >= float(planned),
                'mix_dependencies': related_mixes,
            }

        return {
            'per_peptide': suggestions,
            'mixes': mixes
        }
    
    def update_cycle_status(self, cycle_id: int, new_status: str) -> bool:
        """Update cycle status (planned, active, paused, completed, cancelled)."""
        from .models.cycle import CycleRepository
        repo = CycleRepository(self.conn)
        return repo.update_status(cycle_id, new_status)
    
    def complete_cycle(self, cycle_id: int) -> bool:
        """Mark cycle as completed with current date as actual_end_date."""
        from .models.cycle import CycleRepository
        repo = CycleRepository(self.conn)
        return repo.complete_cycle(cycle_id)
    
    def check_and_complete_expired_cycles(self) -> int:
        """
        Auto-complete cycles that have passed their planned_end_date.
        Should be called periodically (e.g., on app startup or dashboard load).
        Returns number of cycles auto-completed.
        """
        from .models.cycle import CycleRepository
        repo = CycleRepository(self.conn)
        return repo.check_and_complete_expired_cycles()

    # ==================== NON ANCORA MIGRATI (FALLBACK) ====================
    
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
    'ProtocolTemplate',
    'ProtocolTemplateRepository',
    'TreatmentPlan',
    'TreatmentPlanRepository',
]
