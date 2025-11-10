"""
Test per Batch model e BatchRepository.
"""

import pytest
import sqlite3
from datetime import date, timedelta
from decimal import Decimal
from peptide_manager.models.batch import Batch, BatchRepository


@pytest.fixture
def db_connection():
    """Crea database in-memory per test."""
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    
    # Schema suppliers
    conn.execute('''
        CREATE TABLE suppliers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            country TEXT,
            website TEXT,
            email TEXT,
            notes TEXT,
            reliability_rating INTEGER CHECK(reliability_rating BETWEEN 1 AND 5),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Schema batches
    conn.execute('''
        CREATE TABLE batches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            supplier_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            batch_number TEXT NOT NULL,
            manufacturing_date DATE,
            expiration_date DATE,
            mg_per_vial REAL,
            vials_count INTEGER NOT NULL DEFAULT 1,
            vials_remaining INTEGER NOT NULL DEFAULT 1,
            purchase_date DATE,
            price_per_vial REAL,
            storage_location TEXT,
            notes TEXT,
            coa_path TEXT,
            deleted_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
        )
    ''')
    
    # Schema preparations (per test relazioni)
    conn.execute('''
        CREATE TABLE preparations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_id INTEGER NOT NULL,
            FOREIGN KEY (batch_id) REFERENCES batches(id) ON DELETE CASCADE
        )
    ''')
    
    # Aggiungi supplier di test
    conn.execute(
        "INSERT INTO suppliers (name, country) VALUES (?, ?)",
        ('TestSupplier', 'USA')
    )
    
    conn.commit()
    yield conn
    conn.close()


@pytest.fixture
def repo(db_connection):
    """Crea repository per test."""
    return BatchRepository(db_connection)


@pytest.fixture
def sample_batch():
    """Batch di esempio per test."""
    return Batch(
        supplier_id=1,
        product_name='BPC-157',
        batch_number='BATCH001',
        manufacturing_date=date(2024, 1, 1),
        expiration_date=date(2026, 1, 1),
        mg_per_vial=Decimal('5.0'),
        vials_count=10,
        vials_remaining=10,
        purchase_date=date(2024, 1, 15),
        price_per_vial=Decimal('25.50'),
        storage_location='Freezer A',
        notes='Test batch'
    )


class TestBatchModel:
    """Test per Batch dataclass."""
    
    def test_batch_creation(self, sample_batch):
        """Test creazione batch valido."""
        assert sample_batch.supplier_id == 1
        assert sample_batch.product_name == 'BPC-157'
        assert sample_batch.vials_count == 10
        assert isinstance(sample_batch.mg_per_vial, Decimal)
    
    def test_batch_requires_supplier(self):
        """Test che supplier_id sia obbligatorio."""
        with pytest.raises(ValueError, match="Fornitore obbligatorio"):
            Batch(
                supplier_id=None,
                product_name='Test',
                batch_number='BATCH001'
            )
    
    def test_batch_requires_product_name(self):
        """Test che product_name sia obbligatorio."""
        with pytest.raises(ValueError, match="Nome prodotto obbligatorio"):
            Batch(
                supplier_id=1,
                product_name='',
                batch_number='BATCH001'
            )
    
    def test_batch_requires_batch_number(self):
        """Test che batch_number sia obbligatorio."""
        with pytest.raises(ValueError, match="Numero batch obbligatorio"):
            Batch(
                supplier_id=1,
                product_name='Test',
                batch_number=''
            )
    
    def test_batch_vials_validation(self):
        """Test validazione fiale."""
        # Vials count < 1
        with pytest.raises(ValueError, match="Numero fiale deve essere >= 1"):
            Batch(
                supplier_id=1,
                product_name='Test',
                batch_number='BATCH001',
                vials_count=0
            )
        
        # Vials remaining negativo
        with pytest.raises(ValueError, match="Fiale rimanenti non possono essere negative"):
            Batch(
                supplier_id=1,
                product_name='Test',
                batch_number='BATCH001',
                vials_remaining=-1
            )
        
        # Vials remaining > count
        with pytest.raises(ValueError, match="Fiale rimanenti non possono superare fiale totali"):
            Batch(
                supplier_id=1,
                product_name='Test',
                batch_number='BATCH001',
                vials_count=5,
                vials_remaining=10
            )
    
    def test_is_deleted(self, sample_batch):
        """Test metodo is_deleted."""
        assert not sample_batch.is_deleted()
        
        from datetime import datetime
        sample_batch.deleted_at = datetime.now()
        assert sample_batch.is_deleted()
    
    def test_is_depleted(self, sample_batch):
        """Test metodo is_depleted."""
        assert not sample_batch.is_depleted()
        
        sample_batch.vials_remaining = 0
        assert sample_batch.is_depleted()
    
    def test_is_expired(self, sample_batch):
        """Test metodo is_expired."""
        # Batch valido (scadenza futura)
        assert not sample_batch.is_expired()
        
        # Batch scaduto
        sample_batch.expiration_date = date.today() - timedelta(days=1)
        assert sample_batch.is_expired()
        
        # Nessuna scadenza
        sample_batch.expiration_date = None
        assert not sample_batch.is_expired()
    
    def test_days_until_expiration(self, sample_batch):
        """Test calcolo giorni alla scadenza."""
        # Scadenza tra 30 giorni
        sample_batch.expiration_date = date.today() + timedelta(days=30)
        assert sample_batch.days_until_expiration() == 30
        
        # Scaduto da 10 giorni
        sample_batch.expiration_date = date.today() - timedelta(days=10)
        assert sample_batch.days_until_expiration() == -10
        
        # Nessuna scadenza
        sample_batch.expiration_date = None
        assert sample_batch.days_until_expiration() is None


class TestBatchRepository:
    """Test per BatchRepository."""
    
    def test_create_batch(self, repo, sample_batch):
        """Test creazione batch."""
        batch_id = repo.create(sample_batch)
        
        assert batch_id == 1
        
        # Verifica nel database
        retrieved = repo.get_by_id(batch_id)
        assert retrieved is not None
        assert retrieved.product_name == 'BPC-157'
        assert retrieved.vials_count == 10
    
    def test_get_by_id(self, repo, sample_batch):
        """Test recupero batch per ID."""
        batch_id = repo.create(sample_batch)
        
        batch = repo.get_by_id(batch_id)
        
        assert batch is not None
        assert batch.id == batch_id
        assert batch.product_name == 'BPC-157'
    
    def test_get_by_id_not_found(self, repo):
        """Test recupero batch inesistente."""
        batch = repo.get_by_id(999)
        assert batch is None
    
    def test_get_all(self, repo, sample_batch):
        """Test recupero tutti i batches."""
        # Crea 3 batches
        repo.create(sample_batch)
        
        batch2 = Batch(
            supplier_id=1,
            product_name='TB-500',
            batch_number='BATCH002',
            vials_count=5,
            vials_remaining=5
        )
        repo.create(batch2)
        
        batch3 = Batch(
            supplier_id=1,
            product_name='Semaglutide',
            batch_number='BATCH003',
            vials_count=3,
            vials_remaining=0  # Esaurito
        )
        repo.create(batch3)
        
        # Recupera tutti
        batches = repo.get_all()
        assert len(batches) == 3
    
    def test_get_all_with_search(self, repo, sample_batch):
        """Test ricerca batches."""
        repo.create(sample_batch)
        
        batch2 = Batch(
            supplier_id=1,
            product_name='TB-500',
            batch_number='BATCH002',
            vials_count=5,
            vials_remaining=5
        )
        repo.create(batch2)
        
        # Cerca per nome
        results = repo.get_all(search='BPC')
        assert len(results) == 1
        assert results[0].product_name == 'BPC-157'
        
        # Cerca per batch number
        results = repo.get_all(search='BATCH002')
        assert len(results) == 1
        assert results[0].product_name == 'TB-500'
    
    def test_get_all_only_available(self, repo, sample_batch):
        """Test filtro solo batches disponibili."""
        # Batch disponibile
        repo.create(sample_batch)
        
        # Batch esaurito
        batch2 = Batch(
            supplier_id=1,
            product_name='TB-500',
            batch_number='BATCH002',
            vials_count=5,
            vials_remaining=0
        )
        repo.create(batch2)
        
        # Solo disponibili
        available = repo.get_all(only_available=True)
        assert len(available) == 1
        assert available[0].vials_remaining > 0
    
    def test_get_all_only_depleted(self, repo, sample_batch):
        """Test filtro solo batches esauriti."""
        # Batch disponibile
        repo.create(sample_batch)
        
        # Batch esaurito
        batch2 = Batch(
            supplier_id=1,
            product_name='TB-500',
            batch_number='BATCH002',
            vials_count=5,
            vials_remaining=0
        )
        repo.create(batch2)
        
        # Solo esauriti
        depleted = repo.get_all(only_depleted=True)
        assert len(depleted) == 1
        assert depleted[0].vials_remaining == 0
    
    def test_update_batch(self, repo, sample_batch):
        """Test aggiornamento batch."""
        batch_id = repo.create(sample_batch)
        
        # Recupera e modifica
        batch = repo.get_by_id(batch_id)
        batch.vials_remaining = 8
        batch.notes = 'Updated notes'
        
        # Aggiorna
        success = repo.update(batch)
        assert success
        
        # Verifica
        updated = repo.get_by_id(batch_id)
        assert updated.vials_remaining == 8
        assert updated.notes == 'Updated notes'
    
    def test_soft_delete(self, repo, sample_batch):
        """Test soft delete batch."""
        batch_id = repo.create(sample_batch)
        
        # Soft delete
        success, message = repo.delete(batch_id, force=False)
        assert success
        assert 'archiviato' in message.lower()
        
        # Non appare in get_all (default)
        batches = repo.get_all()
        assert len(batches) == 0
        
        # Appare con include_deleted
        batches = repo.get_all(include_deleted=True)
        assert len(batches) == 1
        assert batches[0].is_deleted()
    
    def test_restore_batch(self, repo, sample_batch):
        """Test ripristino batch eliminato."""
        batch_id = repo.create(sample_batch)
        
        # Elimina
        repo.delete(batch_id, force=False)
        
        # Ripristina
        success, message = repo.restore(batch_id)
        assert success
        assert 'ripristinato' in message.lower()
        
        # Appare in get_all
        batches = repo.get_all()
        assert len(batches) == 1
        assert not batches[0].is_deleted()
    
    def test_hard_delete(self, repo, sample_batch):
        """Test hard delete batch."""
        batch_id = repo.create(sample_batch)
        
        # Hard delete
        success, message = repo.delete(batch_id, force=True)
        assert success
        assert 'definitivamente' in message.lower()
        
        # Non appare nemmeno con include_deleted
        batches = repo.get_all(include_deleted=True)
        assert len(batches) == 0
    
    def test_adjust_vials_add(self, repo, sample_batch):
        """Test aggiunta fiale."""
        batch_id = repo.create(sample_batch)
        
        # Aggiungi 2 fiale
        success, message = repo.adjust_vials(batch_id, adjustment=2)
        assert success
        
        # Verifica
        batch = repo.get_by_id(batch_id)
        assert batch.vials_remaining == 12  # Era 10
    
    def test_adjust_vials_remove(self, repo, sample_batch):
        """Test rimozione fiale."""
        batch_id = repo.create(sample_batch)
        
        # Rimuovi 3 fiale
        success, message = repo.adjust_vials(batch_id, adjustment=-3)
        assert success
        
        # Verifica
        batch = repo.get_by_id(batch_id)
        assert batch.vials_remaining == 7  # Era 10
    
    def test_adjust_vials_negative_error(self, repo, sample_batch):
        """Test che non si possano avere fiale negative."""
        batch_id = repo.create(sample_batch)
        
        # Prova a rimuovere più fiale di quelle disponibili
        success, message = repo.adjust_vials(batch_id, adjustment=-15)
        assert not success
        assert 'negative' in message.lower()
    
    def test_get_expiring_soon(self, repo, sample_batch):
        """Test recupero batches in scadenza."""
        # Batch in scadenza tra 10 giorni
        sample_batch.expiration_date = date.today() + timedelta(days=10)
        repo.create(sample_batch)
        
        # Batch in scadenza tra 60 giorni
        batch2 = Batch(
            supplier_id=1,
            product_name='TB-500',
            batch_number='BATCH002',
            expiration_date=date.today() + timedelta(days=60),
            vials_count=5,
            vials_remaining=5
        )
        repo.create(batch2)
        
        # Recupera in scadenza entro 30 giorni
        expiring = repo.get_expiring_soon(days=30)
        assert len(expiring) == 1
        assert expiring[0].product_name == 'BPC-157'
    
    def test_get_inventory_summary(self, repo, sample_batch):
        """Test statistiche inventario."""
        # Batch disponibile
        repo.create(sample_batch)
        
        # Batch esaurito
        batch2 = Batch(
            supplier_id=1,
            product_name='TB-500',
            batch_number='BATCH002',
            vials_count=5,
            vials_remaining=0
        )
        repo.create(batch2)
        
        # Batch scaduto
        batch3 = Batch(
            supplier_id=1,
            product_name='Semaglutide',
            batch_number='BATCH003',
            expiration_date=date.today() - timedelta(days=1),
            vials_count=3,
            vials_remaining=3
        )
        repo.create(batch3)
        
        summary = repo.get_inventory_summary()
        
        assert summary['total_batches'] == 3
        assert summary['available_batches'] == 2  # 2 con fiale > 0
        assert summary['depleted_batches'] == 1
        assert summary['total_vials_remaining'] == 13  # 10 + 0 + 3
        assert summary['expired_batches'] == 1
    
    def test_count(self, repo, sample_batch):
        """Test conteggio batches."""
        assert repo.count() == 0
        
        repo.create(sample_batch)
        assert repo.count() == 1
        
        # Soft delete non conta
        repo.delete(1, force=False)
        assert repo.count() == 0
        
        # Ma con include_deleted sì
        assert repo.count(include_deleted=True) == 1
