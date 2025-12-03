"""
Test per il modulo Protocol.

Testa sia il model Protocol che il repository ProtocolRepository.
"""

import pytest
import sqlite3
from decimal import Decimal
from datetime import datetime

from peptide_manager.models import Protocol, ProtocolRepository


@pytest.fixture
def db_connection():
    """Crea connessione database in-memory per test."""
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    
    cursor = conn.cursor()
    
    # Tabella protocols
    cursor.execute('''
        CREATE TABLE protocols (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            frequency_per_day INTEGER DEFAULT 1,
            days_on INTEGER,
            days_off INTEGER DEFAULT 0,
            cycle_duration_weeks INTEGER,
            notes TEXT,
            active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            deleted_at TIMESTAMP DEFAULT NULL
        )
    ''')
    
    # Tabella peptides (per protocol_peptides)
    cursor.execute('''
        CREATE TABLE peptides (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            deleted_at TIMESTAMP
        )
    ''')
    
    # Tabella protocol_peptides
    cursor.execute('''
        CREATE TABLE protocol_peptides (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            protocol_id INTEGER NOT NULL,
            peptide_id INTEGER NOT NULL,
            target_dose_mcg REAL NOT NULL,
            FOREIGN KEY (protocol_id) REFERENCES protocols(id) ON DELETE CASCADE,
            FOREIGN KEY (peptide_id) REFERENCES peptides(id)
        )
    ''')
    
    # Tabella administrations (per statistiche)
    cursor.execute('''
        CREATE TABLE administrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            protocol_id INTEGER,
            preparation_id INTEGER NOT NULL,
            administration_datetime TIMESTAMP NOT NULL,
            dose_ml REAL NOT NULL,
            deleted_at TIMESTAMP,
            FOREIGN KEY (protocol_id) REFERENCES protocols(id)
        )
    ''')
    
    conn.commit()
    
    yield conn
    
    conn.close()


@pytest.fixture
def repo(db_connection):
    """Repository per test."""
    return ProtocolRepository(db_connection)


@pytest.fixture
def sample_peptide(db_connection):
    """Crea peptide di test."""
    cursor = db_connection.cursor()
    cursor.execute('INSERT INTO peptides (name) VALUES (?)', ('BPC-157',))
    db_connection.commit()
    return cursor.lastrowid


class TestProtocolModel:
    """Test per Protocol dataclass."""
    
    def test_creation_valid(self):
        """Test creazione protocollo valido."""
        protocol = Protocol(
            name="Test Protocol",
            frequency_per_day=2,
            days_on=5,
            days_off=2
        )
        
        assert protocol.name == "Test Protocol"
        assert protocol.frequency_per_day == 2
        assert protocol.days_on == 5
        assert protocol.days_off == 2
        assert protocol.active is True
    
    def test_creation_invalid_name(self):
        """Test validazione nome vuoto."""
        with pytest.raises(ValueError, match="Nome protocollo obbligatorio"):
            Protocol(name="")
    
    def test_creation_invalid_frequency(self):
        """Test validazione frequenza < 1."""
        with pytest.raises(ValueError, match="Frequenza deve essere >= 1"):
            Protocol(name="Test", frequency_per_day=0)
    
    def test_creation_invalid_days_on(self):
        """Test validazione days_on < 1."""
        with pytest.raises(ValueError, match="Days ON deve essere >= 1"):
            Protocol(name="Test", days_on=0)
    
    def test_creation_invalid_days_off(self):
        """Test validazione days_off negativo."""
        with pytest.raises(ValueError, match="Days OFF deve essere >= 0"):
            Protocol(name="Test", days_off=-1)
    
    def test_is_deleted(self):
        """Test metodo is_deleted."""
        protocol1 = Protocol(name="Test")
        assert protocol1.is_deleted() is False
        
        protocol2 = Protocol(
            name="Test",
            deleted_at=datetime.now()
        )
        assert protocol2.is_deleted() is True
    
    def test_is_active(self):
        """Test metodo is_active."""
        # Attivo
        protocol1 = Protocol(name="Test", active=True)
        assert protocol1.is_active() is True
        
        # Disattivo
        protocol2 = Protocol(name="Test", active=False)
        assert protocol2.is_active() is False
        
        # Eliminato (non può essere attivo)
        protocol3 = Protocol(
            name="Test",
            active=True,
            deleted_at=datetime.now()
        )
        assert protocol3.is_active() is False
    
    def test_has_cycle(self):
        """Test metodo has_cycle."""
        # Senza ciclo
        protocol1 = Protocol(name="Test")
        assert protocol1.has_cycle() is False
        
        # Con ciclo
        protocol2 = Protocol(name="Test", days_on=5, days_off=2)
        assert protocol2.has_cycle() is True
    
