"""
Repository - Janoshik Certificates

CRUD operations per janoshik_certificates table.
"""

import sqlite3
from datetime import datetime
from typing import List, Optional, Dict
from pathlib import Path

from ..models import JanoshikCertificate


class JanoshikCertificateRepository:
    """Repository per janoshik_certificates table"""
    
    def __init__(self, db_path: str):
        """
        Inizializza repository.
        
        Args:
            db_path: Path al database SQLite
        """
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {db_path}")
    
    def _get_connection(self) -> sqlite3.Connection:
        """Crea connessione database"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def insert(self, certificate: JanoshikCertificate) -> int:
        """
        Inserisce certificato nel database.
        
        Args:
            certificate: JanoshikCertificate instance
            
        Returns:
            ID record inserito
            
        Raises:
            sqlite3.IntegrityError: Se task_number o image_hash duplicati
        """
        conn = self._get_connection()
        try:
            data = certificate.to_dict()
            
            columns = ', '.join(data.keys())
            placeholders = ', '.join(['?' for _ in data])
            
            query = f"""
                INSERT INTO janoshik_certificates ({columns})
                VALUES ({placeholders})
            """
            
            cursor = conn.execute(query, list(data.values()))
            conn.commit()
            
            return cursor.lastrowid
            
        finally:
            conn.close()
    
    def insert_many(self, certificates: List[JanoshikCertificate]) -> int:
        """
        Inserisce multiple certificati (batch).
        
        Args:
            certificates: Lista JanoshikCertificate
            
        Returns:
            Numero record inseriti
        """
        if not certificates:
            return 0
        
        conn = self._get_connection()
        inserted = 0
        
        try:
            for cert in certificates:
                try:
                    data = cert.to_dict()
                    columns = ', '.join(data.keys())
                    placeholders = ', '.join(['?' for _ in data])
                    
                    query = f"""
                        INSERT INTO janoshik_certificates ({columns})
                        VALUES ({placeholders})
                    """
                    
                    conn.execute(query, list(data.values()))
                    inserted += 1
                    
                except sqlite3.IntegrityError:
                    # Skip duplicati (task_number o image_hash già esistente)
                    continue
            
            conn.commit()
            return inserted
            
        finally:
            conn.close()
    
    def get_by_id(self, cert_id: int) -> Optional[JanoshikCertificate]:
        """Recupera certificato per ID"""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM janoshik_certificates WHERE id = ?",
                (cert_id,)
            )
            row = cursor.fetchone()
            
            if not row:
                return None
            
            return JanoshikCertificate.from_dict(dict(row))
            
        finally:
            conn.close()
    
    def get_by_task_number(self, task_number: str) -> Optional[JanoshikCertificate]:
        """Recupera certificato per task number"""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM janoshik_certificates WHERE task_number = ?",
                (task_number,)
            )
            row = cursor.fetchone()
            
            if not row:
                return None
            
            return JanoshikCertificate.from_dict(dict(row))
            
        finally:
            conn.close()
    
    def get_by_image_hash(self, image_hash: str) -> Optional[JanoshikCertificate]:
        """Recupera certificato per image hash"""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM janoshik_certificates WHERE image_hash = ?",
                (image_hash,)
            )
            row = cursor.fetchone()
            
            if not row:
                return None
            
            return JanoshikCertificate.from_dict(dict(row))
            
        finally:
            conn.close()
    
    def get_by_supplier(self, supplier_name: str) -> List[JanoshikCertificate]:
        """Recupera tutti i certificati di un supplier"""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM janoshik_certificates WHERE supplier_name = ? ORDER BY test_date DESC",
                (supplier_name,)
            )
            rows = cursor.fetchall()
            
            return [JanoshikCertificate.from_dict(dict(row)) for row in rows]
            
        finally:
            conn.close()
    
    def get_unprocessed(self, limit: Optional[int] = None) -> List[JanoshikCertificate]:
        """Recupera certificati non ancora processati"""
        conn = self._get_connection()
        try:
            query = "SELECT * FROM janoshik_certificates WHERE processed = 0 ORDER BY scraped_at"
            if limit:
                query += f" LIMIT {limit}"
            
            cursor = conn.execute(query)
            rows = cursor.fetchall()
            
            return [JanoshikCertificate.from_dict(dict(row)) for row in rows]
            
        finally:
            conn.close()
    
    def get_all(self, limit: Optional[int] = None, offset: int = 0) -> List[JanoshikCertificate]:
        """Recupera tutti i certificati con paginazione"""
        conn = self._get_connection()
        try:
            query = "SELECT * FROM janoshik_certificates ORDER BY test_date DESC"
            if limit:
                query += f" LIMIT {limit} OFFSET {offset}"
            
            cursor = conn.execute(query)
            rows = cursor.fetchall()
            
            return [JanoshikCertificate.from_dict(dict(row)) for row in rows]
            
        finally:
            conn.close()
    
    def get_all_as_dicts(self) -> List[Dict]:
        """
        Recupera tutti i certificati come dict (per scoring).
        
        Returns:
            Lista dict con tutti i campi
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM janoshik_certificates ORDER BY test_date DESC"
            )
            rows = cursor.fetchall()
            
            return [dict(row) for row in rows]
            
        finally:
            conn.close()
    
    def mark_as_processed(self, cert_id: int) -> bool:
        """Marca certificato come processato"""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "UPDATE janoshik_certificates SET processed = 1 WHERE id = ?",
                (cert_id,)
            )
            conn.commit()
            
            return cursor.rowcount > 0
            
        finally:
            conn.close()
    
    def update(self, certificate: JanoshikCertificate) -> bool:
        """
        Aggiorna certificato esistente.
        
        Args:
            certificate: JanoshikCertificate con id settato
            
        Returns:
            True se aggiornato
        """
        if not certificate.id:
            raise ValueError("Certificate ID required for update")
        
        conn = self._get_connection()
        try:
            data = certificate.to_dict()
            
            # Rimuovi id dai dati da aggiornare
            cert_id = certificate.id
            data_no_id = {k: v for k, v in data.items() if k != 'id'}
            
            set_clause = ', '.join([f"{k} = ?" for k in data_no_id.keys()])
            
            query = f"""
                UPDATE janoshik_certificates
                SET {set_clause}
                WHERE id = ?
            """
            
            cursor = conn.execute(query, list(data_no_id.values()) + [cert_id])
            conn.commit()
            
            return cursor.rowcount > 0
            
        finally:
            conn.close()
    
    def delete(self, cert_id: int) -> bool:
        """Elimina certificato per ID"""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "DELETE FROM janoshik_certificates WHERE id = ?",
                (cert_id,)
            )
            conn.commit()
            
            return cursor.rowcount > 0
            
        finally:
            conn.close()
    
    def count(self) -> int:
        """Ritorna numero totale certificati"""
        conn = self._get_connection()
        try:
            cursor = conn.execute("SELECT COUNT(*) FROM janoshik_certificates")
            return cursor.fetchone()[0]
            
        finally:
            conn.close()
    
    def count_by_supplier(self, supplier_name: str) -> int:
        """Ritorna numero certificati per supplier"""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM janoshik_certificates WHERE supplier_name = ?",
                (supplier_name,)
            )
            return cursor.fetchone()[0]
            
        finally:
            conn.close()
    
    def get_unique_suppliers(self) -> List[str]:
        """Ritorna lista supplier unici"""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT DISTINCT supplier_name FROM janoshik_certificates ORDER BY supplier_name"
            )
            return [row[0] for row in cursor.fetchall()]
            
        finally:
            conn.close()
    
    def exists_by_task_number(self, task_number: str) -> bool:
        """Check se certificato con task_number esiste"""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT 1 FROM janoshik_certificates WHERE task_number = ? LIMIT 1",
                (task_number,)
            )
            return cursor.fetchone() is not None
            
        finally:
            conn.close()
    
    def get_all_task_numbers(self) -> List[str]:
        """Recupera tutti i task_number presenti nel database"""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT task_number FROM janoshik_certificates"
            )
            return [row[0] for row in cursor.fetchall()]
            
        finally:
            conn.close()
    
    def exists_by_image_hash(self, image_hash: str) -> bool:
        """Check se certificato con image_hash esiste"""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT 1 FROM janoshik_certificates WHERE image_hash = ? LIMIT 1",
                (image_hash,)
            )
            return cursor.fetchone() is not None

        finally:
            conn.close()

    # === NEW: Verification Key Methods ===

    def get_by_verification_key(self, verification_key: str) -> Optional[JanoshikCertificate]:
        """
        Recupera certificato per verification key.

        Args:
            verification_key: Codice verifica (es. "I3NR16JGXTL8")

        Returns:
            JanoshikCertificate se trovato, altrimenti None
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM janoshik_certificates WHERE verification_key = ?",
                (verification_key,)
            )
            row = cursor.fetchone()

            if not row:
                return None

            return JanoshikCertificate.from_dict(dict(row))

        finally:
            conn.close()

    def exists_by_verification_key(self, verification_key: str) -> bool:
        """
        Verifica se un verification key esiste già nel database.

        Args:
            verification_key: Codice verifica

        Returns:
            True se esiste
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT 1 FROM janoshik_certificates WHERE verification_key = ? LIMIT 1",
                (verification_key,)
            )
            return cursor.fetchone() is not None

        finally:
            conn.close()

    @staticmethod
    def validate_verification_key(verification_key: str) -> bool:
        """
        Valida formato verification key.

        Args:
            verification_key: Codice da validare

        Returns:
            True se formato corretto (12 caratteri alfanumerici uppercase)
        """
        import re
        if not verification_key:
            return False
        return bool(re.match(r'^[A-Z0-9]{12}$', verification_key))

    # === NEW: Blend Methods ===

    def get_all_blends(self) -> List[JanoshikCertificate]:
        """
        Recupera tutti i certificati di miscele (blend).

        Returns:
            Lista certificati blend
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM janoshik_certificates WHERE is_blend = 1 ORDER BY test_date DESC"
            )
            rows = cursor.fetchall()

            return [JanoshikCertificate.from_dict(dict(row)) for row in rows]

        finally:
            conn.close()

    def get_blends_by_protocol(self, protocol_name: str) -> List[JanoshikCertificate]:
        """
        Recupera blend per nome protocollo.

        Args:
            protocol_name: Nome protocollo (es. "GLOW", "BPC+TB")

        Returns:
            Lista certificati del protocollo
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM janoshik_certificates WHERE protocol_name = ? ORDER BY test_date DESC",
                (protocol_name,)
            )
            rows = cursor.fetchall()

            return [JanoshikCertificate.from_dict(dict(row)) for row in rows]

        finally:
            conn.close()

    def search_blends_containing_peptide(self, peptide_name_std: str) -> List[JanoshikCertificate]:
        """
        Trova blend che contengono un peptide specifico.

        Usa JSON search su blend_components.

        Args:
            peptide_name_std: Nome peptide normalizzato (es. "BPC157")

        Returns:
            Lista certificati blend contenenti il peptide
        """
        conn = self._get_connection()
        try:
            # SQLite JSON search (richiede JSON1 extension, disponibile per default)
            query = """
                SELECT * FROM janoshik_certificates
                WHERE is_blend = 1
                AND blend_components LIKE ?
                ORDER BY test_date DESC
            """
            # Semplice LIKE search per JSON (meno preciso ma funziona sempre)
            cursor = conn.execute(query, (f'%"{peptide_name_std}"%',))
            rows = cursor.fetchall()

            return [JanoshikCertificate.from_dict(dict(row)) for row in rows]

        finally:
            conn.close()

    # === NEW: Replicate Methods ===

    def get_certificates_with_replicates(self) -> List[JanoshikCertificate]:
        """
        Recupera certificati con misurazioni replicate.

        Returns:
            Lista certificati con replicati
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM janoshik_certificates WHERE has_replicates = 1 ORDER BY test_date DESC"
            )
            rows = cursor.fetchall()

            return [JanoshikCertificate.from_dict(dict(row)) for row in rows]

        finally:
            conn.close()

    def get_replicates_by_cv_threshold(self, cv_threshold: float) -> List[JanoshikCertificate]:
        """
        Trova replicati con CV% > soglia (controllo qualità).

        Args:
            cv_threshold: Soglia CV% (es. 10.0 per CV > 10%)

        Returns:
            Lista certificati con CV elevato
        """
        conn = self._get_connection()
        try:
            # Estrae CV% da replicate_statistics JSON
            query = """
                SELECT * FROM janoshik_certificates
                WHERE has_replicates = 1
                AND replicate_statistics IS NOT NULL
                AND CAST(
                    json_extract(replicate_statistics, '$.cv_percent') AS REAL
                ) > ?
                ORDER BY test_date DESC
            """
            cursor = conn.execute(query, (cv_threshold,))
            rows = cursor.fetchall()

            return [JanoshikCertificate.from_dict(dict(row)) for row in rows]

        finally:
            conn.close()

    def count_blends(self) -> int:
        """Ritorna numero totale blend"""
        conn = self._get_connection()
        try:
            cursor = conn.execute("SELECT COUNT(*) FROM janoshik_certificates WHERE is_blend = 1")
            return cursor.fetchone()[0]

        finally:
            conn.close()

    def count_replicates(self) -> int:
        """Ritorna numero totale certificati con replicati"""
        conn = self._get_connection()
        try:
            cursor = conn.execute("SELECT COUNT(*) FROM janoshik_certificates WHERE has_replicates = 1")
            return cursor.fetchone()[0]

        finally:
            conn.close()
