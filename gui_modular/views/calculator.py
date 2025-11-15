"""Calculator View - Placeholder"""
import flet as ft

class CalculatorView(ft.Container):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.content = ft.Column([
            ft.Text("Peptide Calculator", size=24, weight=ft.FontWeight.BOLD),
            ft.Text("View to be implemented", size=14, italic=True)
        ], spacing=10)
        self.padding = 20
        self.expand = True
