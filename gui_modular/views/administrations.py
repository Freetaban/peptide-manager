"""AdministrationsView - Complete CRUD with advanced pandas filtering."""
import flet as ft
from datetime import datetime, time
try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

from gui_modular.components.data_table import DataTable, Column, Action
from gui_modular.components.forms import FormBuilder, Field, FieldType
from gui_modular.components.dialogs import DialogBuilder


class AdministrationsView(ft.Container):
    """Complete Administrations view (storico somministrazioni) with pandas filtering."""
    
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.expand = True
        self.padding = 20
        
        # Build initial content
        self.content = self._build_content()
    
    def _build_content(self):
        """Build complete administrations view with pandas filters."""
        if not HAS_PANDAS:
            return ft.Column([
                ft.Text("⚠️ pandas non installato", size=20, color=ft.Colors.ORANGE),
                ft.Text("Installa con: pip install pandas", size=14),
            ])
        
        # Load DataFrame
        try:
            df_all = self.app.manager.get_all_administrations_df()
        except Exception as e:
            return ft.Column([
                ft.Text("❌ Errore caricamento dati", size=20, color=ft.Colors.RED),
                ft.Text(str(e), size=12),
            ])
        
        if len(df_all) == 0:
            return ft.Column([
                ft.Text("Storico Somministrazioni", size=32, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                ft.Container(
                    content=ft.Text("Nessuna somministrazione registrata", size=16, color=ft.Colors.GREY_400),
                    padding=50,
                    alignment=ft.alignment.center,
                ),
            ])
        
        # Extract unique values for dropdowns
        unique_peptides = sorted([p for p in df_all['peptide_names'].unique() if p and p != 'N/A'])
        unique_sites = sorted([s for s in df_all['injection_site'].unique() if s])
        unique_methods = sorted([m for m in df_all['injection_method'].unique() if m])
        unique_protocols = sorted([p for p in df_all['protocol_name'].unique() if p and p != 'Nessuno'])
        
        # Filter fields
        search_field = ft.TextField(
            label="Cerca nelle note",
            hint_text="es: dolore, bruciore...",
            width=300,
            prefix_icon=ft.Icons.SEARCH,
        )
        
        date_from_field = ft.TextField(
            label="Data Da",
            hint_text="YYYY-MM-DD",
            width=150,
        )
        
        date_to_field = ft.TextField(
            label="Data A",
            hint_text="YYYY-MM-DD",
            width=150,
        )
        
        peptide_filter = ft.Dropdown(
            label="Peptide",
            hint_text="Tutti",
            width=200,
            options=[ft.dropdown.Option("", "Tutti")] + [ft.dropdown.Option(p, p) for p in unique_peptides],
        )
        
        site_filter = ft.Dropdown(
            label="Sito Iniezione",
            hint_text="Tutti",
            width=200,
            options=[ft.dropdown.Option("", "Tutti")] + [ft.dropdown.Option(s, s) for s in unique_sites],
        )
        
        method_filter = ft.Dropdown(
            label="Metodo",
            hint_text="Tutti",
            width=150,
            options=[ft.dropdown.Option("", "Tutti")] + [ft.dropdown.Option(m, m) for m in unique_methods],
        )
        
        protocol_filter = ft.Dropdown(
            label="Protocollo",
            hint_text="Tutti",
            width=200,
            options=[ft.dropdown.Option("", "Tutti")] + [ft.dropdown.Option(p, p) for p in unique_protocols],
        )
        
        # Container for results (will be updated dynamically)
        results_container = ft.Container()
        
        def apply_filters(e=None):
            """Apply filters to DataFrame and update view."""
            df = df_all.copy()
            
            # Text search filter
            if search_field.value:
                df = df[df['notes'].str.contains(search_field.value, case=False, na=False)]
            
            # Date from filter
            if date_from_field.value:
                try:
                    date_from = pd.to_datetime(date_from_field.value).date()
                    df = df[df['date'] >= date_from]
                except:
                    pass
            
            # Date to filter
            if date_to_field.value:
                try:
                    date_to = pd.to_datetime(date_to_field.value).date()
                    df = df[df['date'] <= date_to]
                except:
                    pass
            
            # Peptide filter
            if peptide_filter.value and peptide_filter.value.strip():
                df = df[df['peptide_names'].str.contains(peptide_filter.value, case=False, na=False)]
            
            # Site filter
            if site_filter.value and site_filter.value.strip():
                df = df[df['injection_site'] == site_filter.value]
            
            # Method filter
            if method_filter.value and method_filter.value.strip():
                df = df[df['injection_method'] == method_filter.value]
            
            # Protocol filter
            if protocol_filter.value and protocol_filter.value.strip():
                df = df[df['protocol_name'] == protocol_filter.value]
            
            # Build statistics
            stats = ft.Container(
                content=ft.Column([
                    ft.Text("📊 Statistiche Filtrate", size=18, weight=ft.FontWeight.BOLD),
                    ft.Divider(),
                    ft.Row([
                        self._stat_card("Somministrazioni", str(len(df)), ft.Icons.MEDICATION, ft.Colors.BLUE_400),
                        self._stat_card("Totale ml", f"{df['dose_ml'].sum():.2f}", ft.Icons.WATER_DROP, ft.Colors.CYAN_400),
                        self._stat_card("Totale mcg", f"{df['dose_mcg'].sum():.0f}", ft.Icons.SCIENCE, ft.Colors.GREEN_400),
                        self._stat_card("Giorni Unici", str(df['date'].nunique()), ft.Icons.CALENDAR_TODAY, ft.Colors.PURPLE_400),
                    ], wrap=True),
                    ft.Row([
                        ft.Text(f"📅 Prima: {df['date'].min()}", size=12, color=ft.Colors.GREY_400),
                        ft.Text(f"📅 Ultima: {df['date'].max()}", size=12, color=ft.Colors.GREY_400),
                        ft.Text(f"💉 Preparazioni: {df['preparation_id'].nunique()}", size=12, color=ft.Colors.GREY_400),
                        ft.Text(f"📋 Protocolli: {df['protocol_name'].nunique()}", size=12, color=ft.Colors.GREY_400),
                    ], spacing=20),
                ]),
                bgcolor=ft.Colors.GREY_900,
                padding=15,
                border_radius=10,
            )
            
            # Build table
            if len(df) == 0:
                table_content = ft.Container(
                    content=ft.Text("Nessun risultato con questi filtri", size=16, color=ft.Colors.GREY_400),
                    padding=50,
                    alignment=ft.alignment.center,
                )
            else:
                rows = []
                for idx, row in df.iterrows():
                    rows.append(
                        ft.DataRow(
                            cells=[
                                ft.DataCell(ft.Text(f"#{row['id']}", size=12)),
                                ft.DataCell(ft.Text(str(row['date']), size=12)),
                                ft.DataCell(ft.Text(str(row['time'])[:5], size=12)),
                                ft.DataCell(ft.Text(str(row['peptide_names'])[:30], size=12)),
                                ft.DataCell(ft.Text(str(row['batch_product'])[:25], size=12)),
                                ft.DataCell(ft.Text(str(row['preparation_display'])[:20], size=12)),
                                ft.DataCell(ft.Text(f"{row['dose_ml']:.2f}", size=12)),
                                ft.DataCell(ft.Text(f"{row['dose_mcg']:.0f}", size=12)),
                                ft.DataCell(ft.Text(str(row['injection_site'])[:15], size=12)),
                                ft.DataCell(ft.Text(str(row['injection_method']), size=12)),
                                ft.DataCell(ft.Text(str(row['protocol_name'])[:20], size=12)),
                                ft.DataCell(
                                    ft.Row([
                                        ft.IconButton(
                                            icon=ft.Icons.VISIBILITY,
                                            tooltip="Dettagli",
                                            on_click=lambda e, admin_id=row['id']: self._show_details(admin_id),
                                            icon_size=18,
                                        ),
                                        ft.IconButton(
                                            icon=ft.Icons.EDIT,
                                            tooltip="Modifica",
                                            on_click=lambda e, admin_id=row['id']: self._show_edit_dialog(admin_id),
                                            disabled=not self.app.edit_mode,
                                            icon_size=18,
                                        ),
                                        ft.IconButton(
                                            icon=ft.Icons.DELETE,
                                            tooltip="Elimina",
                                            on_click=lambda e, admin_id=row['id']: self._confirm_delete(admin_id),
                                            disabled=not self.app.edit_mode,
                                            icon_color=ft.Colors.RED_400,
                                            icon_size=18,
                                        ),
                                    ], spacing=0),
                                ),
                            ],
                        )
                    )
                
                table_content = ft.DataTable(
                    columns=[
                        ft.DataColumn(ft.Text("ID", size=12)),
                        ft.DataColumn(ft.Text("Data", size=12)),
                        ft.DataColumn(ft.Text("Ora", size=12)),
                        ft.DataColumn(ft.Text("Peptidi", size=12)),
                        ft.DataColumn(ft.Text("Batch", size=12)),
                        ft.DataColumn(ft.Text("Prep", size=12)),
                        ft.DataColumn(ft.Text("ml", size=12)),
                        ft.DataColumn(ft.Text("mcg", size=12)),
                        ft.DataColumn(ft.Text("Sito", size=12)),
                        ft.DataColumn(ft.Text("Metodo", size=12)),
                        ft.DataColumn(ft.Text("Protocollo", size=12)),
                        ft.DataColumn(ft.Text("Azioni", size=12)),
                    ],
                    rows=rows,
                )
            
            # Update results container
            results_container.content = ft.Column([
                stats,
                ft.Container(height=10),
                ft.Container(
                    content=table_content,
                    border=ft.border.all(1, ft.Colors.GREY_800),
                    border_radius=10,
                    padding=10,
                ),
            ])
            self.app.page.update()
        
        # Wire up filter events
        search_field.on_change = apply_filters
        date_from_field.on_change = apply_filters
        date_to_field.on_change = apply_filters
        peptide_filter.on_change = apply_filters
        site_filter.on_change = apply_filters
        method_filter.on_change = apply_filters
        protocol_filter.on_change = apply_filters
        
        # Initial filter application
        apply_filters()
        
        # Build final content
        return ft.Column([
            ft.Text("Storico Somministrazioni", size=32, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            
            # Filters
            ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("🔍 Filtri", size=18, weight=ft.FontWeight.BOLD),
                        ft.Divider(),
                        ft.Row([
                            search_field,
                            date_from_field,
                            date_to_field,
                        ], wrap=True, spacing=10),
                        ft.Row([
                            peptide_filter,
                            site_filter,
                            method_filter,
                            protocol_filter,
                        ], wrap=True, spacing=10),
                    ]),
                    padding=15,
                ),
            ),
            
            ft.Container(height=10),
            
            # Results (stats + table)
            results_container,
        ], scroll=ft.ScrollMode.AUTO)
    
    def _stat_card(self, title, value, icon, color):
        """Create stat card."""
        return ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon(icon, color=color, size=30),
                        ft.Column([
                            ft.Text(title, size=12, color=ft.Colors.GREY_400),
                            ft.Text(value, size=20, weight=ft.FontWeight.BOLD),
                        ], spacing=0),
                    ], alignment=ft.MainAxisAlignment.START),
                ]),
                padding=15,
                width=250,
            ),
        )
    
    def refresh(self):
        """Refresh view content."""
        self.content = self._build_content()
        self.update()
    
    def _show_add_dialog(self, e):
        """Show add administration dialog."""
        # Get active preparations
        preparations = self.app.manager.get_preparations(only_active=True)
        active_preps = [p for p in preparations if p['volume_remaining_ml'] > 0]
        
        if not active_preps:
            self.app.show_snackbar("Nessuna preparazione attiva con volume disponibile!", error=True)
            return
        
        # Get protocols
        protocols = self.app.manager.get_protocols()
        
        fields = [
            Field(
                "preparation_id",
                "Preparazione",
                FieldType.DROPDOWN,
                required=True,
                options=[
                    (str(p['id']), f"#{p['id']} - {p['batch_product']} ({p['volume_remaining_ml']:.1f}ml rimasti)")
                    for p in active_preps
                ],
                width=500,
            ),
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
                ['preparation_id', 'dose_ml']
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
                    preparation_id=int(values['preparation_id']),
                    dose_ml=float(values['dose_ml']),
                    administration_datetime=admin_datetime,
                    protocol_id=int(values['protocol_id']) if values['protocol_id'] else None,
                    injection_site=values['injection_site'] if values['injection_site'] else None,
                    injection_method=values['injection_method'] if values['injection_method'] else None,
                    notes=values['notes'] if values['notes'] else None,
                )
                
                DialogBuilder.close_dialog(self.app.page)
                self.refresh()
                self.app.show_snackbar(f"✅ Somministrazione #{admin_id} registrata con successo!")
                
            except Exception as ex:
                self.app.show_snackbar(f"❌ Errore: {ex}", error=True)
        
        DialogBuilder.show_form_dialog(
            self.app.page,
            "Nuova Somministrazione",
            list(form_controls.values()),  # Convert dict to list
            on_submit,
            height=600,
        )

    def _assign_to_cycle_dialog(self, admin_id: int):
        """Dialog per assegnare una singola somministrazione a un ciclo esistente."""
        cycles = self.app.manager.get_cycles(active_only=False)
        options = [(str(c['id']), f"#{c['id']} - {c.get('name')}") for c in cycles]

        fields = [
            Field('cycle_id', 'Cycle', FieldType.DROPDOWN, required=True, options=options, width=400),
        ]

        form_controls = FormBuilder.build_fields(fields)

        def on_submit(ev=None):
            values = FormBuilder.get_values(form_controls)
            is_valid, err = FormBuilder.validate_required(form_controls, ['cycle_id'])
            if not is_valid:
                self.app.show_snackbar(err, error=True)
                return

            try:
                cycle_id = int(values['cycle_id'])
                count = self.app.manager.assign_administrations_to_cycle([admin_id], cycle_id)
                DialogBuilder.close_dialog(self.app.page)
                self.refresh()
                if count > 0:
                    self.app.show_snackbar(f"✓ Somministrazione assegnata al ciclo #{cycle_id}")
                else:
                    self.app.show_snackbar(f"⚠️ Somministrazione già assegnata ad un altro ciclo o nessuna modifica eseguita", error=True)
            except Exception as ex:
                self.app.show_snackbar(f"❌ Errore: {ex}", error=True)

        DialogBuilder.show_form_dialog(self.app.page, 'Assegna a Ciclo', list(form_controls.values()), on_submit, height=260)
    
    def _show_edit_dialog(self, admin_id):
        """Show edit administration dialog."""
        # Get administration with details
        admins = self.app.manager.get_administrations()
        admin = next((a for a in admins if a['id'] == admin_id), None)
        if not admin:
            return
        
        # Split datetime
        admin_datetime = admin.get('administration_datetime', '')
        if admin_datetime and ' ' in admin_datetime:
            date_part, time_part = admin_datetime.split(' ', 1)
        else:
            date_part = datetime.now().strftime('%Y-%m-%d')
            time_part = datetime.now().strftime('%H:%M:%S')
        
        # Get all preparations and protocols
        preparations = self.app.manager.get_preparations(only_active=False)
        protocols = self.app.manager.get_protocols()
        
        fields = [
            Field(
                "preparation_id",
                "Preparazione",
                FieldType.DROPDOWN,
                value=str(admin['preparation_id']),
                options=[
                    (str(p['id']), f"#{p['id']} - {p['batch_product']}")
                    for p in preparations
                ],
                width=500,
            ),
            Field("dose_ml", "Dose (ml)", FieldType.NUMBER, value=str(admin['dose_ml']), width=150),
            Field("administration_date", "Data", FieldType.DATE, value=date_part, width=150),
            Field("administration_time", "Ora (HH:MM)", FieldType.TEXT, value=time_part[:5], width=150),
            Field(
                "injection_site",
                "Sito",
                FieldType.DROPDOWN,
                value=admin.get('injection_site', 'Addome'),
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
                value=admin.get('injection_method', 'Sottocutanea'),
                options=[
                    ("Sottocutanea", "Sottocutanea"),
                    ("Intramuscolare", "Intramuscolare"),
                    ("Intradermica", "Intradermica"),
                ],
                width=200,
            ),
            Field(
                "protocol_id",
                "Protocollo",
                FieldType.DROPDOWN,
                value=str(admin['protocol_id']) if admin.get('protocol_id') else "",
                options=[("", "Nessuno")] + [(str(p['id']), p['name']) for p in protocols],
                width=300,
            ),
            Field("notes", "Note", FieldType.TEXTAREA, value=admin.get('notes', ''), width=500),
        ]
        
        form_controls = FormBuilder.build_fields(fields)
        
        def on_submit(e):
            values = FormBuilder.get_values(form_controls)
            
            try:
                changes = {}
                
                if int(values['preparation_id']) != admin['preparation_id']:
                    changes['preparation_id'] = int(values['preparation_id'])
                if float(values['dose_ml']) != admin['dose_ml']:
                    changes['dose_ml'] = float(values['dose_ml'])
                
                # Combine date and time for datetime comparison
                new_datetime_str = f"{values['administration_date']} {values['administration_time']}:00"
                if new_datetime_str != admin['administration_datetime']:
                    changes['administration_datetime'] = datetime.strptime(new_datetime_str, '%Y-%m-%d %H:%M:%S')
                
                if values['injection_site'] != (admin.get('injection_site') or ''):
                    changes['injection_site'] = values['injection_site'] if values['injection_site'] else None
                if values['injection_method'] != (admin.get('injection_method') or ''):
                    changes['injection_method'] = values['injection_method'] if values['injection_method'] else None
                
                new_protocol = int(values['protocol_id']) if values['protocol_id'] else None
                if new_protocol != admin.get('protocol_id'):
                    changes['protocol_id'] = new_protocol
                
                if values['notes'] != (admin.get('notes') or ''):
                    changes['notes'] = values['notes'] if values['notes'] else None
                
                if changes:
                    self.app.manager.update_administration(admin_id, **changes)
                    DialogBuilder.close_dialog(self.app.page)
                    self.refresh()
                    self.app.show_snackbar(f"✅ Somministrazione #{admin_id} aggiornata!")
                else:
                    self.app.show_snackbar("Nessuna modifica da salvare")
                    
            except Exception as ex:
                self.app.show_snackbar(f"❌ Errore: {ex}", error=True)
        
        DialogBuilder.show_form_dialog(
            self.app.page,
            f"Modifica Somministrazione #{admin_id}",
            list(form_controls.values()),  # Convert dict to list
            on_submit,
            height=600,
        )
    
    def _show_details(self, admin_id):
        """Show administration details dialog."""
        # Get administration with details
        admins = self.app.manager.get_administrations()
        admin = next((a for a in admins if a['id'] == admin_id), None)
        if not admin:
            return
        
        # Split datetime
        admin_datetime = admin.get('administration_datetime', '')
        if admin_datetime and ' ' in admin_datetime:
            date_part, time_part = admin_datetime.split(' ', 1)
        else:
            date_part = 'N/A'
            time_part = 'N/A'
        
        # Get preparation info
        prep = None
        if admin.get('preparation_id'):
            preps = self.app.manager.get_preparations(only_active=False)
            prep = next((p for p in preps if p['id'] == admin['preparation_id']), None)
        
        protocol_name = "Nessuno"
        if admin.get('protocol_id'):
            protocols = self.app.manager.get_protocols()
            protocol = next((p for p in protocols if p['id'] == admin['protocol_id']), None)
            if protocol:
                protocol_name = protocol['name']
        
        # Calculate dose in mcg
        dose_mcg = 0
        if prep and admin.get('dose_ml'):
            dose_mcg = admin['dose_ml'] * prep.get('concentration_mcg_ml', 0)
        
        content = ft.Column([
            ft.Text(f"💉 Somministrazione #{admin_id}", size=16, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            ft.Text(f"📅 Data: {date_part} alle {time_part[:5]}", size=14),
            ft.Text(f"📦 Preparazione: #{admin['preparation_id']} - {prep['batch_product'] if prep else 'N/A'}", size=14),
            ft.Divider(),
            ft.Text(f"💧 Dose: {admin['dose_ml']:.2f} ml ({dose_mcg:.0f} mcg)", size=14),
            ft.Text(f"📍 Sito: {admin.get('injection_site', 'N/A')}", size=14),
            ft.Text(f"💉 Metodo: {admin.get('injection_method', 'N/A')}", size=14),
            ft.Divider(),
            ft.Text(f"📋 Protocollo: {protocol_name}", size=14),
            ft.Text(f"📝 Note: {admin.get('notes') or 'Nessuna nota'}", size=12, color=ft.Colors.GREY_400),
        ], tight=True, spacing=8)
        
        DialogBuilder.show_info_dialog(
            self.app.page,
            f"Somministrazione #{admin_id}",
            content,
        )
    
    def _confirm_delete(self, admin_id):
        """Confirm administration deletion."""
        # Get administration
        admins = self.app.manager.get_administrations()
        admin = next((a for a in admins if a['id'] == admin_id), None)
        if not admin:
            return
        
        # Split datetime for display
        admin_datetime = admin.get('administration_datetime', '')
        if admin_datetime and ' ' in admin_datetime:
            date_part, _ = admin_datetime.split(' ', 1)
        else:
            date_part = 'N/A'
        
        def on_confirm():
            try:
                self.app.manager.soft_delete_administration(admin_id)
                DialogBuilder.close_dialog(self.app.page)
                self.refresh()
                self.app.show_snackbar(f"✅ Somministrazione #{admin_id} eliminata")
            except Exception as ex:
                self.app.show_snackbar(f"❌ Errore: {ex}", error=True)
        
        DialogBuilder.show_confirm_dialog(
            self.app.page,
            "Conferma Eliminazione",
            f"Eliminare la somministrazione del {date_part}?",
            on_confirm,
        )

