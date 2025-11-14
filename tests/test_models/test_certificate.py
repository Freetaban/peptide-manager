"""
Tests for Certificate model and repository.
"""

import pytest
import sqlite3
from decimal import Decimal
from datetime import datetime
from peptide_manager.models.certificate import Certificate, CertificateDetail, CertificateRepository
from peptide_manager.models.batch import Batch, BatchRepository
from peptide_manager.models.supplier import Supplier, SupplierRepository
from peptide_manager.models.peptide import Peptide, PeptideRepository


@pytest.fixture
def db_conn():
    """Create in-memory database with schema."""
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Enable foreign keys
    cursor.execute('PRAGMA foreign_keys = ON')
    
    # Create suppliers table
    cursor.execute('''
        CREATE TABLE suppliers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            country TEXT,
            website TEXT,
            email TEXT,
            notes TEXT,
            reliability_rating INTEGER CHECK(reliability_rating >= 1 AND reliability_rating <= 5),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            deleted_at TIMESTAMP
        )
    ''')
    
    # Create peptides table
    cursor.execute('''
        CREATE TABLE peptides (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            sequence TEXT,
            molecular_weight REAL,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            deleted_at TIMESTAMP
        )
    ''')
    
    # Create batches table
    cursor.execute('''
        CREATE TABLE batches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            supplier_id INTEGER NOT NULL,
            batch_number TEXT NOT NULL UNIQUE,
            receipt_date DATE,
            quantity_mg REAL,
            purity_percentage REAL,
            storage_location TEXT,
            expiry_date DATE,
            cost_eur REAL,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            deleted_at TIMESTAMP,
            FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
        )
    ''')
    
    # Create certificates table
    cursor.execute('''
        CREATE TABLE certificates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_id INTEGER NOT NULL,
            certificate_type TEXT NOT NULL CHECK(certificate_type IN ('manufacturer', 'third_party', 'personal')),
            lab_name TEXT,
            test_date DATE,
            file_path TEXT,
            file_name TEXT,
            purity_percentage REAL CHECK(purity_percentage >= 0 AND purity_percentage <= 100),
            endotoxin_level TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (batch_id) REFERENCES batches(id) ON DELETE CASCADE
        )
    ''')
    
    # Create certificate_details table
    cursor.execute('''
        CREATE TABLE certificate_details (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            certificate_id INTEGER NOT NULL,
            test_parameter TEXT NOT NULL,
            result_value TEXT,
            unit TEXT,
            specification TEXT,
            pass_fail TEXT CHECK(pass_fail IN ('pass', 'fail', 'n/a')),
            FOREIGN KEY (certificate_id) REFERENCES certificates(id) ON DELETE CASCADE
        )
    ''')
    
    conn.commit()
    yield conn
    conn.close()


@pytest.fixture
def cert_repo(db_conn):
    """Create certificate repository."""
    return CertificateRepository(db_conn)


@pytest.fixture
def sample_batch(db_conn):
    """Create a sample batch for testing."""
    cursor = db_conn.cursor()
    
    # Create supplier directly
    cursor.execute('''
        INSERT INTO suppliers (name, country)
        VALUES (?, ?)
    ''', ("Test Supplier", "IT"))
    supplier_id = cursor.lastrowid
    
    # Create batch
    cursor.execute('''
        INSERT INTO batches (
            supplier_id, batch_number, receipt_date, 
            quantity_mg, purity_percentage
        ) VALUES (?, ?, ?, ?, ?)
    ''', (supplier_id, "BATCH001", "2025-01-01", 100.0, 95.0))
    batch_id = cursor.lastrowid
    
    db_conn.commit()
    
    # Return simple object with ID
    from peptide_manager.models.batch import Batch
    batch = Batch(id=batch_id, supplier_id=supplier_id, product_name="Test", batch_number="BATCH001")
    return batch


class TestCertificateDetail:
    """Tests for CertificateDetail dataclass."""
    
    def test_create_valid_detail(self):
        """Test creating a valid certificate detail."""
        detail = CertificateDetail(
            certificate_id=1,
            test_parameter="Purity",
            result_value="98.5",
            unit="%",
            specification=">95%",
            pass_fail="pass"
        )
        assert detail.certificate_id == 1
        assert detail.test_parameter == "Purity"
        assert detail.pass_fail == "pass"
    
    def test_invalid_pass_fail(self):
        """Test that invalid pass_fail values raise error."""
        with pytest.raises(ValueError, match="pass_fail must be"):
            CertificateDetail(
                certificate_id=1,
                test_parameter="Test",
                pass_fail="invalid"
            )


