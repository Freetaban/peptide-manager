"""
Adapter per retrocompatibilità con il vecchio PeptideManager.

Questo modulo permette al vecchio codice GUI di continuare a funzionare
mentre migriamo progressivamente alla nuova architettura.

Strategia:
- Suppliers e Peptides: usa nuova architettura (DatabaseManager + Repository)
- Altri moduli (Batches, Protocols, etc.): delega al vecchio models.py

Questo permette migrazione incrementale senza bloccare la GUI.
"""

from typing import List, Dict, Optional
from .database import DatabaseManager
from .models import Supplier, Peptide


class PeptideManager:
    """
    Adapter ibrido: nuova architettura per moduli migrati + fallback per il resto.
    
    Moduli migrati (usa nuova architettura):
    - Suppliers ✅
    - Peptides ✅
    
    Moduli non migrati (usa vecchio codice):
    - Batches
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
        """Lazy load del vecchio manager."""
        if self._old_manager is None:
            # Importa da models_legacy nello stesso package
            from .models_legacy import PeptideManager as OldPeptideManager
            self._old_manager = OldPeptideManager(self.db_path)
            print("⚠️  Usando vecchio PeptideManager per moduli non ancora migrati")
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
    
    # ==================== NON ANCORA MIGRATI (FALLBACK) ====================
    # Questi metodi delegano al vecchio PeptideManager in models.py
    
    def get_inventory_summary(self) -> Dict:
        """Delega al vecchio manager (TODO: migrare)."""
        return self._get_old_manager().get_inventory_summary()
    
    # --- BATCHES ---
    
    def get_batches(self, **kwargs) -> List[Dict]:
        """Delega al vecchio manager (TODO: migrare)."""
        return self._get_old_manager().get_batches(**kwargs)
    
    def add_batch(self, *args, **kwargs) -> int:
        """Delega al vecchio manager (TODO: migrare)."""
        return self._get_old_manager().add_batch(*args, **kwargs)
    
    def update_batch(self, *args, **kwargs) -> bool:
        """Delega al vecchio manager (TODO: migrare)."""
        return self._get_old_manager().update_batch(*args, **kwargs)
    
    def soft_delete_batch(self, batch_id: int) -> bool:
        """Elimina batch (implementazione diretta - TODO: migrare a Batch model)."""
        try:
            cursor = self.conn.cursor()
            cursor.execute('DELETE FROM batches WHERE id = ?', (batch_id,))
            self.conn.commit()
            print(f"✓ Batch #{batch_id} eliminato")
            return True
        except Exception as e:
            print(f"❌ Errore eliminazione batch: {e}")
            return False
    
    def get_batch_details(self, *args, **kwargs):
        """Delega al vecchio manager (TODO: migrare)."""
        return self._get_old_manager().get_batch_details(*args, **kwargs)
    
    # --- PREPARATIONS ---
    
    def get_preparations(self, **kwargs) -> List[Dict]:
        """Delega al vecchio manager (TODO: migrare)."""
        return self._get_old_manager().get_preparations(**kwargs)
    
    def add_preparation(self, *args, **kwargs) -> int:
        """Delega al vecchio manager (TODO: migrare)."""
        return self._get_old_manager().add_preparation(*args, **kwargs)
    
    def update_preparation(self, *args, **kwargs) -> bool:
        """Delega al vecchio manager (TODO: migrare)."""
        return self._get_old_manager().update_preparation(*args, **kwargs)
    
    def soft_delete_preparation(self, prep_id: int) -> bool:
        """
        Elimina preparazione SOLO se non ha somministrazioni.
        Business logic: preserva storico somministrazioni reali.
    
        Returns:
            False se ha somministrazioni (blocca eliminazione)
            True se eliminata con successo
        """
        try:
            cursor = self.conn.cursor()
        
            # Verifica somministrazioni
            cursor.execute(
                'SELECT COUNT(*) FROM administrations WHERE preparation_id = ?', 
                (prep_id,)
            )
            admin_count = cursor.fetchone()[0]
        
            if admin_count > 0:
                # BLOCCA: ha storico somministrazioni
                print(f"❌ Impossibile eliminare preparazione #{prep_id}")
                print(f"   Ha {admin_count} somministrazione(i) registrate")
                print(f"   Per preservare lo storico, la preparazione viene mantenuta")
                return False
        
            # OK: nessuna somministrazione
            cursor.execute('DELETE FROM preparations WHERE id = ?', (prep_id,))
            self.conn.commit()
            print(f"✓ Preparazione #{prep_id} eliminata")
            return True
        
        except Exception as e:
            print(f"❌ Errore: {e}")
            self.conn.rollback()
            return False
    
    def get_preparation_details(self, *args, **kwargs):
        """Delega al vecchio manager (TODO: migrare)."""
        return self._get_old_manager().get_preparation_details(*args, **kwargs)
    
    def use_preparation(self, *args, **kwargs):
        """Delega al vecchio manager (TODO: migrare)."""
        return self._get_old_manager().use_preparation(*args, **kwargs)
    
    def reconcile_preparation_volumes(self, *args, **kwargs):
        """Delega al vecchio manager (TODO: migrare)."""
        return self._get_old_manager().reconcile_preparation_volumes(*args, **kwargs)
    
    # --- PROTOCOLS ---
    
    def get_protocols(self, **kwargs) -> List[Dict]:
        """Delega al vecchio manager (TODO: migrare)."""
        return self._get_old_manager().get_protocols(**kwargs)
    
    def add_protocol(self, *args, **kwargs) -> int:
        """Delega al vecchio manager (TODO: migrare)."""
        return self._get_old_manager().add_protocol(*args, **kwargs)
    
    def update_protocol(self, *args, **kwargs) -> bool:
        """Delega al vecchio manager (TODO: migrare)."""
        return self._get_old_manager().update_protocol(*args, **kwargs)
    
    def soft_delete_protocol(self, protocol_id: int) -> bool:
        """Elimina protocollo (implementazione diretta - TODO: migrare a Protocol model)."""
        try:
            cursor = self.conn.cursor()
            cursor.execute('DELETE FROM protocols WHERE id = ?', (protocol_id,))
            self.conn.commit()
            print(f"✓ Protocollo #{protocol_id} eliminato")
            return True
        except Exception as e:
            print(f"❌ Errore eliminazione protocollo: {e}")
            return False
    
    def get_protocol_details(self, *args, **kwargs):
        """Delega al vecchio manager (TODO: migrare)."""
        return self._get_old_manager().get_protocol_details(*args, **kwargs)
    
    # --- ADMINISTRATIONS ---
    
    def update_administration(self, *args, **kwargs) -> bool:
        """Delega al vecchio manager (TODO: migrare)."""
        return self._get_old_manager().update_administration(*args, **kwargs)
    
    def soft_delete_administration(self, *args, **kwargs) -> bool:
        """Delega al vecchio manager (TODO: migrare)."""
        return self._get_old_manager().soft_delete_administration(*args, **kwargs)
    
    def get_all_administrations_df(self, *args, **kwargs):
        """Delega al vecchio manager (TODO: migrare)."""
        return self._get_old_manager().get_all_administrations_df(*args, **kwargs)
    
    # --- UTILITIES ---
    
    def check_data_integrity(self, *args, **kwargs):
        """Delega al vecchio manager (TODO: migrare)."""
        return self._get_old_manager().check_data_integrity(*args, **kwargs)


# Per mantenere il vecchio import path
__all__ = ['PeptideManager']
