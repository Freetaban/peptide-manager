"""Suppliers View - Complete CRUD implementation"""
import flet as ft
from ..components.data_table import DataTable, Column, Action
from ..components.dialogs import DialogBuilder


class SuppliersView(ft.Container):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.search_query = ""
        self._build()
    
    def _build(self):
        """Build suppliers view"""
        # Define table columns
        columns = [
            Column(name="id", label="ID"),
            Column(name="name", label="Nome"),
            Column(name="country", label="Paese"),
            Column(name="website", label="Sito Web"),
            Column(name="rating", label="Rating"),
        ]
        
        # Define actions
        actions = [
            Action(
                icon=ft.Icons.VISIBILITY,
                tooltip="Dettagli",
                handler=self._show_details,
            ),
            Action(
                icon=ft.Icons.EDIT,
                tooltip="Modifica",
                handler=self._show_edit_dialog,
                enabled_when=lambda row: self.app.edit_mode,
            ),
            Action(
                icon=ft.Icons.DELETE,
                tooltip="Elimina",
                handler=self._confirm_delete,
                color=ft.Colors.RED_400,
                enabled_when=lambda row: self.app.edit_mode,
            ),
        ]
        
        # Create table
        self.table = DataTable(columns=columns, actions=actions, app=self.app)
        
        # Build layout
        self.content = ft.Column([
            self.table.build_toolbar(
                title="Fornitori",
                add_button_text="Aggiungi Fornitore",
                on_add=self._show_add_dialog,
                search_value=self.search_query,
                on_search=self._on_search,
            ),
            ft.Divider(),
            self._build_table_content(),
        ], scroll=ft.ScrollMode.AUTO)
        
        self.padding = 20
        self.expand = True
    
    def _build_table_content(self):
        """Build table with current data"""
        suppliers = self.app.manager.get_suppliers(search=self.search_query if self.search_query else None)
        suppliers_sorted = sorted(suppliers, key=lambda x: x['id'])
        return self.table.build(suppliers_sorted)
    
    def _on_search(self, e):
        """Handle search input"""
        self.search_query = e.control.value
        self._refresh()
    
    def _refresh(self):
        """Refresh view"""
        self._build()
        self.app.page.update()
    
    def _show_details(self, supplier: dict):
        """Show supplier details dialog"""
        dialog = ft.AlertDialog(
            title=ft.Text(f"Fornitore #{supplier['id']} - {supplier['name']}"),
            content=ft.Column([
                ft.Text(f"Paese: {supplier['country'] or 'N/A'}"),
                ft.Text(f"Sito web: {supplier['website'] or 'N/A'}"),
                ft.Text(f"Email: {supplier['email'] or 'N/A'}"),
                ft.Text(f"Rating: {supplier['rating']}/5" if supplier['rating'] else "Rating: N/A"),
                ft.Text(f"Note: {supplier['notes'] or 'N/A'}"),
            ], tight=True),
            actions=[
                ft.TextButton("Chiudi", on_click=lambda e: self._close_dialog(dialog)),
            ],
        )
        self._open_dialog(dialog)
    
    def _show_add_dialog(self, e):
        """Show add supplier dialog"""
        name_field = ft.TextField(label="Nome", autofocus=True)
        country_field = ft.TextField(label="Paese")
        website_field = ft.TextField(label="Sito web")
        email_field = ft.TextField(label="Email")
        rating_field = ft.Dropdown(
            label="Rating",
            options=[
                ft.dropdown.Option("1", "1 - Scarso"),
                ft.dropdown.Option("2", "2 - Sufficiente"),
                ft.dropdown.Option("3", "3 - Buono"),
                ft.dropdown.Option("4", "4 - Ottimo"),
                ft.dropdown.Option("5", "5 - Eccellente"),
            ],
        )
        notes_field = ft.TextField(label="Note", multiline=True)
        
        def add_supplier(e):
            try:
                if not name_field.value:
                    self._show_snackbar("Inserisci un nome!", error=True)
                    return
                
                supplier_id = self.app.manager.add_supplier(
                    name=name_field.value,
                    country=country_field.value if country_field.value else None,
                    website=website_field.value if website_field.value else None,
                    email=email_field.value if email_field.value else None,
                    rating=int(rating_field.value) if rating_field.value else None,
                    notes=notes_field.value if notes_field.value else None,
                )
                
                self._close_dialog(dialog)
                self._show_snackbar(f"✅ Fornitore '{name_field.value}' aggiunto!")
                self._refresh()
                
            except Exception as ex:
                self._show_snackbar(f"❌ Errore: {str(ex)}", error=True)
        
        dialog = ft.AlertDialog(
            title=ft.Text("Aggiungi Fornitore"),
            content=ft.Column([
                name_field,
                country_field,
                website_field,
                email_field,
                rating_field,
                notes_field,
            ], tight=True, scroll=ft.ScrollMode.AUTO, height=400),
            actions=[
                ft.TextButton("Annulla", on_click=lambda e: self._close_dialog(dialog)),
                ft.ElevatedButton("Salva", on_click=add_supplier),
            ],
        )
        self._open_dialog(dialog)
    
    def _show_edit_dialog(self, supplier: dict):
        """Show edit supplier dialog"""
        name_field = ft.TextField(label="Nome", value=supplier['name'], autofocus=True)
        country_field = ft.TextField(label="Paese", value=supplier['country'] or "")
        website_field = ft.TextField(label="Sito web", value=supplier['website'] or "")
        email_field = ft.TextField(label="Email", value=supplier['email'] or "")
        rating_field = ft.Dropdown(
            label="Rating",
            value=str(supplier['rating']) if supplier['rating'] else None,
            options=[
                ft.dropdown.Option("1", "1 - Scarso"),
                ft.dropdown.Option("2", "2 - Sufficiente"),
                ft.dropdown.Option("3", "3 - Buono"),
                ft.dropdown.Option("4", "4 - Ottimo"),
                ft.dropdown.Option("5", "5 - Eccellente"),
            ],
        )
        notes_field = ft.TextField(label="Note", value=supplier['notes'] or "", multiline=True)
        
        def update_supplier(e):
            try:
                if not name_field.value:
                    self._show_snackbar("Inserisci un nome!", error=True)
                    return
                
                success = self.app.manager.update_supplier(
                    supplier_id=supplier['id'],
                    name=name_field.value,
                    country=country_field.value if country_field.value else None,
                    website=website_field.value if website_field.value else None,
                    email=email_field.value if email_field.value else None,
                    rating=int(rating_field.value) if rating_field.value else None,
                    notes=notes_field.value if notes_field.value else None,
                )
                
                if success:
                    self._close_dialog(dialog)
                    self._show_snackbar(f"✅ Fornitore '{name_field.value}' aggiornato!")
                    self._refresh()
                else:
                    self._show_snackbar("❌ Errore nell'aggiornamento", error=True)
                
            except Exception as ex:
                self._show_snackbar(f"❌ Errore: {str(ex)}", error=True)
        
        dialog = ft.AlertDialog(
            title=ft.Text(f"Modifica Fornitore #{supplier['id']}"),
            content=ft.Column([
                name_field,
                country_field,
                website_field,
                email_field,
                rating_field,
                notes_field,
            ], tight=True, scroll=ft.ScrollMode.AUTO, height=400),
            actions=[
                ft.TextButton("Annulla", on_click=lambda e: self._close_dialog(dialog)),
                ft.ElevatedButton("Salva", on_click=update_supplier),
            ],
        )
        self._open_dialog(dialog)
    
    def _confirm_delete(self, supplier: dict):
        """Confirm supplier deletion"""
        def do_delete(e):
            try:
                success = self.app.manager.soft_delete_supplier(supplier['id'])
                if success:
                    self._close_dialog(dialog)
                    self._show_snackbar(f"✅ Fornitore '{supplier['name']}' eliminato!")
                    self._refresh()
                else:
                    self._show_snackbar("❌ Errore nell'eliminazione", error=True)
            except Exception as ex:
                self._show_snackbar(f"❌ Errore: {str(ex)}", error=True)
        
        dialog = DialogBuilder.confirm_delete(
            item_name=supplier['name'],
            on_confirm=do_delete,
            on_cancel=lambda e: self._close_dialog(dialog),
        )
        self._open_dialog(dialog)
    
    def _open_dialog(self, dialog):
        """Open dialog"""
        self.app.page.overlay.append(dialog)
        dialog.open = True
        self.app.page.update()
    
    def _close_dialog(self, dialog):
        """Close dialog"""
        dialog.open = False
        self.app.page.update()
    
    def _show_snackbar(self, message: str, error: bool = False):
        """Show snackbar message"""
        self.app.page.snack_bar = ft.SnackBar(
            content=ft.Text(message),
            bgcolor=ft.Colors.RED_400 if error else ft.Colors.GREEN_400,
        )
        self.app.page.snack_bar.open = True
        self.app.page.update()

