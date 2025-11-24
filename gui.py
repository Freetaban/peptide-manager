"""
GUI Flet per Peptide Management System
Interfaccia grafica moderna Material Design con CRUD completo
"""

import flet as ft
from peptide_manager import PeptideManager
from datetime import datetime, timedelta
import sys
import argparse

# Importa gestione ambiente
try:
    from scripts.environment import get_environment
    USE_ENV = True
except ImportError:
    USE_ENV = False
    print("⚠️  Modulo environment non trovato, uso path di default")

class PeptideGUI:
    """Classe principale GUI."""
    
    def __init__(self, db_path=None, environment=None):
        # Se non specificato, usa gestione ambiente
        if USE_ENV and db_path is None:
            env = get_environment(environment)
            self.db_path = str(env.db_path)
            self.environment = env.name or 'unknown'
        else:
            self.db_path = db_path or 'peptide_management.db'
            self.environment = environment or 'unknown'
        
        self.manager = None
        self.page = None
        self.current_view = "dashboard"
        self.edit_mode = False
    

    def _make_handler(self, func, *args, **kwargs):
        """Factory per handler eventi (fix Flet 0.28.3)."""
        def handler(e):
            return func(*args, **kwargs)
        return handler
    
    def toggle_edit_mode(self, e):
        """Toggle modalità modifica."""
        self.edit_mode = e.control.value
        
        # Mostra snackbar
        if self.edit_mode:
            self.show_snackbar("⚠️ Modalità Modifica ATTIVA - Fai attenzione!", error=True)
        else:
            self.show_snackbar("✅ Modalità Modifica disattivata", error=False)
        
        # Ricarica vista corrente per aggiornare bottoni
        self.update_content()

    def build_header(self):
        """Costruisce header con toggle Edit Mode e badge ambiente."""
        # Badge ambiente (solo se non production)
        env_badge = None
        if self.environment == 'development':
            env_badge = ft.Container(
                content=ft.Text(
                    f"🔧 {self.environment.upper()}",
                    size=11,
                    color=ft.Colors.ORANGE_400,
                    weight=ft.FontWeight.BOLD
                ),
                bgcolor=ft.Colors.ORANGE_900,
                padding=ft.padding.symmetric(horizontal=10, vertical=4),
                border_radius=5,
            )
        elif self.environment not in ['production', 'unknown']:
            env_badge = ft.Container(
                content=ft.Text(
                    self.environment.upper(),
                    size=11,
                    color=ft.Colors.BLUE_400,
                    weight=ft.FontWeight.BOLD
                ),
                bgcolor=ft.Colors.BLUE_900,
                padding=ft.padding.symmetric(horizontal=10, vertical=4),
                border_radius=5,
            )
        
        # Elementi header
        header_elements = [
            ft.Text(
                "Peptide Management System", 
                size=24, 
                weight=ft.FontWeight.BOLD
            ),
        ]
        
        if env_badge:
            header_elements.append(env_badge)
        
        header_elements.extend([
            ft.Container(expand=True),  # Spacer
            ft.Row([
                ft.Icon(
                    ft.Icons.LOCK if not self.edit_mode else ft.Icons.LOCK_OPEN,
                    color=ft.Colors.RED_400 if self.edit_mode else ft.Colors.GREEN_400
                ),
                ft.Switch(
                    label="Modalità Modifica",
                    value=self.edit_mode,
                    on_change=self.toggle_edit_mode,
                    active_color=ft.Colors.RED_400,
                ),
            ], spacing=10),
        ])
        
        return ft.Container(
            content=ft.Row(header_elements, alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            padding=15,
            bgcolor=ft.Colors.SURFACE,
            border_radius=ft.border_radius.only(top_left=10, top_right=10),
        )

    def show_delete_confirmation(self, entity_type: str, entity_id: int, 
                                 entity_name: str, delete_callback):
        """Mostra dialog conferma eliminazione."""
        
        def on_confirm(e):
            """Esegue eliminazione dopo conferma."""
            try:
                success = delete_callback(entity_id)
                if success:
                    dialog.open = False
                    self.page.update()
                    self.update_content()
                    self.show_snackbar(f"✅ {entity_type} eliminato")
                else:
                    self.show_snackbar(f"❌ Errore eliminazione {entity_type}", error=True)
            except Exception as ex:
                self.show_snackbar(f"❌ Errore: {ex}", error=True)
        
        def on_cancel(e):
            """Chiude dialog senza eliminare."""
            dialog.open = False
            self.page.update()
        
        dialog = ft.AlertDialog(
            title=ft.Text("⚠️ Conferma Eliminazione"),
            content=ft.Column([
                ft.Text(
                    f"Sei sicuro di voler eliminare questo {entity_type}?",
                    weight=ft.FontWeight.BOLD
                ),
                ft.Text(f'"{entity_name}"', italic=True, size=16),
                ft.Divider(),
                ft.Text(
                    "L'elemento sarà archiviato e non più visibile,\n"
                    "ma rimarrà nel database.",
                    size=12,
                    color=ft.Colors.GREY_400
                ),
            ], spacing=10, tight=True),
            actions=[
                ft.TextButton("Annulla", on_click=on_cancel),
                ft.ElevatedButton(
                    "Elimina",
                    icon=ft.Icons.DELETE,
                    color=ft.Colors.WHITE,
                    bgcolor=ft.Colors.RED_400,
                    on_click=on_confirm,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()

    def confirm_delete_batch(self, batch_id):
        """Conferma eliminazione batch."""
        batch = self.manager.get_batch_details(batch_id)
        if batch:
            self.show_delete_confirmation(
                "Batch",
                batch_id,
                batch['product_name'],
                self.manager.soft_delete_batch
            )

    def confirm_delete_peptide(self, peptide_id):
        """Conferma eliminazione peptide."""
        peptide = self.manager.get_peptide_by_id(peptide_id)
        if peptide:
            self.show_delete_confirmation(
                "Peptide",
                peptide_id,
                peptide['name'],
                self.manager.soft_delete_peptide
            )

    def confirm_delete_supplier(self, supplier_id):
        """Conferma eliminazione fornitore."""
        suppliers = self.manager.get_suppliers()
        supplier = next((s for s in suppliers if s['id'] == supplier_id), None)
        if supplier:
            self.show_delete_confirmation(
                "Fornitore",
                supplier_id,
                supplier['name'],
                self.manager.soft_delete_supplier
            )

    def confirm_delete_preparation(self, prep_id):
        """Conferma eliminazione preparazione."""
        prep = self.manager.get_preparation_details(prep_id)
        if prep:
            self.show_delete_confirmation(
                "Preparazione",
                prep_id,
                f"Prep #{prep_id}",
                self.manager.soft_delete_preparation
            )

    def confirm_delete_protocol(self, protocol_id):
        """Conferma eliminazione protocollo."""
        protocol = self.manager.get_protocol_details(protocol_id)
        if protocol:
            self.show_delete_confirmation(
                "Protocollo",
                protocol_id,
                protocol['name'],
                self.manager.soft_delete_protocol
            )

    def confirm_delete_administration(self, admin_id):
        """Conferma eliminazione somministrazione."""
        self.show_delete_confirmation(
            "Somministrazione",
            admin_id,
            f"Somministrazione #{admin_id}",
            self.manager.soft_delete_administration
        )
    
    def main(self, page: ft.Page):
        """Entry point GUI."""
        self.page = page
        self.manager = PeptideManager(self.db_path)
        
        # Configurazione pagina
        env_suffix = f" [{self.environment.upper()}]" if self.environment != 'production' else ""
        page.title = f"Peptide Management System{env_suffix}"
        page.theme_mode = ft.ThemeMode.DARK
        page.padding = 0
        page.window_width = 1400
        page.window_height = 900
        
        # Navigation rail (sidebar)
        self.nav_rail = ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=100,
            min_extended_width=200,
            destinations=[
                ft.NavigationRailDestination(
                    icon=ft.Icons.DASHBOARD_OUTLINED,
                    selected_icon=ft.Icons.DASHBOARD,
                    label="Dashboard",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.INVENTORY_2_OUTLINED,
                    selected_icon=ft.Icons.INVENTORY_2,
                    label="Batches",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.SCIENCE_OUTLINED,
                    selected_icon=ft.Icons.SCIENCE,
                    label="Peptidi",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.LOCAL_SHIPPING_OUTLINED,
                    selected_icon=ft.Icons.LOCAL_SHIPPING,
                    label="Fornitori",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.WATER_DROP_OUTLINED,
                    selected_icon=ft.Icons.WATER_DROP,
                    label="Preparazioni",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.CALENDAR_TODAY_OUTLINED,
                    selected_icon=ft.Icons.CALENDAR_TODAY,
                    label="Protocolli",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.LIST_ALT_OUTLINED,
                    selected_icon=ft.Icons.LIST_ALT,
                    label="Cicli",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.HISTORY,
                    selected_icon=ft.Icons.HISTORY,
                    label="Storico",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.CALCULATE_OUTLINED,
                    selected_icon=ft.Icons.CALCULATE,
                    label="Calcolatore",
                ),
                
            ],
            on_change=self.nav_changed,
        )
        
        # Container principale per contenuto
        self.content_area = ft.Container(
            content=self.build_dashboard(),
            expand=True,
            padding=20,
        )
        
        # Layout principale con header
        page.add(
            ft.Column([
                self.build_header(),  # Header con toggle Edit Mode
                ft.Row(
                    [
                        self.nav_rail,
                        ft.VerticalDivider(width=1),
                        self.content_area,
                    ],
                    expand=True,
                ),
            ], spacing=0, expand=True)  # ← Aggiunto expand=True
        )
        
        # Check integrità dati all'avvio
        self.check_integrity_on_startup()
    
    def nav_changed(self, e):
        """Gestisce cambio navigazione."""
        index = e.control.selected_index
        
        views = {
            0: "dashboard",
            1: "batches",
            2: "peptides",
            3: "suppliers",
            4: "preparations",
            5: "protocols",
            6: "cycles",
            7: "administrations",
            8: "calculator",
        }
        
        self.current_view = views[index]
        self.update_content()
    
    def update_content(self):
        """Aggiorna area contenuto."""
        views = {
            "dashboard": self.build_dashboard,
            "batches": self.build_batches,
            "peptides": self.build_peptides,
            "suppliers": self.build_suppliers,
            "preparations": self.build_preparations,
            "protocols": self.build_protocols,
            "cycles": self.build_cycles,
            "administrations": self.build_administrations,
            "calculator": self.build_calculator,
        }
        
        self.content_area.content = views[self.current_view]()
        self.page.update()
    
    # ============================================================
    # DASHBOARD
    # ============================================================
    
    def build_dashboard(self):
        """Costruisce dashboard."""
        summary = self.manager.get_inventory_summary()

        # Card statistiche
        stats_cards = ft.Row(
            [
                self.stat_card(
                    "Batches Attivi",
                    f"{summary['available_batches']}/{summary['total_batches']}",
                    ft.Icons.INVENTORY_2,
                    ft.Colors.BLUE_400,
                ),
                self.stat_card(
                    "Peptidi Unici",
                    str(summary['unique_peptides']),
                    ft.Icons.SCIENCE,
                    ft.Colors.GREEN_400,
                ),
                self.stat_card(
                    "Valore Totale",
                    f"€{summary['total_value']:.2f}",
                    ft.Icons.EURO,
                    ft.Colors.AMBER_400,
                ),
                self.stat_card(
                    "In Scadenza",
                    str(summary['expiring_soon']),
                    ft.Icons.WARNING,
                    ft.Colors.RED_400 if summary['expiring_soon'] > 0 else ft.Colors.GREEN_400,
                ),
            ],
            wrap=True,
        )

        # Prepariamo la tabella delle somministrazioni DA FARE oggi (CHECKLIST OPERATIVA)
        today_tasks = self.manager.get_scheduled_administrations()
        today_rows = []
        
        if today_tasks:
            # Raggruppa task per preparazione (mix di peptidi nella stessa prep)
            tasks_by_prep = {}
            for task in today_tasks:
                prep_id = task.get('preparation_id')
                cycle_id = task.get('cycle_id')
                key = (prep_id, cycle_id)  # Raggruppa per prep + ciclo
                if key not in tasks_by_prep:
                    tasks_by_prep[key] = []
                tasks_by_prep[key].append(task)
            
            # Crea una riga per ogni gruppo (prep/ciclo)
            for (prep_id, cycle_id), group_tasks in tasks_by_prep.items():
                # Unisci nomi peptidi
                peptide_names = " + ".join([t.get('peptide_name', '?') for t in group_tasks])
                
                # Somma dosi target e ramped
                total_target_mcg = sum([t.get('target_dose_mcg', 0) for t in group_tasks])
                total_ramped_mcg = sum([t.get('ramped_dose_mcg', t.get('target_dose_mcg', 0)) for t in group_tasks])
                
                # Info ramp (usa primo task, assumendo stesso ciclo)
                ramp_info = group_tasks[0].get('ramp_info')
                
                # Dose display con ramp indicator
                if ramp_info and abs(total_ramped_mcg - total_target_mcg) > 0.1:
                    # C'è ramp attivo - gestisci entrambi i formati
                    if ramp_info.get('type') == 'exact':
                        # Nuovo formato: dose esatta in mcg
                        dose_text = f"{int(total_ramped_mcg)} mcg (ramp settimana {ramp_info['week']})"
                    else:
                        # Vecchio formato: percentuale
                        dose_text = f"{int(total_ramped_mcg)} mcg → {int(total_target_mcg)} mcg ({ramp_info.get('percentage', 100)}% - settimana {ramp_info['week']})"
                    dose_color = ft.Colors.ORANGE_700
                else:
                    dose_text = f"{int(total_target_mcg)} mcg"
                    dose_color = ft.Colors.GREY_700
                
                # Dose totale ml (la stessa per tutti se stesso prep)
                suggested_ml = group_tasks[0].get('suggested_dose_ml')
                
                # Status comune
                status = group_tasks[0].get('status', 'no_prep')
                cycle_name = group_tasks[0].get('cycle_name', '-')
                schedule_status = group_tasks[0].get('schedule_status', 'due_today')
                days_overdue = group_tasks[0].get('days_overdue', 0)
                next_due_date = group_tasks[0].get('next_due_date')
                
                # Icona status prep
                if status == 'ready':
                    status_icon = ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, color=ft.Colors.GREEN_400, size=20, tooltip="Preparazione pronta")
                    dose_display = f"{suggested_ml:.2f} ml" if suggested_ml else "-"
                else:
                    status_icon = ft.Icon(ft.Icons.ERROR_OUTLINE, color=ft.Colors.RED_400, size=20, tooltip="Preparazione non disponibile")
                    dose_display = "N/A"
                
                # Badge schedule status
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
                
                # Badge ciclo
                cycle_badge = ft.Container(
                    content=ft.Text(f"🔄 {cycle_name}", size=11, color=ft.Colors.BLUE_700),
                    bgcolor=ft.Colors.BLUE_50,
                    padding=ft.padding.symmetric(horizontal=6, vertical=2),
                    border_radius=4,
                )
                
                # Prep info
                prep_info = f"Prep #{prep_id}" if prep_id else "Nessuna prep disponibile"
                
                # Bottone registra (apre dialog pre-compilato)
                # Usa lambda per catturare correttamente la lista group_tasks
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

        # Batches in scadenza
        expiring_batches = self.manager.get_expiring_batches(days=60, limit=5)
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
                            on_click=self._make_handler(self.show_batch_details, bid),
                        ),
                    )
                )
        else:
            expiring_list.controls.append(
                ft.Text("✓ Nessun batch in scadenza", color=ft.Colors.GREEN_400)
            )

        return ft.Column(
            [
                ft.Row([
                    ft.Text("Dashboard", size=32, weight=ft.FontWeight.BOLD),
                    ft.Container(expand=True),
                    ft.ElevatedButton(
                        "🔧 Riconcilia Volumi",
                        icon=ft.Icons.SYNC,
                        on_click=lambda e: self.show_reconciliation_dialog(),
                        tooltip="Verifica e correggi consistenza volumi preparazioni"
                    ),
                ]),
                ft.Divider(),

                # Somministrazioni programmate (priorità operativa)
                ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.Text("Somministrazioni Programmate Oggi", size=20, weight=ft.FontWeight.BOLD),
                            ft.Divider(),
                            today_list,
                        ]),
                        padding=20,
                    ),
                ),

                ft.Container(height=20),

                # Statistiche inventario (informative)
                ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.Text("Riepilogo Inventario", size=18, weight=ft.FontWeight.BOLD),
                            ft.Divider(),
                            stats_cards,
                        ]),
                        padding=20,
                    ),
                ),

                ft.Container(height=10),

                # Batches in scadenza
                ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.Text("Batches in Scadenza (60 giorni)", size=18, weight=ft.FontWeight.BOLD),
                            ft.Divider(),
                            expiring_list,
                        ]),
                        padding=20,
                    ),
                ),
            ],
            scroll=ft.ScrollMode.AUTO,
        )
    
    def stat_card(self, title, value, icon, color):
        """Card statistica."""
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
    
    # ============================================================
    # BATCHES
    # ============================================================
    
    def build_batches(self):
        """Costruisce vista batches."""
        batches = self.manager.get_batches(only_available=True)
        batches_sorted = sorted(batches, key=lambda x: x['id'])
        
        # Toolbar
        toolbar = ft.Row([
            ft.Text("Batches", size=32, weight=ft.FontWeight.BOLD),
            ft.Container(expand=True),
            ft.ElevatedButton(
                "Aggiungi Batch",
                icon=ft.Icons.ADD,
                on_click=self.show_add_batch_dialog,
            ),
        ])
        
        # Tabella
        rows = []
        for b in batches_sorted:
            batch_details = self.manager.get_batch_details(b['id'])
            
            # Composizione
            comp_list = [c['name'] for c in batch_details['composition']]
            composition = ", ".join(comp_list[:2])
            if len(comp_list) > 2:
                composition += f" +{len(comp_list)-2}"
            
            # Scadenza con colore
            expiry = b.get('expiry_date', 'None')
            expiry_color = ft.Colors.WHITE
            if expiry and expiry != 'None':
                try:
                    exp_date = datetime.strptime(expiry, '%Y-%m-%d')
                    days_left = (exp_date - datetime.now()).days
                    if days_left < 30:
                        expiry_color = ft.Colors.RED_400
                    elif days_left < 60:
                        expiry_color = ft.Colors.ORANGE_400
                except:
                    pass
            
            # Preparazioni
            prep_count = len([p for p in batch_details['preparations'] if p['volume_remaining_ml'] > 0])
            
            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(f"#{b['id']}")),
                        ft.DataCell(ft.Text(b['product_name'][:30])),
                        ft.DataCell(ft.Text(composition[:30])),
                        ft.DataCell(ft.Text(b['supplier_name'][:20])),
                        ft.DataCell(ft.Text(b['purchase_date'])),
                        ft.DataCell(ft.Text(expiry, color=expiry_color)),
                        ft.DataCell(ft.Text(f"{b['vials_remaining']}/{b['vials_count']}")),
                        ft.DataCell(ft.Text(str(prep_count) if prep_count > 0 else "-")),
                        ft.DataCell(
                            ft.Row([
                                ft.IconButton(
                                    icon=ft.Icons.VISIBILITY,
                                    tooltip="Dettagli",
                                    on_click=self._make_handler(self.show_batch_details, b['id']),
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.EDIT,
                                    tooltip="Modifica",
                                    on_click=self._make_handler(self.show_edit_batch_dialog, b['id']),
                                    disabled=not self.edit_mode,
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.DELETE,
                                    tooltip="Elimina",
                                    on_click=self._make_handler(self.confirm_delete_batch, b['id']),
                                    disabled=not self.edit_mode,
                                    icon_color=ft.Colors.RED_400,
                                ),
                            ], spacing=0),
                        ),
                    ],
                )
            )
        
        table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("ID")),
                ft.DataColumn(ft.Text("Prodotto")),
                ft.DataColumn(ft.Text("Composizione")),
                ft.DataColumn(ft.Text("Fornitore")),
                ft.DataColumn(ft.Text("Acquisto")),
                ft.DataColumn(ft.Text("Scadenza")),
                ft.DataColumn(ft.Text("Fiale")),
                ft.DataColumn(ft.Text("Prep")),
                ft.DataColumn(ft.Text("Azioni")),
            ],
            rows=rows,
        )
        
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
    
    def show_batch_details(self, batch_id):
        """Mostra dettagli batch in dialog."""
        print(f"🔍 DEBUG: show_batch_details chiamato con ID={batch_id}")
        batch = self.manager.get_batch_details(batch_id)
        
        if not batch:
            return
        
        # Composizione
        comp_text = "\n".join([f"• {c['name']}: {c['mg_per_vial']}mg/fiala" 
                               for c in batch['composition']])
        
        # Certificati
        cert_text = f"{len(batch['certificates'])} certificati" if batch['certificates'] else "Nessun certificato"
        
        # Preparazioni
        prep_text = f"{len(batch['preparations'])} preparazioni" if batch['preparations'] else "Nessuna preparazione"
        
        dialog = ft.AlertDialog(
            title=ft.Text(f"Batch #{batch_id} - {batch['product_name']}"),
            content=ft.Column([
                ft.Text(f"Fornitore: {batch['supplier_name']} ({batch['supplier_country']})"),
                ft.Text(f"Acquisto: {batch['purchase_date']}"),
                ft.Text(f"Scadenza: {batch.get('expiry_date', 'N/A')}"),
                ft.Text(f"Fiale: {batch['vials_remaining']}/{batch['vials_count']}"),
                ft.Text(f"Prezzo: {batch['total_price']:.2f} {batch['currency']}"),
                ft.Divider(),
                ft.Text("Composizione:", weight=ft.FontWeight.BOLD),
                ft.Text(comp_text),
                ft.Divider(),
                ft.Text(f"Certificati: {cert_text}"),
                ft.Text(f"Preparazioni: {prep_text}"),
            ], tight=True, scroll=ft.ScrollMode.AUTO, height=400),
            actions=[
                ft.TextButton("Chiudi", on_click=lambda e: self.close_dialog(dialog)),
            ],
        )
        
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()
    
    def show_add_batch_dialog(self, e):
        """Dialog aggiungi batch completo."""
        # Recupera fornitori e peptidi
        suppliers = self.manager.get_suppliers()
        peptides = self.manager.get_peptides()
        
        if not suppliers:
            self.show_snackbar("Aggiungi prima un fornitore!", error=True)
            return
        
        if not peptides:
            self.show_snackbar("Aggiungi prima dei peptidi!", error=True)
            return
        
        # Campi form
        supplier_dd = ft.Dropdown(
            label="Fornitore",
            options=[ft.dropdown.Option(str(s['id']), s['name']) for s in suppliers],
            width=400,
        )
        
        product_field = ft.TextField(label="Nome Prodotto", width=400)
        vials_field = ft.TextField(label="Numero Fiale", width=200, value="1", keyboard_type=ft.KeyboardType.NUMBER)
        price_field = ft.TextField(label="Prezzo Totale (€)", width=200, value="0", keyboard_type=ft.KeyboardType.NUMBER)
        
        # Data acquisto (oggi)
        purchase_field = ft.TextField(
            label="Data Acquisto (YYYY-MM-DD)",
            value=datetime.now().strftime('%Y-%m-%d'),
            width=200,
        )
        
        # Data scadenza (default +1 anno)
        expiry_field = ft.TextField(
            label="Data Scadenza (YYYY-MM-DD)",
            value=(datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d'),
            width=200,
        )
        
        storage_field = ft.TextField(label="Luogo Conservazione", value="Frigo", width=300)
        
        # Composizione peptidi (multi-select)
        peptide_checkboxes = []
        peptide_mg_fields = {}
        
        for p in peptides:
            cb = ft.Checkbox(label=p['name'], value=False)
            mg_field = ft.TextField(
                label=f"mg per fiala",
                width=150,
                value="5",
                keyboard_type=ft.KeyboardType.NUMBER,
                visible=False,
            )
            
            def on_checkbox_change(e, field=mg_field):
                field.visible = e.control.value
                self.page.update()
            
            cb.on_change = on_checkbox_change
            peptide_checkboxes.append(cb)
            peptide_mg_fields[p['id']] = (cb, mg_field)
        
        def add_batch(e):
            print("\n=== DEBUG add_batch chiamato ===")
            try:
                # Validazioni
                print(f"Supplier: {supplier_dd.value}")
                if not supplier_dd.value:
                    self.show_snackbar("Seleziona un fornitore!", error=True)
                    return
                
                print(f"Product: {product_field.value}")
                if not product_field.value:
                    self.show_snackbar("Inserisci nome prodotto!", error=True)
                    return
                
                # Peptidi selezionati
                composition_dict = {}
                print(f"Checking peptides...")
                for pid, (cb, mg_field) in peptide_mg_fields.items():
                    print(f"  Peptide {pid}: checked={cb.value}, mg={mg_field.value}")
                    if cb.value:
                        try:
                            mg = float(mg_field.value)
                            if mg <= 0:
                                raise ValueError()
                            composition_dict[pid] = mg
                        except Exception as e:
                            print(f"  ERROR parsing mg: {e}")
                            self.show_snackbar(f"Inserisci mg validi per {cb.label}!", error=True)
                            return
                
                print(f"Composition dict: {composition_dict}")
                if not composition_dict:
                    self.show_snackbar("Seleziona almeno un peptide!", error=True)
                    return
                
                # Converti composition da dict {pid: mg} a List[Tuple[name, mg]]
                all_peptides = self.manager.get_peptides()
                peptide_map = {p['id']: p['name'] for p in all_peptides}
                
                composition_list = []
                total_mg = 0
                for pid, mg in composition_dict.items():
                    peptide_name = peptide_map.get(pid)
                    if not peptide_name:
                        self.show_snackbar(f"Peptide ID {pid} non trovato!", error=True)
                        return
                    composition_list.append((peptide_name, mg))
                    total_mg += mg
                
                print(f"Composition list: {composition_list}")
                print(f"Total mg per vial: {total_mg}")
                
                # Ottieni supplier_name da supplier_id
                suppliers = self.manager.get_suppliers()
                supplier_name = None
                for s in suppliers:
                    if s['id'] == int(supplier_dd.value):
                        supplier_name = s['name']
                        break
                
                if not supplier_name:
                    self.show_snackbar("Fornitore non trovato!", error=True)
                    return
                
                print(f"Supplier name: {supplier_name}")
                
                # Aggiungi batch con parametri corretti
                print(f"Calling manager.add_batch...")
                batch_id = self.manager.add_batch(
                    supplier_name=supplier_name,  # ✅ Nome fornitore
                    product_name=product_field.value,
                    vials_count=int(vials_field.value),
                    mg_per_vial=total_mg,  # ✅ Totale mg per fiala
                    total_price=float(price_field.value),
                    purchase_date=purchase_field.value,
                    composition=composition_list,  # ✅ List[Tuple[name, mg]]
                    expiry_date=expiry_field.value if expiry_field.value else None,
                    storage_location=storage_field.value if storage_field.value else None,
                )
                
                print(f"Batch created with ID: {batch_id}")
                self.close_dialog()
                self.update_content()
                self.show_snackbar(f"Batch #{batch_id} aggiunto con successo!")
                
            except Exception as ex:
                print(f"EXCEPTION in add_batch: {ex}")
                import traceback
                traceback.print_exc()
                self.show_snackbar(f"Errore: {ex}", error=True)
        
        dialog = ft.AlertDialog(
            title=ft.Text("Aggiungi Batch"),
            content=ft.Column([
                supplier_dd,
                product_field,
                ft.Row([vials_field, price_field]),
                ft.Row([purchase_field, expiry_field]),
                storage_field,
                ft.Divider(),
                ft.Text("Composizione Peptidi:", weight=ft.FontWeight.BOLD),
                *[ft.Row([cb, mg_field]) for cb, mg_field in [peptide_mg_fields[p['id']] for p in peptides]],
            ], tight=True, scroll=ft.ScrollMode.AUTO, height=500),
            actions=[
                ft.TextButton("Annulla", on_click=lambda e: self.close_dialog(dialog)),
                ft.ElevatedButton("Aggiungi", on_click=add_batch),
            ],
        )
        
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()
    
    def show_edit_batch_dialog(self, batch_id):
        """Dialog modifica batch COMPLETO - tutti i campi editabili."""
        batch = self.manager.get_batch_details(batch_id)
        if not batch:
            return
        
        # Recupera fornitori e peptidi per i dropdown
        suppliers = self.manager.get_suppliers()
        peptides = self.manager.get_peptides()
        
        # Campi modificabili - TUTTI
        supplier_dd = ft.Dropdown(
            label="Fornitore",
            value=str(batch['supplier_id']),
            options=[ft.dropdown.Option(str(s['id']), s['name']) for s in suppliers],
            width=400,
        )
        
        product_field = ft.TextField(
            label="Nome Prodotto", 
            value=batch['product_name'], 
            width=400
        )
        
        vials_field = ft.TextField(
            label="Numero Fiale Totali",
            value=str(batch['vials_count']),
            width=200,
            keyboard_type=ft.KeyboardType.NUMBER,
            hint_text="Fiale originali + aggiunte"
        )
        
        vials_remaining_field = ft.TextField(
            label="Fiale Rimanenti",
            value=str(batch['vials_remaining']),
            width=200,
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        
        price_field = ft.TextField(
            label="Prezzo Totale (€)",
            value=str(batch.get('total_price', 0)),
            width=200,
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        
        purchase_field = ft.TextField(
            label="Data Acquisto (YYYY-MM-DD)",
            value=batch.get('purchase_date', ''),
            width=200,
        )
        
        expiry_field = ft.TextField(
            label="Data Scadenza (YYYY-MM-DD)",
            value=batch.get('expiry_date', ''),
            width=200,
        )
        
        storage_field = ft.TextField(
            label="Luogo Conservazione",
            value=batch.get('storage_location', ''),
            width=300,
        )
        
        # Composizione peptidi (checkbox con mg)
        # Converti composition da lista di dict a dict {pid: mg}
        current_composition_list = batch.get('composition', [])
        current_composition = {}
        if current_composition_list:
            for item in current_composition_list:
                # item = {'id': 1, 'name': 'BPC-157', 'mg_per_vial': 5.0}
                pid = item.get('id')
                mg = item.get('mg_per_vial', 5)
                if pid:
                    current_composition[pid] = mg
        
        print(f"Current composition dict: {current_composition}")
        
        peptide_checkboxes = []
        peptide_mg_fields = {}
        
        for p in peptides:
            pid = p['id']
            # Pre-seleziona se già presente
            is_selected = pid in current_composition
            current_mg = current_composition.get(pid, 5)
            
            cb = ft.Checkbox(
                label=p['name'], 
                value=is_selected
            )
            mg_field = ft.TextField(
                label=f"mg per fiala",
                width=150,
                value=str(current_mg),
                keyboard_type=ft.KeyboardType.NUMBER,
                visible=is_selected,
            )
            
            def on_checkbox_change(e, field=mg_field):
                field.visible = e.control.value
                self.page.update()
            
            cb.on_change = on_checkbox_change
            peptide_checkboxes.append(cb)
            peptide_mg_fields[pid] = (cb, mg_field)
        
        def update_batch(e):
            print(f"\n=== DEBUG update_batch #{batch_id} ===")
            try:
                changes = {}
                
                # ✅ TUTTI I CAMPI SONO ORA SUPPORTATI!
                
                # Fornitore ✅
                if int(supplier_dd.value) != batch['supplier_id']:
                    changes['supplier_id'] = int(supplier_dd.value)
                    print(f"  Changed supplier_id: {changes['supplier_id']}")
                
                # Nome prodotto ✅
                if product_field.value != batch['product_name']:
                    changes['product_name'] = product_field.value
                    print(f"  Changed product_name: {changes['product_name']}")
                
                # Fiale totali ✅
                if int(vials_field.value) != batch['vials_count']:
                    changes['vials_count'] = int(vials_field.value)
                    print(f"  Changed vials_count: {changes['vials_count']}")
                
                # Fiale rimanenti ✅
                if int(vials_remaining_field.value) != batch['vials_remaining']:
                    changes['vials_remaining'] = int(vials_remaining_field.value)
                    print(f"  Changed vials_remaining: {changes['vials_remaining']}")
                
                # Prezzo ✅
                new_price = float(price_field.value)
                if new_price != batch.get('total_price', 0):
                    changes['total_price'] = new_price
                    print(f"  Changed total_price: {changes['total_price']}")
                
                # Date ✅
                if purchase_field.value != (batch.get('purchase_date') or ''):
                    changes['purchase_date'] = purchase_field.value if purchase_field.value else None
                    print(f"  Changed purchase_date: {changes['purchase_date']}")
                
                if expiry_field.value != (batch.get('expiry_date') or ''):
                    changes['expiry_date'] = expiry_field.value if expiry_field.value else None
                    print(f"  Changed expiry_date: {changes['expiry_date']}")
                
                # Storage ✅
                if storage_field.value != (batch.get('storage_location') or ''):
                    changes['storage_location'] = storage_field.value if storage_field.value else None
                    print(f"  Changed storage_location: {changes['storage_location']}")
                
                # Composizione ✅
                new_composition = {}
                for pid, (cb, mg_field) in peptide_mg_fields.items():
                    if cb.value:
                        new_composition[pid] = float(mg_field.value)
                
                if new_composition != current_composition:
                    changes['composition'] = new_composition
                    print(f"  Changed composition: {changes['composition']}")
                
                if changes:
                    print(f"Calling manager.update_batch with changes: {changes}")
                    self.manager.update_batch(batch_id, **changes)
                    self.close_dialog()
                    self.update_content()
                    self.show_snackbar(f"✅ Batch #{batch_id} aggiornato completamente!")
                else:
                    self.show_snackbar("Nessuna modifica")
                    
            except Exception as ex:
                print(f"EXCEPTION in update_batch: {ex}")
                import traceback
                traceback.print_exc()
                self.show_snackbar(f"Errore: {ex}", error=True)
        
        dialog = ft.AlertDialog(
            title=ft.Text(f"Modifica Batch #{batch_id}"),
            content=ft.Column([
                ft.Text("✅ TUTTI I CAMPI SONO MODIFICABILI!", 
                       size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_400),
                ft.Text("Modifica tutto ciò che serve per correggere errori di inserimento", 
                       size=12, color=ft.Colors.GREY_400),
                ft.Divider(),
                supplier_dd,
                product_field,
                ft.Row([vials_field, vials_remaining_field]),
                ft.Row([price_field, purchase_field]),
                ft.Row([expiry_field, storage_field]),
                ft.Divider(),
                ft.Text("Composizione Peptidi:", weight=ft.FontWeight.BOLD),
                *[ft.Row([cb, mg_field]) for cb, mg_field in [peptide_mg_fields[p['id']] for p in peptides]],
            ], tight=True, scroll=ft.ScrollMode.AUTO, height=500),
            actions=[
                ft.TextButton("Annulla", on_click=lambda e: self.close_dialog(dialog)),
                ft.ElevatedButton("Salva", on_click=update_batch),
            ],
        )
        
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()
    
    # ============================================================
    # PEPTIDES
    # ============================================================
    
    def build_peptides(self):
        """Costruisce vista peptidi."""
        peptides = self.manager.get_peptides()
        peptides_sorted = sorted(peptides, key=lambda x: x['id'])
        
        # Toolbar
        toolbar = ft.Row([
            ft.Text("Peptidi", size=32, weight=ft.FontWeight.BOLD),
            ft.Container(expand=True),
            ft.ElevatedButton(
                "Aggiungi Peptide",
                icon=ft.Icons.ADD,
                on_click=self.show_add_peptide_dialog,
            ),
        ])
        
        # Tabella
        rows = []
        for p in peptides_sorted:
            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(f"#{p['id']}")),
                        ft.DataCell(ft.Text(p['name'])),
                        ft.DataCell(ft.Text(p['description'][:50] if p['description'] else "")),
                        ft.DataCell(ft.Text(p['common_uses'][:30] if p['common_uses'] else "")),
                        ft.DataCell(
                            ft.Row([
                                ft.IconButton(
                                    icon=ft.Icons.VISIBILITY,
                                    tooltip="Dettagli",
                                    on_click=self._make_handler(self.show_peptide_details, p['id']),
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.EDIT,
                                    tooltip="Modifica",
                                    on_click=self._make_handler(self.show_edit_peptide_dialog, p['id']),
                                    disabled=not self.edit_mode,
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.DELETE,
                                    tooltip="Elimina",
                                    on_click=self._make_handler(self.confirm_delete_peptide, p['id']),
                                    disabled=not self.edit_mode,
                                    icon_color=ft.Colors.RED_400,
                                ),
                            ], spacing=0),
                        ),
                    ],
                )
            )
        
        table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("ID")),
                ft.DataColumn(ft.Text("Nome")),
                ft.DataColumn(ft.Text("Descrizione")),
                ft.DataColumn(ft.Text("Usi")),
                ft.DataColumn(ft.Text("Azioni")),
            ],
            rows=rows,
        )
        
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
    
    def show_peptide_details(self, peptide_id):
        """Mostra dettagli peptide."""
        peptide = self.manager.get_peptide_by_id(peptide_id)
        if not peptide:
            return
        
        dialog = ft.AlertDialog(
            title=ft.Text(f"Peptide #{peptide_id} - {peptide['name']}"),
            content=ft.Column([
                ft.Text(f"Descrizione: {peptide['description'] or 'N/A'}"),
                ft.Text(f"Usi: {peptide['common_uses'] or 'N/A'}"),
                ft.Text(f"Note: {peptide['notes'] or 'N/A'}"),
            ], tight=True),
            actions=[
                ft.TextButton("Chiudi", on_click=lambda e: self.close_dialog(dialog)),
            ],
        )
        
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()
    
    def show_add_peptide_dialog(self, e):
        """Dialog aggiungi peptide."""
        name_field = ft.TextField(label="Nome", autofocus=True)
        desc_field = ft.TextField(label="Descrizione", multiline=True)
        uses_field = ft.TextField(label="Usi comuni", multiline=True)
        notes_field = ft.TextField(label="Note", multiline=True)
        
        def add_peptide(e):
            try:
                if not name_field.value:
                    self.show_snackbar("Inserisci un nome!", error=True)
                    return
                
                peptide_id = self.manager.add_peptide(
                    name=name_field.value,
                    description=desc_field.value if desc_field.value else None,
                    common_uses=uses_field.value if uses_field.value else None,
                    notes=notes_field.value if notes_field.value else None,
                )
                self.close_dialog()
                self.update_content()
                self.show_snackbar(f"Peptide '{name_field.value}' aggiunto!")
            except Exception as ex:
                self.show_snackbar(f"Errore: {ex}", error=True)
        
        dialog = ft.AlertDialog(
            title=ft.Text("Aggiungi Peptide"),
            content=ft.Column([
                name_field,
                desc_field,
                uses_field,
                notes_field,
            ], tight=True, scroll=ft.ScrollMode.AUTO, height=400),
            actions=[
                ft.TextButton("Annulla", on_click=lambda e: self.close_dialog(dialog)),
                ft.ElevatedButton("Aggiungi", on_click=add_peptide),
            ],
        )
        
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()
    
    def show_edit_peptide_dialog(self, peptide_id):
        """Dialog modifica peptide."""
        peptide = self.manager.get_peptide_by_id(peptide_id)
        if not peptide:
            return
        
        name_field = ft.TextField(label="Nome", value=peptide['name'])
        desc_field = ft.TextField(label="Descrizione", value=peptide['description'] or "", multiline=True)
        uses_field = ft.TextField(label="Usi comuni", value=peptide['common_uses'] or "", multiline=True)
        notes_field = ft.TextField(label="Note", value=peptide['notes'] or "", multiline=True)
        
        def update_peptide(e):
            try:
                changes = {}
                if name_field.value != peptide['name']:
                    changes['name'] = name_field.value
                if desc_field.value != (peptide['description'] or ''):
                    changes['description'] = desc_field.value if desc_field.value else None
                if uses_field.value != (peptide['common_uses'] or ''):
                    changes['common_uses'] = uses_field.value if uses_field.value else None
                if notes_field.value != (peptide['notes'] or ''):
                    changes['notes'] = notes_field.value if notes_field.value else None
                
                if changes:
                    self.manager.update_peptide(peptide_id, **changes)
                    self.close_dialog()
                    self.update_content()
                    self.show_snackbar(f"Peptide #{peptide_id} aggiornato!")
                else:
                    self.show_snackbar("Nessuna modifica")
            except Exception as ex:
                self.show_snackbar(f"Errore: {ex}", error=True)
        
        dialog = ft.AlertDialog(
            title=ft.Text(f"Modifica Peptide #{peptide_id}"),
            content=ft.Column([
                name_field,
                desc_field,
                uses_field,
                notes_field,
            ], tight=True, scroll=ft.ScrollMode.AUTO, height=400),
            actions=[
                ft.TextButton("Annulla", on_click=lambda e: self.close_dialog(dialog)),
                ft.ElevatedButton("Salva", on_click=update_peptide),
            ],
        )
        
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()
    
    # ============================================================
    # SUPPLIERS
    # ============================================================
    
    def build_suppliers(self):
        """Costruisce vista fornitori."""
        suppliers = self.manager.get_suppliers()
        suppliers_sorted = sorted(suppliers, key=lambda x: x['id'])
        
        toolbar = ft.Row([
            ft.Text("Fornitori", size=32, weight=ft.FontWeight.BOLD),
            ft.Container(expand=True),
            ft.ElevatedButton(
                "Aggiungi Fornitore",
                icon=ft.Icons.ADD,
                on_click=self.show_add_supplier_dialog,
            ),
        ])
        
        rows = []
        for s in suppliers_sorted:
            rating = "★" * (s['reliability_rating'] or 0)
            
            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(f"#{s['id']}")),
                        ft.DataCell(ft.Text(s['name'])),
                        ft.DataCell(ft.Text(s['country'] or 'N/A')),
                        ft.DataCell(ft.Text(rating if rating else "N/A")),
                        ft.DataCell(
                            ft.Row([
                                ft.IconButton(
                                    icon=ft.Icons.VISIBILITY,
                                    tooltip="Dettagli",
                                    on_click=self._make_handler(self.show_supplier_details, s['id']),
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.EDIT,
                                    tooltip="Modifica",
                                    on_click=self._make_handler(self.show_edit_supplier_dialog, s['id']),
                                    disabled=not self.edit_mode,
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.DELETE,
                                    tooltip="Elimina",
                                    on_click=self._make_handler(self.confirm_delete_supplier, s['id']),
                                    disabled=not self.edit_mode,
                                    icon_color=ft.Colors.RED_400,
                                ),
                            ], spacing=0),
                        ),
                    ],
                )
            )
        
        table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("ID")),
                ft.DataColumn(ft.Text("Nome")),
                ft.DataColumn(ft.Text("Paese")),
                ft.DataColumn(ft.Text("Rating")),
                ft.DataColumn(ft.Text("Azioni")),
            ],
            rows=rows,
        )
        
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
    
    def show_supplier_details(self, supplier_id):
        """Mostra dettagli fornitore."""
        suppliers = self.manager.get_suppliers()
        supplier = next((s for s in suppliers if s['id'] == supplier_id), None)
        if not supplier:
            return
        
        cursor = self.manager.conn.cursor()
        cursor.execute('''
            SELECT COUNT(*), SUM(total_price), SUM(vials_count)
            FROM batches WHERE supplier_id = ?
        ''', (supplier_id,))
        orders, spent, vials = cursor.fetchone()
        
        dialog = ft.AlertDialog(
            title=ft.Text(f"Fornitore #{supplier_id} - {supplier['name']}"),
            content=ft.Column([
                ft.Text(f"Paese: {supplier['country'] or 'N/A'}"),
                ft.Text(f"Website: {supplier['website'] or 'N/A'}"),
                ft.Text(f"Email: {supplier['email'] or 'N/A'}"),
                ft.Text(f"Rating: {'★' * (supplier['reliability_rating'] or 0)} ({supplier['reliability_rating'] or 0}/5)"),
                ft.Divider(),
                ft.Text("Statistiche:", weight=ft.FontWeight.BOLD),
                ft.Text(f"Ordini totali: {orders or 0}"),
                ft.Text(f"Spesa totale: €{spent or 0:.2f}"),
                ft.Text(f"Fiale acquistate: {vials or 0}"),
            ], tight=True),
            actions=[
                ft.TextButton("Chiudi", on_click=lambda e: self.close_dialog(dialog)),
            ],
        )
        
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()
    
    def show_add_supplier_dialog(self, e):
        """Dialog aggiungi fornitore completo."""
        name_field = ft.TextField(label="Nome", autofocus=True, width=400)
        country_field = ft.TextField(label="Paese", width=200)
        website_field = ft.TextField(label="Website", width=400)
        email_field = ft.TextField(label="Email", width=300)
        
        rating_dd = ft.Dropdown(
            label="Rating Affidabilità",
            options=[
                ft.dropdown.Option("1", "★ (1/5)"),
                ft.dropdown.Option("2", "★★ (2/5)"),
                ft.dropdown.Option("3", "★★★ (3/5)"),
                ft.dropdown.Option("4", "★★★★ (4/5)"),
                ft.dropdown.Option("5", "★★★★★ (5/5)"),
            ],
            width=200,
        )
        
        notes_field = ft.TextField(label="Note", multiline=True, width=400)
        
        def add_supplier(e):
            print("\n=== DEBUG add_supplier chiamato ===")
            try:
                print(f"Name: {name_field.value}")
                if not name_field.value:
                    self.show_snackbar("Inserisci un nome!", error=True)
                    return
                
                print(f"Calling manager.add_supplier...")
                supplier_id = self.manager.add_supplier(
                    name=name_field.value,
                    country=country_field.value if country_field.value else None,
                    website=website_field.value if website_field.value else None,
                    email=email_field.value if email_field.value else None,
                    rating=int(rating_dd.value) if rating_dd.value else None,  # ✅ rating non reliability_rating
                    notes=notes_field.value if notes_field.value else None,
                )
                
                print(f"Supplier created with ID: {supplier_id}")
                self.close_dialog()
                self.update_content()
                self.show_snackbar(f"Fornitore '{name_field.value}' aggiunto!")
                
            except Exception as ex:
                print(f"EXCEPTION in add_supplier: {ex}")
                import traceback
                traceback.print_exc()
                self.show_snackbar(f"Errore: {ex}", error=True)
        
        dialog = ft.AlertDialog(
            title=ft.Text("Aggiungi Fornitore"),
            content=ft.Column([
                name_field,
                country_field,
                website_field,
                email_field,
                rating_dd,
                notes_field,
            ], tight=True, scroll=ft.ScrollMode.AUTO, height=450),
            actions=[
                ft.TextButton("Annulla", on_click=lambda e: self.close_dialog(dialog)),
                ft.ElevatedButton("Aggiungi", on_click=add_supplier),
            ],
        )
        
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()
    
    def show_edit_supplier_dialog(self, supplier_id):
        """Dialog modifica fornitore completo."""
        suppliers = self.manager.get_suppliers()
        supplier = next((s for s in suppliers if s['id'] == supplier_id), None)
        if not supplier:
            return
        
        name_field = ft.TextField(label="Nome", value=supplier['name'], width=400)
        country_field = ft.TextField(label="Paese", value=supplier['country'] or "", width=200)
        website_field = ft.TextField(label="Website", value=supplier['website'] or "", width=400)
        email_field = ft.TextField(label="Email", value=supplier['email'] or "", width=300)
        
        rating_dd = ft.Dropdown(
            label="Rating Affidabilità",
            value=str(supplier['reliability_rating']) if supplier['reliability_rating'] else None,
            options=[
                ft.dropdown.Option("1", "★ (1/5)"),
                ft.dropdown.Option("2", "★★ (2/5)"),
                ft.dropdown.Option("3", "★★★ (3/5)"),
                ft.dropdown.Option("4", "★★★★ (4/5)"),
                ft.dropdown.Option("5", "★★★★★ (5/5)"),
            ],
            width=200,
        )
        
        notes_field = ft.TextField(label="Note", value=supplier['notes'] or "", multiline=True, width=400)
        
        def update_supplier(e):
            try:
                changes = {}
                
                if name_field.value != supplier['name']:
                    changes['name'] = name_field.value
                if country_field.value != (supplier['country'] or ''):
                    changes['country'] = country_field.value if country_field.value else None
                if website_field.value != (supplier['website'] or ''):
                    changes['website'] = website_field.value if website_field.value else None
                if email_field.value != (supplier['email'] or ''):
                    changes['email'] = email_field.value if email_field.value else None
                if rating_dd.value and int(rating_dd.value) != (supplier['reliability_rating'] or 0):
                    changes['reliability_rating'] = int(rating_dd.value)
                if notes_field.value != (supplier['notes'] or ''):
                    changes['notes'] = notes_field.value if notes_field.value else None
                
                if changes:
                    self.manager.update_supplier(supplier_id, **changes)
                    self.close_dialog()
                    self.update_content()
                    self.show_snackbar(f"Fornitore #{supplier_id} aggiornato!")
                else:
                    self.show_snackbar("Nessuna modifica")
                    
            except Exception as ex:
                self.show_snackbar(f"Errore: {ex}", error=True)
        
        dialog = ft.AlertDialog(
            title=ft.Text(f"Modifica Fornitore #{supplier_id}"),
            content=ft.Column([
                name_field,
                country_field,
                website_field,
                email_field,
                rating_dd,
                notes_field,
            ], tight=True, scroll=ft.ScrollMode.AUTO, height=450),
            actions=[
                ft.TextButton("Annulla", on_click=lambda e: self.close_dialog(dialog)),
                ft.ElevatedButton("Salva", on_click=update_supplier),
            ],
        )
        
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()
    
    # ============================================================
    # PREPARATIONS
    # ============================================================
    
    def build_preparations(self):
        """Costruisce vista preparazioni."""
        preps = self.manager.get_preparations(only_active=True)
        preps_sorted = sorted(preps, key=lambda x: x['id'])
        
        toolbar = ft.Row([
            ft.Text("Preparazioni", size=32, weight=ft.FontWeight.BOLD),
            ft.Container(expand=True),
            ft.ElevatedButton(
                "Nuova Preparazione",
                icon=ft.Icons.ADD,
                on_click=self.show_add_preparation_dialog,
            ),
        ])
        
        rows = []
        for p in preps_sorted:
            percentage = (p['volume_remaining_ml'] / p['volume_ml'] * 100) if p['volume_ml'] > 0 else 0
            
            # Disabilita somministrazione se volume esaurito
            can_administer = p['volume_remaining_ml'] > 0
            
            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(f"#{p['id']}")),
                        ft.DataCell(ft.Text(p['batch_product'][:30])),
                        ft.DataCell(ft.Text(f"{p['volume_remaining_ml']:.1f}/{p['volume_ml']:.1f}ml")),
                        ft.DataCell(ft.Text(f"{percentage:.0f}%")),
                        ft.DataCell(ft.Text(p['expiry_date'] or 'N/A')),
                        ft.DataCell(
                            ft.Row([
                                ft.IconButton(
                                    icon=ft.Icons.VISIBILITY,
                                    tooltip="Dettagli",
                                    on_click=self._make_handler(self.show_preparation_details, p['id']),
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.EDIT,
                                    tooltip="Modifica",
                                    on_click=self._make_handler(self.show_edit_preparation_dialog, p['id']),
                                    disabled=not self.edit_mode,
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.DELETE,
                                    tooltip="Elimina",
                                    on_click=self._make_handler(self.confirm_delete_preparation, p['id']),
                                    disabled=not self.edit_mode,
                                    icon_color=ft.Colors.RED_400,
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.MEDICATION,
                                    tooltip="Registra Somministrazione",
                                    on_click=self._create_administer_handler(p['id']),
                                    disabled=not can_administer,
                                    icon_color=ft.Colors.GREEN_400 if can_administer else ft.Colors.GREY_600,
                                ),
                            ], spacing=0),
                        ),
                    ],
                )
            )
        
        table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("ID")),
                ft.DataColumn(ft.Text("Batch")),
                ft.DataColumn(ft.Text("Volume")),
                ft.DataColumn(ft.Text("%")),
                ft.DataColumn(ft.Text("Scadenza")),
                ft.DataColumn(ft.Text("Azioni")),
            ],
            rows=rows,
        )
        
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
    
    def show_preparation_details(self, prep_id):
        """Mostra dettagli preparazione."""
        prep = self.manager.get_preparation_details(prep_id)
        if not prep:
            return
        
        # Build content with wastage info if present
        content_items = [
            ft.Text(f"Batch: {prep['product_name']}"),
            ft.Text(f"Data: {prep['preparation_date']}"),
            ft.Text(f"Scadenza: {prep['expiry_date']}"),
            ft.Text(f"Volume: {prep['volume_remaining_ml']:.1f}/{prep['volume_ml']}ml"),
            ft.Text(f"Concentrazione: {prep['concentration_mg_ml']:.3f}mg/ml ({prep['concentration_mg_ml']*1000:.1f}mcg/ml)"),
            ft.Text(f"Fiale usate: {prep['vials_used']}"),
            ft.Text(f"Diluente: {prep['diluent']}"),
            ft.Text(f"Somministrazioni: {prep['administrations_count']}"),
        ]
        
        # Add wastage information if present
        if prep.get('wastage_ml') and prep['wastage_ml'] > 0:
            content_items.append(ft.Divider())
            content_items.append(ft.Text(f"⚠️ Spreco Registrato: {prep['wastage_ml']:.2f} ml", color=ft.colors.ORANGE))
            if prep.get('wastage_reason'):
                reason_labels = {
                    'spillage': 'Fuoriuscita',
                    'measurement_error': 'Errore Misurazione',
                    'contamination': 'Contaminazione',
                    'other': 'Altro'
                }
                reason_text = reason_labels.get(prep['wastage_reason'], prep['wastage_reason'])
                content_items.append(ft.Text(f"Motivo: {reason_text}"))
            if prep.get('wastage_notes'):
                content_items.append(ft.Text(f"Note Spreco:", weight=ft.FontWeight.BOLD, size=12))
                content_items.append(ft.Text(prep['wastage_notes'], size=11, italic=True))
        
        dialog = ft.AlertDialog(
            title=ft.Text(f"Preparazione #{prep_id}"),
            content=ft.Column(content_items, tight=True, scroll=ft.ScrollMode.AUTO),
            actions=[
                ft.TextButton("Registra Spreco", on_click=lambda e: self._show_wastage_dialog(prep_id, dialog)),
                ft.TextButton("Chiudi", on_click=lambda e: self.close_dialog(dialog)),
            ],
        )
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()
    
    def _show_wastage_dialog(self, prep_id, parent_dialog=None):
        """Mostra dialog per registrare spreco."""
        prep = self.manager.get_preparation_details(prep_id)
        if not prep:
            self.show_snackbar("❌ Preparazione non trovata", error=True)
            return
        
        # Chiudi dialog genitore se esiste
        if parent_dialog:
            parent_dialog.open = False
        
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
                # Validazione campo vuoto
                if not volume_field.value or volume_field.value.strip() == '':
                    self.show_snackbar("❌ Inserisci il volume sprecato", error=True)
                    return
                
                volume = float(volume_field.value)
                
                if volume <= 0:
                    self.show_snackbar("❌ Volume deve essere > 0", error=True)
                    return
                
                success, message = self.manager.record_wastage(
                    prep_id=prep_id,
                    volume_ml=volume,
                    reason=reason_dropdown.value,
                    notes=notes_field.value if notes_field.value else None
                )
                
                if success:
                    self.show_snackbar(f"✅ {message}")
                    self.close_dialog(dialog)
                    self.update_content()
                else:
                    self.show_snackbar(f"❌ {message}", error=True)
                    
            except ValueError:
                self.show_snackbar("❌ Inserisci un numero valido per il volume", error=True)
            except Exception as ex:
                self.show_snackbar(f"❌ Errore: {str(ex)}", error=True)
        
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
                ft.TextButton("Annulla", on_click=lambda e: self.close_dialog(dialog)),
                ft.ElevatedButton("Registra", on_click=save_wastage),
            ],
        )
        
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()
    
    
    def _show_register_dialog(self, tasks):
        """Mostra dialog pre-compilato per registrare somministrazione da checklist (con supporto multi-prep)."""
        try:
            from datetime import datetime
            
            # Estrai info comuni dal primo task
            first_task = tasks[0]
            prep_id = first_task.get('preparation_id')
            suggested_ml = first_task.get('suggested_dose_ml')
            cycle_id = first_task.get('cycle_id')
            protocol_id = first_task.get('protocol_id')
            
            # Nome peptidi combinati
            peptide_names = " + ".join([t.get('peptide_name', '?') for t in tasks])
            
            # Dose totale in mcg
            total_dose_mcg = sum([t.get('ramped_dose_mcg', t.get('target_dose_mcg', 0)) for t in tasks])
            
            # Prep details
            prep = self.manager.get_preparation_details(prep_id)
            if not prep:
                self.show_snackbar("❌ Preparazione non trovata", error=True)
                return
            
            # Calcola sempre distribuzione FIFO per consumare preparazioni più vecchie per prime
            needs_multi_prep = False
            multi_prep_distribution = []
            multi_prep_warning = None
            
            if suggested_ml:
                # Recupera tutte le preparazioni disponibili dello stesso batch
                batch_id = prep.get('batch_id')
                all_preps = self.manager.get_preparations(batch_id=batch_id, only_active=True)
                available_preps = [
                    {
                        'id': p['id'],
                        'volume_remaining_ml': p['volume_remaining_ml'],
                        'expiry_date': p['expiry_date']
                    }
                    for p in all_preps if p['volume_remaining_ml'] > 0.01
                ]
                
                # Calcola distribuzione FIFO
                success, distribution, message = self.manager.calculate_multi_prep_distribution(
                    required_ml=suggested_ml,
                    available_preps=available_preps
                )
                
                if success:
                    multi_prep_distribution = distribution
                    # Se usa più di una preparazione, mostra warning
                    if len(distribution) > 1:
                        needs_multi_prep = True
                        # Crea testo informativo
                        breakdown_text = "Verranno utilizzate multiple preparazioni (FIFO per scadenza):\n"
                        for d in distribution:
                            breakdown_text += f"  • Prep #{d['prep_id']}: {d['ml']:.2f} ml (scade {d.get('expiry_date', 'N/A')})\n"
                        multi_prep_warning = ft.Container(
                            content=ft.Column([
                                ft.Text("⚠️ MULTI-PREPARAZIONE (FIFO)", 
                                       color=ft.Colors.ORANGE_700, 
                                       weight=ft.FontWeight.BOLD),
                                ft.Text(breakdown_text, size=12, color=ft.Colors.GREY_700),
                            ], tight=True),
                            bgcolor=ft.Colors.ORANGE_50,
                            padding=10,
                            border_radius=5,
                        )
                else:
                    # Impossibile distribuire
                    self.show_snackbar(f"❌ {message}", error=True)
                    return
            
            # Campi pre-compilati
            dose_field = ft.TextField(
                label="Dose (ml)",
                value=f"{suggested_ml:.2f}" if suggested_ml else "",
                keyboard_type=ft.KeyboardType.NUMBER,
                width=150,
            )
            
            datetime_field = ft.TextField(
                label="Data/Ora (YYYY-MM-DD HH:MM:SS)",
                value=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                width=250,
            )
            
            site_field = ft.Dropdown(
                label="Sito Iniezione",
                options=[
                    ft.dropdown.Option("Addome"),
                    ft.dropdown.Option("Coscia DX"),
                    ft.dropdown.Option("Coscia SX"),
                    ft.dropdown.Option("Braccio DX"),
                    ft.dropdown.Option("Braccio SX"),
                    ft.dropdown.Option("Gluteo DX"),
                    ft.dropdown.Option("Gluteo SX"),
                ],
                width=200,
            )
            
            method_field = ft.Dropdown(
                label="Metodo",
                options=[
                    ft.dropdown.Option("Sottocutanea"),
                    ft.dropdown.Option("Intramuscolare"),
                    ft.dropdown.Option("Endovenosa"),
                ],
                value="Sottocutanea",
                width=200,
            )
            
            notes_field = ft.TextField(
                label="Note",
                value=f"Ciclo: {first_task.get('cycle_name', '-')} - {peptide_names}",
                multiline=True,
                min_lines=2,
                max_lines=4,
            )
            
            side_effects_field = ft.TextField(
                label="Effetti Collaterali",
                multiline=True,
                min_lines=2,
                max_lines=4,
            )
            
            def on_save(e):
                """Salva somministrazione (single o multi-prep)."""
                try:
                    if needs_multi_prep:
                        # Multi-prep administration
                        success, message = self.manager.create_multi_prep_administration(
                            distribution=multi_prep_distribution,
                            protocol_id=protocol_id,
                            administration_datetime=datetime_field.value,
                            injection_site=site_field.value,
                            injection_method=method_field.value,
                            notes=notes_field.value,
                            side_effects=side_effects_field.value,
                            cycle_id=cycle_id,
                        )
                        
                        if not success:
                            self.show_snackbar(f"❌ {message}", error=True)
                            return
                        
                        # Chiudi dialog
                        dialog.open = False
                        self.page.update()
                        
                        self.show_snackbar(f"✅ Multi-prep administration registrata: {peptide_names} ({len(multi_prep_distribution)} preparazioni)")
                    else:
                        # Single prep administration
                        admin_id = self.manager.add_administration(
                            preparation_id=prep_id,
                            dose_ml=float(dose_field.value),
                            administration_datetime=datetime_field.value,
                            injection_site=site_field.value,
                            injection_method=method_field.value,
                            notes=notes_field.value,
                            side_effects=side_effects_field.value,
                        )
                        
                        # Collega al ciclo
                        if cycle_id:
                            cursor = self.manager.conn.cursor()
                            cursor.execute("UPDATE administrations SET cycle_id = ? WHERE id = ?", (cycle_id, admin_id))
                            self.manager.conn.commit()
                        
                        # Chiudi dialog
                        dialog.open = False
                        self.page.update()
                        
                        self.show_snackbar(f"✅ Somministrazione registrata: {peptide_names}")
                    
                    # Ricarica dashboard per rimuovere task completato
                    self.update_content()
                    
                except Exception as ex:
                    self.show_snackbar(f"❌ Errore: {str(ex)}", error=True)
                    import traceback
                    traceback.print_exc()
            
            def close_dialog(e):
                dialog.open = False
                self.page.update()
            
            # Costruisci contenuto dialog
            content_controls = []
            
            if multi_prep_warning:
                content_controls.append(multi_prep_warning)
                content_controls.append(ft.Divider())
            else:
                content_controls.append(
                    ft.Text(f"Preparazione: {prep.get('product_name', f'#{prep_id}')}", weight=ft.FontWeight.BOLD)
                )
                content_controls.append(
                    ft.Text(f"Volume disponibile: {prep.get('volume_remaining_ml', 0):.2f} ml", size=12)
                )
                content_controls.append(ft.Divider())
            
            content_controls.extend([
                dose_field,
                datetime_field,
                site_field,
                method_field,
                notes_field,
                side_effects_field,
            ])
            
            dialog = ft.AlertDialog(
                title=ft.Text(f"Registra Somministrazione - {peptide_names}"),
                modal=True,
                content=ft.Container(
                    content=ft.Column(content_controls, tight=True, scroll=ft.ScrollMode.AUTO),
                    width=500,
                    height=600,
                ),
                actions=[
                    ft.TextButton("Annulla", on_click=close_dialog),
                    ft.ElevatedButton("💾 Salva", on_click=on_save, bgcolor=ft.Colors.GREEN_400),
                ],
            )
            
            dialog.open = True
            self.page.overlay.append(dialog)
            self.page.update()
        except Exception as e:
            self.show_snackbar(f"❌ Errore apertura dialog: {str(e)}", error=True)
            import traceback
            traceback.print_exc()
    
    def _register_administration(self, task):
        """DEPRECATED: Sostituito da _show_register_dialog."""
        pass
    
    def show_edit_preparation_dialog(self, prep_id):
        """Dialog modifica preparazione - TUTTI i campi editabili."""
        prep = self.manager.get_preparation_details(prep_id)
        if not prep:
            return
        
        # Recupera batches disponibili
        batches = self.manager.get_batches(only_available=False)  # Tutti i batch
        
        # Campi modificabili
        batch_dd = ft.Dropdown(
            label="Batch",
            value=str(prep['batch_id']),
            options=[
                ft.dropdown.Option(
                    str(b['id']),
                    f"#{b['id']} - {b['product_name']} ({b['vials_remaining']} fiale)"
                ) for b in batches
            ],
            width=500,
        )
        
        vials_field = ft.TextField(
            label="Fiale usate",
            value=str(prep['vials_used']),
            width=150,
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        
        volume_field = ft.TextField(
            label="Volume totale (ml)",
            value=str(prep['volume_ml']),
            width=150,
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        
        volume_remaining_field = ft.TextField(
            label="Volume rimanente (ml)",
            value=str(prep['volume_remaining_ml']),
            width=150,
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        
        diluent_dd = ft.Dropdown(
            label="Diluente",
            value=prep['diluent'],
            options=[
                ft.dropdown.Option("Bacteriostatic Water", "Bacteriostatic Water"),
                ft.dropdown.Option("Sterile Water", "Sterile Water"),
                ft.dropdown.Option("Sodium Chloride", "Sodium Chloride 0.9%"),
            ],
            width=300,
        )
        
        prep_date_field = ft.TextField(
            label="Data Preparazione (YYYY-MM-DD)",
            value=prep['preparation_date'],
            width=200,
        )
        
        expiry_field = ft.TextField(
            label="Data Scadenza (YYYY-MM-DD)",
            value=prep.get('expiry_date', ''),
            width=200,
        )
        
        notes_field = ft.TextField(
            label="Note",
            value=prep.get('notes', ''),
            multiline=True,
            width=500
        )
        
        def update_preparation(e):
            print(f"\n=== DEBUG update_preparation #{prep_id} ===")
            try:
                changes = {}
                
                # ✅ TUTTI I CAMPI SONO ORA SUPPORTATI!
                
                # Batch ✅
                if int(batch_dd.value) != prep['batch_id']:
                    changes['batch_id'] = int(batch_dd.value)
                    print(f"  Changed batch_id: {changes['batch_id']}")
                
                # Fiale ✅
                if int(vials_field.value) != prep['vials_used']:
                    changes['vials_used'] = int(vials_field.value)
                    print(f"  Changed vials_used: {changes['vials_used']}")
                
                # Volumi ✅
                if float(volume_field.value) != prep['volume_ml']:
                    changes['volume_ml'] = float(volume_field.value)
                    print(f"  Changed volume_ml: {changes['volume_ml']}")
                
                if float(volume_remaining_field.value) != prep['volume_remaining_ml']:
                    changes['volume_remaining_ml'] = float(volume_remaining_field.value)
                    print(f"  Changed volume_remaining_ml: {changes['volume_remaining_ml']}")
                
                # Diluente ✅
                if diluent_dd.value != prep['diluent']:
                    changes['diluent'] = diluent_dd.value
                    print(f"  Changed diluent: {changes['diluent']}")
                
                # Date ✅
                if prep_date_field.value != prep['preparation_date']:
                    changes['preparation_date'] = prep_date_field.value
                    print(f"  Changed preparation_date: {changes['preparation_date']}")
                
                if expiry_field.value != (prep.get('expiry_date') or ''):
                    changes['expiry_date'] = expiry_field.value if expiry_field.value else None
                    print(f"  Changed expiry_date: {changes['expiry_date']}")
                
                # Note ✅
                if notes_field.value != (prep.get('notes') or ''):
                    changes['notes'] = notes_field.value if notes_field.value else None
                    print(f"  Changed notes: {changes['notes']}")
                
                if changes:
                    print(f"Calling manager.update_preparation with changes: {changes}")
                    self.manager.update_preparation(prep_id, **changes)
                    self.close_dialog()
                    self.update_content()
                    
                    # Warning per batch_id o vials_used
                    msg = f"✅ Preparazione #{prep_id} aggiornata completamente!"
                    if 'batch_id' in changes or 'vials_used' in changes:
                        msg += "\n⚠️ Verifica manualmente il conteggio fiale se hai cambiato batch o fiale usate"
                    
                    self.show_snackbar(msg)
                else:
                    self.show_snackbar("Nessuna modifica")
                    
            except Exception as ex:
                print(f"EXCEPTION in update_preparation: {ex}")
                import traceback
                traceback.print_exc()
                self.show_snackbar(f"Errore: {ex}", error=True)
        
        dialog = ft.AlertDialog(
            title=ft.Text(f"Modifica Preparazione #{prep_id}"),
            content=ft.Column([
                ft.Text("✅ TUTTI I CAMPI SONO MODIFICABILI!", 
                       size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_400),
                ft.Text("⚠️ Se modifichi batch o fiale usate, verifica manualmente il conteggio fiale", 
                       size=11, color=ft.Colors.ORANGE_300),
                ft.Divider(),
                batch_dd,
                ft.Row([vials_field, volume_field, volume_remaining_field]),
                diluent_dd,
                ft.Row([prep_date_field, expiry_field]),
                notes_field,
            ], tight=True, scroll=ft.ScrollMode.AUTO, height=400),
            actions=[
                ft.TextButton("Annulla", on_click=lambda e: self.close_dialog(dialog)),
                ft.ElevatedButton("Salva", on_click=update_preparation),
            ],
        )
        
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()
    
    def show_add_preparation_dialog(self, e):
        """Dialog aggiungi preparazione completo."""
        # Recupera batches disponibili
        batches = self.manager.get_batches(only_available=True)
        
        if not batches:
            self.show_snackbar("Nessun batch disponibile!", error=True)
            return
        
        batch_dd = ft.Dropdown(
            label="Batch",
            options=[
                ft.dropdown.Option(
                    str(b['id']),
                    f"#{b['id']} - {b['product_name']} ({b['vials_remaining']} fiale)"
                ) for b in batches
            ],
            width=500,
        )
        
        vials_field = ft.TextField(
            label="Fiale da usare",
            value="1",
            width=150,
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        
        volume_field = ft.TextField(
            label="Volume totale (ml)",
            value="5.0",
            width=150,
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        
        diluent_dd = ft.Dropdown(
            label="Diluente",
            value="Bacteriostatic Water",
            options=[
                ft.dropdown.Option("Bacteriostatic Water", "Bacteriostatic Water"),
                ft.dropdown.Option("Sterile Water", "Sterile Water"),
                ft.dropdown.Option("Sodium Chloride", "Sodium Chloride 0.9%"),
            ],
            width=300,
        )
        
        expiry_field = ft.TextField(
            label="Data Scadenza (YYYY-MM-DD)",
            value=(datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
            width=200,
        )
        
        notes_field = ft.TextField(label="Note", multiline=True, width=500)
        
        def add_preparation(e):
            print("\n=== DEBUG add_preparation chiamato ===")
            try:
                print(f"Batch: {batch_dd.value}")
                if not batch_dd.value:
                    self.show_snackbar("Seleziona un batch!", error=True)
                    return
                
                print(f"Calling manager.add_preparation...")
                print(f"  batch_id={int(batch_dd.value)}")
                print(f"  vials_used={int(vials_field.value)}")
                print(f"  volume_ml={float(volume_field.value)}")
                print(f"  diluent={diluent_dd.value}")
                print(f"  preparation_date={datetime.now().strftime('%Y-%m-%d')}")
                print(f"  expiry_date={expiry_field.value}")
                
                prep_id = self.manager.add_preparation(
                    batch_id=int(batch_dd.value),
                    vials_used=int(vials_field.value),
                    volume_ml=float(volume_field.value),
                    preparation_date=datetime.now().strftime('%Y-%m-%d'),  # ✅ Aggiunto obbligatorio
                    diluent=diluent_dd.value,
                    expiry_date=expiry_field.value if expiry_field.value else None,
                    notes=notes_field.value if notes_field.value else None,
                )
                
                print(f"Preparation created with ID: {prep_id}")
                self.close_dialog()
                self.update_content()
                self.show_snackbar(f"Preparazione #{prep_id} creata con successo!")
                
            except Exception as ex:
                print(f"EXCEPTION in add_preparation: {ex}")
                import traceback
                traceback.print_exc()
                self.show_snackbar(f"Errore: {ex}", error=True)
        
        dialog = ft.AlertDialog(
            title=ft.Text("Nuova Preparazione"),
            content=ft.Column([
                batch_dd,
                ft.Row([vials_field, volume_field]),
                diluent_dd,
                expiry_field,
                notes_field,
            ], tight=True, scroll=ft.ScrollMode.AUTO, height=400),
            actions=[
                ft.TextButton("Annulla", on_click=lambda e: self.close_dialog(dialog)),
                ft.ElevatedButton("Crea", on_click=add_preparation),
            ],
        )
        
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()
    
    def _create_administer_handler(self, prep_id):
        """Factory per handler somministrazione (fix Flet 0.28.3)."""
        def handler(e):
            self.show_administer_dialog(prep_id)
        return handler
    
    def show_administer_dialog(self, prep_id):
        """Dialog registra somministrazione completo."""
        prep = self.manager.get_preparation_details(prep_id)
        if not prep:
            return
        
        # Verifica volume disponibile
        if prep['volume_remaining_ml'] <= 0:
            self.show_snackbar("Preparazione esaurita!", error=True)
            return
        
        # Recupera protocolli attivi (opzionale)
        protocols = self.manager.get_protocols(active_only=True)
        
        # Data e ora (default: adesso)
        date_field = ft.TextField(
            label="Data (YYYY-MM-DD)",
            value=datetime.now().strftime('%Y-%m-%d'),
            width=200,
        )
        
        time_field = ft.TextField(
            label="Ora (HH:MM)",
            value=datetime.now().strftime('%H:%M'),
            width=150,
        )
        
        # Dose (default: 0.5ml)
        # Dose mcg
        dose_mcg_field = ft.TextField(
            label="Dose (mcg)",
            value="500",
            width=150,
            keyboard_type=ft.KeyboardType.NUMBER,
        )

        # Dose ml (calcolato)
        dose_ml_field = ft.TextField(
            label="Dose (ml)",
            value="",
            width=150,
            keyboard_type=ft.KeyboardType.NUMBER,
            hint_text=f"Max: {prep['volume_remaining_ml']:.2f}ml",
        )

        # Calcolo bidirezionale
        def on_mcg_change(e):
            try:
                mcg = float(dose_mcg_field.value)
                ml = mcg / (prep['concentration_mg_ml'] * 1000)
                dose_ml_field.value = f"{ml:.3f}"
                dose_ml_field.update()
            except:
                pass
            
        def on_ml_change(e):
            try:
                ml = float(dose_ml_field.value)
                mcg = ml * prep['concentration_mg_ml'] * 1000
                dose_mcg_field.value = f"{mcg:.0f}"
                dose_mcg_field.update()
            except:
                pass
        
        dose_mcg_field.on_change = on_mcg_change
        dose_ml_field.on_change = on_ml_change

        # Calcolo iniziale
        on_mcg_change(None)


        
        # Sito iniezione (due dropdown separati)
        site_dd = ft.Dropdown(
            label="Sito Anatomico",
            value="Addome",
            options=[
                ft.dropdown.Option("Addome", "Addome"),
                ft.dropdown.Option("Gluteo", "Gluteo"),
                ft.dropdown.Option("Coscia", "Coscia"),
                ft.dropdown.Option("Braccio", "Braccio"),
                ft.dropdown.Option("Fianco", "Fianco"),
                ft.dropdown.Option("Spalla", "Spalla"),
            ],
            width=200,
        )
        
        method_dd = ft.Dropdown(
            label="Modalità",
            value="SubQ",
            options=[
                ft.dropdown.Option("SubQ", "Sottocutaneo"),
                ft.dropdown.Option("IM", "Intramuscolare"),
            ],
            width=180,
        )
        
        # Protocollo (opzionale)
        protocol_dd = ft.Dropdown(
            label="Protocollo (opzionale)",
            options=[ft.dropdown.Option("", "Nessuno")] + [
                ft.dropdown.Option(str(p['id']), p['name']) for p in protocols
            ],
            width=350,
        )
        
        # Ciclo (opzionale) - Recupera cicli attivi
        active_cycles = []
        try:
            all_cycles = self.manager.get_cycles(active_only=False)
            active_cycles = [c for c in all_cycles if c.get('status') == 'active']
        except Exception:
            pass
        
        cycle_dd = ft.Dropdown(
            label="Ciclo (opzionale)",
            options=[ft.dropdown.Option("", "Nessuno")] + [
                ft.dropdown.Option(str(c['id']), c['name']) for c in active_cycles
            ],
            width=350,
        )
        
        # Note
        notes_field = ft.TextField(
            label="Note",
            multiline=True,
            width=500,
        )
        
        # Info preparazione
        info_text = ft.Column([
            ft.Text("Preparazione:", weight=ft.FontWeight.BOLD),
            ft.Text(f"Batch: {prep['product_name']}", size=12),
            ft.Text(f"Volume disponibile: {prep['volume_remaining_ml']:.2f}ml", size=12),
            ft.Text(f"Concentrazione: {prep['concentration_mg_ml']:.3f}mg/ml ({prep['concentration_mg_ml']*1000:.1f}mcg/ml)", size=12),
        ], spacing=2)
        
        def register_administration(e):
            try:
                # Validazioni
                if not dose_ml_field.value:
                    self.show_snackbar("Inserisci la dose!", error=True)
                    return
                
                dose = float(dose_ml_field.value)
                
                if dose <= 0:
                    self.show_snackbar("La dose deve essere > 0!", error=True)
                    return
                
                # Calcola distribuzione FIFO PRIMA del controllo volume
                batch_id = prep.get('batch_id')
                all_preps = self.manager.get_preparations(batch_id=batch_id, only_active=True)
                available_preps = [
                    {
                        'id': p['id'],
                        'volume_remaining_ml': p['volume_remaining_ml'],
                        'expiry_date': p['expiry_date']
                    }
                    for p in all_preps if p['volume_remaining_ml'] > 0.01
                ]
                
                success, distribution, message = self.manager.calculate_multi_prep_distribution(
                    required_ml=dose,
                    available_preps=available_preps
                )
                
                if not success:
                    # Volume totale insufficiente anche con tutte le prep
                    self.show_snackbar(f"❌ {message}", error=True)
                    return
                
                # Volume totale disponibile (somma di tutte le prep)
                volume_totale_disponibile = float(sum(p['volume_remaining_ml'] for p in available_preps))
                volume_disponibile = float(prep['volume_remaining_ml'])
                TOLERANCE = 0.001  # 1 microlitro di tolleranza
                
                # Mostra warning solo se volume totale insufficiente (già gestito sopra)
                # Qui procediamo con la registrazione FIFO
                if dose > volume_disponibile + TOLERANCE and dose <= volume_totale_disponibile + TOLERANCE:
                    # Dose VERAMENTE eccessiva (oltre tolleranza)
                    excess = dose - volume_disponibile
                    
                    def use_remaining(e):
                        """Usa tutto il volume residuo."""
                        dose_ml_field.value = f"{volume_disponibile:.3f}"
                        # Ricalcola mcg
                        dose_mcg_field.value = str(int(volume_disponibile * prep['concentration_mg_ml'] * 1000))
                        confirm_dialog.open = False
                        self.page.update()
                    
                    def cancel_excess(e):
                        """Annulla e torna a editare."""
                        confirm_dialog.open = False
                        self.page.update()
                    
                    confirm_dialog = ft.AlertDialog(
                        title=ft.Text("⚠️ Volume Insufficiente"),
                        content=ft.Column([
                            ft.Text(
                                f"Dose richiesta: {dose:.3f}ml",
                                weight=ft.FontWeight.BOLD,
                            ),
                            ft.Text(
                                f"Volume disponibile: {volume_disponibile:.3f}ml",
                                color=ft.Colors.RED_400,
                            ),
                            ft.Text(
                                f"Eccesso: {excess:.3f}ml",
                                size=12,
                                italic=True,
                            ),
                            ft.Divider(),
                            ft.Text(
                                "Vuoi usare tutto il volume residuo disponibile?",
                                size=14,
                            ),
                        ], tight=True, height=180),
                        actions=[
                            ft.TextButton("Annulla", on_click=cancel_excess),
                            ft.ElevatedButton(
                                f"Usa {volume_disponibile:.3f}ml",
                                on_click=use_remaining,
                                bgcolor=ft.Colors.ORANGE_400,
                            ),
                        ],
                    )
                    
                    # Multi-prep: la dose richiesta usa più preparazioni
                    print(f"ℹ️  Multi-prep necessaria: dose {dose:.3f}ml da {len(distribution)} preparazioni")

                # Costruisci datetime
                try:
                    admin_datetime = f"{date_field.value} {time_field.value}:00"
                    datetime.strptime(admin_datetime, '%Y-%m-%d %H:%M:%S')  # Valida formato
                    print("  ✓ DateTime valido")
                except ValueError as ve:
                    self.show_snackbar("Formato data/ora non valido!", error=True)
                    print(f"  ❌ DateTime invalido: {ve}")
                    return
                except Exception as ex:
                    print(f"  ❌ Errore datetime: {ex}")
                    return
                
                print(f"  ✓ Distribuzione FIFO calcolata: {len(distribution)} preparazioni")
                
                # Registra somministrazione (singola o multi-prep)
                if len(distribution) == 1:
                    # Singola preparazione
                    admin_id = self.manager.use_preparation(
                        prep_id,
                        dose,
                        admin_datetime,
                        injection_site=site_dd.value if site_dd.value else None,
                        injection_method=method_dd.value if method_dd.value else 'SubQ',
                        notes=notes_field.value if notes_field.value else None,
                        protocol_id=int(protocol_dd.value) if protocol_dd.value else None
                    )
                else:
                    # Multi-preparazione (usa FIFO)
                    print(f"  ℹ️  Multi-prep: {distribution}")
                    protocol_id = int(protocol_dd.value) if protocol_dd.value else None
                    
                    success, admin_ids, msg = self.manager.create_multi_prep_administration(
                        distribution=distribution,
                        protocol_id=protocol_id,
                        administration_datetime=admin_datetime,
                        injection_site=site_dd.value if site_dd.value else None,
                        injection_method=method_dd.value if method_dd.value else 'SubQ',
                        notes=notes_field.value if notes_field.value else None
                    )
                    
                    if not success:
                        self.show_snackbar(f"❌ {msg}", error=True)
                        return
                    
                    admin_id = admin_ids[0] if admin_ids else None
                    print(f"  ✓ Multi-prep registrata: {len(admin_ids)} record")
                
                # Se ciclo selezionato, collega la/le somministrazione/i
                if cycle_dd.value and admin_id:
                    cycle_id = int(cycle_dd.value)
                    try:
                        cursor = self.manager.conn.cursor()
                        if len(distribution) == 1:
                            cursor.execute('UPDATE administrations SET cycle_id = ? WHERE id = ?', (cycle_id, admin_id))
                        else:
                            # Multi-prep: collega tutti i record
                            for aid in admin_ids:
                                cursor.execute('UPDATE administrations SET cycle_id = ? WHERE id = ?', (cycle_id, aid))
                        self.manager.conn.commit()
                        print(f"  ✓ Somministrazione/i collegata/e al ciclo #{cycle_id}")
                    except Exception as ex:
                        print(f"  ⚠️ Errore collegamento ciclo: {ex}")
                
                print(f"  ✓ Somministrazione registrata")
                
                self.close_dialog()
                self.update_content()  # Aggiorna il pannello corrente
                
                # Se dashboard è aperta in un'altra vista, aggiornala anche
                # (nota: la dashboard potrebbe essere aperta in background)
                if hasattr(self, 'current_view') and self.current_view == 'dashboard':
                    # Dashboard già aggiornata da update_content()
                    pass
                
                # Calcola dose in mcg per feedback
                dose_mcg = dose * prep['concentration_mg_ml'] * 1000
                if len(distribution) > 1:
                    self.show_snackbar(f"Multi-prep registrata! Dose: {dose}ml ({dose_mcg:.0f}mcg) da {len(distribution)} preparazioni")
                else:
                    self.show_snackbar(f"Somministrazione registrata! Dose: {dose}ml ({dose_mcg:.0f}mcg)")
                
            except Exception as ex:
                print(f"  ❌ EXCEPTION: {ex}")
                import traceback
                traceback.print_exc()
                self.show_snackbar(f"Errore: {ex}", error=True)
        
        dialog = ft.AlertDialog(
            title=ft.Text(f"Registra Somministrazione - Prep #{prep_id}"),
            content=ft.Column([
                info_text,
                ft.Divider(),
                ft.Row([date_field, time_field]),
                ft.Row([dose_mcg_field, dose_ml_field]),
                ft.Row([site_dd, method_dd]),
                protocol_dd,
                cycle_dd,
                notes_field,
            ], tight=True, scroll=ft.ScrollMode.AUTO, height=550),
            actions=[
                ft.TextButton("Annulla", on_click=lambda e: self.close_dialog(dialog)),
                ft.ElevatedButton("Registra", on_click=register_administration),
            ],
        )
        
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()
    
    # ============================================================
    # PROTOCOLS
    # ============================================================
    
    def build_protocols(self):
        """Costruisce vista protocolli."""
        protos = self.manager.get_protocols(active_only=False)
        protos_sorted = sorted(protos, key=lambda x: x['id'])
        
        toolbar = ft.Row([
            ft.Text("Protocolli", size=32, weight=ft.FontWeight.BOLD),
            ft.Container(expand=True),
            ft.ElevatedButton(
                "Nuovo Protocollo",
                icon=ft.Icons.ADD,
                on_click=self.show_add_protocol_dialog,
            ),
        ])
        
        rows = []
        for p in protos_sorted:
            status_icon = "✓" if p['active'] else "✗"
            status_color = ft.Colors.GREEN_400 if p['active'] else ft.Colors.GREY_400
            
            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(status_icon, color=status_color)),
                        ft.DataCell(ft.Text(f"#{p['id']}")),
                        ft.DataCell(ft.Text(p['name'][:30])),
                        ft.DataCell(ft.Text(f"{p.get('peptides_display', 'N/A')} x{p['frequency_per_day']}/d")),
                        ft.DataCell(ft.Text(f"{p['days_on']}ON/{p['days_off']}OFF" if p['days_on'] else "N/A")),
                        ft.DataCell(
                            ft.Row([
                                ft.IconButton(
                                    icon=ft.Icons.VISIBILITY,
                                    tooltip="Dettagli",
                                    on_click=self._make_handler(self.show_protocol_details, p['id']),
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.EDIT,
                                    tooltip="Modifica",
                                    on_click=self._make_handler(self.show_edit_protocol_dialog, p['id']),
                                    disabled=not self.edit_mode,
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.DELETE,
                                    tooltip="Elimina",
                                    on_click=self._make_handler(self.confirm_delete_protocol, p['id']),
                                    disabled=not self.edit_mode,
                                    icon_color=ft.Colors.RED_400,
                                ),
                            ], spacing=0),
                        ),
                    ],
                )
            )
        
        table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("")),
                ft.DataColumn(ft.Text("ID")),
                ft.DataColumn(ft.Text("Nome")),
                ft.DataColumn(ft.Text("Dose")),
                ft.DataColumn(ft.Text("Schema")),
                ft.DataColumn(ft.Text("Azioni")),
            ],
            rows=rows,
        )
        
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

    def build_cycles(self):
        """Costruisce vista Cicli integrando la view modulare se presente."""
        try:
            from gui_modular.views.cycles import CyclesView
            view = CyclesView(self)
            return view
        except Exception as ex:
            # Fallback minimale in caso di errori durante l'import
            return ft.Column([
                ft.Text("Errore caricamento vista Cicli", weight=ft.FontWeight.BOLD),
                ft.Text(str(ex))
            ], scroll=ft.ScrollMode.AUTO)
    
    def show_protocol_details(self, protocol_id):
        """Mostra dettagli protocollo."""
        protocol = self.manager.get_protocol_details(protocol_id)
        if not protocol:
            return
        
        status = "✓ ATTIVO" if protocol['active'] else "✗ DISATTIVATO"
        
        peptides_text = "\n".join([f"• {p['name']}: {p['target_dose_mcg']}mcg" 
                                   for p in protocol['peptides']]) if protocol['peptides'] else "Nessuno"
        
        dialog = ft.AlertDialog(
            title=ft.Text(f"Protocollo #{protocol_id} - {protocol['name']}"),
            content=ft.Column([
                ft.Text(f"Stato: {status}"),
                ft.Text(f"Descrizione: {protocol['description'] or 'N/A'}"),
                ft.Divider(),
                ft.Text(f"Dosaggio: {protocol['dose_ml']}ml x {protocol['frequency_per_day']}/giorno"),
                ft.Text(f"Schema: {protocol['days_on']} ON, {protocol['days_off']} OFF" if protocol['days_on'] else "N/A"),
                ft.Text(f"Durata ciclo: {protocol['cycle_duration_weeks']} settimane" if protocol['cycle_duration_weeks'] else "N/A"),
                ft.Divider(),
                ft.Text("Peptidi richiesti:", weight=ft.FontWeight.BOLD),
                ft.Text(peptides_text),
                ft.Divider(),
                ft.Text(f"Somministrazioni: {protocol['administrations_count']}"),
            ], tight=True, scroll=ft.ScrollMode.AUTO, height=400),
            actions=[
                ft.TextButton("Chiudi", on_click=lambda e: self.close_dialog(dialog)),
            ],
        )
        
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()
    
    def show_add_protocol_dialog(self, e):
        """Dialog aggiungi protocollo completo."""
        peptides = self.manager.get_peptides()
        
        if not peptides:
            self.show_snackbar("Aggiungi prima dei peptidi!", error=True)
            return
        
        name_field = ft.TextField(label="Nome Protocollo", width=400, autofocus=True)
        desc_field = ft.TextField(label="Descrizione", width=400, multiline=True)
        
        freq_field = ft.TextField(
            label="Frequenza giornaliera",
            value="1",
            width=180,  # ✅ Aumentato da 150
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        
        days_on_field = ft.TextField(
            label="Giorni ON",
            value="",
            width=120,  # ✅ Aumentato da 100
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        
        days_off_field = ft.TextField(
            label="Giorni OFF",
            value="",
            width=120,  # ✅ Aumentato da 100
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        
        cycle_field = ft.TextField(
            label="Durata ciclo (settimane)",
            value="",
            width=180,  # ✅ Aumentato da 150
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        
        active_switch = ft.Switch(label="Attivo", value=True)
        
        # Peptidi target
        peptide_inputs = {}
        peptide_checks = []
        
        for p in peptides:
            cb = ft.Checkbox(label=p['name'], value=False)
            dose_input = ft.TextField(
                label="Dose target (mcg)",
                width=150,
                keyboard_type=ft.KeyboardType.NUMBER,
                visible=False,
            )
            
            def on_check(e, inp=dose_input):
                inp.visible = e.control.value
                self.page.update()
            
            cb.on_change = on_check
            peptide_checks.append(ft.Row([cb, dose_input]))
            peptide_inputs[p['id']] = (cb, dose_input)
        
        def add_protocol(e):
            print("\n=== DEBUG add_protocol chiamato ===")
            try:
                print(f"Name: {name_field.value}")
                if not name_field.value:
                    self.show_snackbar("Inserisci un nome!", error=True)
                    return
                
                # Peptidi selezionati
                target_peptides_dict = {}
                print(f"Checking peptides...")
                for pid, (cb, dose_inp) in peptide_inputs.items():
                    print(f"  Peptide {pid}: checked={cb.value}, dose={dose_inp.value}")
                    if cb.value:
                        if not dose_inp.value or not dose_inp.value.strip():
                            self.show_snackbar(f"Inserisci la dose per {cb.label}!", error=True)
                            return
                        try:
                            dose = float(dose_inp.value)
                            if dose <= 0:
                                raise ValueError()
                            target_peptides_dict[pid] = dose
                        except ValueError:
                            print(f"  ERROR parsing dose: invalid value")
                            self.show_snackbar(f"Dose invalida per {cb.label}!", error=True)
                            return
                
                print(f"Target peptides dict: {target_peptides_dict}")
                
                # Converti da dict {pid: dose} a List[Tuple[name, dose]]
                peptides_list = None
                if target_peptides_dict:
                    all_peptides = self.manager.get_peptides()
                    peptide_map = {p['id']: p['name'] for p in all_peptides}
                    
                    peptides_list = []
                    for pid, dose in target_peptides_dict.items():
                        peptide_name = peptide_map.get(pid)
                        if not peptide_name:
                            self.show_snackbar(f"Peptide ID {pid} non trovato!", error=True)
                            return
                        peptides_list.append((peptide_name, dose))
                    
                    print(f"Peptides list: {peptides_list}")
                
                print(f"Calling manager.add_protocol...")
                protocol_id = self.manager.add_protocol(
                    name=name_field.value,
                    description=desc_field.value if desc_field.value else None,
                    frequency_per_day=int(freq_field.value),
                    days_on=int(days_on_field.value) if days_on_field.value else None,
                    days_off=int(days_off_field.value) if days_off_field.value else None,
                    cycle_duration_weeks=int(cycle_field.value) if cycle_field.value else None,
                    peptides=peptides_list,  # ✅ List[Tuple[name, dose]] non dict
                )
                
                print(f"Protocol created with ID: {protocol_id}")
                self.close_dialog()
                self.update_content()
                self.show_snackbar(f"Protocollo '{name_field.value}' creato!")
                
            except Exception as ex:
                print(f"EXCEPTION in add_protocol: {ex}")
                import traceback
                traceback.print_exc()
                self.show_snackbar(f"Errore: {ex}", error=True)
        
        dialog = ft.AlertDialog(
            title=ft.Text("Nuovo Protocollo"),
            content=ft.Column([
                name_field,
                desc_field,
                ft.Text("Frequenza:", weight=ft.FontWeight.BOLD, size=12),
                freq_field,
                ft.Text("Ciclo (opzionale):", weight=ft.FontWeight.BOLD, size=12),
                ft.Row([days_on_field, days_off_field, cycle_field]),
                active_switch,
                ft.Divider(),
                ft.Text("Peptidi Target (opzionale):", weight=ft.FontWeight.BOLD),
                *peptide_checks,
            ], spacing=8, scroll=ft.ScrollMode.AUTO, height=550, width=550),  # ✅ Aumentato width e height
            actions=[
                ft.TextButton("Annulla", on_click=lambda e: self.close_dialog(dialog)),
                ft.ElevatedButton("Crea", on_click=add_protocol),
            ],
        )
        
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()
    
    def show_edit_protocol_dialog(self, protocol_id):
        """Dialog modifica protocollo completo."""
        # Carica dati esistenti
        protocol = self.manager.get_protocol_details(protocol_id)
        if not protocol:
            self.show_snackbar("Protocollo non trovato!", error=True)
            return
        
        peptides = self.manager.get_peptides()
        
        # Campi pre-popolati con valori esistenti
        name_field = ft.TextField(
            label="Nome Protocollo", 
            value=protocol['name'],
            width=400, 
            autofocus=True
        )
        desc_field = ft.TextField(
            label="Descrizione", 
            value=protocol['description'] or "",
            width=400, 
            multiline=True
        )
        
        dose_field = ft.TextField(
            label="Dose per somministrazione (ml)",
            value=str(protocol['dose_ml']),
            width=230,
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        
        freq_field = ft.TextField(
            label="Frequenza giornaliera",
            value=str(protocol['frequency_per_day']),
            width=180,
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        
        days_on_field = ft.TextField(
            label="Giorni ON",
            value=str(protocol['days_on']) if protocol['days_on'] else "",
            width=120,
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        
        days_off_field = ft.TextField(
            label="Giorni OFF",
            value=str(protocol['days_off']) if protocol['days_off'] else "",
            width=120,
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        
        cycle_field = ft.TextField(
            label="Durata ciclo (settimane)",
            value=str(protocol['cycle_duration_weeks']) if protocol['cycle_duration_weeks'] else "",
            width=180,
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        
        active_switch = ft.Switch(
            label="Attivo", 
            value=bool(protocol['active'])
        )
        
        # Peptidi target - pre-selezionati con dosi
        peptide_inputs = {}
        peptide_checks = []
        
        # Crea mappa dei peptidi esistenti nel protocollo
        existing_peptides = {}
        if protocol.get('peptides'):
            for p in protocol['peptides']:
                existing_peptides[p['id']] = p['target_dose_mcg']
        
        for p in peptides:
            is_selected = p['id'] in existing_peptides
            cb = ft.Checkbox(label=p['name'], value=is_selected)
            dose_input = ft.TextField(
                label="Dose target (mcg)",
                value=str(existing_peptides[p['id']]) if is_selected else "",
                width=150,
                keyboard_type=ft.KeyboardType.NUMBER,
                visible=is_selected,
            )
            
            def on_check(e, inp=dose_input):
                inp.visible = e.control.value
                self.page.update()
            
            cb.on_change = on_check
            peptide_checks.append(ft.Row([cb, dose_input]))
            peptide_inputs[p['id']] = (cb, dose_input)
        
        def save_changes(e):
            try:
                if not name_field.value:
                    self.show_snackbar("Inserisci un nome!", error=True)
                    return
                
                # Aggiorna protocollo base
                self.manager.update_protocol(
                    protocol_id=protocol_id,
                    name=name_field.value,
                    description=desc_field.value if desc_field.value else None,
                    dose_ml=float(dose_field.value),
                    frequency_per_day=int(freq_field.value),
                    days_on=int(days_on_field.value) if days_on_field.value else None,
                    days_off=int(days_off_field.value) if days_off_field.value else None,
                    cycle_duration_weeks=int(cycle_field.value) if cycle_field.value else None,
                    active=1 if active_switch.value else 0,
                )
                
                # Gestisci peptidi target - rimuovi vecchi e aggiungi nuovi
                cursor = self.manager.conn.cursor()
                
                # Rimuovi associazioni esistenti
                cursor.execute('DELETE FROM protocol_peptides WHERE protocol_id = ?', (protocol_id,))
                
                # Aggiungi nuove associazioni
                for pid, (cb, dose_inp) in peptide_inputs.items():
                    if cb.value:
                        try:
                            dose = float(dose_inp.value)
                            if dose <= 0:
                                raise ValueError()
                            cursor.execute('''
                                INSERT INTO protocol_peptides (protocol_id, peptide_id, target_dose_mcg)
                                VALUES (?, ?, ?)
                            ''', (protocol_id, pid, dose))
                        except Exception as ex:
                            self.show_snackbar(f"Dose invalida per {cb.label}!", error=True)
                            return
                
                self.manager.conn.commit()
                
                self.close_dialog()
                self.update_content()
                self.show_snackbar(f"✅ Protocollo '{name_field.value}' aggiornato!")
                
            except Exception as ex:
                import traceback
                traceback.print_exc()
                self.show_snackbar(f"❌ Errore: {ex}", error=True)
        
        dialog = ft.AlertDialog(
            title=ft.Text(f"Modifica Protocollo #{protocol_id}"),
            content=ft.Column([
                name_field,
                desc_field,
                ft.Text("Dosaggio:", weight=ft.FontWeight.BOLD, size=12),
                ft.Row([dose_field, freq_field]),
                ft.Text("Ciclo (opzionale):", weight=ft.FontWeight.BOLD, size=12),
                ft.Row([days_on_field, days_off_field, cycle_field]),
                active_switch,
                ft.Divider(),
                ft.Text("Peptidi Target (opzionale):", weight=ft.FontWeight.BOLD),
                *peptide_checks,
            ], spacing=8, scroll=ft.ScrollMode.AUTO, height=550, width=550),
            actions=[
                ft.TextButton("Annulla", on_click=lambda e: self.close_dialog(dialog)),
                ft.ElevatedButton("Salva", on_click=save_changes),
            ],
        )
        
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()
    
    # ============================================================
    # ADMINISTRATIONS
    # ============================================================
    
    def build_administrations(self):
        """Costruisce vista Storico Somministrazioni con filtri avanzati (pandas)."""
        
        # Carica DataFrame (tutto in memoria - velocissimo!)
        try:
            df_all = self.manager.get_all_administrations_df()
        except ImportError:
            return ft.Column([
                ft.Text("⚠️ pandas non installato", size=20, color=ft.Colors.ORANGE),
                ft.Text("Installa con: pip install pandas", size=14),
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
        
        # Estrai valori unici per i dropdown
        unique_peptides = sorted([p for p in df_all['peptide_names'].unique() if p and p != 'N/A'])
        unique_sites = sorted([s for s in df_all['injection_site'].unique() if s])
        unique_methods = sorted([m for m in df_all['injection_method'].unique() if m])
        unique_protocols = sorted([p for p in df_all['protocol_name'].unique() if p and p != 'Nessuno'])
        
        # ============ CAMPI FILTRI ============
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
        
        # Container per tabella e stats (verrà aggiornato dinamicamente)
        results_container = ft.Container()
        
        def apply_filters(e=None):
            """Applica filtri al DataFrame e aggiorna la vista."""
            df = df_all.copy()
            
            # Filtro ricerca testo
            if search_field.value:
                df = df[df['notes'].str.contains(search_field.value, case=False, na=False)]
            
            # Filtro data da
            if date_from_field.value:
                try:
                    date_from = pd.to_datetime(date_from_field.value).date()
                    df = df[df['date'] >= date_from]
                except:
                    pass
            
            # Filtro data a
            if date_to_field.value:
                try:
                    date_to = pd.to_datetime(date_to_field.value).date()
                    df = df[df['date'] <= date_to]
                except:
                    pass
            
            # Filtro peptide (ricerca nel campo peptide_names)
            if peptide_filter.value:
                df = df[df['peptide_names'].str.contains(peptide_filter.value, case=False, na=False)]
            
            # Filtro sito
            if site_filter.value:
                df = df[df['injection_site'] == site_filter.value]
            
            # Filtro metodo
            if method_filter.value:
                df = df[df['injection_method'] == method_filter.value]
            
            # Filtro protocollo
            if protocol_filter.value:
                df = df[df['protocol_name'] == protocol_filter.value]
            
            # ============ STATISTICHE ============
            stats = ft.Container(
                content=ft.Column([
                    ft.Text("📊 Statistiche Filtrate", size=18, weight=ft.FontWeight.BOLD),
                    ft.Divider(),
                    ft.Row([
                        self.stat_card("Somministrazioni", str(len(df)), ft.Icons.MEDICATION, ft.Colors.BLUE_400),
                        self.stat_card("Totale ml", f"{df['dose_ml'].sum():.2f}", ft.Icons.WATER_DROP, ft.Colors.CYAN_400),
                        self.stat_card("Totale mcg", f"{df['dose_mcg'].sum():.0f}", ft.Icons.SCIENCE, ft.Colors.GREEN_400),
                        self.stat_card("Giorni Unici", str(df['date'].nunique()), ft.Icons.CALENDAR_TODAY, ft.Colors.PURPLE_400),
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
            
            # ============ TABELLA ============
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
                                ft.DataCell(ft.Text(f"{row['dose_ml']:.2f}", size=12)),
                                ft.DataCell(ft.Text(f"{row['dose_mcg']:.0f}", size=12)),
                                ft.DataCell(ft.Text(str(row['injection_site'])[:15], size=12)),
                                ft.DataCell(ft.Text(str(row['injection_method']), size=12)),
                                ft.DataCell(ft.Text(str(row['protocol_name'])[:20], size=12)),
                                ft.DataCell(
                                    ft.Row([
                                        ft.IconButton(
                                            icon=ft.Icons.VISIBILITY,
                                            icon_size=16,
                                            tooltip="Dettagli",
                                            on_click=self._make_handler(self.show_administration_details, row['id']),
                                        ),
                                        ft.IconButton(
                                            icon=ft.Icons.EDIT,
                                            icon_size=16,
                                            tooltip="Modifica",
                                            on_click=self._make_handler(self.show_edit_administration_dialog, row['id']),
                                            disabled=not self.edit_mode,
                                        ),
                                        ft.IconButton(
                                            icon=ft.Icons.DELETE,
                                            icon_size=16,
                                            tooltip="Elimina",
                                            on_click=self._make_handler(self.confirm_delete_administration, row['id']),
                                            disabled=not self.edit_mode,
                                            icon_color=ft.Colors.RED_400,
                                        ),
                                    ], spacing=0),
                                ),
                            ],
                        )
                    )
                
                table_content = ft.DataTable(
                    columns=[
                        ft.DataColumn(ft.Text("ID", size=12, weight=ft.FontWeight.BOLD)),
                        ft.DataColumn(ft.Text("Data", size=12, weight=ft.FontWeight.BOLD)),
                        ft.DataColumn(ft.Text("Ora", size=12, weight=ft.FontWeight.BOLD)),
                        ft.DataColumn(ft.Text("Peptidi", size=12, weight=ft.FontWeight.BOLD)),
                        ft.DataColumn(ft.Text("Prodotto", size=12, weight=ft.FontWeight.BOLD)),
                        ft.DataColumn(ft.Text("ml", size=12, weight=ft.FontWeight.BOLD)),
                        ft.DataColumn(ft.Text("mcg", size=12, weight=ft.FontWeight.BOLD)),
                        ft.DataColumn(ft.Text("Sito", size=12, weight=ft.FontWeight.BOLD)),
                        ft.DataColumn(ft.Text("Metodo", size=12, weight=ft.FontWeight.BOLD)),
                        ft.DataColumn(ft.Text("Protocollo", size=12, weight=ft.FontWeight.BOLD)),
                        ft.DataColumn(ft.Text("Azioni", size=12, weight=ft.FontWeight.BOLD)),
                    ],
                    rows=rows[:200],  # Limita a 200 risultati per performance UI
                )
            
            # Pulsante export
            def export_csv(e):
                """Esporta risultati filtrati in CSV."""
                import os
                from datetime import datetime as dt
                
                filename = f"somministrazioni_{dt.now().strftime('%Y%m%d_%H%M%S')}.csv"
                filepath = os.path.join(os.path.expanduser("~"), "Downloads", filename)
                
                try:
                    df.to_csv(filepath, index=False)
                    self.show_snackbar(f"✅ Export salvato: {filename}")
                except Exception as ex:
                    self.show_snackbar(f"❌ Errore export: {ex}", error=True)
            
            export_btn = ft.ElevatedButton(
                "Esporta CSV",
                icon=ft.Icons.DOWNLOAD,
                on_click=export_csv,
            )
            
            # Aggiorna container risultati
            results_container.content = ft.Column([
                stats,
                ft.Divider(),
                ft.Row([
                    ft.Text(f"Risultati: {len(df)}" + (f" (mostrando primi 200)" if len(df) > 200 else ""), 
                            size=14, color=ft.Colors.GREY_400),
                    ft.Container(expand=True),
                    export_btn,
                ]),
                ft.Container(
                    content=table_content,
                    border=ft.border.all(1, ft.Colors.GREY_800),
                    border_radius=10,
                    padding=10,
                ),
            ], scroll=ft.ScrollMode.AUTO)
            
            self.page.update()
        
        def reset_filters(e):
            """Reset tutti i filtri."""
            search_field.value = ""
            date_from_field.value = ""
            date_to_field.value = ""
            peptide_filter.value = ""
            site_filter.value = ""
            method_filter.value = ""
            protocol_filter.value = ""
            apply_filters()
        
        # Applica filtri inizialmente (mostra tutto)
        apply_filters()
        
        # ============ LAYOUT FINALE ============
        return ft.Column([
            # Header
            ft.Row([
                ft.Text("📊 Storico Somministrazioni", size=32, weight=ft.FontWeight.BOLD),
                ft.Container(expand=True),
                ft.Text(f"Totale: {len(df_all)} registrazioni", size=14, color=ft.Colors.GREY_400),
            ]),
            ft.Divider(),
            
            # Filtri
            ft.Container(
                content=ft.Column([
                    ft.Text("🔍 Filtri", size=18, weight=ft.FontWeight.BOLD),
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
                    ft.Row([
                        ft.ElevatedButton("Applica Filtri", icon=ft.Icons.FILTER_ALT, on_click=apply_filters),
                        ft.OutlinedButton("Reset", icon=ft.Icons.REFRESH, on_click=reset_filters),
                    ], spacing=10),
                ]),
                bgcolor=ft.Colors.GREY_900,
                padding=15,
                border_radius=10,
            ),
            
            ft.Divider(),
            
            # Risultati (dinamici)
            results_container,
            
        ], scroll=ft.ScrollMode.AUTO)
    
    # ============================================================
    # CALCULATOR
    # ============================================================
    
    def build_calculator(self):
        """Costruisce vista Calcolatore Dosi."""
        
        # Recupera preparazioni attive
        preparations = self.manager.get_preparations(only_active=True)
        
        if not preparations:
            return ft.Column([
                ft.Text("🧮 Calcolatore Dosi", size=32, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                ft.Container(
                    content=ft.Text(
                        "Nessuna preparazione attiva.\nCrea una preparazione per usare il calcolatore.",
                        size=16,
                        color=ft.Colors.GREY_400
                    ),
                    padding=50,
                    alignment=ft.alignment.center,
                ),
            ])
        
        # Dropdown preparazioni
        prep_dropdown = ft.Dropdown(
            label="Seleziona Preparazione",
            hint_text="Scegli una preparazione...",
            width=500,
            options=[
                ft.dropdown.Option(
                    str(p['id']),
                    f"#{p['id']} - {p['batch_product'][:40]} ({p['volume_remaining_ml']:.2f}ml rimanenti)"
                ) for p in preparations
            ],
        )
        
        # Info preparazione selezionata
        info_container = ft.Container(
            visible=False,
            content=ft.Column([
                ft.Text("", size=16, weight=ft.FontWeight.BOLD),  # Nome
                ft.Text("", size=14),  # Concentrazione
            ], spacing=5),
            padding=10,
            bgcolor=ft.Colors.SURFACE,
            border_radius=10,
        )
        
        # Sezione: mcg → ml
        mcg_input = ft.TextField(
            label="Dose Desiderata (mcg)",
            hint_text="es: 250",
            width=200,
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        
        ml_result = ft.Text("", size=16, weight=ft.FontWeight.BOLD)
        
        # Sezione: ml → mcg
        ml_input = ft.TextField(
            label="Volume da Somministrare (ml)",
            hint_text="es: 0.25",
            width=200,
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        
        mcg_result = ft.Text("", size=16, weight=ft.FontWeight.BOLD)
        
        # Tabella conversioni comuni
        conversions_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Dose (mcg)", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Volume (ml)", weight=ft.FontWeight.BOLD)),
            ],
            rows=[],
        )
        
        conversions_container = ft.Container(
            visible=False,
            content=conversions_table,
            border=ft.border.all(1, ft.Colors.GREY_800),
            border_radius=10,
            padding=10,
        )
        
        # Funzione calcolo mcg → ml
        def calculate_ml(e):
            if not prep_dropdown.value or not mcg_input.value:
                ml_result.value = ""
                self.page.update()
                return
            
            try:
                prep_id = int(prep_dropdown.value)
                prep = next(p for p in preparations if p['id'] == prep_id)
                
                # Calcola concentrazione
                cursor = self.manager.conn.cursor()
                cursor.execute('''
                    SELECT p.vials_used, b.mg_per_vial, p.volume_ml
                    FROM preparations p
                    JOIN batches b ON p.batch_id = b.id
                    WHERE p.id = ?
                ''', (prep_id,))
                vials, mg_per_vial, volume = cursor.fetchone()
                
                concentration_mg_ml = (vials * mg_per_vial) / volume
                concentration_mcg_ml = concentration_mg_ml * 1000
                
                # Calcola volume
                mcg = float(mcg_input.value)
                ml = mcg / concentration_mcg_ml
                
                ml_result.value = f"💉 Volume necessario: {ml:.3f} ml"
                ml_result.color = ft.Colors.GREEN_400
                
            except Exception as ex:
                ml_result.value = f"❌ Errore: {ex}"
                ml_result.color = ft.Colors.RED_400
            
            self.page.update()
        
        # Funzione calcolo ml → mcg
        def calculate_mcg(e):
            if not prep_dropdown.value or not ml_input.value:
                mcg_result.value = ""
                self.page.update()
                return
            
            try:
                prep_id = int(prep_dropdown.value)
                prep = next(p for p in preparations if p['id'] == prep_id)
                
                # Calcola concentrazione
                cursor = self.manager.conn.cursor()
                cursor.execute('''
                    SELECT p.vials_used, b.mg_per_vial, p.volume_ml
                    FROM preparations p
                    JOIN batches b ON p.batch_id = b.id
                    WHERE p.id = ?
                ''', (prep_id,))
                vials, mg_per_vial, volume = cursor.fetchone()
                
                concentration_mg_ml = (vials * mg_per_vial) / volume
                concentration_mcg_ml = concentration_mg_ml * 1000
                
                # Calcola dose
                ml = float(ml_input.value)
                mcg = ml * concentration_mcg_ml
                
                mcg_result.value = f"💊 Dose risultante: {mcg:.0f} mcg"
                mcg_result.color = ft.Colors.BLUE_400
                
            except Exception as ex:
                mcg_result.value = f"❌ Errore: {ex}"
                mcg_result.color = ft.Colors.RED_400
            
            self.page.update()
        
        # Funzione aggiornamento preparazione
        def on_prep_changed(e):
            if not prep_dropdown.value:
                info_container.visible = False
                conversions_container.visible = False
                mcg_input.value = ""
                ml_input.value = ""
                ml_result.value = ""
                mcg_result.value = ""
                self.page.update()
                return
            
            try:
                prep_id = int(prep_dropdown.value)
                prep = next(p for p in preparations if p['id'] == prep_id)
                
                # Calcola concentrazione
                cursor = self.manager.conn.cursor()
                cursor.execute('''
                    SELECT p.vials_used, b.mg_per_vial, p.volume_ml, b.product_name
                    FROM preparations p
                    JOIN batches b ON p.batch_id = b.id
                    WHERE p.id = ?
                ''', (prep_id,))
                vials, mg_per_vial, volume, product = cursor.fetchone()
                
                concentration_mg_ml = (vials * mg_per_vial) / volume
                concentration_mcg_ml = concentration_mg_ml * 1000
                
                # Aggiorna info
                info_container.content.controls[0].value = f"📦 {product}"
                info_container.content.controls[1].value = (
                    f"Concentrazione: {concentration_mg_ml:.3f} mg/ml ({concentration_mcg_ml:.1f} mcg/ml)"
                )
                info_container.visible = True
                
                # Genera tabella conversioni
                common_doses = [100, 250, 500, 750, 1000, 1500, 2000, 2500, 5000]
                conversions_table.rows.clear()
                
                for dose_mcg in common_doses:
                    dose_ml = dose_mcg / concentration_mcg_ml
                    conversions_table.rows.append(
                        ft.DataRow(cells=[
                            ft.DataCell(ft.Text(f"{dose_mcg} mcg")),
                            ft.DataCell(ft.Text(f"{dose_ml:.3f} ml", weight=ft.FontWeight.BOLD)),
                        ])
                    )
                
                conversions_container.visible = True
                
            except Exception as ex:
                self.show_snackbar(f"Errore: {ex}", error=True)
            
            self.page.update()
        
        # Collega eventi
        prep_dropdown.on_change = on_prep_changed
        mcg_input.on_change = calculate_ml
        ml_input.on_change = calculate_mcg
        
        return ft.Column([
            ft.Text("🧮 Calcolatore Dosi", size=32, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            
            # Selezione preparazione
            ft.Container(
                content=ft.Column([
                    ft.Text("Seleziona Preparazione", size=18, weight=ft.FontWeight.BOLD),
                    prep_dropdown,
                    info_container,
                ], spacing=10),
                padding=20,
                bgcolor=ft.Colors.SURFACE,
                border_radius=10,
            ),
            
            ft.Divider(height=20),
            
            # Calcolatore mcg → ml
            ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.ARROW_FORWARD, color=ft.Colors.GREEN_400),
                        ft.Text("Calcola Volume da Dose", size=18, weight=ft.FontWeight.BOLD),
                    ]),
                    ft.Text("Inserisci la dose in mcg per calcolare il volume in ml", size=12, color=ft.Colors.GREY_400),
                    ft.Row([
                        mcg_input,
                        ft.Container(width=20),
                        ft.Container(
                            content=ml_result,
                            padding=10,
                        ),
                    ]),
                ], spacing=10),
                padding=20,
                border=ft.border.all(2, ft.Colors.GREEN_400),
                border_radius=10,
            ),
            
            ft.Divider(height=20),
            
            # Calcolatore ml → mcg
            ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.ARROW_BACK, color=ft.Colors.BLUE_400),
                        ft.Text("Calcola Dose da Volume", size=18, weight=ft.FontWeight.BOLD),
                    ]),
                    ft.Text("Inserisci il volume in ml per calcolare la dose in mcg", size=12, color=ft.Colors.GREY_400),
                    ft.Row([
                        ml_input,
                        ft.Container(width=20),
                        ft.Container(
                            content=mcg_result,
                            padding=10,
                        ),
                    ]),
                ], spacing=10),
                padding=20,
                border=ft.border.all(2, ft.Colors.BLUE_400),
                border_radius=10,
            ),
            
            ft.Divider(height=20),
            
            # Tabella conversioni
            ft.Container(
                content=ft.Column([
                    ft.Text("📊 Conversioni Comuni", size=18, weight=ft.FontWeight.BOLD),
                    conversions_container,
                ], spacing=10),
                padding=20,
            ),
            
        ], scroll=ft.ScrollMode.AUTO)
    
    def show_administration_details(self, admin_id):
        """Mostra dettagli somministrazione."""
        cursor = self.manager.conn.cursor()
        cursor.execute('''
            SELECT 
                a.id,
                a.administration_datetime,
                a.dose_ml,
                a.injection_site,
                a.notes,
                prep.id as prep_id,
                b.product_name,
                pr.name as protocol_name,
                (prep.vials_used * b.mg_per_vial / prep.volume_ml) as concentration_mg_ml,
                prep.volume_ml,
                prep.volume_remaining_ml
            FROM administrations a
            JOIN preparations prep ON a.preparation_id = prep.id
            JOIN batches b ON prep.batch_id = b.id
            LEFT JOIN protocols pr ON a.protocol_id = pr.id
            WHERE a.id = ?
        ''', (admin_id,))
        
        admin = cursor.fetchone()
        if not admin:
            return
        
        admin_id, dt, dose_ml, site, notes, prep_id, product, protocol, conc, vol_tot, vol_rem = admin
        
        # Calcola dose mcg
        dose_mcg = dose_ml * conc * 1000 if conc else 0
        
        dialog = ft.AlertDialog(
            title=ft.Text(f"Somministrazione #{admin_id}"),
            content=ft.Column([
                ft.Text(f"Data e ora: {dt}", weight=ft.FontWeight.BOLD),
                ft.Divider(),
                ft.Text(f"Prodotto: {product}"),
                ft.Text(f"Preparazione: #{prep_id}"),
                ft.Text(f"Protocollo: {protocol if protocol else 'Nessuno'}"),
                ft.Divider(),
                ft.Text(f"Dose: {dose_ml}ml ({dose_mcg:.0f}mcg)", weight=ft.FontWeight.BOLD),
                ft.Text(f"Concentrazione: {conc:.3f}mg/ml ({conc*1000:.1f}mcg/ml)"),
                ft.Text(f"Sito iniezione: {site if site else 'Non specificato'}"),
                ft.Divider(),
                ft.Text(f"Volume preparazione: {vol_rem:.2f}/{vol_tot:.2f}ml"),
                ft.Text(f"Note: {notes if notes else 'Nessuna'}"),
            ], tight=True, scroll=ft.ScrollMode.AUTO, height=400),
            actions=[
                ft.TextButton("Chiudi", on_click=lambda e: self.close_dialog(dialog)),
            ],
        )
        
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()
    
    def show_edit_administration_dialog(self, admin_id):
        """Dialog modifica somministrazione - TUTTI i campi editabili."""
        cursor = self.manager.conn.cursor()
        cursor.execute('''
            SELECT 
                a.id,
                a.preparation_id,
                a.administration_datetime,
                a.dose_ml,
                a.injection_site,
                a.injection_method,
                a.notes,
                a.protocol_id,
                b.product_name,
                (prep.vials_used * b.mg_per_vial / prep.volume_ml) as concentration_mg_ml
            FROM administrations a
            JOIN preparations prep ON a.preparation_id = prep.id
            JOIN batches b ON prep.batch_id = b.id
            WHERE a.id = ?
        ''', (admin_id,))
        
        admin = cursor.fetchone()
        if not admin:
            return
        
        admin_id, prep_id, dt, dose_ml, site, method, notes, protocol_id, product, conc = admin
        
        # Recupera preparazioni e protocolli
        preparations = self.manager.get_preparations(only_active=False)
        protocols = self.manager.get_protocols(active_only=False)
        
        # Parse datetime
        try:
            dt_obj = datetime.strptime(dt, '%Y-%m-%d %H:%M:%S')
            date_val = dt_obj.strftime('%Y-%m-%d')
            time_val = dt_obj.strftime('%H:%M')
        except:
            date_val = dt[:10] if dt else ''
            time_val = dt[11:16] if len(dt) > 11 else ''
        
        # Campi modificabili
        prep_dd = ft.Dropdown(
            label="Preparazione",
            value=str(prep_id),
            options=[
                ft.dropdown.Option(
                    str(p['id']),
                    f"#{p['id']} - {p['batch_product'][:30]}"
                ) for p in preparations
            ],
            width=400,
        )
        
        date_field = ft.TextField(
            label="Data (YYYY-MM-DD)",
            value=date_val,
            width=200,
        )
        
        time_field = ft.TextField(
            label="Ora (HH:MM)",
            value=time_val,
            width=150,
        )
        
        dose_ml_field = ft.TextField(
            label="Dose (ml)",
            value=str(dose_ml),
            width=150,
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        
        # Calcolo dose mcg
        dose_mcg = dose_ml * conc * 1000 if conc else 0
        dose_mcg_field = ft.TextField(
            label="Dose (mcg)",
            value=f"{dose_mcg:.0f}",
            width=150,
            keyboard_type=ft.KeyboardType.NUMBER,
            disabled=True,  # Read-only, calcolato automaticamente
        )
        
        # Parse sito e modalità (retrocompatibilità con dati pre-migrazione)
        if method is None or method == '':
            # Vecchio formato - prova a parsare da site
            if site:
                site_lower = site.lower()
                if any(x in site_lower for x in ['subq', 'sottocutane', 'sc']):
                    method = 'SubQ'
                    # Pulisci site
                    for kw in ['SubQ', 'sub-q', 'sottocutaneo', 'Sottocutaneo', 'SC']:
                        site = site.replace(kw, '').strip()
                elif any(x in site_lower for x in ['im', 'intramuscolare']):
                    method = 'IM'
                    for kw in ['IM', 'intramuscolare', 'Intramuscolare']:
                        site = site.replace(kw, '').strip()
                else:
                    method = 'SubQ'  # Default
            else:
                method = 'SubQ'
        
        site_dd = ft.Dropdown(
            label="Sito Anatomico",
            value=site if site else "Addome",
            options=[
                ft.dropdown.Option("Addome", "Addome"),
                ft.dropdown.Option("Gluteo", "Gluteo"),
                ft.dropdown.Option("Coscia", "Coscia"),
                ft.dropdown.Option("Braccio", "Braccio"),
                ft.dropdown.Option("Fianco", "Fianco"),
                ft.dropdown.Option("Spalla", "Spalla"),
            ],
            width=200,
        )
        
        method_dd = ft.Dropdown(
            label="Modalità",
            value=method if method else "SubQ",
            options=[
                ft.dropdown.Option("SubQ", "Sottocutaneo"),
                ft.dropdown.Option("IM", "Intramuscolare"),
            ],
            width=180,
        )
        
        protocol_dd = ft.Dropdown(
            label="Protocollo (opzionale)",
            value=str(protocol_id) if protocol_id else "",
            options=[ft.dropdown.Option("", "Nessuno")] + [
                ft.dropdown.Option(str(p['id']), p['name']) for p in protocols
            ],
            width=350,
        )
        
        notes_field = ft.TextField(
            label="Note",
            value=notes if notes else "",
            multiline=True,
            width=500,
        )
        
        def update_administration(e):
            print(f"\n=== DEBUG update_administration #{admin_id} ===")
            try:
                changes = {}
                
                # Preparazione
                if int(prep_dd.value) != prep_id:
                    changes['preparation_id'] = int(prep_dd.value)
                    print(f"  Changed preparation_id: {changes['preparation_id']}")
                
                # Datetime
                new_datetime = f"{date_field.value} {time_field.value}:00"
                if new_datetime != dt:
                    changes['administration_datetime'] = new_datetime
                    print(f"  Changed administration_datetime: {changes['administration_datetime']}")
                
                # Dose
                if float(dose_ml_field.value) != dose_ml:
                    changes['dose_ml'] = float(dose_ml_field.value)
                    print(f"  Changed dose_ml: {changes['dose_ml']}")
                
                # Sito
                if site_dd.value != (site or ''):
                    changes['injection_site'] = site_dd.value if site_dd.value else None
                    print(f"  Changed injection_site: {changes['injection_site']}")
                
                # Modalità
                if method_dd.value != (method or 'SubQ'):
                    changes['injection_method'] = method_dd.value if method_dd.value else 'SubQ'
                    print(f"  Changed injection_method: {changes['injection_method']}")
                
                # Protocollo
                new_protocol = int(protocol_dd.value) if protocol_dd.value else None
                if new_protocol != protocol_id:
                    changes['protocol_id'] = new_protocol
                    print(f"  Changed protocol_id: {changes['protocol_id']}")
                
                # Note
                if notes_field.value != (notes or ''):
                    changes['notes'] = notes_field.value if notes_field.value else None
                    print(f"  Changed notes: {changes['notes']}")
                
                if changes:
                    print(f"Calling manager.update_administration with changes: {changes}")
                    self.manager.update_administration(admin_id, **changes)
                    self.close_dialog()
                    self.update_content()
                    self.show_snackbar(f"Somministrazione #{admin_id} aggiornata!")
                else:
                    self.show_snackbar("Nessuna modifica")
                    
            except Exception as ex:
                print(f"EXCEPTION in update_administration: {ex}")
                import traceback
                traceback.print_exc()
                self.show_snackbar(f"Errore: {ex}", error=True)
        
        dialog = ft.AlertDialog(
            title=ft.Text(f"Modifica Somministrazione #{admin_id}"),
            content=ft.Column([
                ft.Text("✅ TUTTI I CAMPI SONO MODIFICABILI", 
                       weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_400),
                ft.Text(f"Prodotto: {product}", size=12),
                ft.Divider(),
                prep_dd,
                ft.Row([date_field, time_field]),
                ft.Row([dose_ml_field, dose_mcg_field]),
                ft.Row([site_dd, method_dd]),  # ✅ Due dropdown nella stessa riga
                protocol_dd,
                notes_field,
            ], tight=True, scroll=ft.ScrollMode.AUTO, height=500),
            actions=[
                ft.TextButton("Annulla", on_click=lambda e: self.close_dialog(dialog)),
                ft.ElevatedButton("Salva", on_click=update_administration),
            ],
        )
        
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()
    
    # ============================================================
    # DATA INTEGRITY & RECONCILIATION
    # ============================================================
    
    def check_integrity_on_startup(self):
        """Verifica integrità dati all'avvio e mostra warning se necessario."""
        try:
            result = self.manager.check_data_integrity()
            
            if result['preparations_inconsistent'] > 0:
                # Mostra snackbar con warning
                self.show_snackbar(
                    f"⚠️ Trovate {result['preparations_inconsistent']} preparazioni con volumi inconsistenti. "
                    f"Vai al Dashboard e clicca 'Riconcilia Volumi'.",
                    error=True
                )
        except Exception as ex:
            print(f"Errore check integrity: {ex}")
    
    def show_reconciliation_dialog(self):
        """Dialog per riconciliazione volumi preparazioni."""
        
        result_text = ft.Text("", size=14)
        result_container = ft.Container(
            content=result_text,
            padding=20,
            visible=False,
        )
        
        details_column = ft.Column([], spacing=5, scroll=ft.ScrollMode.AUTO, height=300)
        details_container = ft.Container(
            content=details_column,
            visible=False,
            border=ft.border.all(1, ft.Colors.GREY_800),
            border_radius=10,
            padding=10,
        )
        
        def run_reconciliation(e):
            """Esegui riconciliazione."""
            try:
                stats = self.manager.reconcile_preparation_volumes()
                
                result_container.visible = True
                
                if stats['fixed'] == 0:
                    result_text.value = f"✅ Tutte le {stats['checked']} preparazioni sono consistenti!"
                    result_text.color = ft.Colors.GREEN_400
                    details_container.visible = False
                else:
                    result_text.value = (
                        f"🔧 Corrette {stats['fixed']}/{stats['checked']} preparazioni\n"
                        f"Differenza totale: {stats['total_diff']:.2f}ml"
                    )
                    result_text.color = ft.Colors.ORANGE_400
                    
                    # Mostra dettagli
                    details_column.controls.clear()
                    details_column.controls.append(
                        ft.Text("Dettagli correzioni:", weight=ft.FontWeight.BOLD, size=14)
                    )
                    
                    for detail in stats['details']:
                        details_column.controls.append(
                            ft.Container(
                                content=ft.Column([
                                    ft.Text(
                                        f"Prep #{detail['prep_id']}: {detail['product_name'][:40]}",
                                        weight=ft.FontWeight.BOLD,
                                        size=12
                                    ),
                                    ft.Text(
                                        f"Volume: {detail['old_volume']:.2f}ml → {detail['new_volume']:.2f}ml "
                                        f"({detail['difference']:+.2f}ml)",
                                        size=11,
                                        color=ft.Colors.GREY_400
                                    ),
                                ], spacing=2),
                                padding=5,
                                bgcolor=ft.Colors.SURFACE,
                                border_radius=5,
                            )
                        )
                    
                    details_container.visible = True
                
                self.page.update()
                
            except Exception as ex:
                result_container.visible = True
                result_text.value = f"❌ Errore: {ex}"
                result_text.color = ft.Colors.RED_400
                self.page.update()
        
        def check_only(e):
            """Solo verifica senza correggere."""
            try:
                result = self.manager.check_data_integrity()
                
                result_container.visible = True
                
                if result['preparations_inconsistent'] == 0:
                    result_text.value = f"✅ Tutte le {result['preparations_ok']} preparazioni sono consistenti!"
                    result_text.color = ft.Colors.GREEN_400
                    details_container.visible = False
                else:
                    result_text.value = (
                        f"⚠️ Trovate {result['preparations_inconsistent']} preparazioni inconsistenti\n"
                        f"Premi 'Correggi Tutto' per risolvere"
                    )
                    result_text.color = ft.Colors.ORANGE_400
                    
                    # Mostra dettagli
                    details_column.controls.clear()
                    details_column.controls.append(
                        ft.Text("Preparazioni con problemi:", weight=ft.FontWeight.BOLD, size=14)
                    )
                    
                    for detail in result['inconsistent_details']:
                        details_column.controls.append(
                            ft.Container(
                                content=ft.Column([
                                    ft.Text(
                                        f"Prep #{detail['prep_id']}: {detail['product_name'][:40]}",
                                        weight=ft.FontWeight.BOLD,
                                        size=12
                                    ),
                                    ft.Text(
                                        f"Attuale: {detail['current_volume']:.2f}ml | "
                                        f"Atteso: {detail['expected_volume']:.2f}ml | "
                                        f"Diff: {detail['difference']:+.2f}ml",
                                        size=11,
                                        color=ft.Colors.RED_400
                                    ),
                                ], spacing=2),
                                padding=5,
                                bgcolor=ft.Colors.SURFACE,
                                border_radius=5,
                            )
                        )
                    
                    details_container.visible = True
                
                self.page.update()
                
            except Exception as ex:
                result_container.visible = True
                result_text.value = f"❌ Errore: {ex}"
                result_text.color = ft.Colors.RED_400
                self.page.update()
        
        dialog = ft.AlertDialog(
            title=ft.Text("🔧 Riconciliazione Volumi"),
            content=ft.Column([
                ft.Text(
                    "Questa funzione ricalcola i volumi rimanenti di tutte le preparazioni "
                    "basandosi sulle somministrazioni attive (non eliminate).",
                    size=14
                ),
                ft.Divider(),
                ft.Text(
                    "Usa questa funzione se sospetti inconsistenze nei dati dovute a:",
                    size=12,
                    weight=ft.FontWeight.BOLD
                ),
                ft.Text("• Eliminazioni/restore di somministrazioni", size=12),
                ft.Text("• Modifiche manuali al database", size=12),
                ft.Text("• Migrazioni o bug passati", size=12),
                ft.Divider(),
                
                result_container,
                details_container,
                
            ], tight=True, scroll=ft.ScrollMode.AUTO, height=500),
            actions=[
                ft.TextButton("Chiudi", on_click=lambda e: self.close_dialog(dialog)),
                ft.ElevatedButton(
                    "Solo Verifica",
                    icon=ft.Icons.SEARCH,
                    on_click=check_only,
                ),
                ft.ElevatedButton(
                    "Correggi Tutto",
                    icon=ft.Icons.BUILD,
                    color=ft.Colors.WHITE,
                    bgcolor=ft.Colors.ORANGE_400,
                    on_click=run_reconciliation,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()
    
    # ============================================================
    # UTILITIES
    # ============================================================
    
    def close_dialog(self, dialog=None):
        """Chiude dialog corrente usando page.overlay."""
        if dialog:
            dialog.open = False
            if dialog in self.page.overlay:
                self.page.overlay.remove(dialog)
        elif self.page.overlay:
            # Chiudi l'ultimo dialog nell'overlay
            for item in reversed(self.page.overlay):
                if isinstance(item, ft.AlertDialog):
                    item.open = False
                    self.page.overlay.remove(item)
                    break
        self.page.update()
    
    def show_snackbar(self, message, error=False):
        """Mostra snackbar con messaggio."""
        self.page.snack_bar = ft.SnackBar(
            content=ft.Text(message),
            bgcolor=ft.Colors.RED_400 if error else ft.Colors.GREEN_400,
        )
        self.page.snack_bar.open = True
        self.page.update()


def start_gui(db_path=None, environment=None):
    """
    Avvia GUI Flet con supporto ambienti.
    
    Args:
        db_path: Path database (se None, usa environment)
        environment: 'production', 'development', o None (usa .env)
    """
    # Importa gestione ambiente
    try:
        import sys
        from pathlib import Path
        
        # Aggiungi scripts al path
        scripts_dir = Path(__file__).parent / 'scripts'
        print(f"DEBUG: scripts_dir = {scripts_dir}")
        print(f"DEBUG: scripts_dir exists = {scripts_dir.exists()}")

        if scripts_dir.exists():
            sys.path.insert(0, str(scripts_dir))
            print(f"DEBUG: sys.path[0] = {sys.path[0]}")
        
        from environment import get_environment
        print("DEBUG: Import riuscito!")
        USE_ENV = True
    except ImportError as e:
        USE_ENV = False
        print(f"⚠️  Errore import: {e}")
        import traceback
        traceback.print_exc()
    
    # Determina path database
    if USE_ENV and db_path is None:
        env = get_environment(environment)
        db_path = str(env.db_path)
        env_name = env.name
        
        # Warning se produzione
        if env_name == 'production':
            print()
            print("="*60)
            print("⚠️  ATTENZIONE: AMBIENTE PRODUZIONE!")
            print("="*60)
            print("Stai per aprire il database di PRODUZIONE.")
            print("Eventuali modifiche influenzeranno i dati reali.")
            print()
            response = input("Continuare? (y/n): ")
            if response.lower() != 'y':
                print("Operazione annullata.")
                return
    else:
        db_path = db_path or 'peptide_management.db'
        env_name = 'unknown'
    
    print(f"🗄️  Database: {db_path}")
    print(f"🌍 Ambiente: {env_name}")
    print()
    
    # Crea e avvia app
    app = PeptideGUI(db_path, environment=env_name)
    ft.app(target=app.main)


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Peptide Management System')
    parser.add_argument(
        '--env',
        choices=['production', 'development'],
        default=None,
        help='Ambiente (production/development, default: da .env)'
    )
    parser.add_argument(
        '--db',
        type=str,
        default=None,
        help='Path database (override configurazione ambiente)'
    )
    
    args = parser.parse_args()

    start_gui(db_path=args.db, environment=args.env)
    
