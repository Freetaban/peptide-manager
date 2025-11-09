"""
Adapter per retrocompatibilità con il vecchio PeptideManager.

Questo modulo permette al vecchio codice GUI di continuare a funzionare
mentre migriamo progressivamente alla nuova architettura.

Esempio:
    # Vecchio codice (funziona ancora)
    from peptide_manager import PeptideManager
    manager = PeptideManager('db.db')
    suppliers = manager.get_suppliers()
    
    # Internamente usa la nuova architettura!
"""

from typing import List, Dict, Optional
from .database import DatabaseManager
from .models import Supplier


class PeptideManager:
    """
    Adapter che mantiene la vecchia interfaccia ma usa la nuova architettura.
    
    Questo permette una migrazione graduale senza rompere il codice esistente.
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
    
    def close(self):
        """Chiude la connessione (compatibile con vecchia interfaccia)."""
        self.db.close()
    
    # ==================== SUPPLIERS ====================
    # Metodi che mantengono la vecchia firma ma usano nuova architettura
    
    def add_supplier(self, name: str, country: str = None, website: str = None,
                     email: str = None, notes: str = None, rating: int = None) -> int:
        """
        Aggiunge un nuovo fornitore (compatibile con vecchia interfaccia).
        
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
    
    def get_suppliers(self, search: str = None) -> List[Dict]:
        """
        Recupera fornitori (compatibile con vecchia interfaccia).
        
        Args:
            search: Filtro ricerca (opzionale)
            
        Returns:
            Lista di dict (come prima)
        """
        suppliers = self.db.suppliers.get_all(search=search)
        
        # Converte Supplier objects in dict (come vecchia interfaccia)
        return [supplier.to_dict() for supplier in suppliers]
    
    def update_supplier(self, supplier_id: int, **kwargs) -> bool:
        """
        Aggiorna fornitore (compatibile con vecchia interfaccia).
        
        Args:
            supplier_id: ID fornitore
            **kwargs: Campi da aggiornare (name, country, etc.)
            
        Returns:
            True se aggiornato
        """
        # Recupera supplier esistente
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
    
    def delete_supplier(self, supplier_id: int, force: bool = False) -> bool:
        """
        Elimina fornitore (compatibile con vecchia interfaccia).
        
        Args:
            supplier_id: ID fornitore
            force: Forza eliminazione anche se ha batches
            
        Returns:
            True se eliminato
        """
        success, message = self.db.suppliers.delete(supplier_id, force=force)
        
        if success:
            print(f"✓ {message}")
        else:
            print(f"❌ {message}")
        
        return success
    
    # TODO: Aggiungi altri metodi per peptides, batches, etc.
    # Man mano che migriamo i moduli, aggiungiamo qui gli adapter
    
    # ==================== PEPTIDES ====================
    
    def add_peptide(self, name: str, description: str = None,
                    common_uses: str = None, notes: str = None) -> int:
        """
        Aggiunge un nuovo peptide (compatibile con vecchia interfaccia).
        
        Args:
            name: Nome peptide
            description: Descrizione (opzionale)
            common_uses: Usi comuni (opzionale)
            notes: Note (opzionale)
            
        Returns:
            ID del peptide creato
        """
        from .models import Peptide
        
        peptide = Peptide(
            name=name,
            description=description,
            common_uses=common_uses,
            notes=notes
        )
        
        peptide_id = self.db.peptides.create(peptide)
        print(f"Peptide '{name}' aggiunto al catalogo (ID: {peptide_id})")
        return peptide_id
    
    def get_peptides(self, search: str = None) -> List[Dict]:
        """
        Recupera peptidi (compatibile con vecchia interfaccia).
        
        Args:
            search: Filtro ricerca (opzionale)
            
        Returns:
            Lista di dict (come prima)
        """
        peptides = self.db.peptides.get_all(search=search)
        
        # Converte Peptide objects in dict (come vecchia interfaccia)
        return [peptide.to_dict() for peptide in peptides]
    
    def get_peptide_by_name(self, name: str) -> Optional[Dict]:
        """
        Recupera peptide per nome (compatibile con vecchia interfaccia).
        
        Args:
            name: Nome del peptide
            
        Returns:
            Dict o None
        """
        peptide = self.db.peptides.get_by_name(name)
        return peptide.to_dict() if peptide else None
    
    def get_peptide_by_id(self, peptide_id: int) -> Optional[Dict]:
        """
        Recupera peptide per ID (compatibile con vecchia interfaccia).
        
        Args:
            peptide_id: ID del peptide
            
        Returns:
            Dict o None
        """
        peptide = self.db.peptides.get_by_id(peptide_id)
        return peptide.to_dict() if peptide else None
    
    def update_peptide(self, peptide_id: int, **kwargs) -> bool:
        """
        Aggiorna peptide (compatibile con vecchia interfaccia).
        
        Args:
            peptide_id: ID peptide
            **kwargs: Campi da aggiornare (name, description, etc.)
            
        Returns:
            True se aggiornato
        """
        # Recupera peptide esistente
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
    
    def delete_peptide(self, peptide_id: int, force: bool = False) -> bool:
        """
        Elimina peptide (compatibile con vecchia interfaccia).
        
        Args:
            peptide_id: ID peptide
            force: Forza eliminazione anche se ha riferimenti
            
        Returns:
            True se eliminato
        """
        success, message = self.db.peptides.delete(peptide_id, force=force)
        
        if success:
            print(f"✓ {message}")
        else:
            print(f"❌ {message}")
        
        return success
    
    # ==================== PLACEHOLDERS ====================
    # Questi sono placeholder per i metodi non ancora migrati
    # In produzione useresti ancora il vecchio PeptideManager
    
    def get_batches(self, **kwargs) -> List[Dict]:
        """Placeholder - da implementare."""
        raise NotImplementedError(
            "Batches non ancora migrato. "
            "Usa il vecchio PeptideManager per questa funzionalità."
        )


# Per mantenere il vecchio import path
__all__ = ['PeptideManager']
