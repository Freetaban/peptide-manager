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
    
    def show_snackbar(self, message: str, error: bool = False):
        """Mostra snackbar per feedback utente."""
        if not self.page:
            return
        
        snack = ft.SnackBar(
            content=ft.Text(message, color=ft.Colors.WHITE),
            bgcolor=ft.Colors.RED_400 if error else ft.Colors.GREEN_400,
            duration=3000,
        )
        self.page.overlay.append(snack)
        snack.open = True
        self.page.update()
    
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
        # Badge ambiente - SEMPRE visibile
        env_badge = None
        if self.environment == 'production':
            # PRODUZIONE: badge rosso prominente
            env_badge = ft.Container(
                content=ft.Text(
                    "🔴 PRODUZIONE",
                    size=12,
                    color=ft.Colors.WHITE,
                    weight=ft.FontWeight.BOLD
                ),
                bgcolor=ft.Colors.RED_700,
                padding=ft.padding.symmetric(horizontal=12, vertical=5),
                border_radius=5,
                border=ft.border.all(2, ft.Colors.RED_400),
            )
        elif self.environment == 'development':
            env_badge = ft.Container(
                content=ft.Text(
                    f"🔧 DEVELOPMENT",
                    size=11,
                    color=ft.Colors.ORANGE_400,
                    weight=ft.FontWeight.BOLD
                ),
                bgcolor=ft.Colors.ORANGE_900,
                padding=ft.padding.symmetric(horizontal=10, vertical=4),
                border_radius=5,
            )
        elif self.environment not in ['unknown']:
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
        
        # Registra handler chiusura per backup automatico
        def on_window_close(e):
            """Handler chiusura finestra con backup automatico."""
            try:
                from peptide_manager.backup import DatabaseBackupManager
                print(f"\n🔒 Chiusura applicazione ({self.environment})...")
                
                # Determina directory backup in base all'ambiente
                if self.environment == 'production':
                    backup_dir = "data/backups/production"
                else:
                    backup_dir = f"data/backups/{self.environment}"
                
                manager = DatabaseBackupManager(self.db_path, backup_dir=backup_dir)
                backup_path = manager.create_backup(label=f"auto_exit_{self.environment}")
                
                # Cleanup automatico
                stats = manager.cleanup_old_backups(dry_run=False)
                
                print(f"📦 Backup automatico completato: {backup_path}")
                if stats["deleted"] > 0:
                    print(f"🧹 Cleanup: {stats['deleted']} backup eliminati, "
                          f"{stats['total_size_freed'] / 1024 / 1024:.2f} MB liberati")
                print()
            except Exception as ex:
                print(f"⚠️  Errore durante backup: {ex}")
            finally:
                # Chiudi manager
                if self.manager:
                    self.manager.close()
        
        page.on_window_event = lambda e: on_window_close(e) if e.data == "close" else None
        
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
        
        # Container principale per contenuto (inizia vuoto)
        self.content_area = ft.Container(
            content=ft.Text("Loading..."),
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
        
        # Carica vista iniziale (Dashboard)
        self.update_content()
    
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
        """Aggiorna area contenuto usando viste modulari con fallback."""
        # Try modular views first, fallback to legacy methods
        modular_views = {
            "dashboard": ("gui_modular.views.dashboard", "DashboardView"),
            "batches": ("gui_modular.views.batches", "BatchesView"),
            "peptides": ("gui_modular.views.peptides", "PeptidesView"),
            "suppliers": ("gui_modular.views.suppliers", "SuppliersView"),
            "preparations": ("gui_modular.views.preparations", "PreparationsView"),
            "protocols": ("gui_modular.views.protocols", "ProtocolsView"),
            "cycles": ("gui_modular.views.cycles", "CyclesView"),
            "administrations": ("gui_modular.views.administrations", "AdministrationsView"),
            "calculator": ("gui_modular.views.calculator", "CalculatorView"),
        }
        
        legacy_views = {
            "cycles": self.build_cycles,  # Only Cycles left as legacy
        }
        
        # Try modular view
        if self.current_view in modular_views:
            module_name, class_name = modular_views[self.current_view]
            try:
                import importlib
                module = importlib.import_module(module_name)
                view_class = getattr(module, class_name)
                self.content_area.content = view_class(self)
                self.page.update()
                print(f"✅ Loaded modular view: {self.current_view}")
                return
            except Exception as e:
                print(f"⚠️  Errore caricamento vista modular {self.current_view}: {e}")
                print(f"   Uso fallback legacy")
                import traceback
                traceback.print_exc()
        
        # Fallback to legacy (only Cycles now)
        if self.current_view in legacy_views:
            self.content_area.content = legacy_views[self.current_view]()
            self.page.update()
            print(f"📦 Loaded legacy view: {self.current_view}")
        else:
            self.content_area.content = ft.Text(f"Vista '{self.current_view}' non trovata")
            self.page.update()
    
    # ============================================================
    # CYCLES (Only legacy view remaining)
    # ============================================================
    
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
                ft.Text(f"Frequenza: {protocol['frequency_per_day']}/giorno"),
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
                            print(f"  ERROR parsing dose: {e}")
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
            current_mg = existing_peptides.get(p['id'], 5)
            
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
            peptide_checks.append(ft.Row([cb, mg_field]))
            peptide_inputs[p['id']] = (cb, mg_field)
        
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
                ft.Text("Frequenza:", weight=ft.FontWeight.BOLD, size=12),
                freq_field,
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

