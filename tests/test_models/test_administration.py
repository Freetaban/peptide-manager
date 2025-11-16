"""
Test per Administration model e AdministrationRepository.
"""

import pytest
import sqlite3
from datetime import datetime, timedelta
from decimal import Decimal

from peptide_manager.models.administration import Administration, AdministrationRepository
from peptide_manager.models.supplier import Supplier, SupplierRepository
from peptide_manager.models.peptide import Peptide, PeptideRepository
from peptide_manager.models.batch import Batch, BatchRepository
from peptide_manager.models.preparation import Preparation, PreparationRepository
from peptide_manager.models.protocol import Protocol, ProtocolRepository


@pytest.fixture
def db_conn():
    """Connessione in-memory per test."""
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    
    # Schema administrations
    conn.execute('''
        CREATE TABLE IF NOT EXISTS administrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            preparation_id INTEGER NOT NULL,
            protocol_id INTEGER,
            administration_datetime TEXT NOT NULL,
            dose_ml REAL NOT NULL,
            injection_site TEXT,
            injection_method TEXT,
            notes TEXT,
            side_effects TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            deleted_at TEXT,
            FOREIGN KEY (preparation_id) REFERENCES preparations(id),
            FOREIGN KEY (protocol_id) REFERENCES protocols(id)
        )
    ''')
    
    # Schema dipendenze
    conn.execute('''
        CREATE TABLE IF NOT EXISTS suppliers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            country TEXT,
            website TEXT,
            email TEXT,
            notes TEXT,
            reliability_rating INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            deleted_at TEXT
        )
    ''')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS peptides (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            sequence TEXT,
            molecular_weight REAL,
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            deleted_at TEXT
        )
    ''')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS batches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_number TEXT UNIQUE,
            product_name TEXT NOT NULL,
            supplier_id INTEGER NOT NULL,
            manufacturing_date TEXT,
            expiration_date TEXT,
            mg_per_vial REAL,
            vials_count INTEGER DEFAULT 1,
            vials_received INTEGER DEFAULT 0,
            vials_remaining INTEGER DEFAULT 1,
            purchase_date TEXT,
            price_per_vial REAL,
            total_price REAL,
            storage_location TEXT,
            notes TEXT,
            lot_number TEXT,
            coa_path TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            deleted_at TEXT,
            FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
        )
    ''')
    # Schema batch_composition (usato per dettagli somministrazioni)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS batch_composition (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_id INTEGER NOT NULL,
            peptide_id INTEGER NOT NULL,
            mg_amount REAL,
            FOREIGN KEY (batch_id) REFERENCES batches(id),
            FOREIGN KEY (peptide_id) REFERENCES peptides(id)
        )
    ''')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS preparations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_id INTEGER NOT NULL,
            vials_used INTEGER NOT NULL,
            volume_ml REAL NOT NULL,
            volume_remaining_ml REAL NOT NULL,
            preparation_date TEXT NOT NULL,
            expiry_date TEXT,
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            deleted_at TEXT,
            FOREIGN KEY (batch_id) REFERENCES batches(id)
        )
    ''')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS protocols (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            injection_method TEXT,
            frequency TEXT,
            duration_weeks INTEGER,
            dose_ml REAL,
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            deleted_at TEXT
        )
    ''')
    
    yield conn
    conn.close()


@pytest.fixture
def repo(db_conn):
    """Repository per test."""
    return AdministrationRepository(db_conn)


@pytest.fixture
def sample_preparation(db_conn):
    """Crea preparazione di test con SQL diretto."""
    cursor = db_conn.cursor()
    
    # Supplier
    cursor.execute("INSERT INTO suppliers (name, email) VALUES (?, ?)",
                   ("Test Supplier", "test@test.com"))
    supplier_id = cursor.lastrowid
    
    # Batch
    cursor.execute('''
        INSERT INTO batches (
            product_name, supplier_id, vials_received, vials_remaining, 
            mg_per_vial, lot_number
        ) VALUES (?, ?, ?, ?, ?, ?)
    ''', ('Test Peptide', supplier_id, 10, 10, 5.0, 'BATCH001'))
    batch_id = cursor.lastrowid
    
    # Preparation
    cursor.execute('''
        INSERT INTO preparations (
            batch_id, vials_used, volume_ml, volume_remaining_ml, preparation_date
        ) VALUES (?, ?, ?, ?, ?)
    ''', (batch_id, 1, 10.0, 10.0, '2025-01-10'))
    prep_id = cursor.lastrowid
    
    db_conn.commit()
    return prep_id


@pytest.fixture
def sample_protocol(db_conn):
    """Crea protocollo di test con SQL diretto."""
    cursor = db_conn.cursor()
    cursor.execute('''
        INSERT INTO protocols (name, description, dose_ml)
        VALUES (?, ?, ?)
    ''', ('Test Protocol', 'Test protocol for administrations', 0.5))
    protocol_id = cursor.lastrowid
    db_conn.commit()
    return protocol_id


# ==================== TEST ADMINISTRATION MODEL ====================

def test_administration_creation():
    """Test creazione Administration."""
    admin = Administration(
        preparation_id=1,
        dose_ml=0.5,
        administration_datetime=datetime.now()
    )
    assert admin.preparation_id == 1
    assert admin.dose_ml == Decimal('0.5')
    assert admin.protocol_id is None


def test_administration_with_protocol():
    """Test Administration con protocollo."""
    admin = Administration(
        preparation_id=1,
        protocol_id=1,
        dose_ml=0.5,
        injection_site="Subcutaneous"
    )
    assert admin.has_protocol()
    assert admin.injection_site == "Subcutaneous"


def test_administration_datetime_conversion():
    """Test conversione datetime da stringa."""
    dt_str = "2025-01-10T10:30:00"
    admin = Administration(
        preparation_id=1,
        dose_ml=0.5,
        administration_datetime=dt_str
    )
    assert isinstance(admin.administration_datetime, datetime)


def test_administration_dose_conversion():
    """Test conversione dose a Decimal."""
    admin = Administration(
        preparation_id=1,
        dose_ml="0.75",
        administration_datetime=datetime.now()
    )
    assert admin.dose_ml == Decimal('0.75')


def test_administration_requires_preparation_id():
    """Test che preparation_id sia obbligatorio."""
    with pytest.raises(ValueError, match="Preparation ID obbligatorio"):
        Administration(
            preparation_id=None,
            dose_ml=0.5
        )


def test_administration_requires_positive_dose():
    """Test che dose sia positiva."""
    with pytest.raises(ValueError, match="Dose deve essere > 0"):
        Administration(
            preparation_id=1,
            dose_ml=0
        )


def test_administration_is_deleted():
    """Test soft delete check."""
    admin = Administration(
        preparation_id=1,
        dose_ml=0.5,
        deleted_at=datetime.now()
    )
    assert admin.is_deleted()


def test_administration_has_side_effects():
    """Test rilevamento effetti collaterali."""
    admin = Administration(
        preparation_id=1,
        dose_ml=0.5,
        side_effects="Mild redness"
    )
    assert admin.has_side_effects()


# ==================== TEST REPOSITORY CRUD ====================

def test_create_administration(repo, sample_preparation):
    """Test creazione somministrazione."""
    admin = Administration(
        preparation_id=sample_preparation,
        dose_ml=0.5,
        injection_site="Abdomen"
    )
    
    admin_id = repo.create(admin)
    assert admin_id > 0
    
    # Verifica creazione
    retrieved = repo.get_by_id(admin_id)
    assert retrieved is not None
    assert retrieved.dose_ml == Decimal('0.5')
    assert retrieved.injection_site == "Abdomen"


def test_create_decrements_preparation_volume(db_conn, sample_preparation):
    """Test che create decrementi volume preparazione."""
    repo = AdministrationRepository(db_conn)
    prep_repo = PreparationRepository(db_conn)
    
    # Volume iniziale
    prep = prep_repo.get_by_id(sample_preparation)
    initial_volume = prep.volume_remaining_ml
    
    # Crea somministrazione
    admin = Administration(
        preparation_id=sample_preparation,
        dose_ml=0.5
    )
    repo.create(admin)
    
    # Verifica decremento
    prep = prep_repo.get_by_id(sample_preparation)
    assert prep.volume_remaining_ml == initial_volume - Decimal('0.5')


def test_create_fails_with_invalid_preparation(repo):
    """Test che create fallisca con preparazione inesistente."""
    admin = Administration(
        preparation_id=9999,
        dose_ml=0.5
    )
    
    with pytest.raises(ValueError, match="non trovata"):
        repo.create(admin)


def test_create_fails_with_insufficient_volume(repo, sample_preparation):
    """Test che create fallisca con volume insufficiente."""
    admin = Administration(
        preparation_id=sample_preparation,
        dose_ml=100.0  # Volume impossibile
    )
    
    with pytest.raises(ValueError, match="insufficiente"):
        repo.create(admin)


def test_create_with_protocol(repo, sample_preparation, sample_protocol):
    """Test creazione con protocollo."""
    admin = Administration(
        preparation_id=sample_preparation,
        protocol_id=sample_protocol,
        dose_ml=0.5
    )
    
    admin_id = repo.create(admin)
    retrieved = repo.get_by_id(admin_id)
    assert retrieved.protocol_id == sample_protocol


def test_create_fails_with_invalid_protocol(repo, sample_preparation):
    """Test che create fallisca con protocollo inesistente."""
    admin = Administration(
        preparation_id=sample_preparation,
        protocol_id=9999,
        dose_ml=0.5
    )
    
    with pytest.raises(ValueError, match="non trovato"):
        repo.create(admin)


def test_get_by_id(repo, sample_preparation):
    """Test recupero per ID."""
    admin = Administration(
        preparation_id=sample_preparation,
        dose_ml=0.5,
        notes="Test notes"
    )
    admin_id = repo.create(admin)
    
    retrieved = repo.get_by_id(admin_id)
    assert retrieved is not None
    assert retrieved.id == admin_id
    assert retrieved.notes == "Test notes"


def test_get_by_id_not_found(repo):
    """Test get_by_id con ID inesistente."""
    result = repo.get_by_id(9999)
    assert result is None


def test_get_all_basic(repo, sample_preparation):
    """Test get_all di base."""
    # Crea 3 somministrazioni
    for i in range(3):
        admin = Administration(
            preparation_id=sample_preparation,
            dose_ml=0.5
        )
        repo.create(admin)
    
    admins = repo.get_all()
    assert len(admins) == 3


def test_get_all_filter_by_preparation(repo, sample_preparation):
    """Test filtro per preparazione."""
    # Crea somministrazioni
    for _ in range(2):
        admin = Administration(
            preparation_id=sample_preparation,
            dose_ml=0.5
        )
        repo.create(admin)
    
    admins = repo.get_all(preparation_id=sample_preparation)
    assert len(admins) == 2
    assert all(a.preparation_id == sample_preparation for a in admins)


def test_get_all_filter_by_protocol(repo, sample_preparation, sample_protocol):
    """Test filtro per protocollo."""
    # Con protocollo
    admin1 = Administration(
        preparation_id=sample_preparation,
        protocol_id=sample_protocol,
        dose_ml=0.5
    )
    repo.create(admin1)
    
    # Senza protocollo
    admin2 = Administration(
        preparation_id=sample_preparation,
        dose_ml=0.5
    )
    repo.create(admin2)
    
    admins = repo.get_all(protocol_id=sample_protocol)
    assert len(admins) == 1
    assert admins[0].protocol_id == sample_protocol


def test_get_all_filter_by_days_back(repo, db_conn, sample_preparation):
    """Test filtro giorni recenti."""
    # Somministrazione vecchia (simulata con UPDATE)
    admin_old = Administration(
        preparation_id=sample_preparation,
        dose_ml=0.5
    )
    admin_old_id = repo.create(admin_old)
    
    # Forza data vecchia
    db_conn.execute(
        "UPDATE administrations SET administration_datetime = ? WHERE id = ?",
        ((datetime.now() - timedelta(days=10)).isoformat(), admin_old_id)
    )
    db_conn.commit()
    
    # Somministrazione recente
    admin_recent = Administration(
        preparation_id=sample_preparation,
        dose_ml=0.5
    )
    repo.create(admin_recent)
    
    # Filtra ultimi 7 giorni
    admins = repo.get_all(days_back=7)
    assert len(admins) == 1


def test_update_administration(repo, sample_preparation):
    """Test aggiornamento somministrazione."""
    admin = Administration(
        preparation_id=sample_preparation,
        dose_ml=0.5,
        notes="Original"
    )
    admin_id = repo.create(admin)
    
    # Aggiorna
    admin.id = admin_id
    admin.notes = "Updated"
    admin.injection_site = "Abdomen"
    
    success = repo.update(admin)
    assert success
    
    # Verifica
    retrieved = repo.get_by_id(admin_id)
    assert retrieved.notes == "Updated"
    assert retrieved.injection_site == "Abdomen"


def test_update_requires_id(repo, sample_preparation):
    """Test che update richieda ID."""
    admin = Administration(
        preparation_id=sample_preparation,
        dose_ml=0.5
    )
    
    with pytest.raises(ValueError, match="ID somministrazione necessario"):
        repo.update(admin)


def test_soft_delete(repo, sample_preparation):
    """Test soft delete."""
    admin = Administration(
        preparation_id=sample_preparation,
        dose_ml=0.5
    )
    admin_id = repo.create(admin)
    
    success, msg = repo.delete(admin_id, force=False)
    assert success
    assert "archiviata" in msg
    
    # Non visibile in get_all
    admins = repo.get_all()
    assert len(admins) == 0
    
    # Visibile con include_deleted
    admins = repo.get_all(include_deleted=True)
    assert len(admins) == 1


def test_hard_delete(repo, sample_preparation):
    """Test eliminazione fisica."""
    admin = Administration(
        preparation_id=sample_preparation,
        dose_ml=0.5
    )
    admin_id = repo.create(admin)
    
    success, msg = repo.delete(admin_id, force=True)
    assert success
    assert "definitivamente" in msg
    
    # Non esiste più
    result = repo.get_by_id(admin_id, include_deleted=True)
    assert result is None


def test_delete_with_volume_restore(db_conn, sample_preparation):
    """Test eliminazione con ripristino volume."""
    repo = AdministrationRepository(db_conn)
    prep_repo = PreparationRepository(db_conn)
    
    # Volume iniziale
    prep = prep_repo.get_by_id(sample_preparation)
    initial_volume = prep.volume_remaining_ml
    
    # Crea somministrazione
    admin = Administration(
        preparation_id=sample_preparation,
        dose_ml=0.5
    )
    admin_id = repo.create(admin)
    
    # Elimina con ripristino
    repo.delete(admin_id, restore_volume=True)
    
    # Verifica ripristino
    prep = prep_repo.get_by_id(sample_preparation)
    assert prep.volume_remaining_ml == initial_volume


def test_count_basic(repo, sample_preparation):
    """Test conteggio base."""
    for _ in range(3):
        admin = Administration(
            preparation_id=sample_preparation,
            dose_ml=0.5
        )
        repo.create(admin)
    
    count = repo.count()
    assert count == 3


def test_count_with_filters(repo, sample_preparation, sample_protocol):
    """Test conteggio con filtri."""
    # Con protocollo
    admin1 = Administration(
        preparation_id=sample_preparation,
        protocol_id=sample_protocol,
        dose_ml=0.5
    )
    repo.create(admin1)
    
    # Senza protocollo
    admin2 = Administration(
        preparation_id=sample_preparation,
        dose_ml=0.5
    )
    repo.create(admin2)
    
    count = repo.count(protocol_id=sample_protocol)
    assert count == 1


# ==================== TEST METODI CUSTOM ====================

def test_get_with_details(repo, db_conn, sample_preparation, sample_protocol):
    """Test recupero con dettagli JOIN."""
    admin = Administration(
        preparation_id=sample_preparation,
        protocol_id=sample_protocol,
        dose_ml=0.5
    )
    repo.create(admin)
    
    details = repo.get_with_details()
    assert len(details) == 1
    
    detail = details[0]
    assert 'protocol_name' in detail
    assert 'batch_product' in detail
    assert detail['protocol_name'] == "Test Protocol"


def test_get_statistics(repo, sample_preparation):
    """Test calcolo statistiche."""
    # Crea 3 somministrazioni
    for dose in [0.3, 0.5, 0.7]:
        admin = Administration(
            preparation_id=sample_preparation,
            dose_ml=dose
        )
        repo.create(admin)
    
    stats = repo.get_statistics()
    assert stats['count'] == 3
    assert stats['total_ml'] == 1.5
    assert stats['avg_dose'] == 0.5


def test_get_statistics_empty(repo):
    """Test statistiche con nessuna somministrazione."""
    stats = repo.get_statistics()
    assert stats['count'] == 0
    assert stats['total_ml'] == 0


def test_link_to_protocol(repo, sample_preparation, sample_protocol):
    """Test collegamento a protocollo."""
    admin = Administration(
        preparation_id=sample_preparation,
        dose_ml=0.5
    )
    admin_id = repo.create(admin)
    
    success, msg = repo.link_to_protocol(admin_id, sample_protocol)
    assert success
    
    retrieved = repo.get_by_id(admin_id)
    assert retrieved.protocol_id == sample_protocol


def test_unlink_from_protocol(repo, sample_preparation, sample_protocol):
    """Test scollegamento da protocollo."""
    admin = Administration(
        preparation_id=sample_preparation,
        protocol_id=sample_protocol,
        dose_ml=0.5
    )
    admin_id = repo.create(admin)
    
    success, msg = repo.unlink_from_protocol(admin_id)
    assert success
    
    retrieved = repo.get_by_id(admin_id)
    assert retrieved.protocol_id is None
