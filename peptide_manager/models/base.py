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
        """Converte l'istanza in dizionario."""
        return {k: v for k, v in self.__dict__.items() if v is not None}


class Repository:
    """Classe base per tutti i repository."""
    
    def __init__(self, connection):
        """
        Args:
            connection: Connessione sqlite3
        """
        self.conn = connection
    
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
