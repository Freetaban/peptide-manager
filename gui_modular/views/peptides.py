"""Peptides View - Complete CRUD implementation"""
import flet as ft
from ..components.data_table import DataTable, Column, Action
from ..components.dialogs import DialogBuilder


class PeptidesView(ft.Container):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.search_query = ""
        self._build()
    
    def _build(self):
        """Build peptides view"""
        # Define table columns
        columns = [
            Column(name="id", label="ID"),
            Column(name="name", label="Nome"),
            Column(name="description", label="Descrizione"),
            Column(name="common_uses", label="Usi Comuni"),
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
                title="Peptidi",
                add_button_text="Aggiungi Peptide",
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
        # Get peptides from manager
        peptides = self.app.manager.get_peptides(search=self.search_query if self.search_query else None)
        # Sort by ID
        peptides_sorted = sorted(peptides, key=lambda x: x['id'])
        return self.table.build(peptides_sorted)
    
    def _on_search(self, e):
        """Handle search input"""
        self.search_query = e.control.value
        self._refresh()
    
    def _refresh(self):
        """Refresh view"""
        self._build()
        self.app.page.update()
    
    def _show_details(self, peptide_id: int):
        """Show peptide details dialog"""
        # Query for full peptide details
        peptides = self.app.manager.get_peptides()
        peptide = next((p for p in peptides if p['id'] == peptide_id), None)
        
        if not peptide:
            self._show_snackbar("Peptide non trovato", bgcolor=ft.colors.RED_400)
            return
        
        dialog = ft.AlertDialog(
            title=ft.Text(f"Peptide #{peptide['id']} - {peptide['name']}"),
            content=ft.Column([
                ft.Text(f"Descrizione: {peptide.get('description') or 'N/A'}"),
                ft.Text(f"Usi: {peptide.get('common_uses') or 'N/A'}"),
                ft.Text(f"Note: {peptide.get('notes') or 'N/A'}"),
            ], tight=True),
            actions=[
                ft.TextButton("Chiudi", on_click=lambda e: self._close_dialog(dialog)),
            ],
        )
        self._open_dialog(dialog)
    
    def _show_add_dialog(self, e):
        """Show add peptide dialog"""
        name_field = ft.TextField(label="Nome", autofocus=True)
        desc_field = ft.TextField(label="Descrizione", multiline=True)
        uses_field = ft.TextField(label="Usi comuni", multiline=True)
        notes_field = ft.TextField(label="Note", multiline=True)
        
        def add_peptide(e):
            try:
                if not name_field.value:
                    self._show_snackbar("Inserisci un nome!", error=True)
                    return
                
                peptide_id = self.app.manager.add_peptide(
                    name=name_field.value,
                    description=desc_field.value if desc_field.value else None,
                    common_uses=uses_field.value if uses_field.value else None,
                    notes=notes_field.value if notes_field.value else None,
                )
                
                self._close_dialog(dialog)
                self._show_snackbar(f"✅ Peptide '{name_field.value}' aggiunto!")
                self._refresh()
                
            except Exception as ex:
                self._show_snackbar(f"❌ Errore: {str(ex)}", error=True)
        
        dialog = ft.AlertDialog(
            title=ft.Text("Aggiungi Peptide"),
            content=ft.Column([
                name_field,
                desc_field,
                uses_field,
                notes_field,
            ], tight=True, scroll=ft.ScrollMode.AUTO, height=400),
            actions=[
                ft.TextButton("Annulla", on_click=lambda e: self._close_dialog(dialog)),
                ft.ElevatedButton("Salva", on_click=add_peptide),
            ],
        )
        self._open_dialog(dialog)
    
    def _show_edit_dialog(self, peptide_id: int):
        """Show edit peptide dialog"""
        # Query for peptide details
        peptides = self.app.manager.get_peptides()
        peptide = next((p for p in peptides if p['id'] == peptide_id), None)
        
        if not peptide:
            self._show_snackbar("Peptide non trovato", bgcolor=ft.Colors.RED_400)
            return
        
        name_field = ft.TextField(label="Nome", value=peptide['name'], autofocus=True)
        desc_field = ft.TextField(label="Descrizione", value=peptide['description'] or "", multiline=True)
        uses_field = ft.TextField(label="Usi comuni", value=peptide['common_uses'] or "", multiline=True)
        notes_field = ft.TextField(label="Note", value=peptide['notes'] or "", multiline=True)
        
        def update_peptide(e):
            try:
                if not name_field.value:
                    self._show_snackbar("Inserisci un nome!", error=True)
                    return
                
                success = self.app.manager.update_peptide(
                    peptide_id=peptide_id,
                    name=name_field.value,
                    description=desc_field.value if desc_field.value else None,
                    common_uses=uses_field.value if uses_field.value else None,
                    notes=notes_field.value if notes_field.value else None,
                )
                
                if success:
                    self._close_dialog(dialog)
                    self._show_snackbar(f"✅ Peptide '{name_field.value}' aggiornato!")
                    self._refresh()
                else:
                    self._show_snackbar("❌ Errore nell'aggiornamento", error=True)
                
            except Exception as ex:
                self._show_snackbar(f"❌ Errore: {str(ex)}", error=True)
        
        dialog = ft.AlertDialog(
            title=ft.Text(f"Modifica Peptide #{peptide['id']}"),
            content=ft.Column([
                name_field,
                desc_field,
                uses_field,
                notes_field,
            ], tight=True, scroll=ft.ScrollMode.AUTO, height=400),
            actions=[
                ft.TextButton("Annulla", on_click=lambda e: self._close_dialog(dialog)),
                ft.ElevatedButton("Salva", on_click=update_peptide),
            ],
        )
        self._open_dialog(dialog)
    
    def _confirm_delete(self, peptide_id: int):
        """Confirm peptide deletion"""
        # Query for peptide details
        peptides = self.app.manager.get_peptides()
        peptide = next((p for p in peptides if p['id'] == peptide_id), None)
        
        if not peptide:
            self._show_snackbar("Peptide non trovato", bgcolor=ft.Colors.RED_400)
            return
        
        def do_delete(e):
            try:
                success = self.app.manager.soft_delete_peptide(peptide_id)
                if success:
                    dialog.open = False
                    self.app.page.update()
                    self._show_snackbar(f"✅ Peptide '{peptide['name']}' eliminato!")
                    self._refresh()
                else:
                    self._show_snackbar("❌ Errore nell'eliminazione", error=True)
            except Exception as ex:
                self._show_snackbar(f"❌ Errore: {str(ex)}", error=True)
        
        def cancel(e):
            dialog.open = False
            self.app.page.update()
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Conferma Eliminazione"),
            content=ft.Text(f"Sei sicuro di voler eliminare '{peptide['name']}'?"),
            actions=[
                ft.TextButton("Annulla", on_click=cancel),
                ft.ElevatedButton(
                    "Elimina",
                    on_click=do_delete,
                    bgcolor=ft.Colors.RED_400,
                ),
            ],
        )
        
        self.app.page.overlay.append(dialog)
        dialog.open = True
        self.app.page.update()
    
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

