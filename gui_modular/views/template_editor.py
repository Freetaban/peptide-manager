"""
Template Editor Dialog - Editor completo per creare/modificare template
"""

import flet as ft
import json
from typing import Dict, Optional, List


class TemplateEditorDialog(ft.Container):
    """Dialog per editing completo template"""
    
    def __init__(self, app, template_data: Optional[Dict], on_save, on_cancel):
        super().__init__()
        self.app = app
        self.template_data = template_data or self._default_template()
        self.on_save_callback = on_save
        self.on_cancel_callback = on_cancel
        self.expand = True
        self._build()
    
    def _default_template(self) -> Dict:
        """Template vuoto di default"""
        return {
            'name': '',
            'short_name': '',
            'category': 'body_recomposition',
            'total_phases': 1,
            'total_duration_weeks': 4,
            'is_active': 1,
            'phases_config': json.dumps([{
                'phase_name': 'Fase 1',
                'phase_number': 1,
                'duration_weeks': 4,
                'daily_frequency': 1,
                'five_two_protocol': False,
                'administration_times': ['morning'],
                'peptides': [],
                'description': ''
            }]),
            'expected_outcomes': json.dumps([]),
            'source': 'Custom',
            'notes': '',
        }
    
    def _build(self):
        """Costruisce editor"""
        # Parse phases config
        self.phases = json.loads(self.template_data.get('phases_config', '[]'))
        if not self.phases:
            self.phases = [{
                'phase_name': 'Fase 1',
                'phase_number': 1,
                'duration_weeks': 4,
                'daily_frequency': 1,
                'five_two_protocol': False,
                'administration_times': ['morning'],
                'peptides': [],
                'description': ''
            }]
        
        # Basic info fields
        self.name_field = ft.TextField(
            label="Nome Template *",
            value=self.template_data.get('name', ''),
            hint_text="es: GH Protocol - Advanced",
            width=400,
        )
        
        self.short_name_field = ft.TextField(
            label="Nome Breve",
            value=self.template_data.get('short_name', ''),
            hint_text="es: GH-Adv",
            width=200,
        )
        
        self.category_dropdown = ft.Dropdown(
            label="Categoria",
            value=self.template_data.get('category', 'body_recomposition'),
            options=[
                ft.dropdown.Option("body_recomposition", "Body Recomposition"),
                ft.dropdown.Option("weight_loss", "Weight Loss"),
                ft.dropdown.Option("metabolic", "Metabolic Health"),
                ft.dropdown.Option("anti_aging", "Anti-Aging"),
                ft.dropdown.Option("performance", "Performance"),
                ft.dropdown.Option("recovery", "Recovery"),
            ],
            width=250,
        )
        
        self.source_field = ft.TextField(
            label="Fonte",
            value=self.template_data.get('source', 'Custom'),
            hint_text="es: Peptide Protocol Book",
            width=300,
        )
        
        self.notes_field = ft.TextField(
            label="Note",
            value=self.template_data.get('notes', ''),
            multiline=True,
            min_lines=2,
            max_lines=4,
        )
        
        # Phases list
        self.phases_container = ft.Column([], spacing=10, scroll=ft.ScrollMode.AUTO)
        self._refresh_phases()
        
        # Actions
        save_button = ft.ElevatedButton(
            "Salva Template",
            icon=ft.Icons.SAVE,
            on_click=self._save,
            bgcolor=ft.Colors.GREEN_700,
        )
        
        cancel_button = ft.ElevatedButton(
            "Chiudi",
            icon=ft.Icons.CLOSE,
            on_click=self.on_cancel_callback,
            bgcolor=ft.Colors.GREY_700,
        )
        
        add_phase_button = ft.ElevatedButton(
            "Aggiungi Fase",
            icon=ft.Icons.ADD,
            on_click=self._add_phase,
        )
        
        self.content = ft.Column([
            ft.Text("Informazioni Template", size=16, weight=ft.FontWeight.BOLD),
            ft.Row([self.name_field, self.short_name_field]),
            ft.Row([self.category_dropdown, self.source_field]),
            self.notes_field,
            ft.Divider(),
            ft.Row([
                ft.Text("Fasi del Template", size=16, weight=ft.FontWeight.BOLD),
                ft.Container(expand=True),
                add_phase_button,
            ]),
            self.phases_container,
            ft.Divider(),
            ft.Row([
                cancel_button,
                ft.Container(expand=True),
                save_button,
            ]),
        ], scroll=ft.ScrollMode.AUTO, expand=True, spacing=10)
    
    def _refresh_phases(self):
        """Aggiorna visualizzazione fasi"""
        self.phases_container.controls.clear()
        for i, phase in enumerate(self.phases):
            self.phases_container.controls.append(
                self._build_phase_editor(i, phase)
            )
        
        if hasattr(self, 'page') and self.page:
            self.update()
    
    def _build_phase_editor(self, index: int, phase: Dict) -> ft.Container:
        """Editor per singola fase"""
        # Peptides list
        peptides = self.app.manager.get_peptides()
        
        # Fields
        phase_name = ft.TextField(
            label="Nome Fase",
            value=phase.get('phase_name', f'Fase {index + 1}'),
            width=250,
            on_change=lambda e: self._update_phase(index, 'phase_name', e.control.value),
        )
        
        duration = ft.TextField(
            label="Settimane",
            value=str(phase.get('duration_weeks', 4)),
            width=100,
            keyboard_type=ft.KeyboardType.NUMBER,
            on_change=lambda e: self._update_phase(index, 'duration_weeks', int(e.control.value) if e.control.value else 4),
        )
        
        frequency = ft.TextField(
            label="Freq/giorno",
            value=str(phase.get('daily_frequency', 1)),
            width=100,
            keyboard_type=ft.KeyboardType.NUMBER,
            on_change=lambda e: self._update_phase(index, 'daily_frequency', int(e.control.value) if e.control.value else 1),
        )
        
        five_two = ft.Checkbox(
            label="5/2 Protocol",
            value=phase.get('five_two_protocol', False),
            on_change=lambda e: self._update_phase(index, 'five_two_protocol', e.control.value),
        )
        
        description = ft.TextField(
            label="Descrizione fase",
            value=phase.get('description', ''),
            multiline=True,
            min_lines=2,
            on_change=lambda e: self._update_phase(index, 'description', e.control.value),
        )
        
        # Peptides in phase
        peptides_list = ft.Column([], spacing=5)
        
        def refresh_peptides():
            peptides_list.controls.clear()
            for pep in phase.get('peptides', []):
                peptides_list.controls.append(
                    ft.Row([
                        ft.Text(pep.get('peptide_name', '?'), size=12, expand=True),
                        ft.Text(f"{pep.get('dose_mcg', 0)} mcg", size=12),
                        ft.Text(pep.get('timing', 'morning'), size=12),
                        ft.IconButton(
                            icon=ft.Icons.DELETE,
                            icon_size=16,
                            on_click=lambda e, p=pep: remove_peptide(p),
                        ),
                    ])
                )
            if hasattr(peptides_list, 'page') and peptides_list.page:
                peptides_list.update()
        
        def remove_peptide(pep):
            phase['peptides'].remove(pep)
            refresh_peptides()
        
        def add_peptide(e):
            if pep_dropdown.value and dose_field.value:
                phase.setdefault('peptides', []).append({
                    'peptide_name': next((p['name'] for p in peptides if p['id'] == int(pep_dropdown.value)), '?'),
                    'peptide_id': int(pep_dropdown.value),
                    'dose_mcg': float(dose_field.value),
                    'timing': timing_dropdown.value,
                    'mg_per_vial': 5.0,
                })
                dose_field.value = ''
                refresh_peptides()
                self.app.page.update()
        
        # Peptide addition controls
        pep_dropdown = ft.Dropdown(
            label="Peptide",
            options=[ft.dropdown.Option(str(p['id']), p['name']) for p in peptides],
            width=200,
        )
        
        dose_field = ft.TextField(
            label="Dose (mcg)",
            width=100,
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        
        timing_dropdown = ft.Dropdown(
            label="Timing",
            value="morning",
            options=[
                ft.dropdown.Option("morning", "Mattina"),
                ft.dropdown.Option("evening", "Sera"),
                ft.dropdown.Option("both", "Entrambi"),
            ],
            width=120,
        )
        
        add_pep_button = ft.IconButton(
            icon=ft.Icons.ADD_CIRCLE,
            on_click=add_peptide,
            tooltip="Aggiungi peptide",
        )
        
        refresh_peptides()
        
        # Remove phase button
        remove_button = ft.IconButton(
            icon=ft.Icons.DELETE,
            tooltip="Rimuovi fase",
            on_click=lambda e: self._remove_phase(index),
            icon_color=ft.Colors.RED_400,
        )
        
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text(f"Fase {index + 1}", weight=ft.FontWeight.BOLD),
                    ft.Container(expand=True),
                    remove_button,
                ]),
                ft.Row([phase_name, duration, frequency, five_two]),
                description,
                ft.Divider(),
                ft.Text("Peptidi in questa fase:", size=12, weight=ft.FontWeight.BOLD),
                peptides_list,
                ft.Row([pep_dropdown, dose_field, timing_dropdown, add_pep_button]),
            ], spacing=5),
            padding=15,
            border=ft.border.all(1, ft.Colors.BLUE_700),
            border_radius=8,
            bgcolor=ft.Colors.GREY_900,
        )
    
    def _update_phase(self, index: int, key: str, value):
        """Aggiorna campo fase"""
        if 0 <= index < len(self.phases):
            self.phases[index][key] = value
            self.phases[index]['phase_number'] = index + 1
    
    def _add_phase(self, e):
        """Aggiungi nuova fase"""
        self.phases.append({
            'phase_name': f'Fase {len(self.phases) + 1}',
            'phase_number': len(self.phases) + 1,
            'duration_weeks': 4,
            'daily_frequency': 1,
            'five_two_protocol': False,
            'administration_times': ['morning'],
            'peptides': [],
            'description': ''
        })
        self._refresh_phases()
    
    def _remove_phase(self, index: int):
        """Rimuovi fase"""
        if len(self.phases) > 1:
            self.phases.pop(index)
            # Rinumera fasi
            for i, phase in enumerate(self.phases):
                phase['phase_number'] = i + 1
            self._refresh_phases()
        else:
            self.app.show_snackbar("Deve esserci almeno una fase", error=True)
    
    def _save(self, e):
        """Salva template"""
        # Validazione
        if not self.name_field.value:
            self.app.show_snackbar("Il nome è obbligatorio", error=True)
            return
        
        if not self.phases:
            self.app.show_snackbar("Aggiungi almeno una fase", error=True)
            return
        
        # Calcola totali
        total_weeks = sum(p.get('duration_weeks', 0) for p in self.phases)
        
        # Prepara dati
        template_data = {
            'name': self.name_field.value,
            'short_name': self.short_name_field.value,
            'category': self.category_dropdown.value,
            'total_phases': len(self.phases),
            'total_duration_weeks': total_weeks,
            'is_active': self.template_data.get('is_active', 1),
            'phases_config': json.dumps(self.phases),
            'expected_outcomes': self.template_data.get('expected_outcomes'),
            'source': self.source_field.value,
            'notes': self.notes_field.value,
        }
        
        # Includi ID se è update
        if 'id' in self.template_data:
            template_data['id'] = self.template_data['id']
        
        # Callback
        self.on_save_callback(template_data)
