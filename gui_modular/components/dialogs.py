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
        
        # Ensure dialog is visible even if some app setups rely on overlay
        try:
            if hasattr(page, 'overlay') and dialog not in list(page.overlay):
                page.overlay.append(dialog)
        except Exception:
            pass

        page.dialog = dialog
        dialog.open = True
        page.update()
    
    @staticmethod
    def show_info_dialog(page: ft.Page, title: str, content: ft.Control):
        """Show information dialog with custom content"""
        def close_dialog(e):
            dialog.open = False
            page.update()
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(title),
            content=content,
            actions=[
                ft.TextButton("Chiudi", on_click=close_dialog)
            ]
        )
        
        try:
            if hasattr(page, 'overlay') and dialog not in list(page.overlay):
                page.overlay.append(dialog)
        except Exception:
            pass

        page.dialog = dialog
        dialog.open = True
        page.update()
    
    @staticmethod
    def show_form_dialog(
        page: ft.Page,
        title: str,
        form_controls: list,
        on_submit: Callable,
        height: int = 400,
    ):
        """Show form dialog with submit/cancel buttons"""
        def close_dialog(e):
            dialog.open = False
            page.update()

        def handle_submit(e):
            # Delegate to provided submit handler
            try:
                print(f"DEBUG: handle_submit called, event={e}")
                on_submit(e)
                print("DEBUG: on_submit completed successfully")
            except Exception as ex:
                import traceback
                error_details = traceback.format_exc()
                print(f"ERROR in handle_submit: {ex}")
                print(f"Full traceback:\n{error_details}")
                traceback.print_exc()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(title),
            content=ft.Container(
                content=ft.Column(
                    form_controls,
                    scroll=ft.ScrollMode.AUTO,
                    tight=True,
                ),
                width=600,
                height=height,
                padding=ft.padding.only(top=20, left=10, right=10, bottom=10),  # Add top padding
            ),
            actions=[
                ft.TextButton("Annulla", on_click=close_dialog),
                ft.ElevatedButton("Salva", on_click=handle_submit),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        try:
            if hasattr(page, 'overlay') and dialog not in list(page.overlay):
                page.overlay.append(dialog)
        except Exception:
            pass

        page.dialog = dialog
        dialog.open = True
        page.update()
    
    @staticmethod
    def show_confirm_dialog(
        page: ft.Page,
        title: str,
        message: str,
        on_confirm: Callable,
    ):
        """Show confirmation dialog"""
        def close_dialog(e):
            dialog.open = False
            page.update()
        
        def handle_confirm(e):
            dialog.open = False
            page.update()
            on_confirm()
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(title),
            content=ft.Text(message),
            actions=[
                ft.TextButton("Annulla", on_click=close_dialog),
                ft.ElevatedButton(
                    "Conferma",
                    on_click=handle_confirm,
                    style=ft.ButtonStyle(bgcolor=ft.Colors.RED_400)
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        try:
            if hasattr(page, 'overlay') and dialog not in list(page.overlay):
                page.overlay.append(dialog)
        except Exception:
            pass

        page.dialog = dialog
        dialog.open = True
        page.update()
    
    @staticmethod
    def close_dialog(page: ft.Page):
        """Close current dialog"""
        if page.dialog:
            page.dialog.open = False
            page.update()
