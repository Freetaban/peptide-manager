"""
Form Builder Component - Reusable form creation utilities
"""

import flet as ft
from typing import List, Dict, Any, Callable, Optional, Union
from dataclasses import dataclass
from enum import Enum


class FieldType(Enum):
    """Form field types"""
    TEXT = "text"
    NUMBER = "number"
    DATE = "date"
    DROPDOWN = "dropdown"
    TEXTAREA = "textarea"
    CHECKBOX = "checkbox"


@dataclass
class Field:
    """Field configuration"""
    key: str
    label: str
    field_type: FieldType
    value: Any = None
    required: bool = False
    width: Optional[int] = None
    options: Optional[List[tuple]] = None  # For dropdown: [(value, label), ...]
    hint_text: Optional[str] = None
    multiline: bool = False
    disabled: bool = False
    on_change: Optional[Callable] = None


class FormBuilder:
    """
    Utility class for building forms with consistent styling.
    
    Usage:
        fields = [
            Field("name", "Nome", FieldType.TEXT, required=True),
            Field("age", "Età", FieldType.NUMBER, value="18"),
        ]
        
        form_fields = FormBuilder.build_fields(fields)
        values = FormBuilder.get_values(form_fields)
    """
    
    @staticmethod
    def build_fields(fields: List[Field]) -> Dict[str, ft.Control]:
        """
        Build Flet controls from field definitions.
        
        Args:
            fields: List of Field definitions
            
        Returns:
            Dictionary of {key: control} for easy access
        """
        controls = {}
        
        for field in fields:
            control = FormBuilder._create_control(field)
            controls[field.key] = control
        
        return controls
    
    @staticmethod
    def _create_control(field: Field) -> ft.Control:
        """Create appropriate Flet control for field type"""
        
        if field.field_type == FieldType.TEXT:
            text_field = ft.TextField(
                value=str(field.value) if field.value else "",
                width=field.width,
                hint_text=field.hint_text,
                disabled=field.disabled,
                on_change=field.on_change,
            )
            return ft.Column(
                [
                    ft.Text(field.label, size=12, weight=ft.FontWeight.W_500),
                    text_field,
                ],
                spacing=4,
                tight=True,
            )
        
        elif field.field_type == FieldType.NUMBER:
            text_field = ft.TextField(
                value=str(field.value) if field.value else "",
                width=field.width,
                keyboard_type=ft.KeyboardType.NUMBER,
                hint_text=field.hint_text,
                disabled=field.disabled,
                on_change=field.on_change,
            )
            return ft.Column(
                [
                    ft.Text(field.label, size=12, weight=ft.FontWeight.W_500),
                    text_field,
                ],
                spacing=4,
                tight=True,
            )
        
        elif field.field_type == FieldType.DATE:
            text_field = ft.TextField(
                value=str(field.value) if field.value else "",
                width=field.width,
                hint_text=field.hint_text or "YYYY-MM-DD",
                disabled=field.disabled,
                on_change=field.on_change,
            )
            return ft.Column(
                [
                    ft.Text(field.label, size=12, weight=ft.FontWeight.W_500),
                    text_field,
                ],
                spacing=4,
                tight=True,
            )
        
        elif field.field_type == FieldType.DROPDOWN:
            options = []
            if field.options:
                options = [ft.dropdown.Option(str(val), label) for val, label in field.options]
            
            return ft.Dropdown(
                label=field.label,
                value=str(field.value) if field.value else None,
                options=options,
                width=field.width,
                disabled=field.disabled,
                on_change=field.on_change,
            )
        
        elif field.field_type == FieldType.TEXTAREA:
            text_field = ft.TextField(
                value=str(field.value) if field.value else "",
                width=field.width,
                multiline=True,
                min_lines=3,
                max_lines=5,
                hint_text=field.hint_text,
                disabled=field.disabled,
                on_change=field.on_change,
            )
            return ft.Column(
                [
                    ft.Text(field.label, size=12, weight=ft.FontWeight.W_500),
                    text_field,
                ],
                spacing=4,
                tight=True,
            )
        
        elif field.field_type == FieldType.CHECKBOX:
            return ft.Checkbox(
                label=field.label,
                value=bool(field.value) if field.value else False,
                disabled=field.disabled,
                on_change=field.on_change,
            )
        
        else:
            # Fallback to text field
            return ft.TextField(
                label=field.label,
                value=str(field.value) if field.value else "",
                width=field.width,
            )
    
    @staticmethod
    def get_values(controls: Dict[str, ft.Control]) -> Dict[str, Any]:
        """
        Extract values from form controls.
        
        Args:
            controls: Dictionary of form controls
            
        Returns:
            Dictionary of {key: value}
        """
        values = {}
        
        for key, control in controls.items():
            # If control is wrapped in Column (for custom label), extract the TextField
            if isinstance(control, ft.Column) and len(control.controls) >= 2:
                actual_control = control.controls[1]  # Second element is the actual field
            else:
                actual_control = control
            
            if isinstance(actual_control, ft.TextField):
                values[key] = actual_control.value
            elif isinstance(actual_control, ft.Dropdown):
                values[key] = actual_control.value
            elif isinstance(actual_control, ft.Checkbox):
                values[key] = actual_control.value
        
        return values
    
    @staticmethod
    def validate_required(controls: Dict[str, ft.Control], required_keys: List[str]) -> tuple[bool, str]:
        """
        Validate required fields.
        
        Args:
            controls: Dictionary of form controls
            required_keys: List of required field keys
            
        Returns:
            (is_valid, error_message)
        """
        for key in required_keys:
            control = controls.get(key)
            if not control:
                continue
            
            # If control is wrapped in Column (for custom label), extract the TextField
            if isinstance(control, ft.Column) and len(control.controls) >= 2:
                actual_control = control.controls[1]  # Second element is the actual field
                label_text = control.controls[0].value if isinstance(control.controls[0], ft.Text) else key
            else:
                actual_control = control
                label_text = getattr(control, 'label', key)
            
            value = None
            if isinstance(actual_control, ft.TextField):
                value = actual_control.value
            elif isinstance(actual_control, ft.Dropdown):
                value = actual_control.value
            
            if not value or (isinstance(value, str) and not value.strip()):
                return False, f"Il campo '{label_text}' è obbligatorio"
        
        return True, ""
    
    @staticmethod
    def create_form_row(controls: List[ft.Control], spacing: int = 10) -> ft.Row:
        """Create a row with multiple form controls"""
        return ft.Row(controls, spacing=spacing)
    
    @staticmethod
    def create_section(title: str, controls: List[ft.Control]) -> ft.Column:
        """Create a form section with title and controls"""
        return ft.Column([
            ft.Text(title, size=16, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            *controls,
        ], spacing=10)
