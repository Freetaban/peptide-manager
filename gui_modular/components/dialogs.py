"""
Dialog Builder Component
"""

import flet as ft
from typing import Callable, Optional


class DialogBuilder:
    """Standard dialogs"""
    
    @staticmethod
    def confirm_delete(
        page: ft.Page,
        entity_name: str,
        on_confirm: Callable,
        on_cancel: Optional[Callable] = None
    ):
        """Show confirmation dialog for delete operation"""
        def handle_confirm(e):
            dialog.open = False
            page.update()
            on_confirm()
        
        def handle_cancel(e):
            dialog.open = False
            page.update()
            if on_cancel:
                on_cancel()
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Confirm Delete"),
            content=ft.Text(f"Are you sure you want to delete '{entity_name}'?"),
            actions=[
                ft.TextButton("Cancel", on_click=handle_cancel),
                ft.ElevatedButton(
                    "Delete",
                    on_click=handle_confirm,
                    style=ft.ButtonStyle(bgcolor=ft.Colors.ERROR)
                )
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()
    
    @staticmethod
    def show_info(page: ft.Page, title: str, message: str):
        """Show information dialog"""
        def close_dialog(e):
            dialog.open = False
            page.update()
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(title),
            content=ft.Text(message),
            actions=[
                ft.TextButton("OK", on_click=close_dialog)
            ]
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()