class TestProtocolRepository:
    """Test per ProtocolRepository."""
    
    def test_create(self, repo):
        """Test creazione protocollo."""
        protocol = Protocol(
            name="BPC-157 Protocol",
            description="Daily protocol",
            frequency_per_day=2,
            days_on=5,
            days_off=2,
            notes="Test notes"
        )
        
        protocol_id = repo.create(protocol)
        assert protocol_id > 0
        
        # Verifica creato
        retrieved = repo.get_by_id(protocol_id)
        assert retrieved is not None
        assert retrieved.name == "BPC-157 Protocol"
        assert retrieved.frequency_per_day == 2
        assert retrieved.active is True
    
    def test_get_by_id(self, repo):
        """Test recupero per ID."""
        # Crea protocollo
        protocol = Protocol(name="Test")
        protocol_id = repo.create(protocol)
        
        # Recupera
        retrieved = repo.get_by_id(protocol_id)
        assert retrieved is not None
        assert retrieved.id == protocol_id
        assert retrieved.name == "Test"
        
        # ID inesistente
        not_found = repo.get_by_id(9999)
        assert not_found is None
    
    def test_get_all_filters(self, repo):
        """Test recupero con filtri."""
        # Crea protocolli
        p1 = Protocol(name="Active 1", active=True)
        p2 = Protocol(name="Active 2", active=True)
        p3 = Protocol(name="Inactive", active=False)
        
        repo.create(p1)
        repo.create(p2)
        p3_id = repo.create(p3)
        
        # Soft delete p3
        repo.delete(p3_id, force=False)
        
        # Test filtri
        all_protocols = repo.get_all(active_only=False, include_deleted=True)
        assert len(all_protocols) == 3
        
        active_only = repo.get_all(active_only=True, include_deleted=False)
        assert len(active_only) == 2
        
        not_deleted = repo.get_all(active_only=False, include_deleted=False)
        assert len(not_deleted) == 2
    
    def test_update(self, repo):
        """Test aggiornamento protocollo."""
        # Crea
        protocol = Protocol(name="Original")
        protocol_id = repo.create(protocol)
        
        # Aggiorna
        protocol.id = protocol_id
        protocol.name = "Updated"
        protocol.frequency_per_day = 3
        
        success = repo.update(protocol)
        assert success is True
        
        # Verifica
        updated = repo.get_by_id(protocol_id)
        assert updated.name == "Updated"
        assert updated.frequency_per_day == 3
    
    def test_update_invalid(self, repo):
        """Test aggiornamento con dati non validi."""
        protocol = Protocol(name="Test")
        protocol_id = repo.create(protocol)
        
        # ID mancante
        with pytest.raises(ValueError, match="ID necessario"):
            protocol_no_id = Protocol(name="Test")
            repo.update(protocol_no_id)
        
        # Nome vuoto
        with pytest.raises(ValueError, match="Nome protocollo obbligatorio"):
            protocol.id = protocol_id
            protocol.name = ""
            repo.update(protocol)
    
    def test_delete_soft(self, repo):
        """Test soft delete."""
        protocol = Protocol(name="Test")
        protocol_id = repo.create(protocol)
        
        # Soft delete
        success, message = repo.delete(protocol_id, force=False)
        assert success is True
        assert "soft delete" in message.lower()
        
        # Non visibile normalmente
        retrieved = repo.get_by_id(protocol_id)
        assert retrieved is None
        
        # Visibile con include_deleted
        deleted = repo.get_by_id(protocol_id, include_deleted=True)
        assert deleted is not None
        assert deleted.is_deleted() is True
        assert deleted.active is False
    
    def test_delete_hard(self, repo):
        """Test hard delete."""
        protocol = Protocol(name="Test")
        protocol_id = repo.create(protocol)
        
        # Hard delete
        success, message = repo.delete(protocol_id, force=True)
        assert success is True
        assert "definitivamente" in message.lower()
        
        # Non esiste più
        retrieved = repo.get_by_id(protocol_id, include_deleted=True)
        assert retrieved is None
    
    def test_activate_deactivate(self, repo):
        """Test attivazione/disattivazione."""
        protocol = Protocol(name="Test", active=True)
        protocol_id = repo.create(protocol)
        
        # Disattiva
        success, message = repo.deactivate(protocol_id)
        assert success is True
        
        deactivated = repo.get_by_id(protocol_id)
        assert deactivated.active is False
        
        # Attiva
        success, message = repo.activate(protocol_id)
        assert success is True
        
        activated = repo.get_by_id(protocol_id)
        assert activated.active is True
    
    def test_peptide_management(self, repo, sample_peptide):
        """Test gestione peptidi nel protocollo."""
        # Crea protocollo
        protocol = Protocol(name="Test")
        protocol_id = repo.create(protocol)
        
        # Aggiungi peptide
        success, message = repo.add_peptide_to_protocol(
            protocol_id,
            sample_peptide,
            250.0  # 250 mcg
        )
        assert success is True
        
        # Verifica peptidi
        peptides = repo.get_peptides_for_protocol(protocol_id)
        assert len(peptides) == 1
        assert peptides[0]['peptide_id'] == sample_peptide
        assert peptides[0]['target_dose_mcg'] == 250.0
        
        # Rimuovi peptide
        success, message = repo.remove_peptide_from_protocol(protocol_id, sample_peptide)
        assert success is True
        
        # Verifica rimosso
        peptides = repo.get_peptides_for_protocol(protocol_id)
        assert len(peptides) == 0
    
    def test_add_peptide_duplicate(self, repo, sample_peptide):
        """Test aggiunta peptide duplicato."""
        protocol = Protocol(name="Test")
        protocol_id = repo.create(protocol)
        
        # Prima aggiunta OK
        success, _ = repo.add_peptide_to_protocol(protocol_id, sample_peptide, 250.0)
        assert success is True
        
        # Seconda aggiunta fallisce
        success, message = repo.add_peptide_to_protocol(protocol_id, sample_peptide, 300.0)
        assert success is False
        assert "già associato" in message.lower()
    
    def test_get_statistics(self, repo, db_connection):
        """Test statistiche protocollo."""
        # Crea protocollo
        protocol = Protocol(name="Test")
        protocol_id = repo.create(protocol)
        
        # Crea alcune amministrazioni fittizie
        cursor = db_connection.cursor()
        cursor.execute('''
            INSERT INTO administrations (protocol_id, preparation_id, administration_datetime, dose_ml)
            VALUES (?, 1, '2025-01-01 10:00:00', 0.5),
                   (?, 1, '2025-01-02 10:00:00', 0.5),
                   (?, 1, '2025-01-03 10:00:00', 0.5)
        ''', (protocol_id, protocol_id, protocol_id))
        db_connection.commit()
        
        # Recupera statistiche
        stats = repo.get_statistics(protocol_id)
        assert stats is not None
        assert stats['count'] == 3
        assert stats['total_ml'] == 1.5
        assert stats['first_date'] == '2025-01-01 10:00:00'
        assert stats['last_date'] == '2025-01-03 10:00:00'
    
    def test_get_statistics_no_administrations(self, repo):
        """Test statistiche protocollo senza amministrazioni."""
        protocol = Protocol(name="Test")
        protocol_id = repo.create(protocol)
        
        stats = repo.get_statistics(protocol_id)
        assert stats is not None
        assert stats['count'] == 0
        assert stats['total_ml'] == 0.0
        assert stats['first_date'] is None
        assert stats['last_date'] is None
    
    def test_count(self, repo):
        """Test conteggio protocolli."""
        # Crea protocolli
        p1 = Protocol(name="Active", active=True)
        p2 = Protocol(name="Inactive", active=False)
        
        repo.create(p1)
        p2_id = repo.create(p2)
        
        # Soft delete p2
        repo.delete(p2_id, force=False)
        
        # Test conteggi
        total = repo.count(active_only=False, include_deleted=True)
        assert total == 2
        
        active_only = repo.count(active_only=True, include_deleted=False)
        assert active_only == 1
        
        not_deleted = repo.count(active_only=False, include_deleted=False)
        assert not_deleted == 1
