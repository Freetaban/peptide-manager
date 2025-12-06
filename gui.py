"""
GUI Flet per Peptide Management System
Interfaccia grafica moderna Material Design con CRUD completo
"""

import flet as ft
from peptide_manager import PeptideManager
from datetime import datetime, timedelta
import sys
import argparse

# Importa Janoshik views logic
try:
    from peptide_manager.janoshik.views_logic import JanoshikViewsLogic, TimeWindow
    HAS_JANOSHIK = True
except ImportError:
    HAS_JANOSHIK = False
    print("⚠️  Modulo Janoshik non disponibile")

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
        # Badge ambiente - discreto ma sempre visibile
        env_badge = None
        if self.environment == 'production':
            # PRODUZIONE: badge blu scuro discreto
            env_badge = ft.Container(
                content=ft.Text(
                    "PRODUZIONE",
                    size=10,
                    color=ft.Colors.BLUE_200,
                    weight=ft.FontWeight.W_500
                ),
                bgcolor=ft.Colors.BLUE_GREY_900,
                padding=ft.padding.symmetric(horizontal=8, vertical=3),
                border_radius=4,
                border=ft.border.all(1, ft.Colors.BLUE_GREY_700),
            )
        elif self.environment == 'development':
            env_badge = ft.Container(
                content=ft.Text(
                    "DEVELOPMENT",
                    size=10,
                    color=ft.Colors.AMBER_200,
                    weight=ft.FontWeight.W_500
                ),
                bgcolor=ft.Colors.BROWN_900,
                padding=ft.padding.symmetric(horizontal=8, vertical=3),
                border_radius=4,
                border=ft.border.all(1, ft.Colors.BROWN_700),
            )
        elif self.environment not in ['unknown']:
            env_badge = ft.Container(
                content=ft.Text(
                    self.environment.upper(),
                    size=10,
                    color=ft.Colors.GREY_400,
                    weight=ft.FontWeight.W_500
                ),
                bgcolor=ft.Colors.GREY_900,
                padding=ft.padding.symmetric(horizontal=8, vertical=3),
                border_radius=4,
                border=ft.border.all(1, ft.Colors.GREY_700),
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
                ft.NavigationRailDestination(
                    icon=ft.Icons.ANALYTICS_OUTLINED,
                    selected_icon=ft.Icons.ANALYTICS,
                    label="Mercato Janoshik",
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
            9: "janoshik",
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
            "janoshik": self.build_janoshik_market,  # TODO: Refactor to modular view
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
    
<<<<<<< HEAD
=======
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
                        ft.DataColumn(ft.Text("Preparazione", size=12, weight=ft.FontWeight.BOLD)),
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
                    f"Concentrazione: {concentration_mg_ml:.3f} mg/ml ({concentration_mcg_ml:.1f}mcg/ml)"
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
                                margin=ft.margin.only(bottom=5),
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
    
    # ============================================================
    # JANOSHIK MARKET
    # ============================================================
    
    def build_janoshik_market(self):
        """Costruisce vista mercato Janoshik con 3 tab."""
        if not HAS_JANOSHIK:
            return ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.WARNING_AMBER, size=64, color=ft.Colors.ORANGE_400),
                    ft.Text(
                        "Modulo Janoshik non disponibile",
                        size=20,
                        weight=ft.FontWeight.BOLD,
                    ),
                    ft.Text(
                        "Verifica l'installazione dei moduli Janoshik",
                        color=ft.Colors.GREY_400,
                    ),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=20),
                padding=40,
                alignment=ft.alignment.center,
            )
        
        try:
            # Inizializza logic layer
            janoshik_logic = JanoshikViewsLogic(self.db_path)
            
            # Container per le tab con caricamento lazy
            supplier_tab_content = self.build_supplier_rankings_tab(janoshik_logic)
            peptide_tab_content = self.build_peptide_rankings_tab(janoshik_logic)
            vendor_tab_content = self.build_vendor_search_tab(janoshik_logic)
            
            # Tab per le tre viste
            tabs = ft.Tabs(
                selected_index=0,
                animation_duration=300,
                tabs=[
                    ft.Tab(
                        text="Classifica Fornitori",
                        icon=ft.Icons.LEADERBOARD,
                        content=supplier_tab_content,
                    ),
                    ft.Tab(
                        text="Peptidi Trend",
                        icon=ft.Icons.TRENDING_UP,
                        content=peptide_tab_content,
                    ),
                    ft.Tab(
                        text="Cerca Vendor",
                        icon=ft.Icons.SEARCH,
                        content=vendor_tab_content,
                    ),
                ],
                expand=True,
            )
            
            # Handler per caricare dati quando tab diventa visibile
            def on_tabs_change(e):
                # Trigger caricamento dati del tab selezionato
                pass  # I dropdown gestiranno il caricamento
            
            tabs.on_change = on_tabs_change
            
            return ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.ANALYTICS, size=32),
                        ft.Text(
                            "Mercato Janoshik - Analisi Qualità Fornitori",
                            size=24,
                            weight=ft.FontWeight.BOLD,
                        ),
                    ], spacing=10),
                    ft.Divider(),
                    tabs,
                ], spacing=10, expand=True),
                padding=20,
                expand=True,
            )
        except Exception as e:
            return ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.ERROR_OUTLINE, size=64, color=ft.Colors.RED_400),
                    ft.Text(
                        f"Errore caricamento dati Janoshik: {str(e)}",
                        size=16,
                        color=ft.Colors.RED_400,
                    ),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=20),
                padding=40,
                alignment=ft.alignment.center,
            )
    
    def build_supplier_rankings_tab(self, janoshik_logic):
        """Tab classifica fornitori."""
        # Dropdown per time window
        time_window_dropdown = ft.Dropdown(
            label="Periodo",
            width=200,
            value="ALL",
            options=[
                ft.dropdown.Option(key="MONTH", text="Ultimo Mese"),
                ft.dropdown.Option(key="QUARTER", text="Ultimo Trimestre"),
                ft.dropdown.Option(key="YEAR", text="Ultimo Anno"),
                ft.dropdown.Option(key="ALL", text="Tutti i Tempi"),
            ],
        )
        
        # Container per la tabella (sarà popolato dinamicamente)
        table_container = ft.Container(expand=True)
        
        def load_rankings(time_window_key):
            """Carica rankings per time window."""
            try:
                time_window = TimeWindow[time_window_key]
                rankings = janoshik_logic.get_supplier_rankings(time_window, min_certificates=3)
                
                # Crea righe tabella
                rows = []
                for item in rankings[:50]:  # Top 50
                    rows.append(
                        ft.DataRow(cells=[
                            ft.DataCell(ft.Text(f"#{item.rank}", weight=ft.FontWeight.BOLD)),
                            ft.DataCell(ft.Text(item.supplier_name, size=14)),
                            ft.DataCell(ft.Text(f"{item.composite_score:.1f}", color=ft.Colors.PURPLE_400, weight=ft.FontWeight.BOLD)),
                            ft.DataCell(ft.Text(f"{item.total_certificates}", color=ft.Colors.BLUE_400)),
                            ft.DataCell(ft.Text(f"{item.avg_purity:.2f}%", weight=ft.FontWeight.BOLD)),
                            ft.DataCell(ft.Text(f"{item.min_purity:.2f}%", color=ft.Colors.ORANGE_300)),
                            ft.DataCell(ft.Text(f"{item.max_purity:.2f}%", color=ft.Colors.GREEN_300)),
                            ft.DataCell(ft.Text(
                                item.quality_badge,
                                size=12,
                                color=ft.Colors.AMBER_400 if "🥇" in item.quality_badge else ft.Colors.GREY_400,
                            )),
                            ft.DataCell(ft.Text(item.activity_badge, size=11)),
                        ])
                    )
                
                # Aggiorna tabella
                table_container.content = ft.Column([
                    ft.DataTable(
                        columns=[
                            ft.DataColumn(ft.Text("#", weight=ft.FontWeight.BOLD)),
                            ft.DataColumn(ft.Text("Fornitore", weight=ft.FontWeight.BOLD)),
                            ft.DataColumn(ft.Text("Score", weight=ft.FontWeight.BOLD)),
                            ft.DataColumn(ft.Text("Certificati", weight=ft.FontWeight.BOLD)),
                            ft.DataColumn(ft.Text("Purezza Media", weight=ft.FontWeight.BOLD)),
                            ft.DataColumn(ft.Text("Min", weight=ft.FontWeight.BOLD)),
                            ft.DataColumn(ft.Text("Max", weight=ft.FontWeight.BOLD)),
                            ft.DataColumn(ft.Text("Qualità", weight=ft.FontWeight.BOLD)),
                            ft.DataColumn(ft.Text("Attività", weight=ft.FontWeight.BOLD)),
                        ],
                        rows=rows,
                        border=ft.border.all(1, ft.Colors.GREY_800),
                        border_radius=10,
                        vertical_lines=ft.BorderSide(1, ft.Colors.GREY_800),
                        horizontal_lines=ft.BorderSide(1, ft.Colors.GREY_900),
                    ),
                ], scroll=ft.ScrollMode.AUTO, expand=True)
                
                if self.page:
                    table_container.update()
                
            except Exception as e:
                table_container.content = ft.Text(f"Errore: {str(e)}", color=ft.Colors.RED_400)
                if self.page:
                    table_container.update()
        
        # Handler dropdown
        def on_time_window_change(e):
            load_rankings(e.control.value)
        
        time_window_dropdown.on_change = on_time_window_change
        
        # Bottone carica dati
        load_button = ft.ElevatedButton(
            "Carica Dati",
            icon=ft.Icons.REFRESH,
            on_click=lambda e: load_rankings(time_window_dropdown.value)
        )
        
        # Popola con messaggio iniziale
        table_container.content = ft.Column([
            ft.Icon(ft.Icons.INFO_OUTLINE, size=48, color=ft.Colors.BLUE_400),
            ft.Text(
                "Clicca 'Carica Dati' per visualizzare la classifica fornitori",
                color=ft.Colors.GREY_400,
                italic=True,
            ),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10)
        
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    time_window_dropdown,
                    load_button,
                    ft.Text(
                        "Top 50 fornitori - Score: 60% qualità + 30% volume + 10% freschezza (min 3 certificati)",
                        color=ft.Colors.GREY_400,
                        italic=True,
                        size=12,
                    ),
                ], alignment=ft.MainAxisAlignment.START, spacing=10),
                ft.Divider(),
                table_container,
            ], spacing=10, expand=True),
            padding=20,
            expand=True,
        )
    
    def build_peptide_rankings_tab(self, janoshik_logic):
        """Tab peptidi più testati."""
        # Dropdown per time window
        time_window_dropdown = ft.Dropdown(
            label="Periodo",
            width=200,
            value="QUARTER",
            options=[
                ft.dropdown.Option(key="MONTH", text="Ultimo Mese"),
                ft.dropdown.Option(key="QUARTER", text="Ultimo Trimestre"),
                ft.dropdown.Option(key="YEAR", text="Ultimo Anno"),
                ft.dropdown.Option(key="ALL", text="Tutti i Tempi"),
            ],
        )
        
        # Container per la tabella
        table_container = ft.Container(expand=True)
        
        def load_peptide_rankings(time_window_key):
            """Carica peptide rankings."""
            try:
                time_window = TimeWindow[time_window_key]
                rankings = janoshik_logic.get_peptide_rankings(time_window, limit=30)
                
                # Crea righe tabella
                rows = []
                for item in rankings:
                    rows.append(
                        ft.DataRow(cells=[
                            ft.DataCell(ft.Text(f"#{item.rank}", weight=ft.FontWeight.BOLD)),
                            ft.DataCell(ft.Text(item.peptide_name, size=14)),
                            ft.DataCell(ft.Text(f"{item.test_count}", color=ft.Colors.BLUE_400, weight=ft.FontWeight.BOLD)),
                            ft.DataCell(ft.Text(f"{item.vendor_count}", color=ft.Colors.PURPLE_300)),
                            ft.DataCell(ft.Text(
                                item.popularity_badge,
                                size=11,
                                color=ft.Colors.ORANGE_400 if "🔥" in item.popularity_badge else ft.Colors.GREY_400,
                            )),
                        ])
                    )
                
                # Aggiorna tabella
                table_container.content = ft.Column([
                    ft.DataTable(
                        columns=[
                            ft.DataColumn(ft.Text("#", weight=ft.FontWeight.BOLD)),
                            ft.DataColumn(ft.Text("Peptide", weight=ft.FontWeight.BOLD)),
                            ft.DataColumn(ft.Text("Test Effettuati", weight=ft.FontWeight.BOLD)),
                            ft.DataColumn(ft.Text("Fornitori", weight=ft.FontWeight.BOLD)),
                            ft.DataColumn(ft.Text("Trend", weight=ft.FontWeight.BOLD)),
                        ],
                        rows=rows,
                        border=ft.border.all(1, ft.Colors.GREY_800),
                        border_radius=10,
                        vertical_lines=ft.BorderSide(1, ft.Colors.GREY_800),
                        horizontal_lines=ft.BorderSide(1, ft.Colors.GREY_900),
                    ),
                ], scroll=ft.ScrollMode.AUTO, expand=True)
                
                if self.page:
                    table_container.update()
                
            except Exception as e:
                table_container.content = ft.Text(f"Errore: {str(e)}", color=ft.Colors.RED_400)
                if self.page:
                    table_container.update()
        
        # Handler dropdown
        def on_time_window_change(e):
            load_peptide_rankings(e.control.value)
        
        time_window_dropdown.on_change = on_time_window_change
        
        # Bottone carica dati
        load_button = ft.ElevatedButton(
            "Carica Dati",
            icon=ft.Icons.REFRESH,
            on_click=lambda e: load_peptide_rankings(time_window_dropdown.value)
        )
        
        # Popola con messaggio iniziale
        table_container.content = ft.Column([
            ft.Icon(ft.Icons.INFO_OUTLINE, size=48, color=ft.Colors.BLUE_400),
            ft.Text(
                "Clicca 'Carica Dati' per visualizzare i peptidi più testati",
                color=ft.Colors.GREY_400,
                italic=True,
            ),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10)
        
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    time_window_dropdown,
                    load_button,
                    ft.Text(
                        "Peptidi più testati per popolarità",
                        color=ft.Colors.GREY_400,
                        italic=True,
                    ),
                ], alignment=ft.MainAxisAlignment.START, spacing=10),
                ft.Divider(),
                table_container,
            ], spacing=10, expand=True),
            padding=20,
            expand=True,
        )
    
    def build_vendor_search_tab(self, janoshik_logic):
        """Tab ricerca vendor per peptide."""
        # TextField per ricerca peptide con autocomplete
        search_field = ft.TextField(
            label="Nome Peptide",
            hint_text="Es: Semaglutide, Tirzepatide, BPC-157...",
            width=400,
            autofocus=True,
        )
        
        # Container per risultati
        results_container = ft.Container(expand=True)
        
        def search_vendors(e):
            """Cerca vendors per peptide."""
            peptide_name = search_field.value.strip()
            if not peptide_name:
                results_container.content = ft.Text(
                    "Inserisci il nome di un peptide per cercare i fornitori",
                    color=ft.Colors.GREY_400,
                    italic=True,
                )
                results_container.update()
                return
            
            try:
                result = janoshik_logic.search_vendors_for_peptide(peptide_name)
                
                if not result['all_vendors']:
                    results_container.content = ft.Column([
                        ft.Icon(ft.Icons.SEARCH_OFF, size=48, color=ft.Colors.GREY_600),
                        ft.Text(
                            f"Nessun vendor trovato per '{peptide_name}'",
                            size=16,
                            color=ft.Colors.GREY_400,
                        ),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10)
                    results_container.update()
                    return
                
                # Card miglior vendor
                best_vendor = result['best_vendor']
                best_card = ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Icon(ft.Icons.STAR, color=ft.Colors.AMBER_400, size=32),
                            ft.Text("MIGLIOR FORNITORE", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.AMBER_400),
                        ], spacing=10),
                        ft.Divider(),
                        ft.Text(best_vendor.supplier_name, size=20, weight=ft.FontWeight.BOLD),
                        ft.Row([
                            ft.Text(f"Purezza: {best_vendor.avg_purity:.2f}%", size=16, color=ft.Colors.GREEN_300),
                            ft.Text(f"Certificati: {best_vendor.total_certificates}", size=14, color=ft.Colors.BLUE_300),
                            ft.Text(f"Score: {best_vendor.recommendation_score:.0f}/100", size=14, color=ft.Colors.PURPLE_300),
                        ], spacing=20),
                        ft.Text(f"Range: {best_vendor.min_purity:.2f}% - {best_vendor.max_purity:.2f}%", size=12, color=ft.Colors.GREY_400),
                    ], spacing=10),
                    bgcolor=ft.Colors.GREY_900,
                    padding=20,
                    border_radius=10,
                    border=ft.border.all(2, ft.Colors.AMBER_700),
                )
                
                # Tabella tutti i vendor
                vendor_rows = []
                for vendor in result['all_vendors']:
                    vendor_rows.append(
                        ft.DataRow(
                            cells=[
                                ft.DataCell(ft.Text(vendor.supplier_name, size=14)),
                                ft.DataCell(ft.Text(f"{vendor.total_certificates}", color=ft.Colors.BLUE_400)),
                                ft.DataCell(ft.Text(f"{vendor.avg_purity:.2f}%", weight=ft.FontWeight.BOLD)),
                                ft.DataCell(ft.Text(f"{vendor.min_purity:.2f}%", color=ft.Colors.ORANGE_300)),
                                ft.DataCell(ft.Text(f"{vendor.max_purity:.2f}%", color=ft.Colors.GREEN_300)),
                                ft.DataCell(ft.Text(
                                    f"{vendor.recommendation_score:.0f}/100",
                                    color=ft.Colors.PURPLE_400,
                                    weight=ft.FontWeight.BOLD,
                                )),
                            ],
                            selected=vendor.supplier_name == best_vendor.supplier_name,
                        )
                    )
                
                vendors_table = ft.DataTable(
                    columns=[
                        ft.DataColumn(ft.Text("Fornitore", weight=ft.FontWeight.BOLD)),
                        ft.DataColumn(ft.Text("Certificati", weight=ft.FontWeight.BOLD)),
                        ft.DataColumn(ft.Text("Purezza Media", weight=ft.FontWeight.BOLD)),
                        ft.DataColumn(ft.Text("Min", weight=ft.FontWeight.BOLD)),
                        ft.DataColumn(ft.Text("Max", weight=ft.FontWeight.BOLD)),
                        ft.DataColumn(ft.Text("Score", weight=ft.FontWeight.BOLD)),
                    ],
                    rows=vendor_rows,
                    border=ft.border.all(1, ft.Colors.GREY_800),
                    border_radius=10,
                    vertical_lines=ft.BorderSide(1, ft.Colors.GREY_800),
                    horizontal_lines=ft.BorderSide(1, ft.Colors.GREY_900),
                )
                
                results_container.content = ft.Column([
                    best_card,
                    ft.Text(
                        f"Tutti i fornitori per {result['peptide_name']} ({len(result['all_vendors'])})",
                        size=16,
                        weight=ft.FontWeight.BOLD,
                    ),
                    ft.Container(
                        content=vendors_table,
                        border=ft.border.all(1, ft.Colors.GREY_800),
                        border_radius=10,
                    ),
                ], spacing=20, scroll=ft.ScrollMode.AUTO, expand=True)
                
                results_container.update()
                
            except Exception as e:
                results_container.content = ft.Text(f"Errore ricerca: {str(e)}", color=ft.Colors.RED_400)
                results_container.update()
        
        # Handler ricerca
        search_field.on_submit = search_vendors
        
        search_button = ft.ElevatedButton(
            "Cerca",
            icon=ft.Icons.SEARCH,
            on_click=search_vendors,
        )
        
        # Istruzioni iniziali
        results_container.content = ft.Column([
            ft.Icon(ft.Icons.INFO_OUTLINE, size=48, color=ft.Colors.BLUE_400),
            ft.Text(
                "Cerca il miglior fornitore per un peptide specifico",
                size=16,
                color=ft.Colors.GREY_400,
                text_align=ft.TextAlign.CENTER,
            ),
            ft.Text(
                "Inserisci il nome del peptide e premi Invio o clicca Cerca",
                size=12,
                color=ft.Colors.GREY_500,
                italic=True,
            ),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10)
        
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    search_field,
                    search_button,
                ], spacing=10),
                ft.Divider(),
                results_container,
            ], spacing=10, expand=True),
            padding=20,
            expand=True,
        )

>>>>>>> b290396 (feat: Add Janoshik market view to GUI)

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
        
        # Mostra solo avviso se produzione (senza richiedere conferma)
        if env_name == 'production':
            print()
            print("="*60)
            print("⚠️  AMBIENTE PRODUZIONE")
            print("="*60)
            print()
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

