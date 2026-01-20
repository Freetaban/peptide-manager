"""
Treatment Planner View - Multi-Phase Treatment Wizard
Wizard con 4 step: Definisci Fasi → Revisiona Risorse → Simulazione → Salva Piano
"""

import flet as ft
from datetime import datetime, date, timedelta
import json
from typing import List, Dict, Optional, Any


class TreatmentPlannerView(ft.Container):
    """Vista principale per Treatment Planner con lista piani e wizard"""
    
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.expand = True
        self.padding = 20
        self._build()
    
    def _build(self):
        """Build main planner view"""
        # Header
        header = ft.Row([
            ft.Text("🗓️ Piani di Trattamento Multi-Fase", size=32, weight=ft.FontWeight.BOLD),
            ft.Container(expand=True),
            ft.ElevatedButton(
                "Nuovo Piano",
                icon=ft.Icons.ADD,
                on_click=self._show_wizard,
            )
        ])
        
        # Lista piani
        self.plans_container = ft.Container()
        self._load_plans()
        
        self.content = ft.Column([
            header,
            ft.Divider(),
            self.plans_container,
        ], scroll=ft.ScrollMode.AUTO, expand=True)
    
    def _load_plans(self):
        """Carica lista piani esistenti"""
        try:
            plans = self.app.manager.list_treatment_plans()
            
            if not plans:
                self.plans_container.content = ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.CALENDAR_MONTH, size=100, color=ft.Colors.BLUE_400),
                        ft.Text(
                            "Nessun piano di trattamento",
                            size=20,
                            color=ft.Colors.WHITE
                        ),
                        ft.Text(
                            "Crea il tuo primo piano multi-fase per calcolare risorse e tracciare il progresso",
                            size=14,
                            color=ft.Colors.GREY_400,
                            text_align=ft.TextAlign.CENTER
                        ),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                    padding=100,
                    alignment=ft.alignment.center,
                )
            else:
                # Mostra piani come cards
                plan_cards = []
                for plan in plans:
                    plan_cards.append(self._build_plan_card(plan))
                
                self.plans_container.content = ft.Column(
                    plan_cards,
                    spacing=10,
                )
        
        except Exception as e:
            self.plans_container.content = ft.Text(f"Errore caricamento: {e}", color=ft.Colors.RED_400)
    
    def _build_plan_card(self, plan: Dict) -> ft.Container:
        """Costruisce card per un piano"""
        # Status badge
        status_colors = {
            'planned': ft.Colors.BLUE_400,
            'active': ft.Colors.GREEN_400,
            'completed': ft.Colors.GREY_400,
            'paused': ft.Colors.ORANGE_400,
        }
        
        status_badge = ft.Container(
            content=ft.Text(
                plan['status'].upper(),
                size=12,
                weight=ft.FontWeight.BOLD,
                color=ft.Colors.WHITE
            ),
            bgcolor=status_colors.get(plan['status'], ft.Colors.GREY_600),
            padding=ft.padding.symmetric(horizontal=10, vertical=5),
            border_radius=5,
        )
        
        # Date info
        start_date = plan.get('start_date', 'N/A')
        end_date = plan.get('planned_end_date', 'N/A')
        
        # Azioni
        actions = ft.Row([
            ft.IconButton(
                icon=ft.Icons.VISIBILITY,
                tooltip="Dettagli",
                on_click=lambda e, pid=plan['id']: self._show_plan_details(pid),
            ),
            ft.IconButton(
                icon=ft.Icons.PLAY_ARROW,
                tooltip="Attiva Prima Fase",
                on_click=lambda e, pid=plan['id']: self._activate_first_phase(pid),
                disabled=plan['status'] != 'planned',
            ),
            ft.IconButton(
                icon=ft.Icons.EDIT,
                tooltip="Modifica",
                on_click=lambda e, pid=plan['id']: self._edit_plan(pid),
                disabled=plan['status'] == 'completed',
            ),
            ft.IconButton(
                icon=ft.Icons.DELETE,
                tooltip="Elimina Piano",
                icon_color=ft.Colors.RED_400,
                on_click=lambda e, pid=plan['id'], pname=plan['name']: self._delete_plan(pid, pname),
            ),
        ], spacing=0)
        
        return ft.Container(
            content=ft.Row([
                ft.Column([
                    ft.Row([
                        ft.Text(plan['name'], size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                        status_badge,
                    ], spacing=10),
                    ft.Text(
                        plan.get('description', 'Nessuna descrizione'),
                        size=12,
                        color=ft.Colors.GREY_300
                    ),
                    ft.Row([
                        ft.Icon(ft.Icons.CALENDAR_TODAY, size=14, color=ft.Colors.BLUE_200),
                        ft.Text(f"Inizio: {start_date}", size=12, color=ft.Colors.WHITE),
                        ft.Icon(ft.Icons.EVENT, size=14, color=ft.Colors.BLUE_200),
                        ft.Text(f"Fine prevista: {end_date}", size=12, color=ft.Colors.WHITE),
                        ft.Icon(ft.Icons.LAYERS, size=14, color=ft.Colors.GREEN_200),
                        ft.Text(f"Fasi: {plan.get('total_phases', 0)}", size=12, color=ft.Colors.WHITE),
                    ], spacing=5),
                ], expand=True),
                actions,
            ]),
            padding=20,
            border=ft.border.all(2, ft.Colors.BLUE_700),
            border_radius=10,
            bgcolor=ft.Colors.with_opacity(0.95, ft.Colors.GREY_900),
        )
    
    def _show_wizard(self, e):
        """Mostra wizard creazione piano"""
        # Create dialog reference first so wizard can close it
        dialog = ft.AlertDialog(
            content=ft.Container(),  # Placeholder, will be replaced
            actions=[],
            modal=True,
        )
        
        def close_wizard():
            """Chiude il wizard"""
            dialog.open = False
            self.app.page.update()
            if dialog in self.app.page.overlay:
                self.app.page.overlay.remove(dialog)
        
        wizard = TreatmentPlanWizard(
            self.app, 
            on_complete=self._on_wizard_complete,
            on_cancel=close_wizard
        )
        
        dialog.content = wizard
        
        self.app.page.overlay.append(dialog)
        dialog.open = True
        self.app.page.update()
    
    def _on_wizard_complete(self, plan_data: Dict):
        """Callback quando wizard completa"""
        # Chiudi dialog
        if self.app.page.overlay:
            for item in reversed(self.app.page.overlay):
                if isinstance(item, ft.AlertDialog):
                    item.open = False
                    self.app.page.overlay.remove(item)
                    break
        
        # Ricarica lista
        self._load_plans()
        self.app.show_snackbar(f"✅ Piano '{plan_data['name']}' creato con successo!")
        self.app.page.update()
    
    def _show_plan_details(self, plan_id: int):
        """Mostra dettagli piano completo"""
        try:
            plan_data = self.app.manager.get_treatment_plan(plan_id)
            if not plan_data:
                self.app.show_snackbar("Piano non trovato", error=True)
                return
            
            details = PlanDetailsDialog(self.app, plan_data)
            
            def close_details(e):
                dialog.open = False
                self.app.page.update()
            
            dialog = ft.AlertDialog(
                title=ft.Text(f"Piano #{plan_id}: {plan_data['plan']['name']}"),
                content=details,
                actions=[
                    ft.TextButton("Chiudi", on_click=close_details)
                ],
            )
            
            self.app.page.overlay.append(dialog)
            dialog.open = True
            self.app.page.update()
            
        except Exception as ex:
            self.app.show_snackbar(f"Errore: {ex}", error=True)
    
    def _activate_first_phase(self, plan_id: int):
        """Attiva prima fase del piano"""
        def confirm(e):
            try:
                result = self.app.manager.activate_plan_phase(
                    plan_id=plan_id,
                    phase_number=1,
                    create_cycle=True
                )
                dialog.open = False
                self.app.page.update()
                self._load_plans()
                self.app.show_snackbar(f"✅ Fase 1 attivata! Cycle ID: {result.get('cycle_id')}")
            except Exception as ex:
                self.app.show_snackbar(f"Errore: {ex}", error=True)
        
        # Conferma
        def cancel_activate(e):
            dialog.open = False
            self.app.page.update()
        
        dialog = ft.AlertDialog(
            title=ft.Text("Attiva Prima Fase"),
            content=ft.Text(
                "Questo attiverà la prima fase del piano e creerà un nuovo Cycle per il tracking.\n\n"
                "Continuare?"
            ),
            actions=[
                ft.TextButton("Annulla", on_click=cancel_activate),
                ft.ElevatedButton("Attiva", on_click=confirm),
            ],
        )
        
        self.app.page.overlay.append(dialog)
        dialog.open = True
        self.app.page.update()
    
    def _edit_plan(self, plan_id: int):
        """Modifica piano esistente"""
        self.app.show_snackbar("Modifica piani: feature in sviluppo", error=False)
    
    def _delete_plan(self, plan_id: int, plan_name: str):
        """Elimina un piano con conferma"""
        def confirm_delete(e):
            try:
                success = self.app.manager.delete_treatment_plan(plan_id, soft=True)
                if success:
                    dialog.open = False
                    self.app.page.update()
                    self._load_plans()
                    self.app.page.update()
                    self.app.show_snackbar(f"✅ Piano '{plan_name}' eliminato")
                else:
                    self.app.show_snackbar("Errore durante l'eliminazione", error=True)
            except ValueError as ex:
                dialog.open = False
                self.app.page.update()
                self.app.show_snackbar(f"❌ {str(ex)}", error=True)
            except Exception as ex:
                dialog.open = False
                self.app.page.update()
                self.app.show_snackbar(f"Errore: {ex}", error=True)
        
        def cancel_delete(e):
            dialog.open = False
            self.app.page.update()
        
        # Dialog di conferma
        dialog = ft.AlertDialog(
            title=ft.Row([
                ft.Icon(ft.Icons.WARNING, color=ft.Colors.ORANGE_400),
                ft.Text("Elimina Piano", color=ft.Colors.WHITE),
            ]),
            content=ft.Column([
                ft.Text(
                    f"Sei sicuro di voler eliminare il piano:",
                    size=14,
                    color=ft.Colors.WHITE
                ),
                ft.Text(
                    f'"{plan_name}"',
                    size=16,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.BLUE_300
                ),
                ft.Divider(),
                ft.Text(
                    "⚠️ Nota: Il piano sarà archiviato (soft delete), non eliminato definitivamente.",
                    size=12,
                    italic=True,
                    color=ft.Colors.GREY_400
                ),
            ], tight=True, spacing=10),
            actions=[
                ft.TextButton("Annulla", on_click=cancel_delete),
                ft.ElevatedButton(
                    "Elimina",
                    icon=ft.Icons.DELETE,
                    bgcolor=ft.Colors.RED_700,
                    color=ft.Colors.WHITE,
                    on_click=confirm_delete
                ),
            ],
        )
        
        self.app.page.overlay.append(dialog)
        dialog.open = True
        self.app.page.update()


class TreatmentPlanWizard(ft.Container):
    """Wizard multi-step per creare un piano di trattamento"""
    
    def __init__(self, app, on_complete, on_cancel=None):
        super().__init__()
        self.app = app
        self.on_complete = on_complete
        self.on_cancel = on_cancel
        self.current_step = 0
        self.plan_data = {
            'name': '',
            'description': '',
            'start_date': date.today().isoformat(),
            'phases': []
        }
        self.width = 900
        self.height = 700
        self._build()
    
    def _build(self):
        """Costruisce wizard"""
        # Close button in top-right corner
        close_btn = ft.IconButton(
            icon=ft.Icons.CLOSE,
            icon_color=ft.Colors.GREY_400,
            tooltip="Chiudi wizard",
            on_click=self._cancel_wizard,
        )
        
        # Steps indicator
        self.steps_indicator = ft.Row([
            self._step_indicator(0, "Definisci Fasi"),
            ft.Icon(ft.Icons.ARROW_FORWARD, size=20, color=ft.Colors.BLUE_400),
            self._step_indicator(1, "Revisiona Risorse"),
            ft.Icon(ft.Icons.ARROW_FORWARD, size=20, color=ft.Colors.BLUE_400),
            self._step_indicator(2, "Simulazione"),
            ft.Icon(ft.Icons.ARROW_FORWARD, size=20, color=ft.Colors.BLUE_400),
            self._step_indicator(3, "Salva Piano"),
        ], alignment=ft.MainAxisAlignment.CENTER, spacing=10)
        
        # Content area (will change per step)
        self.step_content = ft.Container(expand=True)
        
        # Navigation buttons with cancel option
        self.nav_buttons = ft.Row([
            ft.TextButton(
                "Annulla",
                icon=ft.Icons.CANCEL,
                on_click=self._cancel_wizard,
            ),
            ft.TextButton(
                "Indietro",
                icon=ft.Icons.ARROW_BACK,
                on_click=self._prev_step,
            ),
            ft.Container(expand=True),
            ft.ElevatedButton(
                "Avanti",
                icon=ft.Icons.ARROW_FORWARD,
                on_click=self._next_step,
            ),
        ])
        
        # Header with close button
        header_row = ft.Row([
            ft.Container(expand=True),
            self.steps_indicator,
            ft.Container(expand=True),
            close_btn,
        ])
        
        self.content = ft.Column([
            header_row,
            ft.Divider(),
            self.step_content,
            ft.Divider(),
            self.nav_buttons,
        ], expand=True, spacing=10)
        
        # Load first step
        self._load_step()
    
    def _step_indicator(self, step_num: int, label: str):
        """Crea indicatore step"""
        is_active = step_num == self.current_step
        is_completed = step_num < self.current_step
        
        if is_completed:
            icon = ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN_400, size=24)
        elif is_active:
            icon = ft.Icon(ft.Icons.RADIO_BUTTON_CHECKED, color=ft.Colors.BLUE_400, size=24)
        else:
            icon = ft.Icon(ft.Icons.RADIO_BUTTON_UNCHECKED, color=ft.Colors.GREY_400, size=24)
        
        return ft.Column([
            icon,
            ft.Text(
                label,
                size=12,
                weight=ft.FontWeight.BOLD if is_active else ft.FontWeight.NORMAL,
                color=ft.Colors.BLUE_400 if is_active else (ft.Colors.GREEN_400 if is_completed else ft.Colors.GREY_300)
            )
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5)
    
    def _cancel_wizard(self, e=None):
        """Chiude il wizard senza salvare"""
        if self.on_cancel:
            self.on_cancel()
    
    def _load_step(self):
        """Carica contenuto dello step corrente"""
        if self.current_step == 0:
            self.step_content.content = self._build_step_phases()
        elif self.current_step == 1:
            self.step_content.content = self._build_step_resources()
        elif self.current_step == 2:
            self.step_content.content = self._build_step_simulation()
        elif self.current_step == 3:
            self.step_content.content = self._build_step_save()
        
        # Update navigation buttons
        # controls: [0]=Annulla, [1]=Indietro, [2]=Container(expand), [3]=Avanti
        self.nav_buttons.controls[1].disabled = self.current_step == 0
        
        next_btn = self.nav_buttons.controls[3]
        if self.current_step == 3:
            next_btn.text = "Crea Piano"
            next_btn.icon = ft.Icons.SAVE
        else:
            next_btn.text = "Avanti"
            next_btn.icon = ft.Icons.ARROW_FORWARD
        
        # Update steps indicator
        for i, control in enumerate(self.steps_indicator.controls):
            if isinstance(control, ft.Column):  # Skip arrows
                step_num = i // 2  # Ogni step ha un arrow tra loro
                self.steps_indicator.controls[i] = self._step_indicator(step_num, control.controls[1].value)
        
        # Only update if already attached to page
        if hasattr(self, 'page') and self.page:
            self.update()
    
    def _build_step_phases(self) -> ft.Container:
        """Step 1: Definisci Fasi (DESIGN TAB)"""
        
        # ========== Template Selection Section ==========
        templates_container = ft.Column([], spacing=10)
        
        def load_templates():
            """Carica i template disponibili"""
            templates_container.controls.clear()
            try:
                cursor = self.app.manager.db.conn.cursor()
                cursor.execute("""
                    SELECT id, name, short_name, category, total_phases, total_duration_weeks, phases_config
                    FROM treatment_plan_templates 
                    WHERE is_active = 1
                    ORDER BY category, name
                """)
                templates = cursor.fetchall()
                
                if templates:
                    templates_container.controls.append(
                        ft.Text("📚 Scegli un Template (opzionale)", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.AMBER_300)
                    )
                    
                    template_cards = []
                    for t in templates:
                        template_cards.append(
                            ft.Container(
                                content=ft.Column([
                                    ft.Row([
                                        ft.Text(t[1], weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),  # name
                                        ft.Container(
                                            content=ft.Text(t[3] or "", size=10, color=ft.Colors.WHITE),  # category
                                            bgcolor=ft.Colors.BLUE_700,
                                            padding=5,
                                            border_radius=3,
                                        ),
                                    ]),
                                    ft.Text(f"{t[4]} fasi • {t[5]} settimane", size=12, color=ft.Colors.GREY_300),
                                    ft.ElevatedButton(
                                        "Usa Template",
                                        icon=ft.Icons.COPY,
                                        on_click=lambda e, tid=t[0], tname=t[1], config=t[6]: apply_template(tid, tname, config),
                                        bgcolor=ft.Colors.BLUE_700,
                                        color=ft.Colors.WHITE,
                                    ),
                                ], spacing=5),
                                padding=15,
                                border=ft.border.all(2, ft.Colors.BLUE_600),
                                border_radius=10,
                                width=280,
                                bgcolor=ft.Colors.GREY_800,
                            )
                        )
                    
                    templates_container.controls.append(
                        ft.Row(template_cards, wrap=True, spacing=10)
                    )
                    templates_container.controls.append(ft.Divider())
                    
            except Exception as ex:
                print(f"Error loading templates: {ex}")
        
        def apply_template(template_id: int, template_name: str, phases_config: str):
            """Applica un template al piano"""
            import json
            try:
                phases = json.loads(phases_config)
                
                # Arricchisci i dati del template con peptide_id dal database
                # I template salvano solo peptide_name, ma serve peptide_id per inventory check
                all_peptides = self.app.manager.get_peptides()
                
                def find_peptide_match(template_name: str):
                    """Trova corrispondenza peptide con matching intelligente"""
                    name_lower = template_name.lower().strip()
                    
                    # 1. Match esatto
                    for p in all_peptides:
                        if p['name'].lower() == name_lower:
                            return p
                    
                    # 2. Match con varianti comuni
                    # TB500 = Thymosin Beta-4
                    aliases = {
                        'tb500': 'tb500',
                        'thymosin beta-4': 'tb500',
                        'cjc-1295 dac': 'cjc-1295',
                        'cjc-1295 no dac': 'cjc-1295',
                    }
                    if name_lower in aliases:
                        alias = aliases[name_lower]
                        for p in all_peptides:
                            if p['name'].lower() == alias:
                                return p
                    
                    # 3. Match parziale (il nome del template è contenuto nel nome DB o viceversa)
                    for p in all_peptides:
                        db_name = p['name'].lower()
                        # "Semax" -> "Semax, Selank"
                        if name_lower in db_name or db_name.startswith(name_lower):
                            return p
                    
                    # 4. Cerca il nome base senza varianti
                    # "CJC-1295 DAC" -> cerca "CJC-1295"
                    base_name = name_lower.split()[0] if ' ' in name_lower else name_lower
                    for p in all_peptides:
                        if p['name'].lower() == base_name or p['name'].lower().startswith(base_name):
                            return p
                    
                    return None
                
                for phase in phases:
                    for peptide in phase.get('peptides', []):
                        if 'peptide_id' not in peptide or peptide['peptide_id'] is None:
                            # Cerca peptide_id per nome con matching intelligente
                            pep_name = peptide.get('peptide_name', '')
                            matched = find_peptide_match(pep_name)
                            if matched:
                                peptide['peptide_id'] = matched['id']
                                # Log per debug
                                print(f"  Matched '{pep_name}' -> [{matched['id']}] '{matched['name']}'")
                            else:
                                print(f"  ⚠️ No match for '{pep_name}'")
                        # Assicura che mg_per_vial sia presente (default 5mg)
                        if 'mg_per_vial' not in peptide:
                            peptide['mg_per_vial'] = 5.0
                        # Assicura che timing sia presente
                        if 'timing' not in peptide:
                            peptide['timing'] = 'morning'
                
                self.plan_data['name'] = template_name
                self.plan_data['phases'] = phases
                self.plan_data['template_id'] = template_id
                
                # Refresh UI
                name_field.value = template_name
                refresh_phases()
                self.app.show_snackbar(f"✅ Template '{template_name}' applicato")
                self.app.page.update()
                
            except Exception as ex:
                import traceback
                traceback.print_exc()
                self.app.show_snackbar(f"Errore: {ex}", error=True)
        
        load_templates()
        
        # ========== Plan Info Section ==========
        name_field = ft.TextField(
            label="Nome Piano",
            hint_text="es: Protocol 2 - GH Secretagogue",
            value=self.plan_data['name'],
            width=500,
            on_change=lambda e: self.plan_data.update({'name': e.control.value}),
        )
        
        desc_field = ft.TextField(
            label="Descrizione (opzionale)",
            multiline=True,
            value=self.plan_data['description'],
            width=500,
            on_change=lambda e: self.plan_data.update({'description': e.control.value}),
        )
        
        start_date_field = ft.TextField(
            label="Data Inizio",
            value=self.plan_data['start_date'],
            width=200,
            on_change=lambda e: self.plan_data.update({'start_date': e.control.value}),
        )
        
        # ========== Phases List Section ==========
        phases_list = ft.Column([], spacing=10, scroll=ft.ScrollMode.AUTO)
        
        def refresh_phases():
            phases_list.controls.clear()
            for i, phase in enumerate(self.plan_data['phases']):
                phases_list.controls.append(self._build_phase_card(i, phase, refresh_phases))
            # Only update if already attached to page
            if hasattr(phases_list, 'page') and phases_list.page:
                phases_list.update()
        
        def add_phase(e):
            new_phase = {
                'phase_name': f'Fase {len(self.plan_data["phases"]) + 1}',
                'duration_weeks': 4,
                'peptides': [],
                'daily_frequency': 1,
                'five_two_protocol': False,
                'administration_times': ['morning'],
                'weekday_pattern': [1, 2, 3, 4, 5, 6, 7],  # All days
                'description': ''
            }
            self.plan_data['phases'].append(new_phase)
            refresh_phases()
        
        refresh_phases()
        
        return ft.Container(
            content=ft.Column([
                ft.Text("📝 DESIGN: Definisci Piano e Fasi", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                ft.Text("Seleziona un template o crea da zero", size=14, color=ft.Colors.GREY_300),
                ft.Divider(),
                templates_container,
                name_field,
                desc_field,
                start_date_field,
                ft.Divider(),
                ft.Row([
                    ft.Text("Fasi del Trattamento", size=16, weight=ft.FontWeight.BOLD),
                    ft.Container(expand=True),
                    ft.ElevatedButton(
                        "Aggiungi Fase",
                        icon=ft.Icons.ADD,
                        on_click=add_phase,
                    ),
                ]),
                phases_list,
            ], scroll=ft.ScrollMode.AUTO, expand=True),
            padding=20,
        )
    
    def _build_phase_card(self, index: int, phase: Dict, on_change) -> ft.Container:
        """Card per una singola fase con timing configurabile"""
        # Get peptides list
        peptides = self.app.manager.get_peptides()
        
        # Ensure defaults for new fields
        if 'administration_times' not in phase:
            phase['administration_times'] = ['morning']
        if 'weekday_pattern' not in phase:
            phase['weekday_pattern'] = [1, 2, 3, 4, 5, 6, 7]  # All days
        
        # Fields
        name_field = ft.TextField(
            label="Nome Fase",
            value=phase['phase_name'],
            width=250,
            on_change=lambda e: self._update_phase(index, 'phase_name', e.control.value),
        )
        
        weeks_field = ft.TextField(
            label="Settimane",
            value=str(phase['duration_weeks']),
            width=100,
            keyboard_type=ft.KeyboardType.NUMBER,
            on_change=lambda e: self._update_phase(index, 'duration_weeks', int(e.control.value) if e.control.value else 4),
        )
        
        freq_field = ft.TextField(
            label="Frequenza/giorno",
            value=str(phase.get('daily_frequency', 1)),
            width=100,
            keyboard_type=ft.KeyboardType.NUMBER,
            on_change=lambda e: self._update_phase(index, 'daily_frequency', int(e.control.value) if e.control.value else 1),
        )
        
        five_two_switch = ft.Switch(
            label="5/2 Protocol",
            value=phase.get('five_two_protocol', False),
            on_change=lambda e: self._update_phase(index, 'five_two_protocol', e.control.value),
        )
        
        # ========== Timing Section ==========
        def update_timing(timing: str, value: bool):
            times = phase.get('administration_times', [])
            if value and timing not in times:
                times.append(timing)
            elif not value and timing in times:
                times.remove(timing)
            phase['administration_times'] = times
        
        morning_check = ft.Checkbox(
            label="🌅 Mattina",
            value='morning' in phase.get('administration_times', ['morning']),
            on_change=lambda e: update_timing('morning', e.control.value),
        )
        
        evening_check = ft.Checkbox(
            label="🌙 Sera",
            value='evening' in phase.get('administration_times', []),
            on_change=lambda e: update_timing('evening', e.control.value),
        )
        
        # ========== Weekday Pattern Section ==========
        weekday_names = {1: "Lun", 2: "Mar", 3: "Mer", 4: "Gio", 5: "Ven", 6: "Sab", 7: "Dom"}
        
        def update_weekday(day: int, value: bool):
            pattern = phase.get('weekday_pattern', [1, 2, 3, 4, 5, 6, 7])
            if value and day not in pattern:
                pattern.append(day)
                pattern.sort()
            elif not value and day in pattern:
                pattern.remove(day)
            phase['weekday_pattern'] = pattern
        
        weekday_checks = []
        for day_num, day_name in weekday_names.items():
            weekday_checks.append(
                ft.Checkbox(
                    label=day_name,
                    value=day_num in phase.get('weekday_pattern', [1, 2, 3, 4, 5, 6, 7]),
                    on_change=lambda e, d=day_num: update_weekday(d, e.control.value),
                )
            )
        
        # Peptides selection - campi inline invece di dialog
        peptides_column = ft.Column([], spacing=5)
        
        # Campi per aggiungere nuovo peptide (sempre visibili)
        pep_dropdown = ft.Dropdown(
            label="Seleziona Peptide",
            options=[ft.dropdown.Option(str(p['id']), p['name']) for p in peptides],
            width=200,
        )
        
        dose_input = ft.TextField(
            label="Dose (mcg)",
            width=120,
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        
        # Vial size selection (common sizes)
        vial_size_dropdown = ft.Dropdown(
            label="Fiala (mg)",
            options=[
                ft.dropdown.Option("2", "2 mg"),
                ft.dropdown.Option("5", "5 mg"),
                ft.dropdown.Option("10", "10 mg"),
                ft.dropdown.Option("15", "15 mg"),
                ft.dropdown.Option("20", "20 mg"),
            ],
            value="5",
            width=100,
        )
        
        # Timing per peptide (morning/evening)
        pep_timing_dropdown = ft.Dropdown(
            label="Timing",
            options=[
                ft.dropdown.Option("morning", "🌅 Mattina"),
                ft.dropdown.Option("evening", "🌙 Sera"),
                ft.dropdown.Option("both", "🌅+🌙 Entrambi"),
            ],
            value="morning",
            width=130,
        )
        
        # Traccia quale peptide è in modalità edit (indice o None)
        editing_index = {'value': None}
        
        def edit_peptide(pep_idx):
            """Attiva la modalità edit inline per un peptide"""
            editing_index['value'] = pep_idx
            refresh_peptides()
            self.app.page.update()
        
        def cancel_edit():
            """Annulla la modifica"""
            editing_index['value'] = None
            refresh_peptides()
            self.app.page.update()
        
        def save_edit(pep_idx, dose_field, vial_field, timing_field):
            """Salva le modifiche del peptide"""
            try:
                pep = phase['peptides'][pep_idx]
                pep['dose_mcg'] = float(dose_field.value)
                pep['mg_per_vial'] = float(vial_field.value)
                pep['timing'] = timing_field.value
                
                editing_index['value'] = None
                refresh_peptides()
                self.app.page.update()
                self.app.show_snackbar(f"✅ {pep['peptide_name']} modificato")
            except ValueError:
                self.app.show_snackbar("Valori non validi", error=True)
        
        def refresh_peptides():
            peptides_column.controls.clear()
            for i, pep in enumerate(phase['peptides']):
                if editing_index['value'] == i:
                    # Modalità EDIT inline
                    edit_dose = ft.TextField(
                        value=str(pep['dose_mcg']),
                        width=90,
                        dense=True,
                        content_padding=ft.padding.all(8),
                        text_size=13,
                    )
                    edit_vial = ft.Dropdown(
                        options=[
                            ft.dropdown.Option("2", "2mg"),
                            ft.dropdown.Option("5", "5mg"),
                            ft.dropdown.Option("10", "10mg"),
                            ft.dropdown.Option("15", "15mg"),
                            ft.dropdown.Option("20", "20mg"),
                        ],
                        value=str(int(pep.get('mg_per_vial', 5))),
                        width=85,
                        dense=True,
                        content_padding=ft.padding.all(8),
                        text_size=13,
                    )
                    edit_timing = ft.Dropdown(
                        options=[
                            ft.dropdown.Option("morning", "🌅 Mattina"),
                            ft.dropdown.Option("evening", "🌙 Sera"),
                            ft.dropdown.Option("both", "🌅+🌙 Entrambi"),
                        ],
                        value=pep.get('timing', 'morning'),
                        width=140,
                        dense=True,
                        content_padding=ft.padding.all(8),
                        text_size=13,
                    )
                    peptides_column.controls.append(
                        ft.Container(
                            content=ft.Row([
                                ft.Text(f"{pep['peptide_name']}:", size=12, weight=ft.FontWeight.BOLD),
                                edit_dose,
                                ft.Text("mcg", size=10),
                                edit_vial,
                                edit_timing,
                                ft.IconButton(
                                    icon=ft.Icons.CHECK,
                                    icon_size=18,
                                    icon_color=ft.Colors.GREEN_400,
                                    tooltip="Salva",
                                    on_click=lambda e, idx=i, d=edit_dose, v=edit_vial, t=edit_timing: save_edit(idx, d, v, t),
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.CLOSE,
                                    icon_size=18,
                                    icon_color=ft.Colors.RED_400,
                                    tooltip="Annulla",
                                    on_click=lambda e: cancel_edit(),
                                ),
                            ], spacing=5),
                            bgcolor=ft.Colors.BLUE_900,
                            border_radius=5,
                            padding=5,
                        )
                    )
                else:
                    # Modalità VIEW normale
                    timing_icon = "🌅" if pep.get('timing', 'morning') == 'morning' else "🌙" if pep.get('timing') == 'evening' else "🌅🌙"
                    vial_size = pep.get('mg_per_vial', 5)
                    peptides_column.controls.append(
                        ft.Row([
                            ft.Text(f"{timing_icon} {pep['peptide_name']}: {pep['dose_mcg']}mcg (fiala {vial_size}mg)", size=12),
                            ft.IconButton(
                                icon=ft.Icons.EDIT,
                                icon_size=16,
                                tooltip="Modifica",
                                on_click=lambda e, idx=i: edit_peptide(idx),
                            ),
                            ft.IconButton(
                                icon=ft.Icons.DELETE,
                                icon_size=16,
                                tooltip="Elimina",
                                on_click=lambda e, idx=i: remove_peptide(idx),
                            ),
                        ])
                    )
        
        def add_peptide_inline(e):
            """Aggiunge peptide senza dialog"""
            if not pep_dropdown.value:
                self.app.show_snackbar("Seleziona un peptide", error=True)
                return
            
            if not dose_input.value or not dose_input.value.strip():
                self.app.show_snackbar("Inserisci la dose", error=True)
                return
            
            try:
                peptide_id = int(pep_dropdown.value)
                dose_mcg = float(dose_input.value)
                timing = pep_timing_dropdown.value or "morning"
                mg_per_vial = float(vial_size_dropdown.value) if vial_size_dropdown.value else 5.0
                
                if dose_mcg <= 0:
                    self.app.show_snackbar("La dose deve essere > 0", error=True)
                    return
                
                peptide = next((p for p in peptides if p['id'] == peptide_id), None)
                if not peptide:
                    self.app.show_snackbar("Peptide non trovato", error=True)
                    return
                
                # Aggiungi peptide con timing e vial size
                phase['peptides'].append({
                    'peptide_id': peptide_id,
                    'peptide_name': peptide['name'],
                    'dose_mcg': dose_mcg,
                    'timing': timing,
                    'mg_per_vial': mg_per_vial,
                })
                
                # Refresh UI
                refresh_peptides()
                
                # Reset campi
                pep_dropdown.value = None
                dose_input.value = ""
                pep_timing_dropdown.value = "morning"
                vial_size_dropdown.value = "5"
                
                # Update page
                self.app.page.update()
                
                self.app.show_snackbar(f"✅ {peptide['name']} aggiunto (fiala {mg_per_vial}mg)")
                
            except ValueError:
                self.app.show_snackbar("Dose non valida", error=True)
            except Exception as ex:
                import traceback
                traceback.print_exc()
                self.app.show_snackbar(f"Errore: {ex}", error=True)
        
        def remove_peptide(pep_idx):
            phase['peptides'].pop(pep_idx)
            refresh_peptides()
            self.app.page.update()
        
        def delete_phase(e):
            self.plan_data['phases'].pop(index)
            on_change()
        
        refresh_peptides()
        
        # Costruisci UI
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text(f"Fase {index + 1}", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                    ft.Container(expand=True),
                    ft.IconButton(
                        icon=ft.Icons.DELETE,
                        tooltip="Elimina Fase",
                        on_click=delete_phase,
                        icon_color=ft.Colors.RED_400,
                    ),
                ]),
                ft.Row([name_field, weeks_field, freq_field, five_two_switch], wrap=True),
                
                # Timing section
                ft.Divider(height=10, color=ft.Colors.GREY_700),
                ft.Text("⏰ Orari Somministrazione", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.AMBER_300),
                ft.Row([morning_check, evening_check]),
                
                # Weekday pattern (shown only if not using 5/2)
                ft.Text("📅 Giorni della Settimana", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.AMBER_300),
                ft.Row(weekday_checks, spacing=5),
                
                ft.Divider(color=ft.Colors.GREY_700),
                ft.Text("💉 Peptidi", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.CYAN_300),
                # Lista peptidi attuali
                peptides_column if phase['peptides'] else ft.Text("Nessun peptide selezionato", size=12, italic=True, color=ft.Colors.GREY_400),
                ft.Divider(height=5, color=ft.Colors.GREY_700),
                # Campi per aggiungere nuovo peptide (inline)
                ft.Row([
                    pep_dropdown,
                    dose_input,
                    vial_size_dropdown,
                    pep_timing_dropdown,
                    ft.ElevatedButton(
                        "Aggiungi",
                        icon=ft.Icons.ADD,
                        on_click=add_peptide_inline,
                        bgcolor=ft.Colors.BLUE_700,
                        color=ft.Colors.WHITE,
                    ),
                ], wrap=True),
            ]),
            padding=15,
            border=ft.border.all(2, ft.Colors.BLUE_600),
            border_radius=10,
            bgcolor=ft.Colors.GREY_800,
        )
    
    def _update_phase(self, index: int, key: str, value: Any):
        """Aggiorna campo di una fase"""
        self.plan_data['phases'][index][key] = value
    
    def _build_step_resources(self) -> ft.Container:
        """Step 2: PLAN TAB - Revisiona Risorse e Stima Costi"""
        if not self.plan_data['phases']:
            return ft.Container(
                content=ft.Text("Aggiungi almeno una fase nello step precedente", color=ft.Colors.ORANGE_400),
                padding=50,
            )
        
        # Calcola risorse usando backend
        try:
            from peptide_manager.calculator import ResourcePlanner
            planner = ResourcePlanner(self.app.manager.db)
            
            resources = planner.calculate_total_plan_resources(
                self.plan_data['phases'],
                inventory_check=True
            )
            
            # Save in plan_data per step successivi
            self.plan_data['resources'] = resources
            
            # Calculate total_weeks if not present
            summary = resources['summary']
            if 'total_weeks' not in summary:
                summary['total_weeks'] = sum(p['duration_weeks'] for p in self.plan_data['phases'])
            
            # Build UI
            
            # ========== Cost Estimation Section ==========
            cost_section = self._build_cost_estimation(resources)
            
            # ========== Vendor Comparison Section ==========
            vendor_section = self._build_vendor_comparison(resources)
            
            return ft.Container(
                content=ft.Column([
                    ft.Text("📊 PLAN: Risorse e Costi", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                    ft.Text("Verifica disponibilità e stima costi prima di procedere", size=14, color=ft.Colors.GREY_300),
                    ft.Divider(),
                    
                    # Summary cards
                    ft.Row([
                        self._resource_card("Durata Totale", f"{summary['total_weeks']} settimane", ft.Icons.CALENDAR_MONTH),
                        self._resource_card("Iniezioni Totali", str(summary['total_injections']), ft.Icons.MEDICATION),
                        self._resource_card("Peptidi Richiesti", str(len(resources['total_peptides'])), ft.Icons.SCIENCE),
                    ], wrap=True),
                    
                    ft.Divider(),
                    ft.Text("💉 Peptidi Richiesti", size=16, weight=ft.FontWeight.BOLD),
                    
                    # Peptides table with enhanced columns
                    ft.DataTable(
                        columns=[
                            ft.DataColumn(ft.Text("Peptide", weight=ft.FontWeight.BOLD)),
                            ft.DataColumn(ft.Text("Qty (mg)", weight=ft.FontWeight.BOLD)),
                            ft.DataColumn(ft.Text("Vials", weight=ft.FontWeight.BOLD)),
                            ft.DataColumn(ft.Text("In Stock", weight=ft.FontWeight.BOLD)),
                            ft.DataColumn(ft.Text("Da Ordinare", weight=ft.FontWeight.BOLD)),
                            ft.DataColumn(ft.Text("Status", weight=ft.FontWeight.BOLD)),
                        ],
                        rows=[
                            ft.DataRow(cells=[
                                ft.DataCell(ft.Text(pep['resource_name'])),
                                ft.DataCell(ft.Text(f"{pep.get('total_mg', pep['vials_needed'] * 5):.1f}")),
                                ft.DataCell(ft.Text(f"{pep['vials_needed']:.1f}")),
                                ft.DataCell(ft.Text(f"{pep.get('vials_available', 0):.1f}")),
                                ft.DataCell(ft.Text(
                                    f"{max(0, pep.get('vials_gap', 0)):.0f}",
                                    color=ft.Colors.RED_400 if pep.get('vials_gap', 0) > 0 else ft.Colors.GREEN_400,
                                    weight=ft.FontWeight.BOLD if pep.get('vials_gap', 0) > 0 else ft.FontWeight.NORMAL
                                )),
                                ft.DataCell(ft.Icon(
                                    ft.Icons.CHECK_CIRCLE if pep.get('vials_gap', 0) <= 0 else ft.Icons.SHOPPING_CART,
                                    color=ft.Colors.GREEN_400 if pep.get('vials_gap', 0) <= 0 else ft.Colors.ORANGE_400,
                                    size=20
                                )),
                            ]) for pep in resources['total_peptides']
                        ],
                    ),
                    
                    ft.Divider(),
                    ft.Text("🧴 Consumabili", size=16, weight=ft.FontWeight.BOLD),
                    
                    # Consumables
                    ft.Column([
                        ft.Row([
                            ft.Icon(ft.Icons.CHECK, size=16, color=ft.Colors.GREEN_400),
                            ft.Text(f"{cons['resource_name']}: {cons['quantity_needed']:.0f} {cons['quantity_unit']}", size=14)
                        ]) for cons in resources['total_consumables']
                    ], spacing=5),
                    
                    ft.Divider(),
                    cost_section,
                    
                    ft.Divider(),
                    vendor_section,
                    
                ], scroll=ft.ScrollMode.AUTO, expand=True),
                padding=20,
            )
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.ERROR, size=50, color=ft.Colors.RED_400),
                    ft.Text(f"Errore calcolo risorse: {e}", color=ft.Colors.RED_400),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=50,
            )
    
    def _build_cost_estimation(self, resources: Dict) -> ft.Container:
        """Costruisce sezione stima costi"""
        try:
            cursor = self.app.manager.db.conn.cursor()
            
            total_peptide_cost = 0.0
            total_consumable_cost = 0.0
            cost_details = []
            
            # Calcola costi peptidi da vendor_products
            for pep in resources.get('total_peptides', []):
                peptide_name = pep.get('resource_name', '')
                vials_needed = pep.get('vials_needed', 0)
                vials_to_order = max(0, pep.get('vials_gap', 0))
                
                if vials_to_order > 0:
                    # Cerca prezzo in vendor_products
                    cursor.execute("""
                        SELECT vp.price, vp.mg_per_vial, s.name as supplier_name
                        FROM vendor_products vp
                        JOIN suppliers s ON vp.supplier_id = s.id
                        JOIN peptides p ON vp.peptide_id = p.id
                        WHERE p.name LIKE ? AND vp.is_available = 1
                        ORDER BY vp.price_per_mg ASC
                        LIMIT 1
                    """, (f"%{peptide_name}%",))
                    
                    row = cursor.fetchone()
                    if row:
                        price, mg_per_vial, supplier = row
                        cost = price * vials_to_order
                        total_peptide_cost += cost
                        cost_details.append({
                            'item': peptide_name,
                            'qty': vials_to_order,
                            'unit_price': price,
                            'total': cost,
                            'supplier': supplier
                        })
            
            # Calcola costi consumabili da consumable_defaults
            for cons in resources.get('total_consumables', []):
                cons_name = cons.get('resource_name', '')
                qty_needed = cons.get('quantity_needed', 0)
                
                cursor.execute("""
                    SELECT default_price, units_per_pack
                    FROM consumable_defaults
                    WHERE display_name LIKE ?
                    LIMIT 1
                """, (f"%{cons_name}%",))
                
                row = cursor.fetchone()
                if row:
                    price, units = row
                    packs_needed = (qty_needed / units) if units > 0 else qty_needed
                    cost = price * packs_needed
                    total_consumable_cost += cost
            
            total_cost = total_peptide_cost + total_consumable_cost
            
            return ft.Container(
                content=ft.Column([
                    ft.Text("💰 Stima Costi", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.AMBER_300),
                    ft.Row([
                        self._cost_card("Peptidi", f"€{total_peptide_cost:.2f}", ft.Colors.BLUE_400),
                        self._cost_card("Consumabili", f"€{total_consumable_cost:.2f}", ft.Colors.GREEN_400),
                        self._cost_card("TOTALE", f"€{total_cost:.2f}", ft.Colors.ORANGE_400),
                    ], wrap=True),
                    
                    # Dettaglio costi peptidi da ordinare
                    ft.Column([
                        ft.Row([
                            ft.Text(f"• {d['item']}: {d['qty']:.0f} vials x €{d['unit_price']:.2f} = €{d['total']:.2f}", size=12, color=ft.Colors.WHITE),
                            ft.Text(f"({d['supplier']})", size=10, color=ft.Colors.GREY_300),
                        ]) for d in cost_details
                    ], spacing=3) if cost_details else ft.Text("Nessun peptide da ordinare", size=12, color=ft.Colors.GREEN_400, italic=True),
                    
                ], spacing=10),
                padding=15,
                bgcolor=ft.Colors.GREY_800,
                border=ft.border.all(1, ft.Colors.GREY_700),
                border_radius=10,
            )
            
        except Exception as ex:
            return ft.Container(
                content=ft.Text(f"Errore calcolo costi: {ex}", color=ft.Colors.ORANGE_400, size=12),
            )
    
    def _build_vendor_comparison(self, resources: Dict) -> ft.Container:
        """Costruisce sezione confronto vendor"""
        try:
            cursor = self.app.manager.db.conn.cursor()
            
            # Recupera vendor con prodotti disponibili
            cursor.execute("""
                SELECT DISTINCT s.id, s.name, s.country, 
                       COUNT(vp.id) as product_count,
                       AVG(vp.price_per_mg) as avg_price_per_mg
                FROM suppliers s
                JOIN vendor_products vp ON s.id = vp.supplier_id
                WHERE vp.is_available = 1
                GROUP BY s.id
                ORDER BY avg_price_per_mg ASC
                LIMIT 5
            """)
            
            vendors = cursor.fetchall()
            
            if not vendors:
                return ft.Container(
                    content=ft.Column([
                        ft.Text("🏪 Confronto Vendor", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.AMBER_300),
                        ft.Text(
                            "Nessun vendor con listino prezzi. Aggiungi prezzi in 'vendor_products' per confronto.",
                            size=12,
                            color=ft.Colors.GREY_300,
                            italic=True
                        ),
                    ]),
                )
            
            vendor_cards = []
            for v in vendors:
                vendor_cards.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Text(v[1], weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),  # name
                            ft.Text(v[2] or "", size=10, color=ft.Colors.GREY_300),  # country
                            ft.Text(f"{v[3]} prodotti", size=12, color=ft.Colors.WHITE),  # product_count
                            ft.Text(f"€{v[4]:.3f}/mg avg", size=12, color=ft.Colors.GREEN_400) if v[4] else ft.Text("N/A", size=12, color=ft.Colors.GREY_400),
                        ], spacing=3),
                        padding=10,
                        border=ft.border.all(1, ft.Colors.GREY_600),
                        border_radius=8,
                        width=150,
                        bgcolor=ft.Colors.GREY_800,
                    )
                )
            
            return ft.Container(
                content=ft.Column([
                    ft.Text("🏪 Confronto Vendor", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.AMBER_300),
                    ft.Row(vendor_cards, wrap=True, spacing=10),
                ], spacing=10),
            )
            
        except Exception as ex:
            return ft.Container(
                content=ft.Text(f"Errore caricamento vendor: {ex}", color=ft.Colors.ORANGE_400, size=12),
            )
    
    def _cost_card(self, label: str, value: str, color) -> ft.Container:
        """Card costo"""
        return ft.Container(
            content=ft.Column([
                ft.Text(value, size=20, weight=ft.FontWeight.BOLD, color=color),
                ft.Text(label, size=12, color=ft.Colors.GREY_400),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3),
            padding=15,
            border=ft.border.all(1, color),
            border_radius=8,
            width=150,
        )
    
    def _resource_card(self, label: str, value: str, icon) -> ft.Container:
        """Card risorsa"""
        return ft.Container(
            content=ft.Column([
                ft.Icon(icon, size=40, color=ft.Colors.BLUE_400),
                ft.Text(value, size=24, weight=ft.FontWeight.BOLD),
                ft.Text(label, size=12, color=ft.Colors.GREY_400),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
            padding=20,
            border=ft.border.all(1, ft.Colors.GREY_800),
            border_radius=10,
            width=200,
        )
    
    def _build_step_simulation(self) -> ft.Container:
        """Step 3: IMPLEMENT - Timeline e Preview Attivazione"""
        if not self.plan_data.get('resources'):
            return ft.Container(
                content=ft.Text("Calcola prima le risorse", color=ft.Colors.ORANGE_400),
                padding=50,
            )
        
        # Timeline preview
        phases = self.plan_data['phases']
        timeline_items = []
        current_week = 1
        start_date = date.fromisoformat(self.plan_data['start_date'])
        
        for i, phase in enumerate(phases, 1):
            end_week = current_week + phase['duration_weeks'] - 1
            phase_start = start_date + timedelta(weeks=current_week - 1)
            phase_end = start_date + timedelta(weeks=end_week)
            
            # Calcola numero dosi per la fase
            if phase.get('five_two_protocol', False):
                on_days = phase['duration_weeks'] * 5
            else:
                weekday_pattern = phase.get('weekday_pattern', [1, 2, 3, 4, 5, 6, 7])
                on_days = phase['duration_weeks'] * len(weekday_pattern)
            
            total_doses = on_days * phase.get('daily_frequency', 1)
            timing_str = ", ".join(phase.get('administration_times', ['morning']))
            
            timeline_items.append(
                ft.Container(
                    content=ft.Row([
                        # Timeline indicator
                        ft.Container(
                            content=ft.Column([
                                ft.Text(f"W{current_week}", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                                ft.Container(width=2, height=50, bgcolor=ft.Colors.BLUE_400),
                                ft.Text(f"W{end_week}", size=12, color=ft.Colors.WHITE),
                            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                            width=50,
                        ),
                        # Phase details
                        ft.Container(
                            content=ft.Column([
                                ft.Row([
                                    ft.Text(f"Fase {i}: {phase['phase_name']}", weight=ft.FontWeight.BOLD, size=16, color=ft.Colors.WHITE),
                                    ft.Container(
                                        content=ft.Text(f"{phase['duration_weeks']}w", size=10, color=ft.Colors.WHITE),
                                        bgcolor=ft.Colors.BLUE_700,
                                        padding=5,
                                        border_radius=3,
                                    ),
                                ]),
                                ft.Text(f"📅 {phase_start.strftime('%d/%m/%Y')} → {phase_end.strftime('%d/%m/%Y')}", size=12, color=ft.Colors.GREY_300),
                                ft.Text(f"💉 {', '.join([p['peptide_name'] for p in phase['peptides']])}", size=12, color=ft.Colors.WHITE),
                                ft.Text(f"⏰ {timing_str} • {phase.get('daily_frequency', 1)}x/giorno" + 
                                       (" (5/2)" if phase.get('five_two_protocol', False) else ""), size=12, color=ft.Colors.WHITE),
                                ft.Text(f"📊 ~{total_doses} dosi totali in questa fase", size=11, color=ft.Colors.GREEN_400),
                            ], spacing=3),
                            expand=True,
                            padding=10,
                        ),
                    ]),
                    padding=10,
                    border=ft.border.all(2, ft.Colors.BLUE_600 if i == 1 else ft.Colors.GREY_600),
                    border_radius=10,
                    bgcolor=ft.Colors.BLUE_900 if i == 1 else ft.Colors.GREY_800,
                )
            )
            
            current_week = end_week + 1
        
        # Total duration summary
        total_weeks = sum(p['duration_weeks'] for p in phases)
        end_date = start_date + timedelta(weeks=total_weeks)
        total_doses = sum(
            (p['duration_weeks'] * (5 if p.get('five_two_protocol') else len(p.get('weekday_pattern', [1,2,3,4,5,6,7])))) * p.get('daily_frequency', 1)
            for p in phases
        )
        
        # iCal Export Button
        def export_ical(e):
            self._generate_ical_export()
        
        return ft.Container(
            content=ft.Column([
                ft.Text("🚀 IMPLEMENT: Timeline & Attivazione", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                ft.Text(
                    "Preview del piano completo con date e schedule",
                    size=14,
                    color=ft.Colors.GREY_300
                ),
                ft.Divider(),
                
                # Summary row
                ft.Row([
                    ft.Container(
                        content=ft.Column([
                            ft.Text("📅 Inizio", size=12, color=ft.Colors.GREY_300),
                            ft.Text(start_date.strftime('%d/%m/%Y'), size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        padding=10,
                        border=ft.border.all(1, ft.Colors.GREY_600),
                        border_radius=8,
                        bgcolor=ft.Colors.GREY_800,
                    ),
                    ft.Icon(ft.Icons.ARROW_FORWARD, color=ft.Colors.BLUE_400),
                    ft.Container(
                        content=ft.Column([
                            ft.Text("🏁 Fine", size=12, color=ft.Colors.GREY_300),
                            ft.Text(end_date.strftime('%d/%m/%Y'), size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        padding=10,
                        border=ft.border.all(1, ft.Colors.GREY_600),
                        border_radius=8,
                        bgcolor=ft.Colors.GREY_800,
                    ),
                    ft.Container(
                        content=ft.Column([
                            ft.Text("💉 Dosi Totali", size=12, color=ft.Colors.GREY_300),
                            ft.Text(f"~{total_doses}", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_400),
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        padding=10,
                        border=ft.border.all(1, ft.Colors.GREEN_700),
                        border_radius=8,
                        bgcolor=ft.Colors.GREY_800,
                    ),
                ], alignment=ft.MainAxisAlignment.CENTER, spacing=20),
                
                ft.Divider(),
                ft.Text("📋 Timeline Fasi", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.AMBER_300),
                ft.Column(timeline_items, spacing=10),
                
                ft.Divider(),
                
                # Export options
                ft.Container(
                    content=ft.Column([
                        ft.Text("📤 Opzioni Export", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.AMBER_300),
                        ft.Row([
                            ft.ElevatedButton(
                                "Esporta iCal",
                                icon=ft.Icons.CALENDAR_MONTH,
                                on_click=export_ical,
                                bgcolor=ft.Colors.BLUE_700,
                                color=ft.Colors.WHITE,
                            ),
                            ft.Text(
                                "Genera file .ics per importare in Google Calendar, Outlook, Apple Calendar",
                                size=12,
                                color=ft.Colors.GREY_300,
                            ),
                        ]),
                    ], spacing=10),
                    padding=15,
                    bgcolor=ft.Colors.GREY_900,
                    border_radius=10,
                ),
                
                ft.Divider(),
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.INFO_OUTLINE, size=40, color=ft.Colors.BLUE_400),
                        ft.Text("ℹ️ Prossimi passi", weight=ft.FontWeight.BOLD),
                        ft.Text(
                            "1. Clicca 'Avanti' per salvare il piano\n"
                            "2. Dalla lista piani, attiva la prima fase\n"
                            "3. Il sistema creerà un Cycle per tracking somministrazioni\n"
                            "4. Riceverai reminder per ogni dose schedulata",
                            size=12,
                            text_align=ft.TextAlign.CENTER,
                            color=ft.Colors.GREY_400
                        ),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                    padding=20,
                    bgcolor=ft.Colors.BLUE_900,
                    border_radius=10,
                ),
            ], scroll=ft.ScrollMode.AUTO, expand=True),
            padding=20,
        )
    
    def _generate_ical_export(self):
        """Genera file iCal per export calendario"""
        try:
            from pathlib import Path
            
            phases = self.plan_data['phases']
            start_date = date.fromisoformat(self.plan_data['start_date'])
            plan_name = self.plan_data['name']
            
            # Build iCal content
            ical_lines = [
                "BEGIN:VCALENDAR",
                "VERSION:2.0",
                "PRODID:-//Peptide Management System//Treatment Planner//IT",
                f"X-WR-CALNAME:{plan_name}",
            ]
            
            current_week = 0
            event_uid = 1
            
            for phase_num, phase in enumerate(phases, 1):
                phase_start = start_date + timedelta(weeks=current_week)
                duration_weeks = phase['duration_weeks']
                daily_freq = phase.get('daily_frequency', 1)
                five_two = phase.get('five_two_protocol', False)
                weekday_pattern = phase.get('weekday_pattern', [1, 2, 3, 4, 5, 6, 7])
                admin_times = phase.get('administration_times', ['morning'])
                
                # Generate events for each day
                for day_offset in range(duration_weeks * 7):
                    event_date = phase_start + timedelta(days=day_offset)
                    weekday = event_date.isoweekday()
                    
                    # Check if this day should have doses
                    if five_two and weekday > 5:
                        continue  # Skip weekends for 5/2
                    if weekday not in weekday_pattern:
                        continue
                    
                    # Generate event for each admin time
                    for timing in admin_times:
                        if timing == 'morning':
                            event_time = "080000"
                        elif timing == 'evening':
                            event_time = "200000"
                        else:
                            event_time = "120000"
                        
                        peptides_str = ", ".join([p['peptide_name'] for p in phase['peptides']])
                        doses_str = ", ".join([f"{p['peptide_name']} {p['dose_mcg']}mcg" for p in phase['peptides']])
                        
                        ical_lines.extend([
                            "BEGIN:VEVENT",
                            f"UID:peptide-{event_uid}@pms",
                            f"DTSTART:{event_date.strftime('%Y%m%d')}T{event_time}",
                            f"DTEND:{event_date.strftime('%Y%m%d')}T{event_time}",
                            f"SUMMARY:💉 {phase['phase_name']} - {timing.capitalize()}",
                            f"DESCRIPTION:Fase {phase_num}: {phase['phase_name']}\\n{doses_str}",
                            "BEGIN:VALARM",
                            "ACTION:DISPLAY",
                            "TRIGGER:-PT15M",
                            f"DESCRIPTION:Reminder: {peptides_str}",
                            "END:VALARM",
                            "END:VEVENT",
                        ])
                        event_uid += 1
                
                current_week += duration_weeks
            
            ical_lines.append("END:VCALENDAR")
            
            # Save file
            export_dir = Path("data/exports")
            export_dir.mkdir(parents=True, exist_ok=True)
            
            filename = f"{plan_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.ics"
            filepath = export_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("\r\n".join(ical_lines))
            
            self.app.show_snackbar(f"✅ Esportato: {filepath}")
            
        except Exception as ex:
            import traceback
            traceback.print_exc()
            self.app.show_snackbar(f"Errore export: {ex}", error=True)
    
    def _build_step_save(self) -> ft.Container:
        """Step 4: Salva Piano"""
        return ft.Container(
            content=ft.Column([
                ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, size=100, color=ft.Colors.GREEN_400),
                ft.Text("✅ Pronto per Creare il Piano!", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                ft.Divider(),
                ft.Text("Riepilogo:", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.AMBER_300),
                ft.Text(f"Nome: {self.plan_data['name']}", size=14, color=ft.Colors.WHITE),
                ft.Text(f"Data inizio: {self.plan_data['start_date']}", size=14, color=ft.Colors.WHITE),
                ft.Text(f"Fasi: {len(self.plan_data['phases'])}", size=14, color=ft.Colors.WHITE),
                ft.Text(
                    f"Durata totale: {self.plan_data.get('resources', {}).get('summary', {}).get('total_weeks', 0)} settimane",
                    size=14,
                    color=ft.Colors.WHITE
                ),
                ft.Divider(),
                ft.Text(
                    "Cliccando 'Crea Piano' il sistema:\n"
                    "• Salverà il piano nel database\n"
                    "• Calcolerà tutte le risorse necessarie\n"
                    "• Renderà disponibili le fasi per l'attivazione",
                    size=12,
                    color=ft.Colors.GREY_300,
                ),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15),
            padding=50,
            alignment=ft.alignment.center,
        )
    
    def _prev_step(self, e):
        """Torna allo step precedente"""
        if self.current_step > 0:
            self.current_step -= 1
            self._load_step()
    
    def _next_step(self, e):
        """Avanza allo step successivo"""
        # Validazione step corrente
        if self.current_step == 0:
            if not self.plan_data['name']:
                self.app.show_snackbar("Inserisci un nome per il piano", error=True)
                return
            if not self.plan_data['phases']:
                self.app.show_snackbar("Aggiungi almeno una fase", error=True)
                return
        
        if self.current_step < 3:
            self.current_step += 1
            self._load_step()
        else:
            # Step 3 = Salva
            self._create_plan()
    
    def _create_plan(self):
        """Crea il piano nel database"""
        try:
            result = self.app.manager.create_treatment_plan(
                name=self.plan_data['name'],
                start_date=self.plan_data['start_date'],
                phases_config=self.plan_data['phases'],
                description=self.plan_data.get('description'),
                calculate_resources=True
            )
            
            # Callback success
            if self.on_complete:
                self.on_complete({
                    'name': self.plan_data['name'],
                    'plan_id': result['plan_id'],
                })
            
        except Exception as ex:
            import traceback
            traceback.print_exc()
            self.app.show_snackbar(f"Errore creazione piano: {ex}", error=True)


class PlanDetailsDialog(ft.Container):
    """Dialog dettagli piano completo"""
    
    def __init__(self, app, plan_data: Dict):
        super().__init__()
        self.app = app
        self.plan_data = plan_data
        self.width = 800
        self.height = 600
        self._build()
    
    def _build(self):
        """Build details view"""
        plan = self.plan_data['plan']
        phases = self.plan_data['phases']
        resources = self.plan_data['resources']
        
        # Phases list
        phases_column = ft.Column([], spacing=10)
        
        for phase in phases:
            peptides_list = json.loads(phase['peptides_config'])
            
            phases_column.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Text(f"Fase {phase['phase_number']}: {phase['phase_name']}", weight=ft.FontWeight.BOLD),
                            ft.Container(expand=True),
                            ft.Text(phase['status'].upper(), size=12, color=ft.Colors.BLUE_400),
                        ]),
                        ft.Text(f"Durata: {phase['duration_weeks']} settimane", size=12),
                        ft.Text(f"Frequenza: {phase['daily_frequency']}x/giorno", size=12),
                        ft.Text(
                            f"Peptidi: {', '.join([p['peptide_name'] for p in peptides_list])}",
                            size=12,
                            color=ft.Colors.GREY_400
                        ),
                    ], spacing=5),
                    padding=10,
                    border=ft.border.all(1, ft.Colors.GREY_800),
                    border_radius=5,
                )
            )
        
        # Resources summary
        needs_ordering = self.plan_data.get('needs_ordering', False)
        
        self.content = ft.Column([
            ft.Text(f"📅 {plan['name']}", size=20, weight=ft.FontWeight.BOLD),
            ft.Text(f"Status: {plan['status'].upper()}", size=14),
            ft.Text(f"Inizio: {plan['start_date']} | Fine prevista: {plan['planned_end_date']}", size=12),
            ft.Divider(),
            ft.Text("Fasi", size=16, weight=ft.FontWeight.BOLD),
            phases_column,
            ft.Divider(),
            ft.Row([
                ft.Icon(
                    ft.Icons.WARNING if needs_ordering else ft.Icons.CHECK_CIRCLE,
                    color=ft.Colors.ORANGE_400 if needs_ordering else ft.Colors.GREEN_400,
                    size=30
                ),
                ft.Text(
                    "Alcuni peptidi devono essere ordinati" if needs_ordering else "Tutte le risorse disponibili",
                    size=14,
                    weight=ft.FontWeight.BOLD
                ),
            ]),
        ], scroll=ft.ScrollMode.AUTO, expand=True)
