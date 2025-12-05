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
                if 'multi_prep_ids' in group_tasks[0] and len(group_tasks[0]['multi_prep_ids']) > 1:
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
        """Show dialog to register administration (delegates to gui.py)."""
        # Delegate to main app's method
        if hasattr(self.app, '_show_register_dialog'):
            self.app._show_register_dialog(tasks)
        else:
            self.app.show_snackbar("⚠️ Funzione non disponibile", error=True)
    
    def _show_batch_details(self, batch_id):
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
