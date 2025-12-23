"""PreparationsView - Complete CRUD for preparations with volume tracking."""
import flet as ft
from datetime import datetime, timedelta
from gui_modular.components.data_table import DataTable, Column, Action
from gui_modular.components.forms import FormBuilder, Field, FieldType
from gui_modular.components.dialogs import DialogBuilder


class PreparationsView(ft.Container):
    """Complete Preparations view with batch selection and volume management."""
    
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.expand = True
        self.padding = 20
        
        # Build initial content
        self.content = self._build_content()
    
    def _build_content(self):
        """Build complete preparations view."""
        preparations = self.app.manager.get_preparations(only_active=True)
        
        # Build data table
        data_table = DataTable(
            columns=[
                Column("id", "ID", width=60),
                Column("batch_product", "Batch", width=200),
                Column("volume_status", "Volume", width=120),
                Column("percentage", "%", width=80),
                Column("expiry_date", "Scadenza", width=120),
                Column("administrations", "Somm.", width=80),
            ],
            actions=[
                Action(
                    "visibility",
                    lambda prep_id: self._show_details(prep_id),
                    "Dettagli",
                ),
                Action(
                    "edit",
                    lambda prep_id: self._show_edit_dialog(prep_id),
                    "Modifica",
                    enabled_when=lambda row: self.app.edit_mode,
                ),
                Action(
                    "delete",
                    lambda prep_id: self._confirm_delete(prep_id),
                    "Elimina",
                    color=ft.Colors.RED_400,
                    enabled_when=lambda row: self.app.edit_mode,
                ),
                Action(
                    "medication",
                    lambda prep_id: self._administer(prep_id),
                    "Registra Somministrazione",
                    color=ft.Colors.GREEN_400,
                    visible_when=lambda row: row.get('volume_remaining_ml', 0) > 0,
                ),
            ],
            app=self.app,
        )
        
        # Prepare data with calculated fields
        table_data = []
        for prep in preparations:
            percentage = (prep['volume_remaining_ml'] / prep['volume_ml'] * 100) if prep['volume_ml'] > 0 else 0
            
            # Get administrations count
            cursor = self.app.manager.conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM administrations WHERE preparation_id = ?', (prep['id'],))
            admin_count = cursor.fetchone()[0]
            
            table_data.append({
                'id': f"#{prep['id']}",
                'batch_product': prep['batch_product'][:30],
                'volume_status': f"{prep['volume_remaining_ml']:.2f}/{prep['volume_ml']:.2f}ml",
                'percentage': f"{percentage:.0f}%",
                'expiry_date': prep['expiry_date'] or 'N/A',
                'administrations': str(admin_count),
                '_id': prep['id'],  # Hidden ID for actions
                'volume_remaining_ml': prep['volume_remaining_ml'],  # For action visibility
            })
        
        toolbar = data_table.build_toolbar(
            "Preparazioni",
            on_add=self._show_add_dialog,
        )
        
        table = data_table.build(table_data)
        
        return ft.Column([
            toolbar,
            ft.Divider(),
            ft.Container(
                content=table,
                border=ft.border.all(1, ft.Colors.GREY_800),
                border_radius=10,
                padding=10,
            ),
        ], scroll=ft.ScrollMode.AUTO)
    
    def refresh(self):
        """Refresh view content."""
        self.content = self._build_content()
        self.update()
    
    def _show_add_dialog(self, e):
        """Show add preparation dialog."""
        try:
            # Get available batches (with remaining vials)
            batches = self.app.manager.get_batches(only_available=True)
            
            if not batches:
                self.app.show_snackbar("Nessun batch disponibile! Aggiungi prima un batch.", error=True)
                return
            
            # Build form fields
            form_fields = FormBuilder.build_fields([
                Field(
                    "batch_id",
                    "Batch",
                    FieldType.DROPDOWN,
                    required=True,
                    options=[
                        (str(b['id']), f"#{b['id']} - {b['product_name']} ({b['vials_remaining']} fiale)")
                        for b in batches
                    ],
                    width=500,
                ),
                Field("vials_used", "Fiale usate", FieldType.NUMBER, required=True, value="1", width=150),
                Field("volume_ml", "Volume totale (ml)", FieldType.NUMBER, required=True, value="5.0", width=150),
                Field(
                    "diluent",
                    "Diluente",
                    FieldType.DROPDOWN,
                    required=True,
                    value="Bacteriostatic Water",
                    options=[
                        ("Bacteriostatic Water", "Bacteriostatic Water"),
                        ("Sterile Water", "Sterile Water"),
                        ("Sodium Chloride", "Sodium Chloride 0.9%"),
                    ],
                    width=300,
                ),
                Field(
                    "preparation_date",
                    "Data Preparazione",
                    FieldType.DATE,
                    value=datetime.now().strftime('%Y-%m-%d'),
                    width=200,
                ),
                Field(
                    "expiry_date",
                    "Data Scadenza",
                    FieldType.DATE,
                    value=(datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
                    width=200,
                ),
                Field("notes", "Note", FieldType.TEXTAREA, width=500),
            ])
            
            def on_submit(e):
                values = FormBuilder.get_values(form_fields)
                is_valid, error_msg = FormBuilder.validate_required(
                    form_fields,
                    ['batch_id', 'vials_used', 'volume_ml', 'diluent']
                )
                
                if not is_valid:
                    self.app.show_snackbar(error_msg, error=True)
                    return
                
                try:
                    # Get batch ID from form
                    batch_id = int(values['batch_id'])
                    
                    prep_id = self.app.manager.add_preparation(
                        batch_id=batch_id,  # Pass batch_id not batch_name
                        vials_used=int(values['vials_used']),
                        volume_ml=float(values['volume_ml']),
                        diluent=values['diluent'],
                        preparation_date=values['preparation_date'] if values['preparation_date'] else None,
                        expiry_date=values['expiry_date'] if values['expiry_date'] else None,
                        notes=values['notes'] if values['notes'] else None,
                    )
                    
                    self._close_dialog(dialog)
                    self.refresh()
                    self.app.show_snackbar(f"✅ Preparazione #{prep_id} creata con successo!")
                    
                except Exception as ex:
                    self.app.show_snackbar(f"❌ Errore: {ex}", error=True)
            
            # Create dialog
            dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text("Nuova Preparazione"),
                content=ft.Column([
                    form_fields['batch_id'],
                    FormBuilder.create_form_row([
                        form_fields['vials_used'],
                        form_fields['volume_ml'],
                    ]),
                    form_fields['diluent'],
                    FormBuilder.create_form_row([
                        form_fields['preparation_date'],
                        form_fields['expiry_date'],
                    ]),
                    form_fields['notes'],
                ], tight=True, scroll=ft.ScrollMode.AUTO, height=500),
                actions=[
                    ft.TextButton("Annulla", on_click=lambda e: self._close_dialog(dialog)),
                    ft.ElevatedButton("Salva", on_click=on_submit),
                ],
            )
            self._open_dialog(dialog)
            
        except Exception as ex:
            self.app.show_snackbar(f"Errore: {ex}", error=True)
    
    def _show_edit_dialog(self, prep_id):
        """Show edit preparation dialog."""
        prep = self.app.manager.get_preparation_details(prep_id)
        if not prep:
            return
        
        # Get all batches for dropdown
        batches = self.app.manager.get_batches(only_available=False)
        
        # Form fields with current values
        fields = [
            Field(
                "batch_id",
                "Batch",
                FieldType.DROPDOWN,
                value=str(prep['batch_id']),
                required=True,
                options=[
                    (str(b['id']), f"#{b['id']} - {b['product_name']}")
                    for b in batches
                ],
                width=500,
            ),
            Field("vials_used", "Fiale usate", FieldType.NUMBER, value=str(prep['vials_used']), width=150),
            Field("volume_ml", "Volume totale (ml)", FieldType.NUMBER, value=str(prep['volume_ml']), width=150),
            Field(
                "volume_remaining_ml",
                "Volume rimanente (ml)",
                FieldType.NUMBER,
                value=str(prep['volume_remaining_ml']),
                width=150,
            ),
            Field(
                "diluent",
                "Diluente",
                FieldType.DROPDOWN,
                value=prep['diluent'],
                options=[
                    ("Bacteriostatic Water", "Bacteriostatic Water"),
                    ("Sterile Water", "Sterile Water"),
                    ("Sodium Chloride", "Sodium Chloride 0.9%"),
                ],
                width=300,
            ),
            Field("preparation_date", "Data Preparazione", FieldType.DATE, value=prep['preparation_date'], width=200),
            Field("expiry_date", "Data Scadenza", FieldType.DATE, value=prep.get('expiry_date', ''), width=200),
            Field("notes", "Note", FieldType.TEXTAREA, value=prep.get('notes', ''), width=500),
        ]
        
        form_controls = FormBuilder.build_fields(fields)
        
        def on_submit(e):
            values = FormBuilder.get_values(form_controls)
            
            try:
                changes = {}
                
                # Check each field for changes
                if int(values['batch_id']) != prep['batch_id']:
                    changes['batch_id'] = int(values['batch_id'])
                if int(values['vials_used']) != prep['vials_used']:
                    changes['vials_used'] = int(values['vials_used'])
                if float(values['volume_ml']) != prep['volume_ml']:
                    changes['volume_ml'] = float(values['volume_ml'])
                if float(values['volume_remaining_ml']) != prep['volume_remaining_ml']:
                    changes['volume_remaining_ml'] = float(values['volume_remaining_ml'])
                if values['diluent'] != prep['diluent']:
                    changes['diluent'] = values['diluent']
                if values['preparation_date'] != prep['preparation_date']:
                    changes['preparation_date'] = values['preparation_date'] if values['preparation_date'] else None
                if values['expiry_date'] != (prep.get('expiry_date') or ''):
                    changes['expiry_date'] = values['expiry_date'] if values['expiry_date'] else None
                if values['notes'] != (prep.get('notes') or ''):
                    changes['notes'] = values['notes'] if values['notes'] else None
                
                if changes:
                    self.app.manager.update_preparation(prep_id, **changes)
                    self._close_dialog(dialog)
                    self.refresh()
                    self.app.show_snackbar(f"✅ Preparazione #{prep_id} aggiornata!")
                else:
                    self.app.show_snackbar("Nessuna modifica da salvare")
                    
            except Exception as ex:
                self.app.show_snackbar(f"❌ Errore: {ex}", error=True)
        
        # Create dialog with form fields
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"Modifica Preparazione #{prep_id}"),
            content=ft.Column(
                [
                    form_controls['batch_id'],
                    FormBuilder.create_form_row([
                        form_controls['vials_used'],
                        form_controls['volume_ml'],
                        form_controls['volume_remaining_ml'],
                    ]),
                    form_controls['diluent'],
                    FormBuilder.create_form_row([
                        form_controls['preparation_date'],
                        form_controls['expiry_date'],
                    ]),
                    form_controls['notes'],
                ],
                tight=True,
                scroll=ft.ScrollMode.AUTO,
            ),
            actions=[
                ft.TextButton("Annulla", on_click=lambda e: self._close_dialog(dialog)),
                ft.ElevatedButton("Salva", on_click=lambda e: on_submit(e)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        self._open_dialog(dialog)
    
    def _show_details(self, prep_id):
        """Show preparation details dialog with wastage tracking."""
        prep = self.app.manager.get_preparation_details(prep_id)
        if not prep:
            return
        
        # Get administrations count
        cursor = self.app.manager.conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM administrations WHERE preparation_id = ?', (prep_id,))
        admin_count = cursor.fetchone()[0]
        
        content_items = [
            ft.Text(f"📦 Batch: {prep['product_name']}", size=14),
            ft.Text(f"📅 Data Preparazione: {prep['preparation_date']}", size=14),
            ft.Text(f"⏰ Scadenza: {prep['expiry_date']}", size=14),
            ft.Divider(),
            ft.Text(f"💧 Volume: {prep['volume_remaining_ml']:.2f}/{prep['volume_ml']:.2f}ml", size=14),
            ft.Text(
                f"🧪 Concentrazione: {prep['concentration_mg_ml']:.2f}mg/ml ({prep['concentration_mg_ml']*1000:.0f}mcg/ml)",
                size=14
            ),
            ft.Text(f"🧪 Fiale usate: {prep['vials_used']}", size=14),
            ft.Text(f"💉 Diluente: {prep['diluent']}", size=14),
            ft.Divider(),
            ft.Text(f"💊 Somministrazioni: {admin_count}", size=14),
            ft.Text(f"📝 Note: {prep.get('notes') or 'N/A'}", size=12, color=ft.Colors.GREY_400),
        ]
        
        # Add wastage information if present
        if prep.get('wastage_ml') and prep['wastage_ml'] > 0:
            content_items.append(ft.Divider())
            content_items.append(ft.Text(f"⚠️ Spreco Totale: {prep['wastage_ml']:.2f} ml", color=ft.Colors.ORANGE_400, weight=ft.FontWeight.BOLD))
            if prep.get('wastage_reason'):
                reason_labels = {
                    'spillage': 'Fuoriuscita',
                    'measurement_error': 'Errore Misurazione',
                    'contamination': 'Contaminazione',
                    'other': 'Altro'
                }
                reason_text = reason_labels.get(prep['wastage_reason'], prep['wastage_reason'])
                content_items.append(ft.Text(f"Motivo: {reason_text}", size=12))
            if prep.get('wastage_notes'):
                content_items.append(ft.Text(f"Note Spreco:", weight=ft.FontWeight.BOLD, size=12))
                content_items.append(ft.Text(prep['wastage_notes'], size=11, italic=True))
        
        # Add wastage history section
        wastage_history = self.app.manager.get_wastage_history(prep_id)
        if wastage_history:
            content_items.append(ft.Divider())
            content_items.append(ft.Text("📊 Storico Wastage", size=16, weight=ft.FontWeight.BOLD))
            
            for record in wastage_history:
                reason_labels = {
                    'spillage': '💧 Fuoriuscita',
                    'measurement_error': '📏 Errore Misurazione',
                    'contamination': '⚠️ Contaminazione',
                    'other': '❓ Altro'
                }
                reason_icon = reason_labels.get(record.get('reason', 'other'), '❓ Altro')
                
                wastage_card = ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Text(f"{record['date']}", size=12, weight=ft.FontWeight.BOLD),
                            ft.Text(f"{record['volume_ml']:.2f} ml", size=12, color=ft.Colors.ORANGE_400),
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Text(reason_icon, size=11, color=ft.Colors.GREY_400),
                        ft.Text(record.get('notes', ''), size=10, italic=True) if record.get('notes') else ft.Container(),
                    ], spacing=2),
                    padding=8,
                    bgcolor=ft.Colors.GREY_900,
                    border_radius=5,
                    margin=ft.margin.only(bottom=5),
                )
                content_items.append(wastage_card)
        
        content = ft.Column(content_items, tight=True, scroll=ft.ScrollMode.AUTO, height=500)
        
        dialog = ft.AlertDialog(
            title=ft.Text(f"Preparazione #{prep_id}"),
            content=content,
            actions=[
                ft.TextButton("Registra Spreco", on_click=lambda e: self._show_wastage_dialog(prep_id, dialog)),
                ft.TextButton("Chiudi", on_click=lambda e: self._close_dialog(dialog)),
            ],
        )
        self._open_dialog(dialog)
    
    def _confirm_delete(self, prep_id):
        """Confirm preparation deletion."""
        prep = self.app.manager.get_preparation_details(prep_id)
        if not prep:
            return
        
        def on_confirm():
            try:
                self.app.manager.soft_delete_preparation(prep_id)
                DialogBuilder.close_dialog(self.app.page)
                self.refresh()
                self.app.show_snackbar(f"✅ Preparazione #{prep_id} eliminata")
            except Exception as ex:
                self.app.show_snackbar(f"❌ Errore: {ex}", error=True)
        
        DialogBuilder.show_confirm_dialog(
            self.app.page,
            "Conferma Eliminazione",
            f"Eliminare la preparazione #{prep_id} dal batch {prep['product_name']}?",
            on_confirm,
        )
    
    def _administer(self, prep_id):
        """Quick administer from preparation."""
        prep = self.app.manager.get_preparation_details(prep_id)
        if not prep or prep['volume_remaining_ml'] <= 0:
            self.app.show_snackbar("Volume esaurito!", error=True)
            return
        
        # Get protocols for dropdown
        protocols = self.app.manager.get_protocols()
        
        fields = [
            Field(
                "dose_ml",
                "Dose (ml)",
                FieldType.NUMBER,
                required=True,
                value="0.25",
                hint_text="Volume da somministrare",
                width=150,
            ),
            Field(
                "administration_date",
                "Data",
                FieldType.DATE,
                value=datetime.now().strftime('%Y-%m-%d'),
                width=150,
            ),
            Field(
                "administration_time",
                "Ora (HH:MM)",
                FieldType.TEXT,
                value=datetime.now().strftime('%H:%M'),
                hint_text="es: 08:30",
                width=150,
            ),
            Field(
                "injection_site",
                "Sito Iniezione",
                FieldType.DROPDOWN,
                value="Addome",
                options=[
                    ("Addome", "Addome"),
                    ("Coscia", "Coscia"),
                    ("Braccio", "Braccio"),
                    ("Gluteo", "Gluteo"),
                ],
                width=200,
            ),
            Field(
                "injection_method",
                "Metodo",
                FieldType.DROPDOWN,
                value="Sottocutanea",
                options=[
                    ("Sottocutanea", "Sottocutanea (SC)"),
                    ("Intramuscolare", "Intramuscolare (IM)"),
                    ("Intradermica", "Intradermica (ID)"),
                ],
                width=200,
            ),
            Field(
                "protocol_id",
                "Protocollo (opzionale)",
                FieldType.DROPDOWN,
                options=[("", "Nessuno")] + [(str(p['id']), p['name']) for p in protocols],
                width=300,
            ),
            Field("notes", "Note", FieldType.TEXTAREA, width=500),
        ]
        
        form_controls = FormBuilder.build_fields(fields)
        
        def on_submit(e):
            values = FormBuilder.get_values(form_controls)
            is_valid, error_msg = FormBuilder.validate_required(
                form_controls,
                ['dose_ml']
            )
            
            if not is_valid:
                self.app.show_snackbar(error_msg, error=True)
                return
            
            try:
                # Combine date and time into datetime
                date_str = values['administration_date'] or datetime.now().strftime('%Y-%m-%d')
                time_str = values['administration_time'] or datetime.now().strftime('%H:%M')
                datetime_str = f"{date_str} {time_str}:00"
                admin_datetime = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S')
                
                admin_id = self.app.manager.add_administration(
                    preparation_id=prep_id,
                    dose_ml=float(values['dose_ml']),
                    administration_datetime=admin_datetime,
                    protocol_id=int(values['protocol_id']) if values['protocol_id'] else None,
                    injection_site=values['injection_site'] if values['injection_site'] else None,
                    injection_method=values['injection_method'] if values['injection_method'] else None,
                    notes=values['notes'] if values['notes'] else None,
                )
                
                self._close_dialog(dialog)
                self.refresh()
                self.app.show_snackbar(f"✅ Somministrazione #{admin_id} registrata da preparazione #{prep_id}!")
                
            except Exception as ex:
                self.app.show_snackbar(f"❌ Errore: {ex}", error=True)
        
        # Create dialog with form fields
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"Somministrazione da Prep #{prep_id}"),
            content=ft.Column(
                [
                    form_controls['protocol_id'],
                    FormBuilder.create_form_row([
                        form_controls['administration_date'],
                        form_controls['administration_time'],
                    ]),
                    form_controls['dose_ml'],
                    FormBuilder.create_form_row([
                        form_controls['injection_site'],
                        form_controls['injection_method'],
                    ]),
                    form_controls['notes'],
                ],
                tight=True,
                scroll=ft.ScrollMode.AUTO,
            ),
            actions=[
                ft.TextButton("Annulla", on_click=lambda e: self._close_dialog(dialog)),
                ft.ElevatedButton("Registra", on_click=lambda e: on_submit(e)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        self._open_dialog(dialog)
    
    def _show_wastage_dialog(self, prep_id, parent_dialog=None):
        """Show dialog to register wastage."""
        prep = self.app.manager.get_preparation_details(prep_id)
        if not prep:
            self._show_snackbar("❌ Preparazione non trovata", error=True)
            return
        
        # Close parent dialog if exists
        if parent_dialog:
            parent_dialog.open = False
            self.app.page.update()
        
        volume_field = ft.TextField(
            label="Volume Sprecato (ml)",
            hint_text=f"Max: {prep['volume_remaining_ml']:.2f} ml",
            keyboard_type=ft.KeyboardType.NUMBER,
            width=200,
        )
        
        reason_dropdown = ft.Dropdown(
            label="Motivo",
            width=300,
            options=[
                ft.dropdown.Option("spillage", "Fuoriuscita / Perdita"),
                ft.dropdown.Option("measurement_error", "Errore di Misurazione"),
                ft.dropdown.Option("contamination", "Contaminazione"),
                ft.dropdown.Option("other", "Altro"),
            ],
            value="spillage",
        )
        
        notes_field = ft.TextField(
            label="Note (opzionale)",
            multiline=True,
            min_lines=2,
            max_lines=4,
            width=400,
        )
        
        def save_wastage(e):
            try:
                # Validation
                if not volume_field.value or volume_field.value.strip() == '':
                    self._show_snackbar("❌ Inserisci il volume sprecato", error=True)
                    return
                
                volume = float(volume_field.value)
                
                if volume <= 0:
                    self._show_snackbar("❌ Volume deve essere > 0", error=True)
                    return
                
                success, message = self.app.manager.record_wastage(
                    prep_id=prep_id,
                    volume_ml=volume,
                    reason=reason_dropdown.value,
                    notes=notes_field.value if notes_field.value else None
                )
                
                if success:
                    self._show_snackbar(f"✅ {message}")
                    self._close_dialog(dialog)
                    self.refresh()
                else:
                    self._show_snackbar(f"❌ {message}", error=True)
                    
            except ValueError:
                self._show_snackbar("❌ Inserisci un numero valido per il volume", error=True)
            except Exception as ex:
                self._show_snackbar(f"❌ Errore: {str(ex)}", error=True)
        
        dialog = ft.AlertDialog(
            title=ft.Text(f"Registra Spreco - Preparazione #{prep_id}"),
            content=ft.Column([
                ft.Text(f"Batch: {prep['product_name']}"),
                ft.Text(f"Volume Rimanente: {prep['volume_remaining_ml']:.2f} ml"),
                ft.Divider(),
                volume_field,
                reason_dropdown,
                notes_field,
            ], tight=True, scroll=ft.ScrollMode.AUTO, height=400),
            actions=[
                ft.TextButton("Annulla", on_click=lambda e: self._close_dialog(dialog)),
                ft.ElevatedButton("Registra", on_click=save_wastage),
            ],
        )
        
        self._open_dialog(dialog)
    
    def _show_snackbar(self, message, error=False):
        """Show snackbar message."""
        self.app.page.snack_bar = ft.SnackBar(
            content=ft.Text(message),
            bgcolor=ft.Colors.RED_400 if error else ft.Colors.GREEN_400,
        )
        self.app.page.snack_bar.open = True
        self.app.page.update()

    def _open_dialog(self, dialog):
        """Open a dialog"""
        self.app.page.overlay.append(dialog)
        dialog.open = True
        self.app.page.update()
    
    def _close_dialog(self, dialog):
        """Close a dialog"""
        dialog.open = False
        self.app.page.update()
