"""
Test per il modulo Preparation.

Testa sia il model Preparation che il repository PreparationRepository.
"""

import pytest
import sqlite3
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from peptide_manager.models import Preparation, PreparationRepository


@pytest.fixture
def db_connection():
    """Crea connessione database in-memory per test."""
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    
    # Crea schema
    cursor = conn.cursor()
    
    # Tabella suppliers
    cursor.execute('''
        CREATE TABLE suppliers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            deleted_at TIMESTAMP
        )
    ''')
    
    # Tabella peptides
    cursor.execute('''
        CREATE TABLE peptides (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            deleted_at TIMESTAMP
        )
    ''')
    
    # Tabella batches
    cursor.execute('''
        CREATE TABLE batches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT NOT NULL,
            supplier_id INTEGER,
            vials_received INTEGER NOT NULL,
            vials_remaining INTEGER NOT NULL,
            mg_per_vial REAL NOT NULL,
            lot_number TEXT,
            purchase_date DATE,
            deleted_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
        )
    ''')
    
    # Tabella preparations
    cursor.execute('''
        CREATE TABLE preparations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_id INTEGER NOT NULL,
            vials_used INTEGER NOT NULL,
            volume_ml REAL NOT NULL,
            diluent TEXT NOT NULL DEFAULT 'BAC Water',
            preparation_date DATE NOT NULL,
            expiry_date DATE,
            volume_remaining_ml REAL NOT NULL,
            storage_location TEXT,
            notes TEXT,
            deleted_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (batch_id) REFERENCES batches(id) ON DELETE CASCADE
        )
    ''')
    
    # Tabella administrations (per test recalculate_volume)
    cursor.execute('''
        CREATE TABLE administrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            preparation_id INTEGER NOT NULL,
            dose_ml REAL NOT NULL,
            administration_datetime TIMESTAMP NOT NULL,
            deleted_at TIMESTAMP,
            FOREIGN KEY (preparation_id) REFERENCES preparations(id)
        )
    ''')
    
    conn.commit()
    
    yield conn
    
    conn.close()


