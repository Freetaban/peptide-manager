"""Batches View - Complete CRUD with peptide composition management"""
import flet as ft
from datetime import datetime, timedelta
from ..components.data_table import DataTable, Column, Action
from ..components.dialogs import DialogBuilder
from ..components.forms import FormBuilder, Field, FieldType


class BatchesView(ft.Container):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.search_query = ""
        self._build()
    
    def _build(self):
        """Build batches view"""
        columns = [
            Column(name="id", label="ID"),
            Column(name="product_name", label="Prodotto"),
            Column(name="composition_summary", label="Composizione"),
            Column(name="supplier_name", label="Fornitore"),
            Column(name="vials_status", label="Fiale"),
        ]
        
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
        
        self.table = DataTable(columns=columns, actions=actions, app=self.app)
        
        self.content = ft.Column([
            self.table.build_toolbar(
                title="Batches",
                add_button_text="Aggiungi Batch",
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
        batches = self.app.manager.get_batches(
            search=self.search_query if self.search_query else None,
            only_available=True
        )
        batches_sorted = sorted(batches, key=lambda x: x['id'])
        
        enriched_data = []
        for b in batches_sorted:
            batch_details = self.app.manager.get_batch_details(b['id'])
            comp_list = [c['name'] for c in batch_details['composition']]
            composition = ", ".join(comp_list[:2])
            if len(comp_list) > 2:
                composition += f" +{len(comp_list)-2}"
            
            enriched_data.append({
                **b,
                'composition_summary': composition,
                'vials_status': f"{b['vials_remaining']}/{b['vials_count']}",
            })
        
        return self.table.build(enriched_data)
    
    def _on_search(self, e):
        """Handle search input"""
        self.search_query = e.control.value
        self._refresh()
    
    def _refresh(self):
        """Refresh view"""
        self._build()
        self.app.page.update()
    
    def _show_details(self, batch_id: int):
        """Show batch details dialog"""
        batch_details = self.app.manager.get_batch_details(batch_id)
        
        comp_text = "\n".join([
            f"• {c['name']}: {c.get('mg_per_vial', c.get('mg_amount', 0))}mg/fiala" 
            for c in batch_details['composition']
        ])
        
        prep_count = len(batch_details.get('preparations', []))
        
        dialog = ft.AlertDialog(
            title=ft.Text(f"Batch #{batch_id} - {batch_details['product_name']}"),
            content=ft.Column([
                ft.Text(f"Fornitore: {batch_details['supplier_name']}"),
                ft.Text(f"Acquisto: {batch_details['purchase_date']}"),
                ft.Text(f"Scadenza: {batch_details.get('expiry_date', 'N/A')}"),
                ft.Text(f"Fiale: {batch_details['vials_remaining']}/{batch_details['vials_count']}"),
                ft.Text(f"Prezzo: €{batch_details.get('total_price', 0):.2f}"),
                ft.Text(f"Conservazione: {batch_details.get('storage_location', 'N/A')}"),
                ft.Divider(),
                ft.Text("Composizione:", weight=ft.FontWeight.BOLD),
                ft.Text(comp_text if comp_text else "Nessuna composizione"),
                ft.Divider(),
                ft.Text(f"Preparazioni: {prep_count}"),
            ], tight=True, scroll=ft.ScrollMode.AUTO, height=400),
            actions=[
                ft.TextButton("Chiudi", on_click=lambda e: self._close_dialog(dialog)),
            ],
        )
        self._open_dialog(dialog)
    
    def _show_add_dialog(self, e):
        """Show add batch dialog with peptide composition"""
        suppliers = self.app.manager.get_suppliers()
        peptides = self.app.manager.get_peptides()
        
        if not suppliers:
            self._show_snackbar("Aggiungi prima un fornitore!", error=True)
            return
        
        if not peptides:
            self._show_snackbar("Aggiungi prima dei peptidi!", error=True)
            return
        
        # Build form fields
        form_fields = FormBuilder.build_fields([
            Field("supplier_id", "Fornitore", FieldType.DROPDOWN,
                  options=[(str(s['id']), s['name']) for s in suppliers],
                  width=400),
            Field("product_name", "Nome Prodotto", FieldType.TEXT, width=400, required=True),
            Field("vials_count", "Numero Fiale", FieldType.NUMBER, value="1", width=200),
            Field("total_price", "Prezzo Totale (€)", FieldType.NUMBER, value="0", width=200),
            Field("purchase_date", "Data Acquisto", FieldType.DATE,
                  value=datetime.now().strftime('%Y-%m-%d'), width=200),
            Field("expiry_date", "Data Scadenza", FieldType.DATE,
                  value=(datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d'), width=200),
            Field("storage_location", "Conservazione", FieldType.TEXT, value="Frigo", width=300),
        ])
        
        # Peptide composition checkboxes
        peptide_controls = {}
        peptide_rows = []
        
        for p in peptides:
            cb = ft.Checkbox(label=p['name'], value=False)
            mg_field = ft.TextField(
                label="mg/fiala",
                width=100,
                value="5",
                keyboard_type=ft.KeyboardType.NUMBER,
                visible=False,
            )
            
            def make_on_change(field):
                def on_change(e):
                    field.visible = e.control.value
                    self.app.page.update()
                return on_change
            
            cb.on_change = make_on_change(mg_field)
            peptide_controls[p['id']] = (cb, mg_field)
            peptide_rows.append(ft.Row([cb, mg_field]))
        
        def add_batch(e):
            try:
                # Validate form
                is_valid, error_msg = FormBuilder.validate_required(
                    form_fields, 
                    ['supplier_id', 'product_name']
                )
                if not is_valid:
                    self._show_snackbar(error_msg, error=True)
                    return
                
                # Get form values
                values = FormBuilder.get_values(form_fields)
                
                # Collect peptide composition
                peptide_ids = []
                peptide_amounts = {}
                for pid, (cb, mg_field) in peptide_controls.items():
                    if cb.value:
                        try:
                            mg = float(mg_field.value)
                            if mg <= 0:
                                raise ValueError()
                            peptide_ids.append(pid)
                            peptide_amounts[pid] = mg
                        except:
                            self._show_snackbar(f"Inserisci mg validi per {cb.label}!", error=True)
                            return
                
                if not peptide_ids:
                    self._show_snackbar("Seleziona almeno un peptide!", error=True)
                    return
                
                # Calculate total mg
                total_mg = sum(peptide_amounts.values())
                
                # Add batch
                batch_id = self.app.manager.add_batch(
                    supplier_id=int(values['supplier_id']),
                    product_name=values['product_name'],
                    peptide_ids=peptide_ids,
                    peptide_amounts=peptide_amounts,
                    vials_count=int(values['vials_count']),
                    mg_per_vial=total_mg,
                    total_price=float(values['total_price']),
                    purchase_date=values['purchase_date'],
                    expiry_date=values['expiry_date'] if values['expiry_date'] else None,
                    storage_location=values['storage_location'] if values['storage_location'] else None,
                )
                
                self._close_dialog(dialog)
                self._show_snackbar(f"✅ Batch #{batch_id} aggiunto!")
                self._refresh()
                
            except Exception as ex:
                self._show_snackbar(f"❌ Errore: {str(ex)}", error=True)
        
        dialog = ft.AlertDialog(
            title=ft.Text("Aggiungi Batch"),
            content=ft.Column([
                form_fields['supplier_id'],
                form_fields['product_name'],
                FormBuilder.create_form_row([
                    form_fields['vials_count'],
                    form_fields['total_price'],
                ]),
                FormBuilder.create_form_row([
                    form_fields['purchase_date'],
                    form_fields['expiry_date'],
                ]),
                form_fields['storage_location'],
                ft.Divider(),
                ft.Text("Composizione Peptidi:", weight=ft.FontWeight.BOLD),
                *peptide_rows,
            ], tight=True, scroll=ft.ScrollMode.AUTO, height=500),
            actions=[
                ft.TextButton("Annulla", on_click=lambda e: self._close_dialog(dialog)),
                ft.ElevatedButton("Salva", on_click=add_batch),
            ],
        )
        self._open_dialog(dialog)
    
    def _show_edit_dialog(self, batch_id: int):
        """Show edit batch dialog"""
        batch_details = self.app.manager.get_batch_details(batch_id)
        suppliers = self.app.manager.get_suppliers()
        peptides = self.app.manager.get_peptides()
        
        # Build form fields with current values
        form_fields = FormBuilder.build_fields([
            Field("supplier_id", "Fornitore", FieldType.DROPDOWN,
                  value=str(batch_details['supplier_id']),
                  options=[(str(s['id']), s['name']) for s in suppliers],
                  width=400),
            Field("product_name", "Nome Prodotto", FieldType.TEXT,
                  value=batch_details['product_name'], width=400, required=True),
            Field("vials_count", "Fiale Totali", FieldType.NUMBER,
                  value=str(batch_details['vials_count']), width=150),
            Field("vials_remaining", "Fiale Rimanenti", FieldType.NUMBER,
                  value=str(batch_details['vials_remaining']), width=150),
            Field("total_price", "Prezzo (€)", FieldType.NUMBER,
                  value=str(batch_details.get('total_price', 0)), width=150),
            Field("purchase_date", "Data Acquisto", FieldType.DATE,
                  value=batch_details.get('purchase_date', ''), width=200),
            Field("expiry_date", "Data Scadenza", FieldType.DATE,
                  value=batch_details.get('expiry_date', ''), width=200),
            Field("storage_location", "Conservazione", FieldType.TEXT,
                  value=batch_details.get('storage_location', ''), width=300),
        ])
        
        # Current composition
        current_comp = {c.get('peptide_id', c.get('id')): c.get('mg_per_vial', c.get('mg_amount', 5)) 
                       for c in batch_details['composition']}
        
        # Peptide composition
        peptide_controls = {}
        peptide_rows = []
        
        for p in peptides:
            is_selected = p['id'] in current_comp
            cb = ft.Checkbox(label=p['name'], value=is_selected)
            mg_field = ft.TextField(
                label="mg/fiala",
                width=100,
                value=str(current_comp.get(p['id'], 5)),
                keyboard_type=ft.KeyboardType.NUMBER,
                visible=is_selected,
            )
            
            def make_on_change(field):
                def on_change(e):
                    field.visible = e.control.value
                    self.app.page.update()
                return on_change
            
            cb.on_change = make_on_change(mg_field)
            peptide_controls[p['id']] = (cb, mg_field)
            peptide_rows.append(ft.Row([cb, mg_field]))
        
        def update_batch(e):
            try:
                # Validate
                is_valid, error_msg = FormBuilder.validate_required(
                    form_fields,
                    ['product_name']
                )
                if not is_valid:
                    self._show_snackbar(error_msg, error=True)
                    return
                
                # Get values
                values = FormBuilder.get_values(form_fields)
                
                # Collect composition
                peptide_ids = []
                peptide_amounts = {}
                for pid, (cb, mg_field) in peptide_controls.items():
                    if cb.value:
                        try:
                            mg = float(mg_field.value)
                            if mg <= 0:
                                raise ValueError()
                            peptide_ids.append(pid)
                            peptide_amounts[pid] = mg
                        except:
                            self._show_snackbar(f"Inserisci mg validi per {cb.label}!", error=True)
                            return
                
                # Calculate total mg
                total_mg = sum(peptide_amounts.values()) if peptide_amounts else None
                
                # Update batch
                success = self.app.manager.update_batch(
                    batch_id=batch_id,
                    supplier_id=int(values['supplier_id']),
                    product_name=values['product_name'],
                    peptide_ids=peptide_ids if peptide_ids else None,
                    peptide_amounts=peptide_amounts if peptide_amounts else None,
                    vials_count=int(values['vials_count']),
                    vials_remaining=int(values['vials_remaining']),
                    mg_per_vial=total_mg,
                    total_price=float(values['total_price']),
                    purchase_date=values['purchase_date'],
                    expiry_date=values['expiry_date'] if values['expiry_date'] else None,
                    storage_location=values['storage_location'] if values['storage_location'] else None,
                )
                
                if success:
                    self._close_dialog(dialog)
                    self._show_snackbar(f"✅ Batch #{batch['id']} aggiornato!")
                    self._refresh()
                else:
                    self._show_snackbar("❌ Errore nell'aggiornamento", error=True)
                
            except Exception as ex:
                self._show_snackbar(f"❌ Errore: {str(ex)}", error=True)
        
        dialog = ft.AlertDialog(
            title=ft.Text(f"Modifica Batch #{batch_id}"),
            content=ft.Column([
                form_fields['supplier_id'],
                form_fields['product_name'],
                FormBuilder.create_form_row([
                    form_fields['vials_count'],
                    form_fields['vials_remaining'],
                    form_fields['total_price'],
                ]),
                FormBuilder.create_form_row([
                    form_fields['purchase_date'],
                    form_fields['expiry_date'],
                ]),
                form_fields['storage_location'],
                ft.Divider(),
                ft.Text("Composizione Peptidi:", weight=ft.FontWeight.BOLD),
                *peptide_rows,
            ], tight=True, scroll=ft.ScrollMode.AUTO, height=500),
            actions=[
                ft.TextButton("Annulla", on_click=lambda e: self._close_dialog(dialog)),
                ft.ElevatedButton("Salva", on_click=update_batch),
            ],
        )
        self._open_dialog(dialog)
    
    def _confirm_delete(self, batch_id: int):
        """Confirm batch deletion"""
        # Query for batch details
        batch_details = self.app.manager.get_batch_details(batch_id)
        
        def do_delete(e):
            print(f"DEBUG: do_delete called for batch_id={batch_id}")
            try:
                success = self.app.manager.soft_delete_batch(batch_id)
                print(f"DEBUG: soft_delete_batch returned {success}")
                if success:
                    dialog.open = False
                    self.app.page.update()
                    self._show_snackbar(f"✅ Batch '{batch_details['product_name']}' eliminato!")
                    self._refresh()
                else:
                    self._show_snackbar("❌ Errore nell'eliminazione", error=True)
            except Exception as ex:
                print(f"DEBUG: Exception in do_delete: {ex}")
                self._show_snackbar(f"❌ Errore: {str(ex)}", error=True)
        
        def cancel(e):
            dialog.open = False
            self.app.page.update()
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Conferma Eliminazione"),
            content=ft.Text(f"Sei sicuro di voler eliminare '{batch_details['product_name']}'?"),
            actions=[
                ft.TextButton("Annulla", on_click=cancel),
                ft.ElevatedButton(
                    "Elimina",
                    on_click=do_delete,
                    bgcolor=ft.colors.RED_400,
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

