"""
Form Builder Component
"""

import flet as ft
from typing import List, Dict, Any, Callable
from dataclasses import dataclass
from enum import Enum


class FieldType(Enum):
    TEXT = "text"
    NUMBER = "number"
    DATE = "date"
    SELECT = "select"
    TEXTAREA = "textarea"


@dataclass
class Field:
    """Field configuration"""
    key: str
    label: str
    field_type: FieldType
    required: bool = False
    options: List[Dict[str, Any]] = None


class FormBuilder(ft.Container):
    """Dynamic form builder"""
    
    def __init__(self, fields: List[Field], on_submit: Callable, initial_data: Dict[str, Any] = None):
        super().__init__()
        self.fields = fields
        self.on_submit_callback = on_submit
        self.initial_data = initial_data or {}
        
        self._build()
    
    def _build(self):
        """Build the form"""
        # TODO: Implement full FormBuilder component
        self.content = ft.Column([
            ft.Text("FormBuilder Component", size=16, weight=ft.FontWeight.BOLD),
            ft.Text("To be implemented", size=12, italic=True)
        ])
        self.padding = 20
