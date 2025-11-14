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
        # Aggiungi alias 'name' per compatibilità GUI
        for peptide in peptides:
            peptide['name'] = peptide['peptide_name']
            if peptide.get('mg_per_vial'):
                peptide['mg_amount'] = peptide['mg_per_vial']  # Alias per compatibilità
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
            
            # Aggiungi composizione peptidi dal batch
            compositions = self.db.batch_composition.get_peptides_in_batch(preparation.batch_id)
            result['peptides'] = []
            for comp in compositions:
                result['peptides'].append({
                    'peptide_id': comp['peptide_id'],
                    'name': comp['peptide_name'],
                    'mg_per_vial': float(comp['mg_per_vial']) if comp['mg_per_vial'] else 0
                })
        
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
        return [p.to_dict() for p in protocols]
    
    def add_protocol(
        self,
        name: str,
        dose_ml: float,
        frequency_per_day: int = 1,
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
            dose_ml=Decimal(str(dose_ml)),
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
                'id', 'preparation_id', 'protocol_id', 'protocol_name',
                'administration_datetime', 'dose_ml', 'dose_mcg', 'date',
                'injection_site', 'injection_method', 'notes', 'side_effects',
                'batch_product', 'peptide_names'
            ])
        
        df = pd.DataFrame(administrations)
        
        # Aggiungi colonna date (solo data senza ora)
        df['date'] = pd.to_datetime(df['administration_datetime']).dt.date
        
        # Aggiungi colonna time (solo ora senza data)
        df['time'] = pd.to_datetime(df['administration_datetime']).dt.time
        
        # Calcola dose_mcg: devo recuperare mg_per_vial dalla preparazione
        # Per ora uso una stima basata su batch_product (TODO: migliorare)
        # Assumo dose_ml * concentrazione_tipica (es. 1mg/ml = 1000mcg/ml)
        # La GUI legacy usava preparazione con mg totali / volume
        # Per compatibility, calcolo da preparations
        df['dose_mcg'] = df.apply(lambda row: self._calculate_dose_mcg(
            row['preparation_id'], row['dose_ml']
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
]
