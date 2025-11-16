"""
BatchComposition model - gestisce la relazione M:N tra batches e peptides.

Un batch può contenere più peptidi (blend) e un peptide può apparire in più batches.
"""

from dataclasses import dataclass
from typing import Optional, List
from decimal import Decimal
from .base import BaseModel, Repository


@dataclass
class BatchComposition(BaseModel):
    """Rappresenta un peptide all'interno di un batch."""
    batch_id: int = None
    peptide_id: int = None
    mg_amount: Optional[Decimal] = None  # Quantità in mg di questo peptide nel batch
    
    def __post_init__(self):
        """Validazione dopo inizializzazione."""
        if self.batch_id is None:
            raise ValueError("Batch ID obbligatorio")
        if self.peptide_id is None:
            raise ValueError("Peptide ID obbligatorio")
        
        # Converti mg_amount in Decimal se necessario
        if isinstance(self.mg_amount, (int, float, str)) and self.mg_amount is not None:
            self.mg_amount = Decimal(str(self.mg_amount))


class BatchCompositionRepository(Repository):
    """Repository per operazioni sulla composizione dei batches."""
    
    def get_by_batch(self, batch_id: int) -> List[BatchComposition]:
        """
        Recupera tutti i peptidi di un batch.
        
        Args:
            batch_id: ID del batch
            
        Returns:
            Lista di BatchComposition
        """
        query = 'SELECT * FROM batch_composition WHERE batch_id = ?'
        rows = self._fetch_all(query, (batch_id,))
        return [BatchComposition.from_row(row) for row in rows]
    
    def get_peptides_in_batch(self, batch_id: int) -> List[dict]:
        """
        Recupera i peptidi di un batch con informazioni complete.
        
        Args:
            batch_id: ID del batch
            
        Returns:
            Lista di dict con: peptide_id, name, mg_per_vial
        """
        # Adatta selezione del campo mg secondo schema (mg_per_vial vs mg_amount)
        # I test si aspettano le chiavi 'name' e 'mg_amount'. Restituiamo
        # una struttura compatibile con quelle aspettative.
        mg_field = 'mg_amount' if self.has_column('batch_composition', 'mg_amount') else 'mg_per_vial'
        query = f'''
            SELECT 
                bc.peptide_id,
                p.name,
                bc.{mg_field}
            FROM batch_composition bc
            JOIN peptides p ON bc.peptide_id = p.id
            WHERE bc.batch_id = ?
            ORDER BY p.name
        '''
        rows = self._fetch_all(query, (batch_id,))

        return [
            {
                'peptide_id': row[0],
                'name': row[1],
                'mg_amount': Decimal(str(row[2])) if row[2] is not None else None
            }
            for row in rows
        ]
    
    def get_by_peptide(self, peptide_id: int) -> List[BatchComposition]:
        """
        Recupera tutti i batches che contengono un peptide.
        
        Args:
            peptide_id: ID del peptide
            
        Returns:
            Lista di BatchComposition
        """
        query = 'SELECT * FROM batch_composition WHERE peptide_id = ?'
        rows = self._fetch_all(query, (peptide_id,))
        return [BatchComposition.from_row(row) for row in rows]
    
    def get_batches_with_peptide(self, peptide_id: int) -> List[dict]:
        """
        Recupera i batches che contengono un peptide con informazioni complete.
        
        Args:
            peptide_id: ID del peptide
            
        Returns:
            Lista di dict con: batch_id, product_name, mg_amount, vials_remaining
        """
        query = '''
            SELECT 
                bc.batch_id,
                b.product_name,
                bc.mg_amount,
                b.vials_remaining
            FROM batch_composition bc
            JOIN batches b ON bc.batch_id = b.id
            WHERE bc.peptide_id = ? AND b.deleted_at IS NULL
            ORDER BY b.product_name
        '''
        rows = self._fetch_all(query, (peptide_id,))
        
        return [
            {
                'batch_id': row[0],
                'product_name': row[1],
                'mg_amount': Decimal(str(row[2])) if row[2] else None,
                'vials_remaining': row[3]
            }
            for row in rows
        ]
    
    def add_peptide_to_batch(
        self, 
        batch_id: int, 
        peptide_id: int, 
        mg_amount: Optional[Decimal] = None
    ) -> int:
        """
        Aggiunge un peptide alla composizione di un batch.
        
        Args:
            batch_id: ID del batch
            peptide_id: ID del peptide
            mg_amount: Quantità in mg (opzionale)
            
        Returns:
            ID della composizione creata
            
        Raises:
            ValueError: Se batch o peptide non esistono, o se già presente
        """
        # Verifica esistenza batch
        query = 'SELECT id FROM batches WHERE id = ? AND deleted_at IS NULL'
        if not self._fetch_one(query, (batch_id,)):
            raise ValueError(f"Batch #{batch_id} non trovato")
        
        # Verifica esistenza peptide
        query = 'SELECT id FROM peptides WHERE id = ?'
        if not self._fetch_one(query, (peptide_id,)):
            raise ValueError(f"Peptide #{peptide_id} non trovato")
        
        # Verifica duplicato
        query = 'SELECT id FROM batch_composition WHERE batch_id = ? AND peptide_id = ?'
        if self._fetch_one(query, (batch_id, peptide_id)):
            raise ValueError(
                f"Peptide #{peptide_id} già presente nel batch #{batch_id}"
            )
        
        # Converti mg_amount
        if mg_amount is not None:
            mg_value = float(Decimal(str(mg_amount)))
        else:
            mg_value = 0.0

        # Scegli la colonna corretta a runtime (mg_per_vial o mg_amount)
        if self.has_column('batch_composition', 'mg_per_vial'):
            insert_query = 'INSERT INTO batch_composition (batch_id, peptide_id, mg_per_vial) VALUES (?, ?, ?)'
        elif self.has_column('batch_composition', 'mg_amount'):
            insert_query = 'INSERT INTO batch_composition (batch_id, peptide_id, mg_amount) VALUES (?, ?, ?)'
        else:
            # Campo non presente: fallback su inserimento minimale (batch_id, peptide_id)
            insert_query = 'INSERT INTO batch_composition (batch_id, peptide_id) VALUES (?, ?)'

        # Esegui inserimento (adatta parametri se necessario)
        if 'mg_' in insert_query:
            cursor = self._execute(insert_query, (batch_id, peptide_id, mg_value))
        else:
            cursor = self._execute(insert_query, (batch_id, peptide_id))
        self._commit()
        
        return cursor.lastrowid
    
    def update_mg_amount(
        self, 
        batch_id: int, 
        peptide_id: int, 
        mg_amount: Decimal
    ) -> bool:
        """
        Aggiorna la quantità di un peptide in un batch.
        
        Args:
            batch_id: ID del batch
            peptide_id: ID del peptide
            mg_amount: Nuova quantità in mg
            
        Returns:
            True se aggiornato
            
        Raises:
            ValueError: Se composizione non trovata
        """
        # Verifica esistenza
        query = 'SELECT id FROM batch_composition WHERE batch_id = ? AND peptide_id = ?'
        if not self._fetch_one(query, (batch_id, peptide_id)):
            raise ValueError(
                f"Composizione Batch #{batch_id} - Peptide #{peptide_id} non trovata"
            )
        
        # Converti
        mg_amount = float(Decimal(str(mg_amount)))
        
        # Aggiorna
        query = '''
            UPDATE batch_composition 
            SET mg_amount = ?
            WHERE batch_id = ? AND peptide_id = ?
        '''
        self._execute(query, (mg_amount, batch_id, peptide_id))
        self._commit()
        
        return True
    
    def remove_peptide_from_batch(self, batch_id: int, peptide_id: int) -> tuple[bool, str]:
        """
        Rimuove un peptide dalla composizione di un batch.
        
        Args:
            batch_id: ID del batch
            peptide_id: ID del peptide
            
        Returns:
            (success: bool, message: str)
        """
        # Verifica esistenza
        query = 'SELECT id FROM batch_composition WHERE batch_id = ? AND peptide_id = ?'
        if not self._fetch_one(query, (batch_id, peptide_id)):
            return False, f"Composizione Batch #{batch_id} - Peptide #{peptide_id} non trovata"
        
        # Elimina
        query = 'DELETE FROM batch_composition WHERE batch_id = ? AND peptide_id = ?'
        self._execute(query, (batch_id, peptide_id))
        self._commit()
        
        return True, f"Peptide #{peptide_id} rimosso dal Batch #{batch_id}"
    
    def clear_batch_composition(self, batch_id: int) -> int:
        """
        Rimuove tutti i peptidi dalla composizione di un batch.
        
        Args:
            batch_id: ID del batch
            
        Returns:
            Numero di peptidi rimossi
        """
        query = 'DELETE FROM batch_composition WHERE batch_id = ?'
        cursor = self._execute(query, (batch_id,))
        self._commit()
        
        return cursor.rowcount
    
    def set_batch_composition(
        self, 
        batch_id: int, 
        peptides: List[tuple[int, Optional[Decimal]]]
    ) -> int:
        """
        Imposta la composizione completa di un batch (sovrascrive esistente).
        
        Args:
            batch_id: ID del batch
            peptides: Lista di tuple (peptide_id, mg_amount)
            
        Returns:
            Numero di peptidi aggiunti
            
        Example:
            >>> repo.set_batch_composition(1, [(5, 10.0), (7, 5.0)])
        """
        # Rimuovi composizione esistente
        self.clear_batch_composition(batch_id)
        
        # Aggiungi nuova composizione
        count = 0
        for peptide_id, mg_amount in peptides:
            try:
                self.add_peptide_to_batch(batch_id, peptide_id, mg_amount)
                count += 1
            except ValueError as e:
                # Ignora errori (peptide già presente, etc.)
                print(f"⚠️  {e}")
        
        return count
    
    def is_blend(self, batch_id: int) -> bool:
        """
        Verifica se un batch è un blend (contiene più peptidi).
        
        Args:
            batch_id: ID del batch
            
        Returns:
            True se blend (>1 peptide)
        """
        query = 'SELECT COUNT(*) FROM batch_composition WHERE batch_id = ?'
        row = self._fetch_one(query, (batch_id,))
        count = row[0] if row else 0
        return count > 1
    
    def get_blend_batches(self) -> List[int]:
        """
        Recupera tutti i batch_id che sono blend (multi-peptide).
        
        Returns:
            Lista di batch_id
        """
        query = '''
            SELECT batch_id
            FROM batch_composition
            GROUP BY batch_id
            HAVING COUNT(*) > 1
        '''
        rows = self._fetch_all(query)
        return [row[0] for row in rows]
    
    def count_peptides_in_batch(self, batch_id: int) -> int:
        """
        Conta quanti peptidi contiene un batch.
        
        Args:
            batch_id: ID del batch
            
        Returns:
            Numero di peptidi
        """
        query = 'SELECT COUNT(*) FROM batch_composition WHERE batch_id = ?'
        row = self._fetch_one(query, (batch_id,))
        return row[0] if row else 0
    
    def get_total_mg_in_batch(self, batch_id: int) -> Optional[Decimal]:
        """
        Calcola il totale mg di tutti i peptidi in un batch.
        
        Args:
            batch_id: ID del batch
            
        Returns:
            Totale mg o None se mancano dati
        """
        query = 'SELECT SUM(mg_amount) FROM batch_composition WHERE batch_id = ?'
        row = self._fetch_one(query, (batch_id,))
        
        if row and row[0]:
            return Decimal(str(row[0]))
        return None
