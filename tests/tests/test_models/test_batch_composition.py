"""
Test per BatchComposition model e BatchCompositionRepository.
"""

import pytest
import sqlite3
from datetime import date
from decimal import Decimal
from peptide_manager.models.batch_composition import BatchComposition, BatchCompositionRepository


@pytest.fixture
def db_connection():
    """Crea database in-memory per test."""
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    
    # Schema suppliers
    conn.execute('''
        CREATE TABLE suppliers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        )
    ''')
    
    # Schema peptides
    conn.execute('''
        CREATE TABLE peptides (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT
        )
    ''')
    
    # Schema batches
    conn.execute('''
        CREATE TABLE batches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            supplier_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            batch_number TEXT NOT NULL,
            vials_count INTEGER NOT NULL DEFAULT 1,
            vials_remaining INTEGER NOT NULL DEFAULT 1,
            deleted_at TIMESTAMP,
            FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
        )
    ''')
    
    # Schema batch_composition
    conn.execute('''
        CREATE TABLE batch_composition (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_id INTEGER NOT NULL,
            peptide_id INTEGER NOT NULL,
            mg_amount REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (batch_id) REFERENCES batches(id) ON DELETE CASCADE,
            FOREIGN KEY (peptide_id) REFERENCES peptides(id) ON DELETE CASCADE,
            UNIQUE(batch_id, peptide_id)
        )
    ''')
    
    # Dati di test
    conn.execute("INSERT INTO suppliers (name) VALUES ('TestSupplier')")
    conn.execute("INSERT INTO peptides (name) VALUES ('BPC-157')")
    conn.execute("INSERT INTO peptides (name) VALUES ('TB-500')")
    conn.execute("INSERT INTO peptides (name) VALUES ('Semaglutide')")
    
    conn.execute('''
        INSERT INTO batches (supplier_id, product_name, batch_number, vials_count, vials_remaining)
        VALUES (1, 'Test Batch 1', 'BATCH001', 10, 10)
    ''')
    conn.execute('''
        INSERT INTO batches (supplier_id, product_name, batch_number, vials_count, vials_remaining)
        VALUES (1, 'Test Batch 2', 'BATCH002', 5, 5)
    ''')
    
    conn.commit()
    yield conn
    conn.close()


@pytest.fixture
def repo(db_connection):
    """Crea repository per test."""
    return BatchCompositionRepository(db_connection)


class TestBatchCompositionModel:
    """Test per BatchComposition dataclass."""
    
    def test_composition_creation(self):
        """Test creazione composizione valida."""
        comp = BatchComposition(
            batch_id=1,
            peptide_id=1,
            mg_amount=Decimal('5.0')
        )
        
        assert comp.batch_id == 1
        assert comp.peptide_id == 1
        assert comp.mg_amount == Decimal('5.0')
    
    def test_composition_requires_batch_id(self):
        """Test che batch_id sia obbligatorio."""
        with pytest.raises(ValueError, match="Batch ID obbligatorio"):
            BatchComposition(
                batch_id=None,
                peptide_id=1
            )
    
    def test_composition_requires_peptide_id(self):
        """Test che peptide_id sia obbligatorio."""
        with pytest.raises(ValueError, match="Peptide ID obbligatorio"):
            BatchComposition(
                batch_id=1,
                peptide_id=None
            )
    
    def test_mg_amount_conversion(self):
        """Test conversione mg_amount a Decimal."""
        # Da int
        comp1 = BatchComposition(batch_id=1, peptide_id=1, mg_amount=5)
        assert isinstance(comp1.mg_amount, Decimal)
        assert comp1.mg_amount == Decimal('5')
        
        # Da float
        comp2 = BatchComposition(batch_id=1, peptide_id=1, mg_amount=5.5)
        assert isinstance(comp2.mg_amount, Decimal)
        
        # Da string
        comp3 = BatchComposition(batch_id=1, peptide_id=1, mg_amount='5.0')
        assert isinstance(comp3.mg_amount, Decimal)
        assert comp3.mg_amount == Decimal('5.0')


