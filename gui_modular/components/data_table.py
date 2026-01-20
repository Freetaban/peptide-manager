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
    icon: str  # Icon name (e.g., "visibility", "edit", "delete")
    handler: Callable  # Function to call when clicked (receives entity_id)
    tooltip: str  # Tooltip text
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
        self._sort_column_index = None
        self._sort_ascending = True
        self._container = None
        
    def build(self, data: List[dict]) -> ft.Container:
        """
        Build Flet DataTable from data.
        
        Args:
            data: List of dictionaries (one per row)
            
        Returns:
            Container with DataTable
        """
        self.data = data
        
        # Sort data if sort is active
        if self._sort_column_index is not None and self._sort_column_index < len(self.columns):
            sorted_data = self._sort_data(data)
        else:
            sorted_data = data
        
        # Build rows
        rows = []
        for item in sorted_data:
            cells = []
            
            # Data cells
            for col in self.columns:
                value = item.get(col.name, "")
                
                # Special formatting for janoshik_quality_score
                if col.name == 'janoshik_quality_score' and value:
                    # Format score with 1 decimal
                    formatted_value = f"{float(value):.1f}" if value else ""
                    cells.append(ft.DataCell(ft.Text(formatted_value)))
                else:
                    # Truncate long text
                    if isinstance(value, str) and len(value) > 50:
                        value = value[:50] + "..."
                    cells.append(ft.DataCell(ft.Text(str(value) if value else "")))
            
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
                
                # Extract ID from item (support both _id and id fields)
                item_id = item.get('_id') or item.get('id')
                
                # Convert icon string to ft.Icons constant
                icon_obj = getattr(ft.Icons, action.icon.upper(), ft.Icons.HELP)
                
                # Create button
                btn = ft.IconButton(
                    icon=icon_obj,
                    tooltip=action.tooltip,
                    on_click=lambda e, entity_id=item_id, handler=action.handler: handler(entity_id),
                    icon_color=action.color,
                    disabled=not enabled,
                )
                action_buttons.append(btn)
            
            cells.append(ft.DataCell(
                ft.Row(action_buttons, spacing=0)
            ))
            
            rows.append(ft.DataRow(cells=cells))
        
        # Create table columns with sort handlers
        flet_columns = []
        for idx, col in enumerate(self.columns):
            flet_columns.append(ft.DataColumn(
                label=ft.Text(col.label),
                on_sort=lambda e, col_idx=idx: self._on_sort(col_idx, e.ascending),
            ))
        flet_columns.append(ft.DataColumn(ft.Text("Azioni")))
        
        self._table = ft.DataTable(
            columns=flet_columns,
            rows=rows,
            sort_column_index=self._sort_column_index,
            sort_ascending=self._sort_ascending,
        )
        
        self._container = ft.Container(
            content=self._table,
            border=ft.border.all(1, ft.Colors.GREY_800),
            border_radius=10,
            padding=10,
        )
        
        return self._container
    
    def _sort_data(self, data: List[dict]) -> List[dict]:
        """Sort data by current sort column"""
        if not data or self._sort_column_index is None:
            return data
        
        col = self.columns[self._sort_column_index]
        
        # Sort with None handling
        def sort_key(item):
            value = item.get(col.name)
            # Handle None values - put them at the end
            if value is None:
                return (1, "")  # Tuple: (1 for None, empty string)
            # Handle numeric values
            if isinstance(value, (int, float)):
                return (0, value)
            # Handle strings
            return (0, str(value).lower())
        
        sorted_data = sorted(data, key=sort_key, reverse=not self._sort_ascending)
        return sorted_data
    
    def _on_sort(self, column_index: int, ascending: bool):
        """Handle column sort event"""
        self._sort_column_index = column_index
        self._sort_ascending = ascending
        
        # Rebuild table with sorted data
        if self._container and self.app and self.app.page:
            # Get parent view to trigger refresh
            # This is a bit hacky but works for now
            if hasattr(self.app, 'page'):
                self.app.page.update()
    
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
            # Wrap the provided handler to add a console debug print
            add_btn = ft.ElevatedButton(
                add_button_text,
                icon=ft.Icons.ADD,
                on_click=on_add,
            )
            # Note: Add button is always enabled (no edit_mode check)
            # Only edit/delete actions require edit_mode
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
