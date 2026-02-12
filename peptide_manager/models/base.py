"""
Base classes e utilities per i modelli.
"""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class BaseModel:
    """Classe base per tutti i modelli."""
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    
    @classmethod
    def from_row(cls, row):
        """Crea un'istanza dal risultato di una query SQL."""
        if row is None:
            return None
        
        # Converte sqlite3.Row in dict
        data = dict(row) if hasattr(row, 'keys') else row
        
        # Filtra solo i campi che esistono nella dataclass
        field_names = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in field_names}
        
        return cls(**filtered_data)
    
    def to_dict(self):
        """Converte l'istanza in dizionario (include anche campi None)."""
        return {k: v for k, v in self.__dict__.items()}


class Repository:
    """Classe base per tutti i repository."""

    def __init__(self, connection, table_name: str = None, entity_class=None):
        """
        Args:
            connection: Connessione sqlite3
            table_name: Nome tabella (opzionale, usato dai repo estesi)
            entity_class: Classe dataclass dell'entità (opzionale)
        """
        self.conn = connection
        self.db = self  # backward compat: subclasses use self.db.conn
        self.table_name = table_name
        self.entity_class = entity_class
    
    def _execute(self, query: str, params: tuple = ()):
        """Esegue una query e restituisce il cursor."""
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return cursor
    
    def _execute_many(self, query: str, params_list: list):
        """Esegue una query multipla."""
        cursor = self.conn.cursor()
        cursor.executemany(query, params_list)
        return cursor
    
    def _fetch_all(self, query: str, params: tuple = ()):
        """Esegue una query e restituisce tutti i risultati."""
        cursor = self._execute(query, params)
        return cursor.fetchall()
    
    def _fetch_one(self, query: str, params: tuple = ()):
        """Esegue una query e restituisce un solo risultato."""
        cursor = self._execute(query, params)
        return cursor.fetchone()
    
    def _commit(self):
        """Commit delle modifiche."""
        self.conn.commit()

    def _row_to_entity(self, row_dict: dict):
        """Converte un dict riga DB in istanza dell'entity_class."""
        if self.entity_class is None:
            raise NotImplementedError(
                f"{self.__class__.__name__} has no entity_class set"
            )
        return self.entity_class.from_row(row_dict)

    def has_column(self, table: str, column: str) -> bool:
        """
        Verifica se una tabella contiene una colonna specifica.
        """
        # Validate table name: only alphanumeric and underscores allowed
        if not table.replace('_', '').isalnum():
            raise ValueError(f"Invalid table name: {table}")
        cursor = self.conn.cursor()
        cursor.execute(f"PRAGMA table_info({table})")
        rows = cursor.fetchall()
        # PRAGMA table_info returns rows with second column "name"
        return any(r[1] == column for r in rows)
