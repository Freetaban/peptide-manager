"""
Certificate model and repository.

Handles quality control certificates and test details for batches.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
from .base import BaseModel, Repository


@dataclass
class CertificateDetail(BaseModel):
    """Individual test parameter from a certificate."""
    test_parameter: str = ""
    certificate_id: int = 0
    result_value: Optional[str] = None
    unit: Optional[str] = None
    specification: Optional[str] = None
    pass_fail: Optional[str] = None  # 'pass', 'fail', 'n/a'
    
    def __post_init__(self):
        """Validate certificate detail data."""
        if self.pass_fail and self.pass_fail not in ('pass', 'fail', 'n/a'):
            raise ValueError(f"pass_fail must be 'pass', 'fail', or 'n/a', got: {self.pass_fail}")


@dataclass
class Certificate(BaseModel):
    """Quality control certificate for a batch."""
    batch_id: int = 0
    certificate_type: str = ""
    lab_name: Optional[str] = None
    test_date: Optional[str] = None
    file_path: Optional[str] = None
    file_name: Optional[str] = None
    purity_percentage: Optional[Decimal] = None
    endotoxin_level: Optional[str] = None
    notes: Optional[str] = None
    details: List[CertificateDetail] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate certificate data."""
        valid_types = ('manufacturer', 'third_party', 'personal')
        if self.certificate_type and self.certificate_type not in valid_types:
            raise ValueError(f"certificate_type must be one of {valid_types}, got: {self.certificate_type}")
        
        if self.purity_percentage is not None:
            if isinstance(self.purity_percentage, (int, float)):
                self.purity_percentage = Decimal(str(self.purity_percentage))
            if not (0 <= self.purity_percentage <= 100):
                raise ValueError(f"purity_percentage must be between 0 and 100, got: {self.purity_percentage}")


