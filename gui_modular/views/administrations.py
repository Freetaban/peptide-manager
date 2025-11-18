"""AdministrationsView - Complete CRUD with advanced filtering."""
import flet as ft
from datetime import datetime, time
from gui_modular.components.data_table import DataTable, Column, Action
from gui_modular.components.forms import FormBuilder, Field, FieldType
from gui_modular.components.dialogs import DialogBuilder


class AdministrationsView(ft.Container):
    """Complete Administrations view (storico somministrazioni)."""
    
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.expand = True
        self.padding = 20
        
        # Build initial content
        self.content = self._build_content()
    
    def _build_content(self):
        """Build complete administrations view with filters."""
        administrations = self.app.manager.get_administrations()
        
        # Build data table
        data_table = DataTable(
            columns=[
                Column("id", "ID", width=50),
                Column("date", "Data", width=100),
                Column("time", "Ora", width=70),
                Column("preparation", "Preparazione", width=200),
                Column("dose_ml", "ml", width=70),
                Column("dose_mcg", "mcg", width=90),
                Column("site", "Sito", width=120),
                Column("protocol", "Protocollo", width=150),
            ],
            actions=[
                Action(
                    "visibility",
                    lambda admin_id: self._show_details(admin_id),
                    "Dettagli",
                ),
                    Action(
                        "link",
                        lambda admin_id: self._assign_to_cycle_dialog(admin_id),
                        "Assegna a Ciclo",
                        enabled_when=lambda row: self.app.edit_mode,
                    ),
                Action(
                    "edit",
                    lambda admin_id: self._show_edit_dialog(admin_id),
                    "Modifica",
                    enabled_when=lambda row: self.app.edit_mode,
                ),
                Action(
                    "delete",
                    lambda admin_id: self._confirm_delete(admin_id),
                    "Elimina",
                    color=ft.Colors.RED_400,
                    enabled_when=lambda row: self.app.edit_mode,
                ),
            ],
            app=self.app,
        )
        
        # Prepare data
        table_data = []
        for admin in administrations:
            # Get preparation and protocol details
            prep = self.app.manager.get_preparation_details(admin['preparation_id'])
            protocol_name = "Nessuno"
            if admin.get('protocol_id'):
                protocol = self.app.manager.get_protocol_details(admin['protocol_id'])
                if protocol:
                    protocol_name = protocol['name']
            
            # Split administration_datetime into date and time
            admin_datetime = admin.get('administration_datetime', '')
            if admin_datetime and ' ' in admin_datetime:
                date_part, time_part = admin_datetime.split(' ', 1)
            else:
                date_part = admin_datetime or 'N/A'
                time_part = ''
            
            # Calculate dose in mcg from ml and concentration
            dose_mcg = 0
            if prep and admin.get('dose_ml'):
                dose_mcg = admin['dose_ml'] * prep.get('concentration_mcg_ml', 0)
            
            table_data.append({
                'id': f"#{admin['id']}",
                'date': date_part,
                'time': time_part[:5] if time_part else '',
                'preparation': f"Prep #{admin['preparation_id']} - {prep['product_name'][:25]}" if prep else f"Prep #{admin['preparation_id']}",
                'dose_ml': f"{admin['dose_ml']:.2f}",
                'dose_mcg': f"{dose_mcg:.0f}",
                'site': admin['injection_site'][:15] if admin['injection_site'] else 'N/A',
                'protocol': protocol_name[:20],
                '_id': admin['id'],
            })
        
        toolbar = ft.Row([
            ft.Text("Storico Somministrazioni", size=32, weight=ft.FontWeight.BOLD),
            ft.Container(expand=True),
            ft.ElevatedButton(
                "Nuova Somministrazione",
                icon=ft.Icons.ADD,
                on_click=self._show_add_dialog,
            ),
        ])
        
        table = data_table.build(table_data)
        
        # Statistics card - calculate dose_mcg for each administration
        total_administrations = len(administrations)
        total_ml = sum(a['dose_ml'] for a in administrations)
        
        # Calculate total mcg from preparations
        total_mcg = 0
        for admin in administrations:
            prep = self.app.manager.get_preparation_details(admin['preparation_id'])
            if prep and admin.get('dose_ml'):
                total_mcg += admin['dose_ml'] * prep.get('concentration_mcg_ml', 0)
        
        stats = ft.Card(
            content=ft.Container(
                content=ft.Row([
                    ft.Column([
                        ft.Text("Somministrazioni", size=12, color=ft.Colors.GREY_400),
                        ft.Text(str(total_administrations), size=20, weight=ft.FontWeight.BOLD),
                    ], spacing=2),
                    ft.VerticalDivider(),
                    ft.Column([
                        ft.Text("Totale ml", size=12, color=ft.Colors.GREY_400),
                        ft.Text(f"{total_ml:.1f}", size=20, weight=ft.FontWeight.BOLD),
                    ], spacing=2),
                    ft.VerticalDivider(),
                    ft.Column([
                        ft.Text("Totale mcg", size=12, color=ft.Colors.GREY_400),
                        ft.Text(f"{total_mcg:.0f}", size=20, weight=ft.FontWeight.BOLD),
                    ], spacing=2),
                ], alignment=ft.MainAxisAlignment.SPACE_AROUND),
                padding=15,
            ),
        )
        
        return ft.Column([
            toolbar,
            ft.Divider(),
            stats,
            ft.Container(height=10),
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

