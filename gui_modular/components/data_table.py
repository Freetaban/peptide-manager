"""
DataTable Component - Reusable data table with actions
"""

import flet as ft
from dataclasses import dataclass
from typing import List, Callable, Optional, Any


@dataclass
class Column:
    """Table column definition"""
    name: str
    label: str
    width: Optional[int] = None
    
    def to_flet_column(self) -> ft.DataColumn:
        """Convert to Flet DataColumn"""
        return ft.DataColumn(ft.Text(self.label))


@dataclass
class Action:
    """Row action button definition"""
    icon: str
    tooltip: str
    handler: Callable
    color: Optional[str] = None
    visible_when: Optional[Callable[[dict], bool]] = None  # Show/hide based on row data
    enabled_when: Optional[Callable[[dict], bool]] = None  # Enable/disable based on row data


class DataTable:
    """
    Reusable data table component with action buttons.
    
    Features:
    - Sortable columns
    - Row action buttons
    - Pagination support (future)
    - Search/filter integration
    """
    
    def __init__(
        self,
        columns: List[Column],
        actions: List[Action],
        app=None,
    ):
        """
        Initialize data table.
        
        Args:
            columns: List of Column definitions
            actions: List of Action buttons for each row
            app: Reference to main app (for edit_mode access)
        """
        self.columns = columns
        self.actions = actions
        self.app = app
        self.data = []
        self._table = None
        
    def build(self, data: List[dict]) -> ft.Container:
        """
        Build Flet DataTable from data.
        
        Args:
            data: List of dictionaries (one per row)
            
        Returns:
            Container with DataTable
        """
        self.data = data
        
        # Build rows
        rows = []
        for item in data:
            cells = []
            
            # Data cells
            for col in self.columns:
                value = item.get(col.name, "")
                # Truncate long text
                if isinstance(value, str) and len(value) > 50:
                    value = value[:50] + "..."
                cells.append(ft.DataCell(ft.Text(str(value))))
            
            # Actions cell
            action_buttons = []
            for action in self.actions:
                # Check visibility condition
                if action.visible_when and not action.visible_when(item):
                    continue
                
                # Check enabled condition
                enabled = True
                if action.enabled_when:
                    enabled = action.enabled_when(item)
                
                # Create button
                btn = ft.IconButton(
                    icon=action.icon,
                    tooltip=action.tooltip,
                    on_click=lambda e, row=item, handler=action.handler: handler(row),
                    icon_color=action.color,
                    disabled=not enabled,
                )
                action_buttons.append(btn)
            
            cells.append(ft.DataCell(
                ft.Row(action_buttons, spacing=0)
            ))
            
            rows.append(ft.DataRow(cells=cells))
        
        # Create table
        flet_columns = [col.to_flet_column() for col in self.columns]
        flet_columns.append(ft.DataColumn(ft.Text("Azioni")))
        
        self._table = ft.DataTable(
            columns=flet_columns,
            rows=rows,
        )
        
        return ft.Container(
            content=self._table,
            border=ft.border.all(1, ft.Colors.GREY_800),
            border_radius=10,
            padding=10,
        )
    
    def build_toolbar(
        self,
        title: str,
        add_button_text: str = "Aggiungi",
        on_add: Optional[Callable] = None,
        search_value: str = "",
        on_search: Optional[Callable] = None,
    ) -> ft.Row:
        """
        Build standard toolbar with title, search, and add button.
        
        Args:
            title: Page title
            add_button_text: Text for add button
            on_add: Handler for add button
            search_value: Current search value
            on_search: Handler for search changes
            
        Returns:
            Toolbar row
        """
        elements = [
            ft.Text(title, size=32, weight=ft.FontWeight.BOLD),
            ft.Container(expand=True),
        ]
        
        # Search field (if handler provided)
        if on_search:
            search_field = ft.TextField(
                label="Cerca",
                width=300,
                value=search_value,
                on_change=on_search,
                prefix_icon=ft.Icons.SEARCH,
            )
            elements.append(search_field)
        
        # Add button (if handler provided)
        if on_add:
            add_btn = ft.ElevatedButton(
                add_button_text,
                icon=ft.Icons.ADD,
                on_click=on_add,
            )
            # Disable if edit mode is off (when app reference available)
            if self.app:
                add_btn.disabled = not self.app.edit_mode
            elements.append(add_btn)
        
        return ft.Row(elements)
    
    def update(self, data: List[dict]):
        """
        Update table with new data.
        
        Args:
            data: New data to display
        """
        if self._table:
            self.data = data
            # Rebuild would require page reference - caller should rebuild
            pass


# Helper functions for common action conditions
def edit_mode_required(app) -> Callable[[dict], bool]:
    """Return function that checks if edit mode is enabled"""
    return lambda row: app.edit_mode if app else True


def always_visible(row: dict) -> bool:
    """Action always visible"""
    return True


def always_enabled(row: dict) -> bool:
    """Action always enabled"""
    return True