class CertificateRepository(Repository):
    """Repository for Certificate operations."""
    
    def create(self, certificate: Certificate) -> Certificate:
        """
        Create a new certificate with optional details.
        
        Args:
            certificate: Certificate object with optional details list
            
        Returns:
            Created certificate with ID
        """
        cursor = self.conn.cursor()
        
        # Convert Decimal to float for SQLite
        purity = float(certificate.purity_percentage) if certificate.purity_percentage else None
        
        cursor.execute('''
            INSERT INTO certificates (
                batch_id, certificate_type, lab_name, test_date,
                file_path, file_name, purity_percentage, endotoxin_level, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            certificate.batch_id,
            certificate.certificate_type,
            certificate.lab_name,
            certificate.test_date,
            certificate.file_path,
            certificate.file_name,
            purity,
            certificate.endotoxin_level,
            certificate.notes
        ))
        
        certificate.id = cursor.lastrowid
        
        # Insert details if present
        if certificate.details:
            for detail in certificate.details:
                cursor.execute('''
                    INSERT INTO certificate_details (
                        certificate_id, test_parameter, result_value,
                        unit, specification, pass_fail
                    ) VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    certificate.id,
                    detail.test_parameter,
                    detail.result_value,
                    detail.unit,
                    detail.specification,
                    detail.pass_fail
                ))
                detail.id = cursor.lastrowid
        
        self.conn.commit()
        return certificate
    
    def get_by_id(self, certificate_id: int) -> Optional[Certificate]:
        """
        Get certificate by ID with all details.
        
        Args:
            certificate_id: Certificate ID
            
        Returns:
            Certificate object with details or None if not found
        """
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM certificates WHERE id = ?', (certificate_id,))
        row = cursor.fetchone()
        
        if not row:
            return None
        
        cert = Certificate(**dict(row))
        
        # Convert purity to Decimal
        if cert.purity_percentage is not None:
            cert.purity_percentage = Decimal(str(cert.purity_percentage))
        
        # Load details
        cursor.execute('''
            SELECT * FROM certificate_details
            WHERE certificate_id = ?
            ORDER BY id
        ''', (certificate_id,))
        
        cert.details = [CertificateDetail(**dict(row)) for row in cursor.fetchall()]
        
        return cert
    
    def get_all(self) -> List[Certificate]:
        """
        Get all certificates with details.
        
        Returns:
            List of all certificates
        """
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM certificates ORDER BY created_at DESC')
        certificates = []
        
        for row in cursor.fetchall():
            cert = Certificate(**dict(row))
            
            # Convert purity to Decimal
            if cert.purity_percentage is not None:
                cert.purity_percentage = Decimal(str(cert.purity_percentage))
            
            # Load details
            cursor.execute('''
                SELECT * FROM certificate_details
                WHERE certificate_id = ?
                ORDER BY id
            ''', (cert.id,))
            
            cert.details = [CertificateDetail(**dict(row)) for row in cursor.fetchall()]
            certificates.append(cert)
        
        return certificates
    
    def get_by_batch(self, batch_id: int) -> List[Certificate]:
        """
        Get all certificates for a specific batch with details.
        
        Args:
            batch_id: Batch ID
            
        Returns:
            List of certificates for the batch
        """
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM certificates
            WHERE batch_id = ?
            ORDER BY test_date DESC, created_at DESC
        ''', (batch_id,))
        
        certificates = []
        for row in cursor.fetchall():
            cert = Certificate(**dict(row))
            
            # Convert purity to Decimal
            if cert.purity_percentage is not None:
                cert.purity_percentage = Decimal(str(cert.purity_percentage))
            
            # Load details
            cursor.execute('''
                SELECT * FROM certificate_details
                WHERE certificate_id = ?
                ORDER BY id
            ''', (cert.id,))
            
            cert.details = [CertificateDetail(**dict(row)) for row in cursor.fetchall()]
            certificates.append(cert)
        
        return certificates
    
    def update(self, certificate: Certificate) -> bool:
        """
        Update certificate (excluding details).
        
        Note: To update details, delete and recreate or add new detail management methods.
        
        Args:
            certificate: Certificate with updated data
            
        Returns:
            True if updated successfully
        """
        if not certificate.id:
            raise ValueError("Certificate must have an ID to update")
        
        cursor = self.conn.cursor()
        
        # Convert Decimal to float for SQLite
        purity = float(certificate.purity_percentage) if certificate.purity_percentage else None
        
        cursor.execute('''
            UPDATE certificates
            SET batch_id = ?,
                certificate_type = ?,
                lab_name = ?,
                test_date = ?,
                file_path = ?,
                file_name = ?,
                purity_percentage = ?,
                endotoxin_level = ?,
                notes = ?
            WHERE id = ?
        ''', (
            certificate.batch_id,
            certificate.certificate_type,
            certificate.lab_name,
            certificate.test_date,
            certificate.file_path,
            certificate.file_name,
            purity,
            certificate.endotoxin_level,
            certificate.notes,
            certificate.id
        ))
        
        self.conn.commit()
        return cursor.rowcount > 0
    
    def delete(self, certificate_id: int) -> bool:
        """
        Hard delete certificate (cascade deletes details).
        
        Args:
            certificate_id: Certificate ID
            
        Returns:
            True if deleted successfully
        """
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM certificates WHERE id = ?', (certificate_id,))
        self.conn.commit()
        return cursor.rowcount > 0
    
    def add_detail(self, detail: CertificateDetail) -> CertificateDetail:
        """
        Add a test detail to an existing certificate.
        
        Args:
            detail: CertificateDetail object
            
        Returns:
            Detail with assigned ID
        """
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO certificate_details (
                certificate_id, test_parameter, result_value,
                unit, specification, pass_fail
            ) VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            detail.certificate_id,
            detail.test_parameter,
            detail.result_value,
            detail.unit,
            detail.specification,
            detail.pass_fail
        ))
        
        detail.id = cursor.lastrowid
        self.conn.commit()
        return detail
    
    def delete_detail(self, detail_id: int) -> bool:
        """
        Delete a certificate detail.
        
        Args:
            detail_id: Detail ID
            
        Returns:
            True if deleted successfully
        """
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM certificate_details WHERE id = ?', (detail_id,))
        self.conn.commit()
        return cursor.rowcount > 0
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get certificate statistics.
        
        Returns:
            Dictionary with statistics
        """
        cursor = self.conn.cursor()
        
        # Total certificates by type
        cursor.execute('''
            SELECT certificate_type, COUNT(*) as count
            FROM certificates
            GROUP BY certificate_type
        ''')
        by_type = {row['certificate_type']: row['count'] for row in cursor.fetchall()}
        
        # Average purity
        cursor.execute('''
            SELECT AVG(purity_percentage) as avg_purity
            FROM certificates
            WHERE purity_percentage IS NOT NULL
        ''')
        avg_purity = cursor.fetchone()['avg_purity']
        
        # Batches with certificates
        cursor.execute('''
            SELECT COUNT(DISTINCT batch_id) as batches_with_certs
            FROM certificates
        ''')
        batches_with_certs = cursor.fetchone()['batches_with_certs']
        
        return {
            'total': sum(by_type.values()),
            'by_type': by_type,
            'average_purity': round(avg_purity, 2) if avg_purity else None,
            'batches_with_certificates': batches_with_certs
        }