class TestCertificate:
    """Tests for Certificate dataclass."""
    
    def test_create_valid_certificate(self):
        """Test creating a valid certificate."""
        cert = Certificate(
            batch_id=1,
            certificate_type="manufacturer",
            lab_name="Test Lab",
            purity_percentage=98.5
        )
        assert cert.batch_id == 1
        assert cert.certificate_type == "manufacturer"
        assert cert.purity_percentage == Decimal("98.5")
    
    def test_invalid_certificate_type(self):
        """Test that invalid certificate types raise error."""
        with pytest.raises(ValueError, match="certificate_type must be one of"):
            Certificate(batch_id=1, certificate_type="invalid")
    
    def test_purity_percentage_conversion(self):
        """Test that purity is converted to Decimal."""
        cert = Certificate(batch_id=1, certificate_type="manufacturer", purity_percentage=98.5)
        assert isinstance(cert.purity_percentage, Decimal)
        assert cert.purity_percentage == Decimal("98.5")
    
    def test_purity_percentage_validation(self):
        """Test purity percentage range validation."""
        with pytest.raises(ValueError, match="must be between 0 and 100"):
            Certificate(batch_id=1, certificate_type="manufacturer", purity_percentage=150.0)
        
        with pytest.raises(ValueError, match="must be between 0 and 100"):
            Certificate(batch_id=1, certificate_type="manufacturer", purity_percentage=-5.0)
    
    def test_certificate_with_details(self):
        """Test creating certificate with details."""
        details = [
            CertificateDetail(
                certificate_id=0,
                test_parameter="Purity",
                result_value="98.5",
                pass_fail="pass"
            )
        ]
        cert = Certificate(
            batch_id=1,
            certificate_type="third_party",
            details=details
        )
        assert len(cert.details) == 1
        assert cert.details[0].test_parameter == "Purity"


