"""
Repository - Supplier Rankings

CRUD operations per supplier_rankings table.
"""

import sqlite3
from datetime import datetime
from typing import List, Optional, Dict
from pathlib import Path

from ..models import SupplierRanking


class SupplierRankingRepository:
    """Repository per supplier_rankings table"""
    
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
    
    def insert(self, ranking: SupplierRanking) -> int:
        """
        Inserisce ranking nel database.
        
        Args:
            ranking: SupplierRanking instance
            
        Returns:
            ID record inserito
        """
        conn = self._get_connection()
        try:
            data = ranking.to_dict()
            
            columns = ', '.join(data.keys())
            placeholders = ', '.join(['?' for _ in data])
            
            query = f"""
                INSERT INTO supplier_rankings ({columns})
                VALUES ({placeholders})
            """
            
            cursor = conn.execute(query, list(data.values()))
            conn.commit()
            
            return cursor.lastrowid
            
        finally:
            conn.close()
    
    def insert_many(self, rankings: List[SupplierRanking]) -> int:
        """
        Inserisce multipli ranking.
        Elimina prima i vecchi ranking per evitare duplicati.
        
        Args:
            rankings: Lista SupplierRanking
            
        Returns:
            Numero record inseriti
        """
        if not rankings:
            return 0
        
        conn = self._get_connection()
        inserted = 0
        
        try:
            # Elimina tutti i vecchi rankings per evitare duplicati
            conn.execute("DELETE FROM supplier_rankings")
            conn.commit()
            
            for ranking in rankings:
                data = ranking.to_dict()
                columns = ', '.join(data.keys())
                placeholders = ', '.join(['?' for _ in data])
                
                query = f"""
                    INSERT INTO supplier_rankings ({columns})
                    VALUES ({placeholders})
                """
                
                conn.execute(query, list(data.values()))
                inserted += 1
            
            conn.commit()
            return inserted
            
        finally:
            conn.close()
    
    def get_by_id(self, ranking_id: int) -> Optional[SupplierRanking]:
        """Recupera ranking per ID"""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM supplier_rankings WHERE id = ?",
                (ranking_id,)
            )
            row = cursor.fetchone()
            
            if not row:
                return None
            
            return SupplierRanking.from_dict(dict(row))
            
        finally:
            conn.close()
    
    def get_latest(self, limit: int = 100) -> List[SupplierRanking]:
        """
        Recupera latest ranking (più recente calculated_at).
        
        Args:
            limit: Numero massimo risultati
            
        Returns:
            Lista ranking ordinata per total_score DESC
        """
        conn = self._get_connection()
        try:
            # Trova data calcolo più recente
            cursor = conn.execute(
                "SELECT MAX(calculated_at) FROM supplier_rankings"
            )
            latest_date = cursor.fetchone()[0]
            
            if not latest_date:
                return []
            
            # Recupera ranking di quella data
            cursor = conn.execute(
                """
                SELECT * FROM supplier_rankings
                WHERE calculated_at = ?
                ORDER BY total_score DESC
                LIMIT ?
                """,
                (latest_date, limit)
            )
            rows = cursor.fetchall()
            
            return [SupplierRanking.from_dict(dict(row)) for row in rows]
            
        finally:
            conn.close()
    
    def get_by_supplier(self, supplier_name: str, limit: int = 10) -> List[SupplierRanking]:
        """
        Recupera storico ranking per supplier.
        
        Args:
            supplier_name: Nome supplier
            limit: Numero massimo risultati
            
        Returns:
            Lista ranking ordinata per calculated_at DESC
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT * FROM supplier_rankings
                WHERE supplier_name = ?
                ORDER BY calculated_at DESC
                LIMIT ?
                """,
                (supplier_name, limit)
            )
            rows = cursor.fetchall()
            
            return [SupplierRanking.from_dict(dict(row)) for row in rows]
            
        finally:
            conn.close()
    
    def get_top_suppliers(self, top_n: int = 10) -> List[SupplierRanking]:
        """
        Recupera top N supplier dal ranking più recente.
        
        Args:
            top_n: Numero supplier da ritornare
            
        Returns:
            Lista top supplier ordinata per rank_position
        """
        latest = self.get_latest(limit=top_n)
        return latest
    
    def get_all(self, limit: Optional[int] = None, offset: int = 0) -> List[SupplierRanking]:
        """Recupera tutti i ranking con paginazione"""
        conn = self._get_connection()
        try:
            query = "SELECT * FROM supplier_rankings ORDER BY calculated_at DESC, total_score DESC"
            if limit:
                query += f" LIMIT {limit} OFFSET {offset}"
            
            cursor = conn.execute(query)
            rows = cursor.fetchall()
            
            return [SupplierRanking.from_dict(dict(row)) for row in rows]
            
        finally:
            conn.close()
    
    def delete_old_rankings(self, keep_last_n: int = 10) -> int:
        """
        Elimina vecchi ranking mantenendo ultimi N calcoli.
        
        Args:
            keep_last_n: Numero calcoli da mantenere
            
        Returns:
            Numero record eliminati
        """
        conn = self._get_connection()
        try:
            # Trova date da mantenere
            cursor = conn.execute(
                """
                SELECT DISTINCT calculated_at
                FROM supplier_rankings
                ORDER BY calculated_at DESC
                LIMIT ?
                """,
                (keep_last_n,)
            )
            dates_to_keep = [row[0] for row in cursor.fetchall()]
            
            if not dates_to_keep:
                return 0
            
            # Elimina ranking non in quelle date
            placeholders = ','.join(['?' for _ in dates_to_keep])
            cursor = conn.execute(
                f"""
                DELETE FROM supplier_rankings
                WHERE calculated_at NOT IN ({placeholders})
                """,
                dates_to_keep
            )
            conn.commit()
            
            return cursor.rowcount
            
        finally:
            conn.close()
    
    def count(self) -> int:
        """Ritorna numero totale ranking"""
        conn = self._get_connection()
        try:
            cursor = conn.execute("SELECT COUNT(*) FROM supplier_rankings")
            return cursor.fetchone()[0]
            
        finally:
            conn.close()
    
    def count_calculations(self) -> int:
        """Ritorna numero calcoli effettuati (distinct calculated_at)"""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT COUNT(DISTINCT calculated_at) FROM supplier_rankings"
            )
            return cursor.fetchone()[0]
            
        finally:
            conn.close()
    
    def get_supplier_trend(self, supplier_name: str) -> List[Dict]:
        """
        Recupera trend score supplier nel tempo.
        
        Args:
            supplier_name: Nome supplier
            
        Returns:
            Lista dict con {calculated_at, total_score, rank_position}
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT calculated_at, total_score, rank_position
                FROM supplier_rankings
                WHERE supplier_name = ?
                ORDER BY calculated_at ASC
                """,
                (supplier_name,)
            )
            rows = cursor.fetchall()
            
            return [dict(row) for row in rows]
            
        finally:
            conn.close()
