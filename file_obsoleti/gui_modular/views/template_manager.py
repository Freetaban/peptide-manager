"""
Template Manager Dialog - CRUD per Treatment Plan Templates
Permette di creare, modificare, eliminare e salvare template da piani esistenti
"""

import flet as ft
import json
from datetime import datetime
from typing import Dict, List, Optional


class TemplateManagerDialog(ft.Container):
    """Dialog per gestione completa template"""
    
    def __init__(self, app, on_close):
        super().__init__()
        self.app = app
        self.on_close = on_close
        self.expand = True
        self._build()
    
    def _build(self):
        """Costruisce interfaccia manager"""
        # Lista template
        self.templates_list = ft.Column([], spacing=10, scroll=ft.ScrollMode.AUTO)
        
        # Header con azioni
        header = ft.Row([
            ft.Text("Template Disponibili", size=18, weight=ft.FontWeight.BOLD),
            ft.Container(expand=True),
            ft.ElevatedButton(
                "Nuovo Template",
                icon=ft.Icons.ADD,
                on_click=self._create_new_template,
                bgcolor=ft.Colors.GREEN_700,
            ),
            ft.OutlinedButton(
                "Aggiungi Template Esempio",
                icon=ft.Icons.LIBRARY_ADD,
                on_click=self._add_example_templates,
            ),
        ])
        
        self.content = ft.Column([
            header,
            ft.Divider(),
            self.templates_list,
        ], expand=True)
        
        self._load_templates()
    
    def _load_templates(self):
        """Carica e mostra template esistenti"""
        self.templates_list.controls.clear()
        
        try:
            cursor = self.app.manager.db.conn.cursor()
            cursor.execute("""
                SELECT id, name, short_name, category, total_phases, 
                       total_duration_weeks, is_active, phases_config,
                       expected_outcomes, source, notes
                FROM treatment_plan_templates 
                ORDER BY category, name
            """)
            templates = cursor.fetchall()
            
            if not templates:
                self.templates_list.controls.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Icon(ft.Icons.FOLDER_OFF, size=80, color=ft.Colors.GREY_600),
                            ft.Text(
                                "Nessun template disponibile",
                                size=16,
                                color=ft.Colors.GREY_400
                            ),
                            ft.Text(
                                "Crea un nuovo template o aggiungi gli esempi",
                                size=12,
                                color=ft.Colors.GREY_500
                            ),
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                        padding=40,
                        alignment=ft.alignment.center,
                    )
                )
            else:
                for t in templates:
                    self.templates_list.controls.append(
                        self._build_template_card(t)
                    )
        
        except Exception as ex:
            self.templates_list.controls.append(
                ft.Text(f"Errore caricamento: {ex}", color=ft.Colors.RED_400)
            )
        
        if hasattr(self, 'page') and self.page:
            self.update()
    
    def _build_template_card(self, template: tuple) -> ft.Container:
        """Costruisce card per un template"""
        (tid, name, short_name, category, phases, weeks, 
         is_active, phases_config, outcomes, source, notes) = template
        
        # Status badge
        status_badge = ft.Container(
            content=ft.Text(
                "ATTIVO" if is_active else "DISABILITATO",
                size=10,
                weight=ft.FontWeight.BOLD,
                color=ft.Colors.WHITE
            ),
            bgcolor=ft.Colors.GREEN_700 if is_active else ft.Colors.GREY_700,
            padding=5,
            border_radius=3,
        )
        
        # Category badge
        category_colors = {
            'weight_loss': ft.Colors.PINK_700,
            'body_recomposition': ft.Colors.PURPLE_700,
            'metabolic': ft.Colors.ORANGE_700,
            'anti_aging': ft.Colors.BLUE_700,
        }
        category_badge = ft.Container(
            content=ft.Text(
                (category or "general").upper(),
                size=10,
                color=ft.Colors.WHITE
            ),
            bgcolor=category_colors.get(category, ft.Colors.GREY_700),
            padding=5,
            border_radius=3,
        )
        
        # Azioni
        actions = ft.Row([
            ft.IconButton(
                icon=ft.Icons.EDIT,
                tooltip="Modifica",
                on_click=lambda e, t=template: self._edit_template(t),
                icon_color=ft.Colors.BLUE_400,
            ),
            ft.IconButton(
                icon=ft.Icons.CONTENT_COPY,
                tooltip="Duplica",
                on_click=lambda e, t=template: self._duplicate_template(t),
                icon_color=ft.Colors.GREEN_400,
            ),
            ft.IconButton(
                icon=ft.Icons.VISIBILITY if is_active else ft.Icons.VISIBILITY_OFF,
                tooltip="Attiva/Disattiva",
                on_click=lambda e, t_id=tid, active=is_active: self._toggle_active(t_id, active),
                icon_color=ft.Colors.AMBER_400,
            ),
            ft.IconButton(
                icon=ft.Icons.DELETE,
                tooltip="Elimina",
                on_click=lambda e, t_id=tid, t_name=name: self._delete_template(t_id, t_name),
                icon_color=ft.Colors.RED_400,
            ),
        ], spacing=0)
        
        return ft.Container(
            content=ft.Row([
                ft.Column([
                    ft.Row([
                        ft.Text(name, size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                        category_badge,
                        status_badge,
                    ], spacing=5),
                    ft.Text(short_name or "", size=12, color=ft.Colors.GREY_400, italic=True),
                    ft.Row([
                        ft.Icon(ft.Icons.LAYERS, size=14, color=ft.Colors.BLUE_300),
                        ft.Text(f"{phases} fasi", size=12, color=ft.Colors.GREY_300),
                        ft.Icon(ft.Icons.CALENDAR_TODAY, size=14, color=ft.Colors.BLUE_300),
                        ft.Text(f"{weeks} settimane", size=12, color=ft.Colors.GREY_300),
                    ], spacing=5),
                    ft.Text(f"Fonte: {source or 'Custom'}", size=10, color=ft.Colors.GREY_500),
                ], spacing=5, expand=True),
                actions,
            ]),
            padding=15,
            border=ft.border.all(1, ft.Colors.GREY_700),
            border_radius=8,
            bgcolor=ft.Colors.GREY_900,
        )
    
    def _create_new_template(self, e):
        """Crea nuovo template da zero"""
        from gui_modular.views.template_editor import TemplateEditorDialog
        
        def on_save(template_data):
            self._save_template(template_data)
            editor_dialog.open = False
            self.app.page.update()
            self._load_templates()
        
        def on_cancel(e):
            editor_dialog.open = False
            self.app.page.update()
        
        editor_dialog = ft.AlertDialog(
            title=ft.Row([
                ft.Text("Nuovo Template"),
                ft.Container(expand=True),
                ft.IconButton(
                    icon=ft.Icons.CLOSE,
                    on_click=on_cancel,
                    tooltip="Chiudi",
                ),
            ]),
            content=ft.Container(
                content=TemplateEditorDialog(self.app, None, on_save, on_cancel),
                width=800,
                height=600,
            ),
            modal=True,
        )
        
        self.app.page.overlay.append(editor_dialog)
        editor_dialog.open = True
        self.app.page.update()
    
    def _edit_template(self, template: tuple):
        """Modifica template esistente"""
        from gui_modular.views.template_editor import TemplateEditorDialog
        
        (tid, name, short_name, category, phases, weeks, 
         is_active, phases_config, outcomes, source, notes) = template
        
        template_data = {
            'id': tid,
            'name': name,
            'short_name': short_name,
            'category': category,
            'total_phases': phases,
            'total_duration_weeks': weeks,
            'is_active': is_active,
            'phases_config': phases_config,
            'expected_outcomes': outcomes,
            'source': source,
            'notes': notes,
        }
        
        def on_save(updated_data):
            self._save_template(updated_data, template_id=tid)
            editor_dialog.open = False
            self.app.page.update()
            self._load_templates()
        
        def on_cancel(e):
            editor_dialog.open = False
            self.app.page.update()
        
        editor_dialog = ft.AlertDialog(
            title=ft.Row([
                ft.Text(f"Modifica Template: {name}"),
                ft.Container(expand=True),
                ft.IconButton(
                    icon=ft.Icons.CLOSE,
                    on_click=on_cancel,
                    tooltip="Chiudi",
                ),
            ]),
            content=ft.Container(
                content=TemplateEditorDialog(self.app, template_data, on_save, on_cancel),
                width=800,
                height=600,
            ),
            modal=True,
        )
        
        self.app.page.overlay.append(editor_dialog)
        editor_dialog.open = True
        self.app.page.update()
    
    def _duplicate_template(self, template: tuple):
        """Duplica template esistente"""
        (tid, name, short_name, category, phases, weeks, 
         is_active, phases_config, outcomes, source, notes) = template
        
        # Crea copia con nome modificato
        new_template = {
            'name': f"{name} (Copia)",
            'short_name': short_name,
            'category': category,
            'total_phases': phases,
            'total_duration_weeks': weeks,
            'is_active': 1,
            'phases_config': phases_config,
            'expected_outcomes': outcomes,
            'source': f"Duplicato da: {source or name}",
            'notes': notes,
        }
        
        self._save_template(new_template)
        self._load_templates()
        self.app.show_snackbar(f"✅ Template '{name}' duplicato")
    
    def _toggle_active(self, template_id: int, current_state: bool):
        """Attiva/disattiva template"""
        try:
            cursor = self.app.manager.db.conn.cursor()
            cursor.execute("""
                UPDATE treatment_plan_templates 
                SET is_active = ?
                WHERE id = ?
            """, (0 if current_state else 1, template_id))
            self.app.manager.db.conn.commit()
            
            self._load_templates()
            status = "disattivato" if current_state else "attivato"
            self.app.show_snackbar(f"✅ Template {status}")
        except Exception as ex:
            self.app.show_snackbar(f"❌ Errore: {ex}", error=True)
    
    def _delete_template(self, template_id: int, template_name: str):
        """Elimina template con conferma"""
        def confirm(e):
            try:
                cursor = self.app.manager.db.conn.cursor()
                cursor.execute("""
                    DELETE FROM treatment_plan_templates 
                    WHERE id = ?
                """, (template_id,))
                self.app.manager.db.conn.commit()
                
                confirm_dialog.open = False
                self.app.page.update()
                self._load_templates()
                self.app.show_snackbar(f"✅ Template '{template_name}' eliminato")
            except Exception as ex:
                self.app.show_snackbar(f"❌ Errore: {ex}", error=True)
        
        def cancel(e):
            confirm_dialog.open = False
            self.app.page.update()
        
        confirm_dialog = ft.AlertDialog(
            title=ft.Text("Conferma Eliminazione"),
            content=ft.Text(
                f"Eliminare definitivamente il template '{template_name}'?\n\nQuesta azione non può essere annullata.",
                size=14
            ),
            actions=[
                ft.TextButton("Annulla", on_click=cancel),
                ft.ElevatedButton("Elimina", on_click=confirm, bgcolor=ft.Colors.RED_700),
            ],
        )
        
        self.app.page.overlay.append(confirm_dialog)
        confirm_dialog.open = True
        self.app.page.update()
    
    def _save_template(self, template_data: Dict, template_id: Optional[int] = None):
        """Salva template (insert o update)"""
        try:
            cursor = self.app.manager.db.conn.cursor()
            
            if template_id:
                # Update existing
                cursor.execute("""
                    UPDATE treatment_plan_templates 
                    SET name = ?, short_name = ?, category = ?,
                        total_phases = ?, total_duration_weeks = ?,
                        is_active = ?, phases_config = ?,
                        expected_outcomes = ?, source = ?, notes = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (
                    template_data['name'],
                    template_data.get('short_name'),
                    template_data.get('category'),
                    template_data['total_phases'],
                    template_data['total_duration_weeks'],
                    template_data.get('is_active', 1),
                    template_data['phases_config'],
                    template_data.get('expected_outcomes'),
                    template_data.get('source'),
                    template_data.get('notes'),
                    template_id
                ))
                message = f"✅ Template '{template_data['name']}' aggiornato"
            else:
                # Insert new
                cursor.execute("""
                    INSERT INTO treatment_plan_templates 
                    (name, short_name, category, total_phases, total_duration_weeks,
                     is_active, phases_config, expected_outcomes, source, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    template_data['name'],
                    template_data.get('short_name'),
                    template_data.get('category'),
                    template_data['total_phases'],
                    template_data['total_duration_weeks'],
                    template_data.get('is_active', 1),
                    template_data['phases_config'],
                    template_data.get('expected_outcomes'),
                    template_data.get('source'),
                    template_data.get('notes'),
                ))
                message = f"✅ Template '{template_data['name']}' creato"
            
            self.app.manager.db.conn.commit()
            self.app.show_snackbar(message)
            
        except Exception as ex:
            self.app.show_snackbar(f"❌ Errore salvataggio: {ex}", error=True)
    
    def _add_example_templates(self, e):
        """Aggiunge template di esempio predefiniti"""
        examples = self._get_example_templates()
        
        try:
            added = 0
            for template in examples:
                # Verifica se esiste già
                cursor = self.app.manager.db.conn.cursor()
                cursor.execute("""
                    SELECT id FROM treatment_plan_templates 
                    WHERE name = ?
                """, (template['name'],))
                
                if not cursor.fetchone():
                    self._save_template(template)
                    added += 1
            
            self._load_templates()
            self.app.show_snackbar(f"✅ Aggiunti {added} template di esempio")
        except Exception as ex:
            self.app.show_snackbar(f"❌ Errore: {ex}", error=True)
    
    def _get_example_templates(self) -> List[Dict]:
        """Restituisce lista di template di esempio"""
        return [
            {
                'name': 'GH Secretagogue Protocol - Foundation',
                'short_name': 'GH-Basic',
                'category': 'body_recomposition',
                'total_phases': 3,
                'total_duration_weeks': 16,
                'phases_config': json.dumps([
                    {
                        'phase_name': 'Foundation (Weeks 1-4)',
                        'phase_number': 1,
                        'duration_weeks': 4,
                        'daily_frequency': 1,
                        'five_two_protocol': False,
                        'administration_times': ['evening'],
                        'peptides': [
                            {'peptide_name': 'CJC-1295', 'dose_mcg': 100, 'timing': 'evening'},
                            {'peptide_name': 'Ipamorelin', 'dose_mcg': 100, 'timing': 'evening'},
                        ],
                        'description': 'Low dose foundation phase'
                    },
                    {
                        'phase_name': 'Intensification (Weeks 5-12)',
                        'phase_number': 2,
                        'duration_weeks': 8,
                        'daily_frequency': 2,
                        'five_two_protocol': True,
                        'administration_times': ['morning', 'evening'],
                        'peptides': [
                            {'peptide_name': 'CJC-1295', 'dose_mcg': 200, 'timing': 'evening'},
                            {'peptide_name': 'Ipamorelin', 'dose_mcg': 200, 'timing': 'both'},
                        ],
                        'description': 'Increased dosing with 5-on-2-off pattern'
                    },
                    {
                        'phase_name': 'Maintenance (Weeks 13-16)',
                        'phase_number': 3,
                        'duration_weeks': 4,
                        'daily_frequency': 1,
                        'five_two_protocol': True,
                        'administration_times': ['evening'],
                        'peptides': [
                            {'peptide_name': 'CJC-1295', 'dose_mcg': 150, 'timing': 'evening'},
                            {'peptide_name': 'Ipamorelin', 'dose_mcg': 150, 'timing': 'evening'},
                        ],
                        'description': 'Reduced frequency maintenance'
                    },
                ]),
                'expected_outcomes': json.dumps([
                    'Improved sleep quality',
                    'Increased lean muscle mass',
                    'Enhanced recovery',
                    'Fat loss support'
                ]),
                'source': 'Peptide Protocol Guide',
                'notes': 'Standard GH secretagogue protocol for body recomposition',
                'is_active': 1,
            },
            {
                'name': 'Metabolic Reset - 12 Week',
                'short_name': 'MetRestore',
                'category': 'metabolic',
                'total_phases': 2,
                'total_duration_weeks': 12,
                'phases_config': json.dumps([
                    {
                        'phase_name': 'Reset Phase (Weeks 1-8)',
                        'phase_number': 1,
                        'duration_weeks': 8,
                        'daily_frequency': 1,
                        'five_two_protocol': False,
                        'administration_times': ['morning'],
                        'peptides': [
                            {'peptide_name': 'Semaglutide', 'dose_mcg': 250, 'timing': 'morning'},
                            {'peptide_name': 'BPC-157', 'dose_mcg': 250, 'timing': 'morning'},
                        ],
                        'description': 'Metabolic reset with gut healing'
                    },
                    {
                        'phase_name': 'Consolidation (Weeks 9-12)',
                        'phase_number': 2,
                        'duration_weeks': 4,
                        'daily_frequency': 1,
                        'five_two_protocol': True,
                        'administration_times': ['morning'],
                        'peptides': [
                            {'peptide_name': 'Semaglutide', 'dose_mcg': 500, 'timing': 'morning'},
                        ],
                        'description': 'Maintenance dosing'
                    },
                ]),
                'expected_outcomes': json.dumps([
                    'Improved insulin sensitivity',
                    'Reduced appetite',
                    'Steady weight loss',
                    'Better gut health'
                ]),
                'source': 'Metabolic Health Protocol',
                'notes': '12-week metabolic reset with gradual dose escalation',
                'is_active': 1,
            },
        ]