class TestBatchCompositionRepository:
    """Test per BatchCompositionRepository."""
    
    def test_add_peptide_to_batch(self, repo):
        """Test aggiunta peptide a batch."""
        comp_id = repo.add_peptide_to_batch(
            batch_id=1,
            peptide_id=1,
            mg_amount=Decimal('5.0')
        )
        
        assert comp_id == 1
        
        # Verifica nel database
        compositions = repo.get_by_batch(1)
        assert len(compositions) == 1
        assert compositions[0].peptide_id == 1
    
    def test_add_peptide_duplicate_error(self, repo):
        """Test che non si possa aggiungere stesso peptide due volte."""
        repo.add_peptide_to_batch(batch_id=1, peptide_id=1)
        
        with pytest.raises(ValueError, match="già presente"):
            repo.add_peptide_to_batch(batch_id=1, peptide_id=1)
    
    def test_add_peptide_invalid_batch(self, repo):
        """Test errore con batch inesistente."""
        with pytest.raises(ValueError, match="Batch .* non trovato"):
            repo.add_peptide_to_batch(batch_id=999, peptide_id=1)
    
    def test_add_peptide_invalid_peptide(self, repo):
        """Test errore con peptide inesistente."""
        with pytest.raises(ValueError, match="Peptide .* non trovato"):
            repo.add_peptide_to_batch(batch_id=1, peptide_id=999)
    
    def test_get_by_batch(self, repo):
        """Test recupero composizione per batch."""
        # Aggiungi 2 peptidi al batch 1
        repo.add_peptide_to_batch(batch_id=1, peptide_id=1, mg_amount=Decimal('5.0'))
        repo.add_peptide_to_batch(batch_id=1, peptide_id=2, mg_amount=Decimal('3.0'))
        
        compositions = repo.get_by_batch(1)
        
        assert len(compositions) == 2
        assert compositions[0].batch_id == 1
        assert compositions[1].batch_id == 1
    
    def test_get_peptides_in_batch(self, repo):
        """Test recupero peptidi con info complete."""
        repo.add_peptide_to_batch(batch_id=1, peptide_id=1, mg_amount=Decimal('5.0'))
        repo.add_peptide_to_batch(batch_id=1, peptide_id=2, mg_amount=Decimal('3.0'))
        
        peptides = repo.get_peptides_in_batch(1)
        
        assert len(peptides) == 2
        assert peptides[0]['peptide_id'] == 1
        assert peptides[0]['name'] == 'BPC-157'
        assert peptides[0]['mg_amount'] == Decimal('5.0')
        assert peptides[1]['name'] == 'TB-500'
    
    def test_get_by_peptide(self, repo):
        """Test recupero composizione per peptide."""
        # Aggiungi peptide 1 a batch 1 e 2
        repo.add_peptide_to_batch(batch_id=1, peptide_id=1, mg_amount=Decimal('5.0'))
        repo.add_peptide_to_batch(batch_id=2, peptide_id=1, mg_amount=Decimal('10.0'))
        
        compositions = repo.get_by_peptide(1)
        
        assert len(compositions) == 2
        assert all(c.peptide_id == 1 for c in compositions)
    
    def test_get_batches_with_peptide(self, repo):
        """Test recupero batches con info complete."""
        repo.add_peptide_to_batch(batch_id=1, peptide_id=1, mg_amount=Decimal('5.0'))
        repo.add_peptide_to_batch(batch_id=2, peptide_id=1, mg_amount=Decimal('10.0'))
        
        batches = repo.get_batches_with_peptide(1)
        
        assert len(batches) == 2
        assert batches[0]['batch_id'] in [1, 2]
        assert batches[0]['product_name'] in ['Test Batch 1', 'Test Batch 2']
        assert batches[0]['vials_remaining'] > 0
    
    def test_update_mg_amount(self, repo):
        """Test aggiornamento quantità mg."""
        repo.add_peptide_to_batch(batch_id=1, peptide_id=1, mg_amount=Decimal('5.0'))
        
        # Aggiorna
        success = repo.update_mg_amount(
            batch_id=1,
            peptide_id=1,
            mg_amount=Decimal('10.0')
        )
        assert success
        
        # Verifica
        compositions = repo.get_by_batch(1)
        assert compositions[0].mg_amount == Decimal('10.0')
    
    def test_update_mg_amount_not_found(self, repo):
        """Test errore aggiornamento composizione inesistente."""
        with pytest.raises(ValueError, match="non trovata"):
            repo.update_mg_amount(
                batch_id=1,
                peptide_id=1,
                mg_amount=Decimal('10.0')
            )
    
    def test_remove_peptide_from_batch(self, repo):
        """Test rimozione peptide da batch."""
        repo.add_peptide_to_batch(batch_id=1, peptide_id=1)
        repo.add_peptide_to_batch(batch_id=1, peptide_id=2)
        
        # Rimuovi peptide 1
        success, message = repo.remove_peptide_from_batch(batch_id=1, peptide_id=1)
        assert success
        
        # Verifica
        compositions = repo.get_by_batch(1)
        assert len(compositions) == 1
        assert compositions[0].peptide_id == 2
    
    def test_remove_peptide_not_found(self, repo):
        """Test errore rimozione composizione inesistente."""
        success, message = repo.remove_peptide_from_batch(batch_id=1, peptide_id=1)
        assert not success
        assert 'non trovata' in message.lower()
    
    def test_clear_batch_composition(self, repo):
        """Test rimozione tutti i peptidi da un batch."""
        repo.add_peptide_to_batch(batch_id=1, peptide_id=1)
        repo.add_peptide_to_batch(batch_id=1, peptide_id=2)
        repo.add_peptide_to_batch(batch_id=1, peptide_id=3)
        
        # Rimuovi tutti
        count = repo.clear_batch_composition(1)
        assert count == 3
        
        # Verifica
        compositions = repo.get_by_batch(1)
        assert len(compositions) == 0
    
    def test_set_batch_composition(self, repo):
        """Test impostazione completa composizione batch."""
        # Aggiungi composizione iniziale
        repo.add_peptide_to_batch(batch_id=1, peptide_id=1)
        
        # Sostituisci con nuova composizione
        count = repo.set_batch_composition(
            batch_id=1,
            peptides=[
                (2, Decimal('5.0')),
                (3, Decimal('3.0'))
            ]
        )
        
        assert count == 2
        
        # Verifica
        compositions = repo.get_by_batch(1)
        assert len(compositions) == 2
        assert all(c.peptide_id in [2, 3] for c in compositions)
    
    def test_is_blend(self, repo):
        """Test verifica se batch è blend."""
        # Single peptide
        repo.add_peptide_to_batch(batch_id=1, peptide_id=1)
        assert not repo.is_blend(1)
        
        # Blend (multi-peptide)
        repo.add_peptide_to_batch(batch_id=1, peptide_id=2)
        assert repo.is_blend(1)
    
    def test_get_blend_batches(self, repo):
        """Test recupero batch che sono blend."""
        # Batch 1: single peptide
        repo.add_peptide_to_batch(batch_id=1, peptide_id=1)
        
        # Batch 2: blend
        repo.add_peptide_to_batch(batch_id=2, peptide_id=2)
        repo.add_peptide_to_batch(batch_id=2, peptide_id=3)
        
        blend_batches = repo.get_blend_batches()
        
        assert len(blend_batches) == 1
        assert blend_batches[0] == 2
    
    def test_count_peptides_in_batch(self, repo):
        """Test conteggio peptidi in batch."""
        assert repo.count_peptides_in_batch(1) == 0
        
        repo.add_peptide_to_batch(batch_id=1, peptide_id=1)
        assert repo.count_peptides_in_batch(1) == 1
        
        repo.add_peptide_to_batch(batch_id=1, peptide_id=2)
        assert repo.count_peptides_in_batch(1) == 2
    
    def test_get_total_mg_in_batch(self, repo):
        """Test calcolo totale mg in batch."""
        # Nessun peptide
        assert repo.get_total_mg_in_batch(1) is None
        
        # Aggiungi peptidi con quantità
        repo.add_peptide_to_batch(batch_id=1, peptide_id=1, mg_amount=Decimal('5.0'))
        repo.add_peptide_to_batch(batch_id=1, peptide_id=2, mg_amount=Decimal('3.0'))
        
        total = repo.get_total_mg_in_batch(1)
        assert total == Decimal('8.0')
    
    def test_get_total_mg_missing_amounts(self, repo):
        """Test calcolo totale mg con dati mancanti."""
        # Aggiungi peptide senza quantità
        repo.add_peptide_to_batch(batch_id=1, peptide_id=1, mg_amount=None)
        
        total = repo.get_total_mg_in_batch(1)
        assert total is None  # O 0, dipende dall'implementazione
