"""
Reusable data-table component — Phase 1.

Planned API
-----------
class DataTable(QTableWidget):
    def __init__(self, columns: list[dict], parent=None)
    def load_data(self, rows: list[dict]) -> None
    def selected_row(self) -> dict | None
    def set_context_menu(self, actions: list) -> None
"""
