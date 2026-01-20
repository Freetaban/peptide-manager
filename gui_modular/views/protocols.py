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
        """Show add protocol dialog with peptide selection."""
        # Lista peptidi disponibili
        available_peptides = self.app.manager.get_peptides()
        
        # Form fields base
        name_field = ft.TextField(
            label="Nome Protocollo",
            hint_text="Es: GLOW, Wolverine, Sleep Support",
            width=500,
        )
        
        frequency_field = ft.TextField(
            label="Frequenza al giorno",
            value="1",
            hint_text="1, 2 o 3 volte al giorno",
            width=150,
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        
        days_on_field = ft.TextField(
            label="Giorni ON",
            hint_text="Giorni consecutivi (es: 7)",
            width=150,
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        
        days_off_field = ft.TextField(
            label="Giorni OFF",
            value="0",
            hint_text="Giorni di pausa (es: 0)",
            width=150,
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        
        cycle_weeks_field = ft.TextField(
            label="Durata ciclo (settimane)",
            hint_text="Es: 24 settimane (opzionale)",
            width=200,
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        
        description_field = ft.TextField(
            label="Descrizione",
            hint_text="Obiettivi, indicazioni, ecc.",
            multiline=True,
            min_lines=2,
            max_lines=3,
            width=500,
        )
        
        notes_field = ft.TextField(
            label="Note",
            hint_text="Precauzioni, effetti collaterali, ecc.",
            multiline=True,
            min_lines=2,
            max_lines=3,
            width=500,
        )
        
        # Peptide selection
        selected_peptides = []  # Lista di {peptide_id, peptide_name, dose_mcg_field}
        peptides_container = ft.Column([], spacing=10)
        
        def add_peptide_row(peptide_id=None, peptide_name=None, dose_mcg=None):
            """Aggiunge una riga per selezionare peptide + dosaggio"""
            # Dropdown per scegliere peptide
            peptide_dropdown = ft.Dropdown(
                label="Peptide",
                options=[ft.dropdown.Option(key=str(p['id']), text=p['name']) for p in available_peptides],
                value=str(peptide_id) if peptide_id else None,
                width=250,
            )
            
            # Campo dosaggio
            dose_field = ft.TextField(
                label="Dosaggio (mcg/giorno)",
                value=str(dose_mcg) if dose_mcg else "",
                hint_text="Es: 250, 1000, 5000",
                width=180,
                keyboard_type=ft.KeyboardType.NUMBER,
            )
            
            # Label per dose per somministrazione (calcolata dinamicamente)
            dose_per_admin_label = ft.Text(
                "",
                size=11,
                color=ft.Colors.BLUE_300,
                italic=True,
            )
            
            def update_dose_hint(e=None):
                """Aggiorna l'hint con la dose per somministrazione"""
                try:
                    freq = int(frequency_field.value) if frequency_field.value else 1
                    dose = float(dose_field.value) if dose_field.value else 0
                    if dose > 0 and freq > 0:
                        dose_per_admin = dose / freq
                        dose_per_admin_label.value = f"→ {dose_per_admin:.1f} mcg per somministrazione"
                    else:
                        dose_per_admin_label.value = ""
                except (ValueError, ZeroDivisionError):
                    dose_per_admin_label.value = ""
                dose_per_admin_label.update()
            
            # Aggiorna hint quando cambiano dose o frequenza
            dose_field.on_change = update_dose_hint
            frequency_field.on_change = lambda e: [
                update_dose_hint(),
                # Propaga l'update a tutte le righe peptidi
                [update_dose_hint() for row in selected_peptides]
            ]
            
            # Pulsante rimuovi
            def remove_row(e):
                peptides_container.controls.remove(row_container)
                selected_peptides.remove(row_data)
                peptides_container.update()
            
            remove_btn = ft.IconButton(
                icon=ft.Icons.DELETE,
                icon_color=ft.Colors.RED_400,
                tooltip="Rimuovi peptide",
                on_click=remove_row,
            )
            
            # Container con row e label hint
            row_container = ft.Column([
                ft.Row([
                    peptide_dropdown,
                    dose_field,
                    remove_btn,
                ], spacing=10),
                ft.Container(
                    content=dose_per_admin_label,
                    padding=ft.padding.only(left=10, top=2),
                )
            ], spacing=2)
            
            row_data = {
                'row_container': row_container,
                'peptide_dropdown': peptide_dropdown,
                'dose_field': dose_field,
                'update_hint': update_dose_hint,
            }
            
            selected_peptides.append(row_data)
            peptides_container.controls.append(row_container)
            return row_container
        
        def add_peptide_click(e):
            add_peptide_row()
            peptides_container.update()
        
        add_peptide_btn = ft.OutlinedButton(
            "➕ Aggiungi Peptide",
            on_click=add_peptide_click,
            icon=ft.Icons.ADD,
        )
        
        # Aggiungi almeno una riga iniziale
        add_peptide_row()
        
        form_content = ft.Column([
            ft.Text("Informazioni Base", size=16, weight=ft.FontWeight.BOLD),
            ft.Row([name_field]),
            ft.Row([frequency_field, days_on_field, days_off_field]),
            ft.Row([cycle_weeks_field]),
            
            ft.Divider(height=20),
            ft.Text("Peptidi e Dosaggi", size=16, weight=ft.FontWeight.BOLD),
            ft.Text(
                "Seleziona i peptidi con dosaggio GIORNALIERO totale. "
                "La dose per singola somministrazione sarà divisa automaticamente.", 
                size=12, 
                color=ft.Colors.GREY_400
            ),
            peptides_container,
            add_peptide_btn,
            
            ft.Divider(height=20),
            ft.Text("Descrizione e Note", size=16, weight=ft.FontWeight.BOLD),
            description_field,
            notes_field,
        ], spacing=10, scroll=ft.ScrollMode.AUTO)
        
        def on_submit(e):
            # Validazione
            if not name_field.value or not name_field.value.strip():
                self.app.show_snackbar("❌ Nome protocollo obbligatorio", error=True)
                return
            
            # Validazione peptidi
            peptides_data = []
            for row_data in selected_peptides:
                peptide_id = row_data['peptide_dropdown'].value
                dose_mcg = row_data['dose_field'].value
                
                if not peptide_id:
                    self.app.show_snackbar("❌ Seleziona un peptide per ogni riga", error=True)
                    return
                
                if not dose_mcg or not dose_mcg.strip():
                    self.app.show_snackbar("❌ Specifica il dosaggio per ogni peptide", error=True)
                    return
                
                try:
                    dose_value = float(dose_mcg)
                    if dose_value <= 0:
                        self.app.show_snackbar("❌ Il dosaggio deve essere > 0", error=True)
                        return
                    peptides_data.append((int(peptide_id), dose_value))
                except ValueError:
                    self.app.show_snackbar("❌ Dosaggio non valido", error=True)
                    return
            
            if not peptides_data:
                self.app.show_snackbar("❌ Aggiungi almeno un peptide al protocollo", error=True)
                return
            
            try:
                protocol_id = self.app.manager.add_protocol(
                    name=name_field.value.strip(),
                    frequency_per_day=int(frequency_field.value) if frequency_field.value else 1,
                    days_on=int(days_on_field.value) if days_on_field.value else None,
                    days_off=int(days_off_field.value) if days_off_field.value else 0,
                    cycle_duration_weeks=int(cycle_weeks_field.value) if cycle_weeks_field.value else None,
                    peptides=peptides_data,  # Lista di (peptide_id, target_dose_mcg)
                    description=description_field.value if description_field.value else None,
                    notes=notes_field.value if notes_field.value else None,
                )
                
                DialogBuilder.close_dialog(self.app.page)
                self.refresh()
                self.app.show_snackbar(f"✅ Protocollo '{name_field.value}' creato con {len(peptides_data)} peptide(i)!")
                
            except Exception as ex:
                import traceback
                traceback.print_exc()
                self.app.show_snackbar(f"❌ Errore: {ex}", error=True)
        
        DialogBuilder.show_form_dialog(
            self.app.page,
            "Nuovo Protocollo",
            [form_content],
            on_submit,
            height=700,
        )
    
    def _show_edit_dialog(self, protocol_id):
        """Show edit protocol dialog with peptide display."""
        protocol = self.app.manager.get_protocol_details(protocol_id)
        if not protocol:
            return
        
        # Get protocol peptides
        protocol_peptides = protocol.get('peptides', [])
        
        # Form fields base
        name_field = ft.TextField(
            label="Nome Protocollo",
            value=protocol['name'],
            width=500,
        )
        
        frequency_field = ft.TextField(
            label="Frequenza al giorno",
            value=str(protocol.get('frequency_per_day', 1)),
            width=150,
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        
        days_on_field = ft.TextField(
            label="Giorni ON",
            value=str(protocol['days_on']) if protocol.get('days_on') else "",
            width=150,
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        
        days_off_field = ft.TextField(
            label="Giorni OFF",
            value=str(protocol.get('days_off', 0)),
            width=150,
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        
        cycle_weeks_field = ft.TextField(
            label="Durata ciclo (settimane)",
            value=str(protocol['cycle_duration_weeks']) if protocol.get('cycle_duration_weeks') else "",
            width=200,
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        
        description_field = ft.TextField(
            label="Descrizione",
            value=protocol.get('description', ''),
            multiline=True,
            min_lines=2,
            max_lines=3,
            width=500,
        )
        
        notes_field = ft.TextField(
            label="Note",
            value=protocol.get('notes', ''),
            multiline=True,
            min_lines=2,
            max_lines=3,
            width=500,
        )
        
        # Display peptides (read-only for now - full editing in future enhancement)
        peptides_display = ft.Column([], spacing=8)
        
        if protocol_peptides:
            for peptide in protocol_peptides:
                peptides_display.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.Icons.MEDICATION, size=20, color=ft.Colors.BLUE_400),
                            ft.Text(
                                f"{peptide['name']}: {peptide['target_dose_mcg']} mcg/giorno",
                                size=14,
                                weight=ft.FontWeight.W_500,
                            ),
                        ], spacing=10),
                        padding=10,
                        bgcolor=ft.Colors.BLUE_900,
                        border_radius=8,
                    )
                )
        else:
            peptides_display.controls.append(
                ft.Text("Nessun peptide associato", size=12, color=ft.Colors.GREY_500, italic=True)
            )
        
        peptides_note = ft.Text(
            "ℹ️ Per modificare i peptidi, elimina e ricrea il protocollo (gestione peptidi in edit coming soon)",
            size=11,
            color=ft.Colors.ORANGE_400,
            italic=True,
        )
        
        form_content = ft.Column([
            ft.Text("Informazioni Base", size=16, weight=ft.FontWeight.BOLD),
            ft.Row([name_field]),
            ft.Row([frequency_field, days_on_field, days_off_field]),
            ft.Row([cycle_weeks_field]),
            
            ft.Divider(height=20),
            ft.Text("Peptidi nel Protocollo", size=16, weight=ft.FontWeight.BOLD),
            peptides_display,
            peptides_note,
            
            ft.Divider(height=20),
            ft.Text("Descrizione e Note", size=16, weight=ft.FontWeight.BOLD),
            description_field,
            notes_field,
        ], spacing=10, scroll=ft.ScrollMode.AUTO)
        
        def on_submit(e):
            try:
                changes = {}
                
                if name_field.value != protocol['name']:
                    changes['name'] = name_field.value
                if int(frequency_field.value) != protocol.get('frequency_per_day', 1):
                    changes['frequency_per_day'] = int(frequency_field.value)
                
                new_days_on = int(days_on_field.value) if days_on_field.value else None
                if new_days_on != protocol.get('days_on'):
                    changes['days_on'] = new_days_on
                
                if int(days_off_field.value) != protocol.get('days_off', 0):
                    changes['days_off'] = int(days_off_field.value)
                
                new_cycle = int(cycle_weeks_field.value) if cycle_weeks_field.value else None
                if new_cycle != protocol.get('cycle_duration_weeks'):
                    changes['cycle_duration_weeks'] = new_cycle
                
                if description_field.value != (protocol.get('description') or ''):
                    changes['description'] = description_field.value if description_field.value else None
                
                if notes_field.value != (protocol.get('notes') or ''):
                    changes['notes'] = notes_field.value if notes_field.value else None
                
                if changes:
                    self.app.manager.update_protocol(protocol_id, **changes)
                    DialogBuilder.close_dialog(self.app.page)
                    self.refresh()
                    self.app.show_snackbar(f"✅ Protocollo #{protocol_id} aggiornato!")
                else:
                    self.app.show_snackbar("Nessuna modifica da salvare")
                    
            except Exception as ex:
                import traceback
                traceback.print_exc()
                self.app.show_snackbar(f"❌ Errore: {ex}", error=True)
        
        DialogBuilder.show_form_dialog(
            self.app.page,
            f"Modifica Protocollo #{protocol_id}",
            [form_content],
            on_submit,
            height=700,
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
        
        # Get protocol peptides
        protocol_peptides = protocol.get('peptides', [])
        frequency = protocol.get('frequency_per_day', 1)
        
        # Build peptides list
        peptides_list = []
        if protocol_peptides:
            for peptide in protocol_peptides:
                target_daily = peptide['target_dose_mcg']
                per_admin = target_daily / frequency
                peptides_list.append(
                    ft.Text(
                        f"   • {peptide['name']}: {target_daily} mcg/giorno "
                        f"({per_admin:.1f} mcg × {frequency}x/die)",
                        size=13,
                        color=ft.Colors.BLUE_300,
                    )
                )
        else:
            peptides_list.append(
                ft.Text("   Nessun peptide associato", size=12, color=ft.Colors.GREY_500, italic=True)
            )
        
        content = ft.Column([
            ft.Text(f"📋 Nome: {protocol['name']}", size=16, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            ft.Text(f"⏱️ Frequenza: {frequency_text}", size=14),
            ft.Divider(),
            ft.Text("💊 Peptidi nel Protocollo:", size=14, weight=ft.FontWeight.BOLD),
            *peptides_list,
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

