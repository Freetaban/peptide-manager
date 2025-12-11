"""
Dashboard View - Complete with scheduled administrations and expiring batches
"""

import flet as ft
from datetime import datetime
from ..components import CardBuilder


class DashboardView(ft.Container):
    """Dashboard with statistics, scheduled administrations, and expiring batches"""
    
    def __init__(self, app):
        super().__init__()
        self.app = app
        self._build()
    
    def _build(self):
        """Build dashboard"""
        manager = self.app.manager
        
        # Get inventory summary
        try:
            summary = manager.get_inventory_summary()
        except Exception as e:
            print(f"Error loading inventory summary: {e}")
            summary = {
                'available_batches': 0, 'total_batches': 0,
                'unique_peptides': 0, 'total_value': 0, 'expiring_soon': 0
            }
        
        # Build stats cards
        stats_row = ft.Row([
            self._stat_card(
                "Batches Attivi",
                f"{summary['available_batches']}/{summary['total_batches']}",
                ft.Icons.INVENTORY_2,
                ft.Colors.BLUE_400,
            ),
            self._stat_card(
                "Peptidi Unici",
                str(summary['unique_peptides']),
                ft.Icons.SCIENCE,
                ft.Colors.GREEN_400,
            ),
            self._stat_card(
                "Valore Totale",
                f"€{summary['total_value']:.2f}",
                ft.Icons.EURO,
                ft.Colors.AMBER_400,
            ),
            self._stat_card(
                "In Scadenza",
                str(summary['expiring_soon']),
                ft.Icons.WARNING,
                ft.Colors.RED_400 if summary['expiring_soon'] > 0 else ft.Colors.GREEN_400,
            ),
        ], wrap=True, spacing=10)
        
        # Scheduled administrations table
        scheduled_card = self._build_scheduled_administrations()
        
        # Expiring batches
        expiring_card = self._build_expiring_batches()
        
        # Build content
        self.content = ft.Column([
            ft.Row([
                ft.Text("Dashboard", size=32, weight=ft.FontWeight.BOLD),
                ft.Container(expand=True),
                ft.ElevatedButton(
                    "🔧 Riconcilia Volumi",
                    icon=ft.Icons.SYNC,
                    on_click=lambda e: self._show_reconciliation_dialog(),
                    tooltip="Verifica e correggi consistenza volumi preparazioni"
                ),
            ]),
            ft.Divider(),
            
            # Scheduled administrations (priority)
            scheduled_card,
            ft.Container(height=20),
            
            # Inventory stats
            ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("Riepilogo Inventario", size=18, weight=ft.FontWeight.BOLD),
                        ft.Divider(),
                        stats_row,
                    ]),
                    padding=20,
                ),
            ),
            ft.Container(height=10),
            
            # Expiring batches
            expiring_card,
        ], spacing=0, scroll=ft.ScrollMode.AUTO)
        
        self.padding = 20
        self.expand = True
    
    def _stat_card(self, title, value, icon, color):
        """Create stat card."""
        return ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon(icon, color=color, size=40),
                        ft.Column([
                            ft.Text(title, size=14, color=ft.Colors.GREY_400),
                            ft.Text(value, size=24, weight=ft.FontWeight.BOLD),
                        ], spacing=0),
                    ], alignment=ft.MainAxisAlignment.START),
                ]),
                padding=20,
                width=300,
            ),
        )
    
    def _build_scheduled_administrations(self):
        """Build scheduled administrations checklist."""
        today_tasks = self.app.manager.get_scheduled_administrations()
        today_rows = []
        
        if today_tasks:
            # Group tasks by preparation + cycle
            tasks_by_prep = {}
            for task in today_tasks:
                prep_id = task.get('preparation_id')
                cycle_id = task.get('cycle_id')
                key = (prep_id, cycle_id)
                if key not in tasks_by_prep:
                    tasks_by_prep[key] = []
                tasks_by_prep[key].append(task)
            
            # Create row for each group
            for (prep_id, cycle_id), group_tasks in tasks_by_prep.items():
                # Join peptide names
                peptide_names = " + ".join([t.get('peptide_name', '?') for t in group_tasks])
                
                # Sum target and ramped doses
                total_target_mcg = sum([t.get('target_dose_mcg', 0) for t in group_tasks])
                total_ramped_mcg = sum([t.get('ramped_dose_mcg', t.get('target_dose_mcg', 0)) for t in group_tasks])
                
                # Ramp info
                ramp_info = group_tasks[0].get('ramp_info')
                
                # Dose display with ramp indicator
                if ramp_info and abs(total_ramped_mcg - total_target_mcg) > 0.1:
                    if ramp_info.get('type') == 'exact':
                        dose_text = f"{int(total_ramped_mcg)} mcg (ramp settimana {ramp_info['week']})"
                    else:
                        dose_text = f"{int(total_ramped_mcg)} mcg → {int(total_target_mcg)} mcg ({ramp_info.get('percentage', 100)}% - settimana {ramp_info['week']})"
                    dose_color = ft.Colors.ORANGE_700
                else:
                    dose_text = f"{int(total_target_mcg)} mcg"
                    dose_color = ft.Colors.GREY_700
                
                # Suggested ml dose
                suggested_ml = group_tasks[0].get('suggested_dose_ml')
                
                # Status
                status = group_tasks[0].get('status', 'no_prep')
                cycle_name = group_tasks[0].get('cycle_name', '-')
                schedule_status = group_tasks[0].get('schedule_status', 'due_today')
                days_overdue = group_tasks[0].get('days_overdue', 0)
                
                # Status icon
                if status == 'ready':
                    status_icon = ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, color=ft.Colors.GREEN_400, size=20, tooltip="Preparazione pronta")
                    dose_display = f"{suggested_ml:.2f} ml" if suggested_ml else "-"
                elif status == 'insufficient_volume':
                    # Volume disponibile ma insufficiente
                    available_ml = group_tasks[0].get('available_ml', 0)
                    missing_ml = group_tasks[0].get('missing_ml', 0)
                    missing_mcg = group_tasks[0].get('missing_mcg', 0)
                    status_icon = ft.Icon(ft.Icons.WARNING_AMBER, color=ft.Colors.ORANGE_400, size=20, 
                                         tooltip=f"Volume insufficiente! Disponibili {available_ml:.2f}ml, mancano ~{missing_ml:.2f}ml (~{missing_mcg:.0f}mcg)")
                    dose_display = f"⚠️ {available_ml:.2f}/{suggested_ml + missing_ml:.2f} ml"
                else:
                    status_icon = ft.Icon(ft.Icons.ERROR_OUTLINE, color=ft.Colors.RED_400, size=20, tooltip="Preparazione non disponibile")
                    dose_display = "N/A"
                
                # Schedule badge
                if schedule_status == 'overdue':
                    schedule_badge = ft.Container(
                        content=ft.Text(f"⚠️ In ritardo di {days_overdue}gg", size=10, color=ft.Colors.RED_700),
                        bgcolor=ft.Colors.RED_50,
                        padding=ft.padding.symmetric(horizontal=5, vertical=2),
                        border_radius=3,
                    )
                else:
                    schedule_badge = ft.Container(
                        content=ft.Text(f"✅ Previsto oggi", size=10, color=ft.Colors.GREEN_700),
                        bgcolor=ft.Colors.GREEN_50,
                        padding=ft.padding.symmetric(horizontal=5, vertical=2),
                        border_radius=3,
                    )
                
                # Cycle badge
                cycle_badge = ft.Container(
                    content=ft.Text(f"🔄 {cycle_name}", size=11, color=ft.Colors.BLUE_700),
                    bgcolor=ft.Colors.BLUE_50,
                    padding=ft.padding.symmetric(horizontal=6, vertical=2),
                    border_radius=4,
                )
                
                # Prep info
                if status == 'insufficient_volume':
                    available_ml = group_tasks[0].get('available_ml', 0)
                    missing_ml = group_tasks[0].get('missing_ml', 0)
                    if 'multi_prep_ids' in group_tasks[0] and len(group_tasks[0]['multi_prep_ids']) > 1:
                        prep_list = ", ".join([f"Prep #{pid}" for pid in group_tasks[0]['multi_prep_ids']])
                        prep_info = f"⚠️ {prep_list} - Volume insufficiente! Preparare nuova dose"
                    else:
                        prep_info = f"⚠️ Prep #{prep_id} - Volume insufficiente! Preparare nuova dose"
                elif 'multi_prep_ids' in group_tasks[0] and len(group_tasks[0]['multi_prep_ids']) > 1:
                    prep_info = ", ".join([f"Prep #{pid}" for pid in group_tasks[0]['multi_prep_ids']])
                else:
                    prep_info = f"Prep #{prep_id}" if prep_id else "Nessuna prep disponibile"
                
                # Register button
                register_btn = ft.ElevatedButton(
                    "✓ Registra",
                    icon=ft.Icons.ADD_TASK,
                    on_click=lambda e, tasks=group_tasks: self._show_register_dialog(tasks),
                    disabled=(status != 'ready'),
                    bgcolor=ft.Colors.GREEN_400 if status == 'ready' else None,
                )
                
                today_rows.append(
                    ft.DataRow(
                        cells=[
                            ft.DataCell(ft.Row([status_icon], spacing=5)),
                            ft.DataCell(ft.Column([
                                ft.Text(peptide_names, weight=ft.FontWeight.BOLD),
                                ft.Row([cycle_badge, schedule_badge], spacing=4)
                            ], spacing=2)),
                            ft.DataCell(ft.Text(dose_text, color=dose_color)),
                            ft.DataCell(ft.Text(dose_display, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_600 if status == 'ready' else None)),
                            ft.DataCell(ft.Text(prep_info)),
                            ft.DataCell(register_btn),
                        ]
                    )
                )
        else:
            today_rows.append(
                ft.DataRow(cells=[
                    ft.DataCell(ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN_400)),
                    ft.DataCell(ft.Text("✅ Tutto completato per oggi!", weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_600)),
                    ft.DataCell(ft.Text("-")),
                    ft.DataCell(ft.Text("-")),
                    ft.DataCell(ft.Text("-")),
                    ft.DataCell(ft.Text("-")),
                ])
            )
        
        today_list = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("✓")),
                ft.DataColumn(ft.Text("Peptide / Ciclo")),
                ft.DataColumn(ft.Text("Dose (mcg)")),
                ft.DataColumn(ft.Text("Preleva (ml)")),
                ft.DataColumn(ft.Text("Preparazione")),
                ft.DataColumn(ft.Text("Azione")),
            ],
            rows=today_rows,
        )
        
        return ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Text("Somministrazioni Programmate Oggi", size=20, weight=ft.FontWeight.BOLD),
                    ft.Divider(),
                    today_list,
                ]),
                padding=20,
            ),
        )
    
    def _build_expiring_batches(self):
        """Build expiring batches list."""
        expiring_batches = self.app.manager.get_expiring_batches(days=60, limit=5)
        expiring_list = ft.Column()
        
        if expiring_batches:
            for batch in expiring_batches:
                bid = batch['id']
                product = batch['product_name']
                expiry = batch['expiration_date']
                vials = batch['vials_remaining']
                
                try:
                    exp_date = datetime.strptime(expiry, '%Y-%m-%d')
                    days_left = (exp_date - datetime.now()).days
                except Exception:
                    days_left = 9999
                
                color = ft.Colors.RED_400 if days_left < 30 else ft.Colors.ORANGE_400
                
                expiring_list.controls.append(
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.WARNING, color=color),
                        title=ft.Text(f"#{bid} - {product}"),
                        subtitle=ft.Text(f"Scade: {expiry} (tra {days_left} giorni) - {vials} fiale"),
                        trailing=ft.IconButton(
                            icon=ft.Icons.ARROW_FORWARD,
                            on_click=lambda e, batch_id=bid: self._show_batch_details(batch_id),
                        ),
                    )
                )
        else:
            expiring_list.controls.append(
                ft.Text("✓ Nessun batch in scadenza", color=ft.Colors.GREEN_400)
            )
        
        return ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Text("Batches in Scadenza (60 giorni)", size=18, weight=ft.FontWeight.BOLD),
                    ft.Divider(),
                    expiring_list,
                ]),
                padding=20,
            ),
        )
    
    def _show_register_dialog(self, tasks):
        """Show dialog to register administration with pre-filled data."""
        from datetime import datetime
        
        # Get data from first task
        task = tasks[0]
        
        # Check if preparation is available
        if task.get('status') == 'no_prep':
            peptide_name = task.get('peptide_name', 'peptide')
            self.app.show_snackbar(
                f"❌ Impossibile registrare: nessuna preparazione disponibile per {peptide_name}!",
                error=True
            )
            return
        
        # Verify preparation_id exists
        prep_id = task.get('preparation_id')
        if not prep_id:
            self.app.show_snackbar(
                "❌ Errore: ID preparazione mancante. Creare preparazione prima di registrare.",
                error=True
            )
            return
        
        # Get active preparations and protocols
        preparations = self.app.manager.get_preparations(only_active=True)
        active_preps = [p for p in preparations if p['volume_remaining_ml'] > 0]
        protocols = self.app.manager.get_protocols()
        
        if not active_preps:
            self.app.show_snackbar("❌ Nessuna preparazione attiva con volume disponibile!", error=True)
            return
        
        # Verify the specific preparation is in active list
        prep_exists = any(p['id'] == prep_id for p in active_preps)
        if not prep_exists:
            self.app.show_snackbar(
                f"❌ Preparazione #{prep_id} non più disponibile o senza volume!",
                error=True
            )
            return
        
        # Pre-fill values
        prep_id = str(task.get('preparation_id', ''))
        dose_ml = str(round(task.get('suggested_dose_ml', 0.25), 2))  # Round to 2 decimals
        # Extract protocol_id - ensure it's valid
        protocol_id_raw = task.get('protocol_id')
        protocol_id = str(protocol_id_raw) if protocol_id_raw else ""
        cycle_name = task.get('cycle_name', 'N/A')
        target_dose = task.get('target_dose_mcg', 0)
        
        # Multi-prep info for notes field
        multi_prep_dist = task.get('multi_prep_distribution', [])
        if len(multi_prep_dist) > 1:
            prep_info_note = f"Multi-prep FIFO:\n"
            for idx, d in enumerate(multi_prep_dist, 1):
                prep_info_note += f"{idx}. Prep #{d['prep_id']}: {d['ml']:.2f}ml\n"
            prep_info_note += f"\nTotale: {sum(d['ml'] for d in multi_prep_dist):.2f}ml"
        elif len(multi_prep_dist) == 1:
            prep_info_note = f"Preparazione #{multi_prep_dist[0]['prep_id']}"
        else:
            prep_info_note = f"Preparazione #{prep_id}"
        
        # Add cycle info to notes
        notes_default = f"{prep_info_note}\n\nCiclo: {cycle_name}\nDose target: {target_dose} mcg"
        
        from gui_modular.components.forms import Field, FieldType, FormBuilder
        
        fields = [
            Field(
                "dose_ml",
                "Dose (ml)",
                FieldType.TEXT,  # Changed from NUMBER to TEXT to fix label display
                required=True,
                value=dose_ml,
                hint_text="Volume da somministrare",
                width=250,  # Increased from 150 to allow label to display
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
                    ("Coscia DX", "Coscia DX"),
                    ("Coscia SX", "Coscia SX"),
                    ("Braccio DX", "Braccio DX"),
                    ("Braccio SX", "Braccio SX"),
                    ("Gluteo DX", "Gluteo DX"),
                    ("Gluteo SX", "Gluteo SX"),
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
                value=protocol_id,
                options=[("", "Nessuno")] + [(str(p['id']), p['name']) for p in protocols],
                width=300,
            ),
            Field(
                "notes",
                "Note",
                FieldType.TEXTAREA,
                value=notes_default,
                width=500
            ),
        ]
        
        form_controls = FormBuilder.build_fields(fields)
        
        def on_submit(e):
            from gui_modular.components.dialogs import DialogBuilder
            
            values = FormBuilder.get_values(form_controls)
            is_valid, error_msg = FormBuilder.validate_required(
                form_controls,
                [f.key for f in fields if f.required]
            )
            
            if not is_valid:
                self.app.show_snackbar(error_msg, error=True)
                return
            
            try:
                # Combine date and time
                admin_datetime = f"{values['administration_date']} {values['administration_time']}"
                
                # Get cycle_id from task
                cycle_id = task.get('cycle_id')
                
                # Get user-specified dose
                user_dose_ml = float(values['dose_ml'])
                
                # Multi-prep distribution: recalculate if user changed dose
                multi_prep_dist = task.get('multi_prep_distribution', [])
                admin_ids = []
                
                if multi_prep_dist and len(multi_prep_dist) > 0:
                    # Recalculate distribution based on user dose
                    original_dose = sum(d['ml'] for d in multi_prep_dist)
                    
                    # If user changed dose significantly, recalculate FIFO
                    if abs(user_dose_ml - original_dose) > 0.01:
                        # Recalculate FIFO distribution with new dose
                        remaining_ml = user_dose_ml
                        recalc_dist = []
                        
                        for dist in multi_prep_dist:
                            if remaining_ml <= 0:
                                break
                            prep_id = dist['prep_id']
                            concentration = dist['concentration_mcg_per_ml']
                            prep_details = dist['prep_details']
                            available_ml = prep_details.get('volume_remaining_ml', 0)
                            
                            # Take what we need or what's available
                            take_ml = round(min(remaining_ml, available_ml), 2)  # Round to 2 decimals
                            if take_ml > 0.01:
                                recalc_dist.append({
                                    'prep_id': prep_id,
                                    'ml': take_ml,
                                    'concentration_mcg_per_ml': concentration
                                })
                                remaining_ml -= take_ml
                        
                        multi_prep_dist = recalc_dist
                    
                    # Register one administration per prep used
                    for idx, prep_dist in enumerate(multi_prep_dist):
                        prep_id = prep_dist['prep_id']
                        prep_ml = round(prep_dist['ml'], 2)  # Round to 2 decimals
                        
                        # Add note about multi-prep
                        notes_text = values.get('notes', '')
                        if len(multi_prep_dist) > 1:
                            notes_text += f"\n[Multi-prep {idx+1}/{len(multi_prep_dist)}: {prep_ml:.2f}ml da Prep #{prep_id}]"
                        
                        admin_id = self.app.manager.add_administration(
                            preparation_id=prep_id,
                            dose_ml=prep_ml,
                            administration_datetime=admin_datetime,
                            injection_site=values['injection_site'],
                            injection_method=values['injection_method'],
                            protocol_id=int(values['protocol_id']) if values.get('protocol_id') else None,
                            notes=notes_text,
                        )
                        admin_ids.append(admin_id)
                else:
                    # Single prep (fallback)
                    admin_id = self.app.manager.add_administration(
                        preparation_id=int(values['preparation_id']),
                        dose_ml=float(values['dose_ml']),
                        administration_datetime=admin_datetime,
                        injection_site=values['injection_site'],
                        injection_method=values['injection_method'],
                        protocol_id=int(values['protocol_id']) if values.get('protocol_id') else None,
                        notes=values.get('notes'),
                    )
                    admin_ids.append(admin_id)
                
                # Assign all administrations to cycle if present
                if cycle_id and admin_ids:
                    self.app.manager.assign_administrations_to_cycle(admin_ids, cycle_id)
                
                DialogBuilder.close_dialog(self.app.page)
                self._build()  # Rebuild dashboard to refresh data
                self.update()  # Update the container
                self.app.page.update()  # Update the page
                
                if len(admin_ids) > 1:
                    self.app.show_snackbar(f"✅ {len(admin_ids)} somministrazioni registrate (multi-prep)!")
                else:
                    self.app.show_snackbar(f"✅ Somministrazione #{admin_ids[0]} registrata!")
                
            except Exception as ex:
                import traceback
                traceback.print_exc()
                self.app.show_snackbar(f"❌ Errore: {ex}", error=True)
        
        from gui_modular.components.dialogs import DialogBuilder
        
        # Create 2-column layout for compact display
        col1 = ft.Column([
            form_controls['dose_ml'],
            form_controls['administration_date'],
            form_controls['administration_time'],
        ], spacing=10, tight=True)
        
        col2 = ft.Column([
            form_controls['injection_site'],
            form_controls['injection_method'],
            form_controls['protocol_id'],
        ], spacing=10, tight=True)
        
        notes_row = ft.Column([
            form_controls['notes'],
        ], spacing=10)
        
        layout = ft.Column([
            ft.Row([col1, col2], spacing=20),
            notes_row,
        ], spacing=15, tight=True)
        
        def handle_submit(e):
            try:
                on_submit(e)
            except Exception as ex:
                import traceback
                print(f"ERROR in handle_submit: {ex}")
                traceback.print_exc()
        
        def close_dialog(e):
            self.app.page.dialog.open = False
            self.app.page.update()
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Nuova Somministrazione"),
            content=ft.Container(
                content=layout,
                width=700,
                padding=ft.padding.only(top=20, left=10, right=10, bottom=10),
            ),
            actions=[
                ft.TextButton("Annulla", on_click=close_dialog),
                ft.ElevatedButton("Salva", on_click=handle_submit),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        try:
            if hasattr(self.app.page, 'overlay') and dialog not in list(self.app.page.overlay):
                self.app.page.overlay.append(dialog)
        except Exception:
            pass
        
        self.app.page.dialog = dialog
        dialog.open = True
        self.app.page.update()
    
    def _show_reconciliation_dialog(self):
        """Show reconciliation dialog (placeholder)."""
        self.app.show_snackbar("⚠️ Funzione non disponibile", error=True)
        """Show batch details (delegates to gui.py)."""
        if hasattr(self.app, 'show_batch_details'):
            self.app.show_batch_details(batch_id)
        else:
            self.app.show_snackbar("⚠️ Funzione non disponibile", error=True)
    
    def _show_reconciliation_dialog(self):
        """Show reconciliation dialog (delegates to gui.py)."""
        if hasattr(self.app, 'show_reconciliation_dialog'):
            self.app.show_reconciliation_dialog()
        else:
            self.app.show_snackbar("⚠️ Funzione non disponibile", error=True)
