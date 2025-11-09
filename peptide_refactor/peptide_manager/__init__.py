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
    
    # ==================== PLACEHOLDERS ====================
    # Questi sono placeholder per i metodi non ancora migrati
    # In produzione useresti ancora il vecchio PeptideManager
    
    def get_peptides(self, search: str = None) -> List[Dict]:
        """Placeholder - da implementare."""
        raise NotImplementedError(
            "Peptides non ancora migrato. "
            "Usa il vecchio PeptideManager per questa funzionalità."
        )
    
    def get_batches(self, **kwargs) -> List[Dict]:
        """Placeholder - da implementare."""
        raise NotImplementedError(
            "Batches non ancora migrato. "
            "Usa il vecchio PeptideManager per questa funzionalità."
        )


# Per mantenere il vecchio import path
__all__ = ['PeptideManager']
