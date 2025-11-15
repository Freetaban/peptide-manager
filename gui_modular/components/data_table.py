"""
Reusable DataTable Component
"""

import flet as ft
from typing import List, Dict, Any, Callable, Optional
from dataclasses import dataclass


@dataclass
class Column:
    """Column configuration"""
    label: str
    key: str
    width: Optional[int] = None


@dataclass
class Action:
    """Action button configuration"""
    label: str
    icon: str
    on_click: Callable
    color: Optional[str] = None


class DataTable(ft.Container):
    """Reusable data table with CRUD operations"""
    
    def __init__(
        self,
        columns: List[Column],
        actions: List[Action],
        data_source: Callable[[], List[Dict[str, Any]]],
        on_add: Optional[Callable] = None,
        title: str = "Data"
    ):
        super().__init__()
        self.columns = columns
        self.actions = actions
        self.data_source = data_source
        self.on_add_callback = on_add
        self.title = title
        
        # Build content
        self._build()
    
    def _build(self):
        """Build the data table"""
        # TODO: Implement full DataTable component
        self.content = ft.Column([
            ft.Text(f"{self.title} - DataTable Component", size=16, weight=ft.FontWeight.BOLD),
            ft.Text("To be implemented", size=12, italic=True)
        ])
        self.padding = 20
