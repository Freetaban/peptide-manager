"""
Peptide model - gestisce catalogo peptidi.
"""

from dataclasses import dataclass
from typing import Optional, List
from .base import BaseModel, Repository


@dataclass
class Peptide(BaseModel):
    """Rappresenta un peptide nel catalogo."""
    name: str = ""
    description: Optional[str] = None
    common_uses: Optional[str] = None
    notes: Optional[str] = None
    
    def __post_init__(self):
        """Validazione dopo inizializzazione."""
        if not self.name or not self.name.strip():
            raise ValueError("Nome peptide obbligatorio")


class PeptideRepository(Repository):
    """Repository per operazioni CRUD sui peptidi."""
    
    def get_all(self, search: Optional[str] = None) -> List[Peptide]:
        """
        Recupera tutti i peptidi dal catalogo.
        
        Args:
            search: Filtro opzionale per nome o descrizione
            
        Returns:
            Lista di Peptide
        """
        if search:
            query = '''
                SELECT * FROM peptides 
                WHERE name LIKE ? OR description LIKE ?
                ORDER BY name
            '''
            rows = self._fetch_all(query, (f'%{search}%', f'%{search}%'))
        else:
            query = 'SELECT * FROM peptides ORDER BY name'
            rows = self._fetch_all(query)
        
        return [Peptide.from_row(row) for row in rows]
    
    def get_by_id(self, peptide_id: int) -> Optional[Peptide]:
        """
        Recupera un peptide per ID.
        
        Args:
            peptide_id: ID del peptide
            
        Returns:
            Peptide o None se non trovato
        """
        query = 'SELECT * FROM peptides WHERE id = ?'
        row = self._fetch_one(query, (peptide_id,))
        return Peptide.from_row(row) if row else None
    
    def get_by_name(self, name: str) -> Optional[Peptide]:
        """
        Recupera un peptide per nome esatto.
        
        Args:
            name: Nome del peptide
            
        Returns:
            Peptide o None se non trovato
        """
        query = 'SELECT * FROM peptides WHERE name = ?'
        row = self._fetch_one(query, (name,))
        return Peptide.from_row(row) if row else None
    
    def create(self, peptide: Peptide) -> int:
        """
        Crea un nuovo peptide.
        
        Args:
            peptide: Oggetto Peptide da creare
            
        Returns:
            ID del peptide creato
            
        Raises:
            ValueError: Se nome è vuoto o già esistente
        """
        # Validazione
        if not peptide.name or not peptide.name.strip():
            raise ValueError("Nome peptide obbligatorio")
        
        # Verifica duplicati
        existing = self.get_by_name(peptide.name)
        if existing:
            raise ValueError(f"Peptide '{peptide.name}' già esistente")
        
        query = '''
            INSERT INTO peptides (name, description, common_uses, notes)
            VALUES (?, ?, ?, ?)
        '''
        cursor = self._execute(query, (
            peptide.name,
            peptide.description,
            peptide.common_uses,
            peptide.notes
        ))
        
        self._commit()
        return cursor.lastrowid
    
    def update(self, peptide: Peptide) -> bool:
        """
        Aggiorna un peptide esistente.
        
        Args:
            peptide: Oggetto Peptide con dati aggiornati (deve avere id)
            
        Returns:
            True se aggiornato, False altrimenti
            
        Raises:
            ValueError: Se id non specificato o dati non validi
        """
        if peptide.id is None:
            raise ValueError("ID peptide necessario per update")
        
        if not peptide.name or not peptide.name.strip():
            raise ValueError("Nome peptide obbligatorio")
        
        # Verifica duplicati (escluso se stesso)
        query = 'SELECT id FROM peptides WHERE name = ? AND id != ?'
        row = self._fetch_one(query, (peptide.name, peptide.id))
        if row:
            raise ValueError(f"Peptide '{peptide.name}' già esistente")
        
        query = '''
            UPDATE peptides 
            SET name = ?, description = ?, common_uses = ?, notes = ?
            WHERE id = ?
        '''
        self._execute(query, (
            peptide.name,
            peptide.description,
            peptide.common_uses,
            peptide.notes,
            peptide.id
        ))
        
        self._commit()
        return True
    
    def delete(self, peptide_id: int, force: bool = False) -> tuple[bool, str]:
        """
        Elimina un peptide.
        
        Args:
            peptide_id: ID del peptide da eliminare
            force: Se True, elimina anche se ci sono riferimenti
            
        Returns:
            (success: bool, message: str)
        """
        # Verifica esistenza
        peptide = self.get_by_id(peptide_id)
        if not peptide:
            return False, f"Peptide #{peptide_id} non trovato"
        
        # Controlla riferimenti in batch_composition
        query = 'SELECT COUNT(*) FROM batch_composition WHERE peptide_id = ?'
        row = self._fetch_one(query, (peptide_id,))
        batch_refs = row[0] if row else 0
        
        # Controlla riferimenti in protocol_peptides
        query = 'SELECT COUNT(*) FROM protocol_peptides WHERE peptide_id = ?'
        row = self._fetch_one(query, (peptide_id,))
        protocol_refs = row[0] if row else 0
        
        if (batch_refs > 0 or protocol_refs > 0) and not force:
            return False, (
                f"Impossibile eliminare '{peptide.name}': "
                f"riferimenti in {batch_refs} batch(es) e {protocol_refs} protocollo(i). "
                f"Usa force=True per forzare l'eliminazione."
            )
        
        # Elimina (CASCADE eliminerà automaticamente da tabelle correlate)
        query = 'DELETE FROM peptides WHERE id = ?'
        self._execute(query, (peptide_id,))
        self._commit()
        
        return True, f"Peptide '{peptide.name}' eliminato"
    
    def count(self) -> int:
        """Conta i peptidi totali nel catalogo."""
        query = 'SELECT COUNT(*) FROM peptides'
        row = self._fetch_one(query)
        return row[0] if row else 0
    
    def get_with_usage_count(self) -> List[dict]:
        """
        Recupera peptidi con conteggio utilizzi.
        
        Returns:
            Lista di dict con campi peptide + batch_count + protocol_count
        """
        query = '''
            SELECT 
                p.*,
                COUNT(DISTINCT bc.batch_id) as batch_count,
                COUNT(DISTINCT pp.protocol_id) as protocol_count
            FROM peptides p
            LEFT JOIN batch_composition bc ON p.id = bc.peptide_id
            LEFT JOIN protocol_peptides pp ON p.id = pp.peptide_id
            GROUP BY p.id
            ORDER BY p.name
        '''
        rows = self._fetch_all(query)
        
        result = []
        for row in rows:
            data = dict(row)
            batch_count = data.pop('batch_count', 0)
            protocol_count = data.pop('protocol_count', 0)
            peptide = Peptide.from_row(data)
            result.append({
                'peptide': peptide,
                'batch_count': batch_count,
                'protocol_count': protocol_count,
                'total_usage': batch_count + protocol_count
            })
        
        return result
    
    def get_most_used(self, limit: int = 10) -> List[dict]:
        """
        Recupera i peptidi più utilizzati.
        
        Args:
            limit: Numero massimo di risultati
            
        Returns:
            Lista di dict ordinata per utilizzo decrescente
        """
        peptides_with_usage = self.get_with_usage_count()
        
        # Ordina per utilizzo totale decrescente
        sorted_peptides = sorted(
            peptides_with_usage, 
            key=lambda x: x['total_usage'], 
            reverse=True
        )
        
        return sorted_peptides[:limit]
    
    def search_by_use(self, use_keyword: str) -> List[Peptide]:
        """
        Cerca peptidi per uso comune.
        
        Args:
            use_keyword: Keyword da cercare in common_uses
            
        Returns:
            Lista di Peptide che matchano
        """
        query = '''
            SELECT * FROM peptides 
            WHERE common_uses LIKE ?
            ORDER BY name
        '''
        rows = self._fetch_all(query, (f'%{use_keyword}%',))
        return [Peptide.from_row(row) for row in rows]
