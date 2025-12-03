"""
Dashboard View
"""

import flet as ft
from ..components import CardBuilder


class DashboardView(ft.Container):
    """Dashboard with statistics and overview"""
    
    def __init__(self, app):
        super().__init__()
        self.app = app
        self._build()
    
    def _build(self):
        """Build dashboard"""
        # Get statistics
        try:
            manager = self.app.manager
            
            # Count entities
            peptides_count = len(manager.get_peptides())
            batches_count = len(manager.get_batches())
            suppliers_count = len(manager.get_suppliers())
            preparations_count = len(manager.get_preparations())
            
        except Exception as e:
            print(f"Error loading stats: {e}")
            peptides_count = batches_count = suppliers_count = preparations_count = 0
        
        # Build stats cards
        stats_row = ft.Row([
            CardBuilder.stat_card(
                "Peptidi",
                str(peptides_count),
                ft.Icons.SCIENCE,
                ft.Colors.BLUE_400
            ),
            CardBuilder.stat_card(
                "Lotti",
                str(batches_count),
                ft.Icons.INVENTORY_2,
                ft.Colors.GREEN_400
            ),
            CardBuilder.stat_card(
                "Fornitori",
                str(suppliers_count),
                ft.Icons.BUSINESS,
                ft.Colors.ORANGE_400
            ),
            CardBuilder.stat_card(
                "Preparazioni",
                str(preparations_count),
                ft.Icons.MEDICATION,
                ft.Colors.PURPLE_400
            ),
        ], wrap=True, spacing=20)
        
        # Build content
        self.content = ft.Column([
            ft.Text("Dashboard", size=28, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            ft.Text("Statistiche", size=20, weight=ft.FontWeight.BOLD),
            stats_row,
            ft.Container(height=20),
            CardBuilder.info_card(
                "Benvenuto",
                f"Sistema in modalità: {self.app.environment.upper()}",
                ft.Icons.INFO
            )
        ], spacing=20, scroll=ft.ScrollMode.AUTO)
        
        self.padding = 20
        self.expand = True