@pytest.fixture
def sample_batch(db_connection):
    """Crea un batch di esempio per i test."""
    cursor = db_connection.cursor()
    
    # Crea supplier
    cursor.execute("INSERT INTO suppliers (name) VALUES ('Test Supplier')")
    supplier_id = cursor.lastrowid
    
    # Crea batch
    cursor.execute('''
        INSERT INTO batches (
            product_name, supplier_id, vials_received, vials_remaining, 
            mg_per_vial, lot_number, purchase_date
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', ('Test Peptide', supplier_id, 10, 10, 5.0, 'LOT123', '2025-01-01'))
    
    batch_id = cursor.lastrowid
    db_connection.commit()
    
    return batch_id


@pytest.fixture
def repo(db_connection):
    """Crea repository per i test."""
    return PreparationRepository(db_connection)


# ============================================================================
# TEST MODEL - Preparation
# ============================================================================

class TestPreparationModel:
    """Test per il model Preparation."""
    
    def test_creation_valid(self):
        """Test creazione preparation valida."""
        prep = Preparation(
            batch_id=1,
            vials_used=2,
            volume_ml=4.0,
            diluent='BAC Water'
        )
        
        assert prep.batch_id == 1
        assert prep.vials_used == 2
        assert prep.volume_ml == Decimal('4.0')
        assert prep.diluent == 'BAC Water'
        assert prep.volume_remaining_ml == Decimal('4.0')  # Default
        assert prep.preparation_date == date.today()  # Default
    
    def test_creation_invalid_batch_id(self):
        """Test validazione batch_id obbligatorio."""
        with pytest.raises(ValueError, match="Batch ID obbligatorio"):
            Preparation(
                batch_id=None,
                vials_used=1,
                volume_ml=2.0
            )
    
    def test_creation_invalid_vials(self):
        """Test validazione vials_used >= 1."""
        with pytest.raises(ValueError, match="Vials used deve essere >= 1"):
            Preparation(
                batch_id=1,
                vials_used=0,
                volume_ml=2.0
            )
    
    def test_creation_invalid_volume(self):
        """Test validazione volume > 0."""
        with pytest.raises(ValueError, match="Volume deve essere > 0"):
            Preparation(
                batch_id=1,
                vials_used=1,
                volume_ml=0
            )
    
    def test_decimal_conversion(self):
        """Test conversione automatica a Decimal."""
        # Da int
        prep1 = Preparation(batch_id=1, vials_used=1, volume_ml=5)
        assert isinstance(prep1.volume_ml, Decimal)
        assert prep1.volume_ml == Decimal('5')
        
        # Da float
        prep2 = Preparation(batch_id=1, vials_used=1, volume_ml=3.5)
        assert isinstance(prep2.volume_ml, Decimal)
        assert prep2.volume_ml == Decimal('3.5')
        
        # Da string
        prep3 = Preparation(batch_id=1, vials_used=1, volume_ml=2.75)
        assert isinstance(prep3.volume_ml, Decimal)
        assert prep3.volume_ml == Decimal('2.75')
        
        # volume_remaining_ml
        prep4 = Preparation(
            batch_id=1, 
            vials_used=1, 
            volume_ml=5.0,
            volume_remaining_ml=3.5
        )
        assert isinstance(prep4.volume_remaining_ml, Decimal)
        assert prep4.volume_remaining_ml == Decimal('3.5')
    
    def test_date_conversion(self):
        """Test conversione automatica date."""
        # preparation_date da string
        prep1 = Preparation(
            batch_id=1,
            vials_used=1,
            volume_ml=2.0,
            preparation_date='2025-01-15'
        )
        assert isinstance(prep1.preparation_date, date)
        assert prep1.preparation_date == date(2025, 1, 15)
        
        # expiry_date da string
        prep2 = Preparation(
            batch_id=1,
            vials_used=1,
            volume_ml=2.0,
            expiry_date='2025-12-31'
        )
        assert isinstance(prep2.expiry_date, date)
        assert prep2.expiry_date == date(2025, 12, 31)
    
    def test_is_deleted(self):
        """Test metodo is_deleted()."""
        prep1 = Preparation(batch_id=1, vials_used=1, volume_ml=2.0)
        assert prep1.is_deleted() is False
        
        prep2 = Preparation(
            batch_id=1, 
            vials_used=1, 
            volume_ml=2.0,
            deleted_at=datetime.now()
        )
        assert prep2.is_deleted() is True
    
    def test_is_depleted(self):
        """Test metodo is_depleted()."""
        prep1 = Preparation(
            batch_id=1, 
            vials_used=1, 
            volume_ml=5.0,
            volume_remaining_ml=2.5
        )
        assert prep1.is_depleted() is False
        
        prep2 = Preparation(
            batch_id=1, 
            vials_used=1, 
            volume_ml=5.0,
            volume_remaining_ml=0
        )
        assert prep2.is_depleted() is True
        
        prep3 = Preparation(
            batch_id=1, 
            vials_used=1, 
            volume_ml=5.0,
            volume_remaining_ml=-0.1
        )
        assert prep3.is_depleted() is True
    
    def test_is_expired(self):
        """Test metodo is_expired()."""
        # Senza expiry_date
        prep1 = Preparation(batch_id=1, vials_used=1, volume_ml=2.0)
        assert prep1.is_expired() is False
        
        # Con expiry_date futura
        tomorrow = date.today() + timedelta(days=1)
        prep2 = Preparation(
            batch_id=1,
            vials_used=1,
            volume_ml=2.0,
            expiry_date=tomorrow
        )
        assert prep2.is_expired() is False
        
        # Con expiry_date passata
        yesterday = date.today() - timedelta(days=1)
        prep3 = Preparation(
            batch_id=1,
            vials_used=1,
            volume_ml=2.0,
            expiry_date=yesterday
        )
        assert prep3.is_expired() is True
    
    def test_is_active(self):
        """Test metodo is_active()."""
        # Attiva
        prep1 = Preparation(
            batch_id=1,
            vials_used=1,
            volume_ml=5.0,
            volume_remaining_ml=3.0
        )
        assert prep1.is_active() is True
        
        # Non attiva - eliminata
        prep2 = Preparation(
            batch_id=1,
            vials_used=1,
            volume_ml=5.0,
            deleted_at=datetime.now()
        )
        assert prep2.is_active() is False
        
        # Non attiva - esaurita
        prep3 = Preparation(
            batch_id=1,
            vials_used=1,
            volume_ml=5.0,
            volume_remaining_ml=0
        )
        assert prep3.is_active() is False
        
        # Non attiva - scaduta
        yesterday = date.today() - timedelta(days=1)
        prep4 = Preparation(
            batch_id=1,
            vials_used=1,
            volume_ml=5.0,
            expiry_date=yesterday
        )
        assert prep4.is_active() is False
    
    def test_calculate_concentration(self):
        """Test calcolo concentrazione mg/ml."""
        prep = Preparation(
            batch_id=1,
            vials_used=2,
            volume_ml=4.0
        )
        
        # 2 fiale * 5mg = 10mg totali
        # 10mg / 4ml = 2.5 mg/ml
        concentration = prep.calculate_concentration_mg_ml(Decimal('5.0'))
        assert concentration == Decimal('2.5')
        
        # Test con altri valori
        prep2 = Preparation(
            batch_id=1,
            vials_used=1,
            volume_ml=2.0
        )
        concentration2 = prep2.calculate_concentration_mg_ml(10.0)
        assert concentration2 == Decimal('5.0')  # 1 * 10mg / 2ml = 5 mg/ml


# ============================================================================
# TEST REPOSITORY - PreparationRepository
# ============================================================================

class TestPreparationRepository:
    """Test per PreparationRepository."""
    
    def test_create(self, repo, sample_batch):
        """Test creazione preparation e decremento fiale."""
        # Verifica fiale iniziali
        cursor = repo.conn.cursor()
        cursor.execute('SELECT vials_remaining FROM batches WHERE id = ?', (sample_batch,))
        initial_vials = cursor.fetchone()[0]
        assert initial_vials == 10
        
        # Crea preparation
        prep = Preparation(
            batch_id=sample_batch,
            vials_used=3,
            volume_ml=6.0,
            diluent='BAC Water',
            preparation_date=date(2025, 1, 15)
        )
        
        prep_id = repo.create(prep)
        assert prep_id > 0
        
        # Verifica fiale decrementate
        cursor.execute('SELECT vials_remaining FROM batches WHERE id = ?', (sample_batch,))
        remaining_vials = cursor.fetchone()[0]
        assert remaining_vials == 7  # 10 - 3 = 7
        
        # Verifica preparation salvata
        saved_prep = repo.get_by_id(prep_id)
        assert saved_prep is not None
        assert saved_prep.batch_id == sample_batch
        assert saved_prep.vials_used == 3
        assert saved_prep.volume_ml == Decimal('6.0')
    
    def test_create_insufficient_vials(self, repo, sample_batch):
        """Test errore quando fiale insufficienti."""
        prep = Preparation(
            batch_id=sample_batch,
            vials_used=15,  # Più di 10 disponibili
            volume_ml=10.0
        )
        
        with pytest.raises(ValueError, match="Fiale insufficienti"):
            repo.create(prep)
    
    def test_create_batch_not_found(self, repo):
        """Test errore quando batch non esiste."""
        prep = Preparation(
            batch_id=9999,  # Non esiste
            vials_used=1,
            volume_ml=2.0
        )
        
        with pytest.raises(ValueError, match="Batch #9999 non trovato"):
            repo.create(prep)
    
    def test_get_by_id(self, repo, sample_batch):
        """Test recupero preparation per ID."""
        # Crea preparation
        prep = Preparation(
            batch_id=sample_batch,
            vials_used=2,
            volume_ml=4.0,
            notes='Test prep'
        )
        prep_id = repo.create(prep)
        
        # Recupera
        retrieved = repo.get_by_id(prep_id)
        assert retrieved is not None
        assert retrieved.id == prep_id
        assert retrieved.batch_id == sample_batch
        assert retrieved.vials_used == 2
        assert retrieved.notes == 'Test prep'
        
        # ID non esistente
        not_found = repo.get_by_id(9999)
        assert not_found is None
    
    def test_get_all_filters(self, repo, sample_batch):
        """Test get_all con vari filtri."""
        # Crea preparations diverse
        prep1 = Preparation(batch_id=sample_batch, vials_used=1, volume_ml=2.0)
        prep2 = Preparation(batch_id=sample_batch, vials_used=1, volume_ml=2.0, volume_remaining_ml=0)  # Esaurita
        prep3 = Preparation(batch_id=sample_batch, vials_used=1, volume_ml=2.0)
        
        id1 = repo.create(prep1)
        id2 = repo.create(prep2)
        id3 = repo.create(prep3)
        
        # Elimina prep3 (soft delete)
        repo.delete(id3)
        
        # Test: tutte (esclude eliminate)
        all_preps = repo.get_all()
        assert len(all_preps) == 2
        
        # Test: include eliminate
        all_with_deleted = repo.get_all(include_deleted=True)
        assert len(all_with_deleted) == 3
        
        # Test: solo attive
        active_preps = repo.get_all(only_active=True)
        assert len(active_preps) == 1  # Solo prep1 (prep2 è esaurita)
        
        # Test: per batch_id
        batch_preps = repo.get_all(batch_id=sample_batch)
        assert len(batch_preps) == 2
    
    def test_update(self, repo, sample_batch):
        """Test aggiornamento preparation."""
        # Crea preparation
        prep = Preparation(
            batch_id=sample_batch,
            vials_used=2,
            volume_ml=4.0,
            notes='Original'
        )
        prep_id = repo.create(prep)
        
        # Recupera e modifica
        prep = repo.get_by_id(prep_id)
        prep.notes = 'Updated'
        prep.volume_remaining_ml = Decimal('2.5')
        prep.storage_location = 'Fridge A'
        
        # Aggiorna
        success = repo.update(prep)
        assert success is True
        
        # Verifica modifiche
        updated = repo.get_by_id(prep_id)
        assert updated.notes == 'Updated'
        assert updated.volume_remaining_ml == Decimal('2.5')
        assert updated.storage_location == 'Fridge A'
    
    def test_delete_soft(self, repo, sample_batch):
        """Test soft delete."""
        # Crea preparation
        prep = Preparation(batch_id=sample_batch, vials_used=2, volume_ml=4.0)
        prep_id = repo.create(prep)
        
        # Soft delete
        success, message = repo.delete(prep_id, force=False)
        assert success is True
        assert 'eliminata' in message
        
        # Verifica non più recuperabile (senza include_deleted)
        deleted_prep = repo.get_by_id(prep_id)
        assert deleted_prep is None
        
        # Ma esiste ancora con include_deleted
        deleted_prep = repo.get_by_id(prep_id, include_deleted=True)
        assert deleted_prep is not None
        assert deleted_prep.deleted_at is not None
    
    def test_delete_with_restore_vials(self, repo, sample_batch):
        """Test delete con ripristino fiale."""
        # Verifica fiale iniziali
        cursor = repo.conn.cursor()
        cursor.execute('SELECT vials_remaining FROM batches WHERE id = ?', (sample_batch,))
        initial_vials = cursor.fetchone()[0]
        
        # Crea preparation (usa 3 fiale)
        prep = Preparation(batch_id=sample_batch, vials_used=3, volume_ml=6.0)
        prep_id = repo.create(prep)
        
        # Verifica fiale decrementate
        cursor.execute('SELECT vials_remaining FROM batches WHERE id = ?', (sample_batch,))
        after_create_vials = cursor.fetchone()[0]
        assert after_create_vials == initial_vials - 3
        
        # Delete con restore_vials
        success, message = repo.delete(prep_id, restore_vials=True)
        assert success is True
        assert 'fiale ripristinate' in message
        
        # Verifica fiale ripristinate
        cursor.execute('SELECT vials_remaining FROM batches WHERE id = ?', (sample_batch,))
        after_delete_vials = cursor.fetchone()[0]
        assert after_delete_vials == initial_vials  # Torna al valore iniziale
    
    def test_delete_hard(self, repo, sample_batch):
        """Test hard delete (eliminazione permanente)."""
        # Crea preparation
        prep = Preparation(batch_id=sample_batch, vials_used=1, volume_ml=2.0)
        prep_id = repo.create(prep)
        
        # Hard delete
        success, message = repo.delete(prep_id, force=True)
        assert success is True
        assert 'permanentemente' in message
        
        # Verifica non esiste più (nemmeno con include_deleted)
        deleted_prep = repo.get_by_id(prep_id, include_deleted=True)
        assert deleted_prep is None
    
    def test_restore(self, repo, sample_batch):
        """Test ripristino preparation eliminata."""
        # Crea e elimina preparation
        prep = Preparation(batch_id=sample_batch, vials_used=1, volume_ml=2.0)
        prep_id = repo.create(prep)
        repo.delete(prep_id)
        
        # Verifica eliminata
        assert repo.get_by_id(prep_id) is None
        
        # Ripristina
        success, message = repo.restore(prep_id)
        assert success is True
        assert 'ripristinata' in message
        
        # Verifica ripristinata
        restored = repo.get_by_id(prep_id)
        assert restored is not None
        assert restored.deleted_at is None
    
    def test_use_volume(self, repo, sample_batch):
        """Test uso volume dalla preparation."""
        # Crea preparation con 5ml
        prep = Preparation(
            batch_id=sample_batch,
            vials_used=1,
            volume_ml=5.0
        )
        prep_id = repo.create(prep)
        
        # Usa 2ml
        success, message = repo.use_volume(prep_id, 2.0)
        assert success is True
        assert '2' in message
        
        # Verifica volume rimanente
        prep = repo.get_by_id(prep_id)
        assert prep.volume_remaining_ml == Decimal('3.0')  # 5 - 2 = 3
        
        # Usa altri 3ml (esaurisce)
        success, message = repo.use_volume(prep_id, 3.0)
        assert success is True
        assert 'esaurita' in message
        
        # Verifica esaurita
        prep = repo.get_by_id(prep_id)
        assert prep.volume_remaining_ml == Decimal('0')
        assert prep.is_depleted() is True
    
    def test_use_volume_insufficient(self, repo, sample_batch):
        """Test errore quando volume insufficiente."""
        # Crea preparation con 2ml
        prep = Preparation(
            batch_id=sample_batch,
            vials_used=1,
            volume_ml=2.0
        )
        prep_id = repo.create(prep)
        
        # Prova a usare 3ml (più di quanto disponibile)
        with pytest.raises(ValueError, match="Volume insufficiente"):
            repo.use_volume(prep_id, 3.0)
    
    def test_recalculate_volume(self, repo, sample_batch):
        """Test ricalcolo volume basato su somministrazioni."""
        # Crea preparation con 10ml
        prep = Preparation(
            batch_id=sample_batch,
            vials_used=2,
            volume_ml=10.0
        )
        prep_id = repo.create(prep)
        
        # Simula somministrazioni (3ml + 2ml = 5ml totali)
        cursor = repo.conn.cursor()
        cursor.execute('''
            INSERT INTO administrations (preparation_id, dose_ml, administration_datetime)
            VALUES (?, ?, ?)
        ''', (prep_id, 3.0, datetime.now().isoformat()))
        cursor.execute('''
            INSERT INTO administrations (preparation_id, dose_ml, administration_datetime)
            VALUES (?, ?, ?)
        ''', (prep_id, 2.0, datetime.now().isoformat()))
        repo.conn.commit()
        
        # Modifica manualmente volume_remaining (simula discrepanza)
        cursor.execute('''
            UPDATE preparations 
            SET volume_remaining_ml = ?
            WHERE id = ?
        ''', (7.0, prep_id))  # Dovrebbe essere 5ml (10 - 5)
        repo.conn.commit()
        
        # Ricalcola
        success, message = repo.recalculate_volume(prep_id)
        assert success is True
        assert 'ricalcolato' in message
        assert '2' in message  # Differenza di 2ml
        
        # Verifica volume corretto
        prep = repo.get_by_id(prep_id)
        assert prep.volume_remaining_ml == Decimal('5.0')  # 10 - 5 = 5
    
    def test_get_expired(self, repo, sample_batch):
        """Test recupero preparations scadute."""
        yesterday = date.today() - timedelta(days=1)
        tomorrow = date.today() + timedelta(days=1)
        
        # Crea preparation scaduta
        prep1 = Preparation(
            batch_id=sample_batch,
            vials_used=1,
            volume_ml=2.0,
            expiry_date=yesterday
        )
        id1 = repo.create(prep1)
        
        # Crea preparation non scaduta
        prep2 = Preparation(
            batch_id=sample_batch,
            vials_used=1,
            volume_ml=2.0,
            expiry_date=tomorrow
        )
        id2 = repo.create(prep2)
        
        # Crea preparation senza expiry
        prep3 = Preparation(
            batch_id=sample_batch,
            vials_used=1,
            volume_ml=2.0
        )
        id3 = repo.create(prep3)
        
        # Recupera scadute
        expired = repo.get_expired()
        assert len(expired) == 1
        assert expired[0].id == id1
    
    def test_count(self, repo, sample_batch):
        """Test conteggio preparations."""
        # Crea preparations
        prep1 = Preparation(batch_id=sample_batch, vials_used=1, volume_ml=2.0)
        prep2 = Preparation(batch_id=sample_batch, vials_used=1, volume_ml=2.0, volume_remaining_ml=0)
        prep3 = Preparation(batch_id=sample_batch, vials_used=1, volume_ml=2.0)
        
        id1 = repo.create(prep1)
        id2 = repo.create(prep2)
        id3 = repo.create(prep3)
        
        # Elimina prep3
        repo.delete(id3)
        
        # Test: count totale (esclude eliminate)
        total = repo.count()
        assert total == 2
        
        # Test: count con eliminate
        total_with_deleted = repo.count(include_deleted=True)
        assert total_with_deleted == 3
        
        # Test: count solo attive
        active = repo.count(only_active=True)
        assert active == 1  # Solo prep1 (prep2 è esaurita)
        
        # Test: count per batch
        batch_count = repo.count(batch_id=sample_batch)
        assert batch_count == 2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