class TestCertificateRepository:
    """Tests for CertificateRepository."""
    
    def test_create_certificate(self, cert_repo, sample_batch):
        """Test creating a certificate."""
        cert = Certificate(
            batch_id=sample_batch.id,
            certificate_type="manufacturer",
            lab_name="GenScript",
            test_date="2025-01-15",
            purity_percentage=98.5,
            endotoxin_level="<0.1 EU/mg"
        )
        
        created = cert_repo.create(cert)
        assert created.id is not None
        assert created.batch_id == sample_batch.id
        assert created.purity_percentage == Decimal("98.5")
    
    def test_create_certificate_with_details(self, cert_repo, sample_batch):
        """Test creating certificate with test details."""
        details = [
            CertificateDetail(
                certificate_id=0,
                test_parameter="Purity (HPLC)",
                result_value="98.5",
                unit="%",
                specification=">95%",
                pass_fail="pass"
            ),
            CertificateDetail(
                certificate_id=0,
                test_parameter="Endotoxin",
                result_value="0.05",
                unit="EU/mg",
                specification="<0.1 EU/mg",
                pass_fail="pass"
            )
        ]
        
        cert = Certificate(
            batch_id=sample_batch.id,
            certificate_type="third_party",
            lab_name="External Lab",
            test_date="2025-01-20",
            details=details
        )
        
        created = cert_repo.create(cert)
        assert created.id is not None
        assert len(created.details) == 2
        assert all(d.id is not None for d in created.details)
        assert created.details[0].test_parameter == "Purity (HPLC)"
    
    def test_get_by_id(self, cert_repo, sample_batch):
        """Test retrieving certificate by ID."""
        cert = Certificate(
            batch_id=sample_batch.id,
            certificate_type="personal",
            notes="Internal testing"
        )
        created = cert_repo.create(cert)
        
        retrieved = cert_repo.get_by_id(created.id)
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.certificate_type == "personal"
    
    def test_get_by_id_not_found(self, cert_repo):
        """Test retrieving non-existent certificate."""
        result = cert_repo.get_by_id(9999)
        assert result is None
    
    def test_get_all(self, cert_repo, sample_batch):
        """Test retrieving all certificates."""
        cert1 = Certificate(batch_id=sample_batch.id, certificate_type="manufacturer")
        cert2 = Certificate(batch_id=sample_batch.id, certificate_type="third_party")
        
        cert_repo.create(cert1)
        cert_repo.create(cert2)
        
        all_certs = cert_repo.get_all()
        assert len(all_certs) == 2
    
    def test_get_by_batch(self, cert_repo, sample_batch, db_conn):
        """Test retrieving certificates for a specific batch."""
        # Create another batch directly
        cursor = db_conn.cursor()
        cursor.execute('''
            INSERT INTO batches (supplier_id, batch_number)
            VALUES (?, ?)
        ''', (sample_batch.supplier_id, "BATCH002"))
        batch2_id = cursor.lastrowid
        db_conn.commit()
        
        # Create certificates for different batches
        cert1 = Certificate(batch_id=sample_batch.id, certificate_type="manufacturer")
        cert2 = Certificate(batch_id=sample_batch.id, certificate_type="third_party")
        cert3 = Certificate(batch_id=batch2_id, certificate_type="personal")
        
        cert_repo.create(cert1)
        cert_repo.create(cert2)
        cert_repo.create(cert3)
        
        # Get certificates for first batch
        batch1_certs = cert_repo.get_by_batch(sample_batch.id)
        assert len(batch1_certs) == 2
        assert all(c.batch_id == sample_batch.id for c in batch1_certs)
    
    def test_update_certificate(self, cert_repo, sample_batch):
        """Test updating a certificate."""
        cert = Certificate(
            batch_id=sample_batch.id,
            certificate_type="manufacturer",
            lab_name="Old Lab"
        )
        created = cert_repo.create(cert)
        
        # Update
        created.lab_name = "New Lab"
        created.purity_percentage = Decimal("99.0")
        success = cert_repo.update(created)
        
        assert success
        
        # Verify update
        updated = cert_repo.get_by_id(created.id)
        assert updated.lab_name == "New Lab"
        assert updated.purity_percentage == Decimal("99.0")
    
    def test_delete_certificate(self, cert_repo, sample_batch):
        """Test deleting a certificate."""
        cert = Certificate(batch_id=sample_batch.id, certificate_type="manufacturer")
        created = cert_repo.create(cert)
        
        success = cert_repo.delete(created.id)
        assert success
        
        # Verify deletion
        deleted = cert_repo.get_by_id(created.id)
        assert deleted is None
    
    def test_delete_certificate_cascades_details(self, cert_repo, sample_batch):
        """Test that deleting certificate also deletes details."""
        details = [
            CertificateDetail(
                certificate_id=0,
                test_parameter="Test1",
                pass_fail="pass"
            )
        ]
        cert = Certificate(
            batch_id=sample_batch.id,
            certificate_type="manufacturer",
            details=details
        )
        created = cert_repo.create(cert)
        
        # Delete certificate
        cert_repo.delete(created.id)
        
        # Verify certificate and details are gone
        cursor = cert_repo.conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM certificate_details WHERE certificate_id = ?', (created.id,))
        count = cursor.fetchone()[0]
        assert count == 0
    
    def test_add_detail(self, cert_repo, sample_batch):
        """Test adding a detail to existing certificate."""
        cert = Certificate(batch_id=sample_batch.id, certificate_type="manufacturer")
        created = cert_repo.create(cert)
        
        detail = CertificateDetail(
            certificate_id=created.id,
            test_parameter="New Test",
            result_value="Good",
            pass_fail="pass"
        )
        
        added = cert_repo.add_detail(detail)
        assert added.id is not None
        
        # Verify detail was added
        retrieved = cert_repo.get_by_id(created.id)
        assert len(retrieved.details) == 1
        assert retrieved.details[0].test_parameter == "New Test"
    
    def test_delete_detail(self, cert_repo, sample_batch):
        """Test deleting a certificate detail."""
        details = [
            CertificateDetail(
                certificate_id=0,
                test_parameter="Test1",
                pass_fail="pass"
            )
        ]
        cert = Certificate(
            batch_id=sample_batch.id,
            certificate_type="manufacturer",
            details=details
        )
        created = cert_repo.create(cert)
        detail_id = created.details[0].id
        
        success = cert_repo.delete_detail(detail_id)
        assert success
        
        # Verify detail is gone
        retrieved = cert_repo.get_by_id(created.id)
        assert len(retrieved.details) == 0
    
    def test_get_statistics(self, cert_repo, sample_batch):
        """Test getting certificate statistics."""
        # Create certificates with different types
        cert1 = Certificate(
            batch_id=sample_batch.id,
            certificate_type="manufacturer",
            purity_percentage=98.5
        )
        cert2 = Certificate(
            batch_id=sample_batch.id,
            certificate_type="manufacturer",
            purity_percentage=97.5
        )
        cert3 = Certificate(
            batch_id=sample_batch.id,
            certificate_type="third_party",
            purity_percentage=99.0
        )
        
        cert_repo.create(cert1)
        cert_repo.create(cert2)
        cert_repo.create(cert3)
        
        stats = cert_repo.get_statistics()
        
        assert stats['total'] == 3
        assert stats['by_type']['manufacturer'] == 2
        assert stats['by_type']['third_party'] == 1
        assert stats['average_purity'] == 98.33  # (98.5 + 97.5 + 99.0) / 3
        assert stats['batches_with_certificates'] == 1
    
    def test_ordering_by_test_date(self, cert_repo, sample_batch):
        """Test that certificates are ordered by test date descending."""
        cert1 = Certificate(
            batch_id=sample_batch.id,
            certificate_type="manufacturer",
            test_date="2025-01-01"
        )
        cert2 = Certificate(
            batch_id=sample_batch.id,
            certificate_type="third_party",
            test_date="2025-01-15"
        )
        
        cert_repo.create(cert1)
        cert_repo.create(cert2)
        
        certs = cert_repo.get_by_batch(sample_batch.id)
        assert certs[0].test_date == "2025-01-15"  # Most recent first
        assert certs[1].test_date == "2025-01-01"
