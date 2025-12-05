"""ProtocolsView - Complete CRUD for administration protocols."""
import flet as ft
from gui_modular.components.data_table import DataTable, Column, Action
from gui_modular.components.forms import FormBuilder, Field, FieldType
from gui_modular.components.dialogs import DialogBuilder


class ProtocolsView(ft.Container):
    """Complete Protocols view for managing administration schedules."""
    
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.expand = True
        self.padding = 20
        
        # Build initial content
        self.content = self._build_content()
    
    def _build_content(self):
        """Build complete protocols view."""
        protocols = self.app.manager.get_protocols()
        
        # Build data table
        data_table = DataTable(
            columns=[
                Column("id", "ID", width=60),
                Column("name", "Nome", width=250),
                Column("frequency", "Frequenza", width=180),
                Column("administrations", "Somm.", width=100),
            ],
            actions=[
                Action(
                    "visibility",
                    lambda protocol_id: self._show_details(protocol_id),
                    "Dettagli",
                ),
                Action(
                    "edit",
                    lambda protocol_id: self._show_edit_dialog(protocol_id),
                    "Modifica",
                    enabled_when=lambda row: self.app.edit_mode,
                ),
                Action(
                    "delete",
                    lambda protocol_id: self._confirm_delete(protocol_id),
                    "Elimina",
                    color=ft.Colors.RED_400,
                    enabled_when=lambda row: self.app.edit_mode,
                ),
            ],
            app=self.app,
        )
        
        # Prepare data
        table_data = []
        for protocol in protocols:
            # Get administrations count
            cursor = self.app.manager.conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM administrations WHERE protocol_id = ?', (protocol['id'],))
            admin_count = cursor.fetchone()[0]
            
            # Build frequency description from protocol fields
            freq_parts = []
            if protocol.get('frequency_per_day', 1) > 1:
                freq_parts.append(f"{protocol['frequency_per_day']}x/giorno")
            else:
                freq_parts.append("1x/giorno")
            
            if protocol.get('days_on') and protocol.get('days_off', 0) > 0:
                freq_parts.append(f"{protocol['days_on']}gg ON, {protocol['days_off']}gg OFF")
            elif protocol.get('days_on'):
                freq_parts.append(f"{protocol['days_on']}gg ON")
            
            if protocol.get('cycle_duration_weeks'):
                freq_parts.append(f"ciclo {protocol['cycle_duration_weeks']}sett")
            
            frequency_desc = ", ".join(freq_parts)
            
            table_data.append({
                'id': f"#{protocol['id']}",
                'name': protocol['name'][:40],
                'frequency': frequency_desc[:30],
                'administrations': str(admin_count),
                '_id': protocol['id'],
            })
        
        toolbar = data_table.build_toolbar(
            "Protocolli",
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
        """Show add protocol dialog."""
        fields = [
            Field("name", "Nome Protocollo", FieldType.TEXT, required=True, width=400),
            Field(
                "dose_ml",
                "Dose per somministrazione (ml)",
                FieldType.NUMBER,
                required=True,
                value="0.25",
                hint_text="Volume per ogni iniezione",
                width=200,
            ),
            Field(
                "frequency_per_day",
                "Frequenza al giorno",
                FieldType.NUMBER,
                value="1",
                hint_text="Quante volte al giorno",
                width=150,
            ),
            Field(
                "days_on",
                "Giorni ON",
                FieldType.NUMBER,
                hint_text="Giorni consecutivi di somministrazione (opzionale)",
                width=150,
            ),
            Field(
                "days_off",
                "Giorni OFF",
                FieldType.NUMBER,
                value="0",
                hint_text="Giorni di pausa tra i cicli",
                width=150,
            ),
            Field(
                "cycle_duration_weeks",
                "Durata ciclo (settimane)",
                FieldType.NUMBER,
                hint_text="Durata totale del ciclo (opzionale)",
                width=150,
            ),
            Field(
                "description",
                "Descrizione",
                FieldType.TEXTAREA,
                hint_text="Informazioni sul protocollo, obiettivi, ecc.",
                width=500,
            ),
            Field(
                "notes",
                "Note",
                FieldType.TEXTAREA,
                hint_text="Precauzioni, controindicazioni, effetti collaterali",
                width=500,
            ),
        ]
        
        form_controls = FormBuilder.build_fields(fields)
        
        def on_submit(e):
            values = FormBuilder.get_values(form_controls)
            is_valid, error_msg = FormBuilder.validate_required(
                form_controls,
                ['name', 'dose_ml']
            )
            
            if not is_valid:
                self.app.show_snackbar(error_msg, error=True)
                return
            
            try:
                protocol_id = self.app.manager.add_protocol(
                    name=values['name'],
                    dose_ml=float(values['dose_ml']),
                    frequency_per_day=int(values['frequency_per_day']) if values['frequency_per_day'] else 1,
                    days_on=int(values['days_on']) if values['days_on'] else None,
                    days_off=int(values['days_off']) if values['days_off'] else 0,
                    cycle_duration_weeks=int(values['cycle_duration_weeks']) if values['cycle_duration_weeks'] else None,
                    description=values['description'] if values['description'] else None,
                    notes=values['notes'] if values['notes'] else None,
                )
                
                DialogBuilder.close_dialog(self.app.page)
                self.refresh()
                self.app.show_snackbar(f"✅ Protocollo '{values['name']}' creato con successo!")
                
            except Exception as ex:
                self.app.show_snackbar(f"❌ Errore: {ex}", error=True)
        
        DialogBuilder.show_form_dialog(
            self.app.page,
            "Nuovo Protocollo",
            list(form_controls.values()),  # Convert dict to list
            on_submit,
            height=600,
        )
    
    def _show_edit_dialog(self, protocol_id):
        """Show edit protocol dialog."""
        protocol = self.app.manager.get_protocol_details(protocol_id)
        if not protocol:
            return
        
        fields = [
            Field("name", "Nome Protocollo", FieldType.TEXT, value=protocol['name'], required=True, width=400),
            Field(
                "dose_ml",
                "Dose (ml)",
                FieldType.NUMBER,
                value=str(protocol['dose_ml']),
                required=True,
                width=200,
            ),
            Field(
                "frequency_per_day",
                "Frequenza/giorno",
                FieldType.NUMBER,
                value=str(protocol.get('frequency_per_day', 1)),
                width=150,
            ),
            Field(
                "days_on",
                "Giorni ON",
                FieldType.NUMBER,
                value=str(protocol['days_on']) if protocol.get('days_on') else "",
                width=150,
            ),
            Field(
                "days_off",
                "Giorni OFF",
                FieldType.NUMBER,
                value=str(protocol.get('days_off', 0)),
                width=150,
            ),
            Field(
                "cycle_duration_weeks",
                "Durata ciclo (sett)",
                FieldType.NUMBER,
                value=str(protocol['cycle_duration_weeks']) if protocol.get('cycle_duration_weeks') else "",
                width=150,
            ),
            Field(
                "description",
                "Descrizione",
                FieldType.TEXTAREA,
                value=protocol.get('description', ''),
                width=500,
            ),
            Field(
                "notes",
                "Note",
                FieldType.TEXTAREA,
                value=protocol.get('notes', ''),
                width=500,
            ),
        ]
        
        form_controls = FormBuilder.build_fields(fields)
        
        def on_submit(e):
            values = FormBuilder.get_values(form_controls)
            
            try:
                changes = {}
                
                if values['name'] != protocol['name']:
                    changes['name'] = values['name']
                if float(values['dose_ml']) != float(protocol['dose_ml']):
                    changes['dose_ml'] = float(values['dose_ml'])
                if int(values['frequency_per_day']) != protocol.get('frequency_per_day', 1):
                    changes['frequency_per_day'] = int(values['frequency_per_day'])
                
                new_days_on = int(values['days_on']) if values['days_on'] else None
                if new_days_on != protocol.get('days_on'):
                    changes['days_on'] = new_days_on
                
                if int(values['days_off']) != protocol.get('days_off', 0):
                    changes['days_off'] = int(values['days_off'])
                
                new_cycle = int(values['cycle_duration_weeks']) if values['cycle_duration_weeks'] else None
                if new_cycle != protocol.get('cycle_duration_weeks'):
                    changes['cycle_duration_weeks'] = new_cycle
                
                if values['description'] != (protocol.get('description') or ''):
                    changes['description'] = values['description'] if values['description'] else None
                
                if values['notes'] != (protocol.get('notes') or ''):
                    changes['notes'] = values['notes'] if values['notes'] else None
                
                if changes:
                    self.app.manager.update_protocol(protocol_id, **changes)
                    DialogBuilder.close_dialog(self.app.page)
                    self.refresh()
                    self.app.show_snackbar(f"✅ Protocollo #{protocol_id} aggiornato!")
                else:
                    self.app.show_snackbar("Nessuna modifica da salvare")
                    
            except Exception as ex:
                self.app.show_snackbar(f"❌ Errore: {ex}", error=True)
        
        DialogBuilder.show_form_dialog(
            self.app.page,
            f"Modifica Protocollo #{protocol_id}",
            list(form_controls.values()),  # Convert dict to list
            on_submit,
            height=600,
        )
    
    def _show_details(self, protocol_id):
        """Show protocol details dialog."""
        protocol = self.app.manager.get_protocol_details(protocol_id)
        if not protocol:
            return
        
        # Get administrations count and stats
        cursor = self.app.manager.conn.cursor()
        cursor.execute('''
            SELECT COUNT(*), MIN(administration_datetime), MAX(administration_datetime)
            FROM administrations WHERE protocol_id = ?
        ''', (protocol_id,))
        count, first_date, last_date = cursor.fetchone()
        
        # Build frequency description
        freq_parts = []
        if protocol.get('frequency_per_day', 1) > 1:
            freq_parts.append(f"{protocol['frequency_per_day']} volte al giorno")
        else:
            freq_parts.append("Una volta al giorno")
        
        if protocol.get('days_on') and protocol.get('days_off', 0) > 0:
            freq_parts.append(f"{protocol['days_on']} giorni ON, {protocol['days_off']} giorni OFF")
        elif protocol.get('days_on'):
            freq_parts.append(f"{protocol['days_on']} giorni consecutivi")
        
        if protocol.get('cycle_duration_weeks'):
            freq_parts.append(f"Ciclo di {protocol['cycle_duration_weeks']} settimane")
        
        frequency_text = " • ".join(freq_parts)
        
        content = ft.Column([
            ft.Text(f"📋 Nome: {protocol['name']}", size=16, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            ft.Text(f"💉 Dose: {protocol['dose_ml']} ml per somministrazione", size=14),
            ft.Text(f"⏱️ Frequenza: {frequency_text}", size=14),
            ft.Divider(),
            ft.Text("📊 Statistiche:", size=14, weight=ft.FontWeight.BOLD),
            ft.Text(f"   Somministrazioni totali: {count or 0}", size=13),
            ft.Text(f"   Prima: {first_date or 'N/A'}", size=13, color=ft.Colors.GREY_400),
            ft.Text(f"   Ultima: {last_date or 'N/A'}", size=13, color=ft.Colors.GREY_400),
            ft.Divider(),
            ft.Text(f"📄 Descrizione:", size=14, weight=ft.FontWeight.BOLD),
            ft.Text(protocol.get('description') or 'Nessuna descrizione', size=12, color=ft.Colors.GREY_400),
            ft.Divider(),
            ft.Text(f"📝 Note:", size=14, weight=ft.FontWeight.BOLD),
            ft.Text(protocol.get('notes') or 'Nessuna nota', size=12, color=ft.Colors.GREY_400),
        ], tight=True, spacing=8)
        
        DialogBuilder.show_info_dialog(
            self.app.page,
            f"Protocollo #{protocol_id}",
            content,
        )
    
    def _confirm_delete(self, protocol_id):
        """Confirm protocol deletion."""
        protocol = self.app.manager.get_protocol_details(protocol_id)
        if not protocol:
            return
        
        # Check if protocol has administrations
        cursor = self.app.manager.conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM administrations WHERE protocol_id = ?', (protocol_id,))
        admin_count = cursor.fetchone()[0]
        
        message = f"Eliminare il protocollo '{protocol['name']}'?"
        if admin_count > 0:
            message += f"\n\nAttenzione: Questo protocollo ha {admin_count} somministrazioni associate."
        
        def on_confirm():
            try:
                self.app.manager.soft_delete_protocol(protocol_id)
                DialogBuilder.close_dialog(self.app.page)
                self.refresh()
                self.app.show_snackbar(f"✅ Protocollo '{protocol['name']}' eliminato")
            except Exception as ex:
                self.app.show_snackbar(f"❌ Errore: {ex}", error=True)
        
        DialogBuilder.show_confirm_dialog(
            self.app.page,
            "Conferma Eliminazione",
            message,
            on_confirm,
        )

