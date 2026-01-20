"""CalculatorView - Dose calculator for peptide preparations."""
import flet as ft


class CalculatorView(ft.Container):
    """Peptide dose calculator: mcg ↔ ml conversions."""
    
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.expand = True
        self.padding = 20
        self._is_initializing = True
        
        # Build initial content
        self.content = self._build_content()
        self._is_initializing = False
    
    def _build_content(self):
        """Build calculator view."""
        # Get active preparations
        preparations = self.app.manager.get_preparations(only_active=True)
        
        # Initialize persistent state if not exists
        if not hasattr(self.app, 'calculator_state'):
            self.app.calculator_state = {
                'mode': 'active' if preparations else 'simulate',
                'simulate_mg': '',
                'simulate_vials': '1',
                'simulate_water': '',
                'prep_id': None,
            }
        
        # Store current concentration
        self.current_concentration = {"mcg_ml": 0}
        
        # Mode selector
        self.mode_radio = ft.RadioGroup(
            content=ft.Row([
                ft.Radio(value="active", label="Usa Preparazione Attiva"),
                ft.Radio(value="simulate", label="Simula Preparazione"),
            ]),
            value=self.app.calculator_state['mode'],
            on_change=self._on_mode_changed,
        )
        
        # Preparation selector (restore selected prep if exists)
        saved_prep_id = self.app.calculator_state.get('prep_id')
        self.prep_dropdown = ft.Dropdown(
            label="Seleziona Preparazione",
            hint_text="Scegli una preparazione...",
            options=[
                ft.dropdown.Option(
                    str(p['id']),
                    f"#{p['id']} - {p['batch_product']} ({p['volume_remaining_ml']:.1f}ml rimasti)"
                )
                for p in preparations
            ],
            value=str(saved_prep_id) if saved_prep_id and any(p['id'] == saved_prep_id for p in preparations) else None,
            width=600,
            on_change=self._on_prep_changed,
            visible=len(preparations) > 0,
        )
        
        # Simulation fields (restore saved values)
        self.simulate_mg_input = ft.TextField(
            label="mg per fiala",
            hint_text="es: 5",
            width=150,
            keyboard_type=ft.KeyboardType.NUMBER,
            value=self.app.calculator_state['simulate_mg'],
            on_change=self._update_simulation,
            visible=False,
        )
        
        self.simulate_vials_input = ft.TextField(
            label="Numero fiale",
            hint_text="es: 1",
            width=150,
            keyboard_type=ft.KeyboardType.NUMBER,
            value=self.app.calculator_state['simulate_vials'],
            on_change=self._update_simulation,
            visible=False,
        )
        
        self.simulate_water_input = ft.TextField(
            label="ml acqua batteriost.",
            hint_text="es: 2",
            width=150,
            keyboard_type=ft.KeyboardType.NUMBER,
            value=self.app.calculator_state['simulate_water'],
            on_change=self._update_simulation,
            visible=False,
        )
        
        self.simulate_container = ft.Container(
            content=ft.Column([
                ft.Text("Parametri Simulazione", size=14, weight=ft.FontWeight.BOLD),
                ft.Row([
                    self.simulate_mg_input,
                    ft.Text("×", size=20),
                    self.simulate_vials_input,
                    ft.Text("fiale +", size=14),
                    self.simulate_water_input,
                ]),
            ], spacing=10),
            visible=False,
        )
        
        # Info container (hidden initially)
        self.info_container = ft.Container(
            visible=False,
            content=ft.Column([
                ft.Text("", size=16, weight=ft.FontWeight.BOLD),
                ft.Text("", size=14, color=ft.Colors.BLUE_300),
            ], spacing=5),
            bgcolor=ft.Colors.GREY_900,
            padding=15,
            border_radius=10,
        )
        
        # Calculator: mcg → ml
        self.mcg_input = ft.TextField(
            label="Dose Desiderata (mcg)",
            hint_text="es: 250",
            width=200,
            keyboard_type=ft.KeyboardType.NUMBER,
            on_change=self._calculate_ml,
        )
        
        self.ml_result = ft.Text("", size=16, weight=ft.FontWeight.BOLD)
        
        # Calculator: ml → mcg
        self.ml_input = ft.TextField(
            label="Volume da Somministrare (ml)",
            hint_text="es: 0.25",
            width=200,
            keyboard_type=ft.KeyboardType.NUMBER,
            on_change=self._calculate_mcg,
        )
        
        self.mcg_result = ft.Text("", size=16, weight=ft.FontWeight.BOLD)
        
        # Conversion table (hidden initially)
        self.conversions_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Dose (mcg)", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Volume (ml)", weight=ft.FontWeight.BOLD)),
            ],
            rows=[],
        )
        
        self.conversions_container = ft.Container(
            visible=False,
            content=self.conversions_table,
            border=ft.border.all(1, ft.Colors.GREY_800),
            border_radius=10,
            padding=10,
        )
        
        # Reset button
        reset_button = ft.ElevatedButton(
            text="Reset Configurazione",
            icon=ft.Icons.REFRESH,
            on_click=self._reset_calculator,
            bgcolor=ft.Colors.ORANGE_700,
            color=ft.Colors.WHITE,
        )
        
        # Restore state after building UI
        # Trigger appropriate update based on saved mode
        if self.app.calculator_state['mode'] == 'simulate':
            self.simulate_container.visible = True
            self.simulate_mg_input.visible = True
            self.simulate_vials_input.visible = True
            self.simulate_water_input.visible = True
            self.prep_dropdown.visible = False
            # Trigger simulation update if values exist
            if self.simulate_mg_input.value and self.simulate_water_input.value:
                self._update_simulation(None)
        elif self.prep_dropdown.value:
            # Trigger prep update if value exists
            self._on_prep_changed(None)
        
        # Build layout
        return ft.Column([
            ft.Row([
                ft.Text("Calcolatore Dosi", size=32, weight=ft.FontWeight.BOLD),
                ft.Container(expand=True),
                reset_button,
            ]),
            ft.Divider(),
            
            # Mode selector
            ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("Modalità", size=18, weight=ft.FontWeight.BOLD),
                        self.mode_radio,
                    ], spacing=10),
                    padding=20,
                ),
            ),
            
            ft.Container(height=10),
            
            # Preparation selector or simulation
            ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("1. Configurazione", size=18, weight=ft.FontWeight.BOLD),
                        self.prep_dropdown,
                        self.simulate_container,
                        self.info_container,
                    ], spacing=15),
                    padding=20,
                ),
            ),
            
            ft.Container(height=20),
            
            # Calculators
            ft.Row([
                # mcg → ml
                ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.Text("2a. Calcola Volume (mcg → ml)", size=16, weight=ft.FontWeight.BOLD),
                            ft.Text("Inserisci la dose in mcg per ottenere il volume", size=12, color=ft.Colors.GREY_400),
                            ft.Divider(),
                            self.mcg_input,
                            self.ml_result,
                        ], spacing=10),
                        padding=20,
                        width=350,
                    ),
                ),
                
                # ml → mcg
                ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.Text("2b. Calcola Dose (ml → mcg)", size=16, weight=ft.FontWeight.BOLD),
                            ft.Text("Inserisci il volume per ottenere la dose", size=12, color=ft.Colors.GREY_400),
                            ft.Divider(),
                            self.ml_input,
                            self.mcg_result,
                        ], spacing=10),
                        padding=20,
                        width=350,
                    ),
                ),
            ], wrap=True),
            
            ft.Container(height=20),
            
            # Conversion table
            ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("3. Conversioni Comuni", size=18, weight=ft.FontWeight.BOLD),
                        ft.Text("Tabella di riferimento rapido", size=12, color=ft.Colors.GREY_400),
                        ft.Divider(),
                        self.conversions_container,
                    ], spacing=10),
                    padding=20,
                ),
            ),
            
        ], scroll=ft.ScrollMode.AUTO, spacing=10)
    
    def _on_mode_changed(self, e):
        """Handle mode change."""
        is_active_mode = self.mode_radio.value == "active"
        
        # Save mode to persistent state
        self.app.calculator_state['mode'] = self.mode_radio.value
        
        # Show/hide appropriate controls
        preparations = self.app.manager.get_preparations(only_active=True)
        self.prep_dropdown.visible = is_active_mode and len(preparations) > 0
        self.simulate_container.visible = not is_active_mode
        self.simulate_mg_input.visible = not is_active_mode
        self.simulate_vials_input.visible = not is_active_mode
        self.simulate_water_input.visible = not is_active_mode
        
        # Reset state
        self.info_container.visible = False
        self.conversions_container.visible = False
        self.mcg_input.value = ""
        self.ml_input.value = ""
        self.ml_result.value = ""
        self.mcg_result.value = ""
        self.current_concentration["mcg_ml"] = 0
        
        if is_active_mode:
            self.prep_dropdown.value = None
        else:
            # Don't reset simulation values, keep saved ones
            pass
        
        if not self._is_initializing:
            self.update()
    
    def _update_simulation(self, e):
        """Update simulation parameters."""
        # Save simulation values to persistent state
        self.app.calculator_state['simulate_mg'] = self.simulate_mg_input.value
        self.app.calculator_state['simulate_vials'] = self.simulate_vials_input.value
        self.app.calculator_state['simulate_water'] = self.simulate_water_input.value
        
        if not self.simulate_mg_input.value or not self.simulate_water_input.value:
            self.info_container.visible = False
            self.conversions_container.visible = False
            self.current_concentration["mcg_ml"] = 0
            if not self._is_initializing:
                self.update()
            return
        
        try:
            mg_per_vial = float(self.simulate_mg_input.value)
            vials = float(self.simulate_vials_input.value) if self.simulate_vials_input.value else 1
            water_ml = float(self.simulate_water_input.value)
            
            # Calculate concentration
            concentration_mg_ml = (mg_per_vial * vials) / water_ml
            concentration_mcg_ml = concentration_mg_ml * 1000
            
            self.current_concentration["mcg_ml"] = concentration_mcg_ml
            
            # Update info
            self.info_container.content.controls[0].value = "🧪 Simulazione Preparazione"
            self.info_container.content.controls[1].value = (
                f"Configurazione: {mg_per_vial:.1f}mg × {vials:.0f} fiala/e + {water_ml:.1f}ml acqua\n"
                f"Concentrazione: {concentration_mg_ml:.3f} mg/ml ({concentration_mcg_ml:.1f} mcg/ml)"
            )
            self.info_container.visible = True
            
            # Generate conversion table
            common_doses = [100, 250, 500, 750, 1000, 1500, 2000, 2500, 5000]
            self.conversions_table.rows.clear()
            
            for dose_mcg in common_doses:
                dose_ml = dose_mcg / concentration_mcg_ml
                self.conversions_table.rows.append(
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text(f"{dose_mcg} mcg")),
                        ft.DataCell(ft.Text(f"{dose_ml:.2f} ml", weight=ft.FontWeight.BOLD)),
                    ])
                )
            
            self.conversions_container.visible = True
            
            # Recalculate results if inputs exist
            if self.mcg_input.value:
                self._calculate_ml(None)
            if self.ml_input.value:
                self._calculate_mcg(None)
            
        except ValueError:
            self.info_container.visible = False
            self.conversions_container.visible = False
            self.current_concentration["mcg_ml"] = 0
        except Exception as ex:
            self.info_container.visible = False
            self.conversions_container.visible = False
            self.current_concentration["mcg_ml"] = 0
            if not self._is_initializing:
                self.app.show_snackbar(f"Errore simulazione: {ex}", error=True)
        
        if not self._is_initializing:
            self.update()
    
    def _on_prep_changed(self, e):
        """Handle preparation selection change."""
        if not self.prep_dropdown.value:
            self.info_container.visible = False
            self.conversions_container.visible = False
            self.mcg_input.value = ""
            self.ml_input.value = ""
            self.ml_result.value = ""
            self.mcg_result.value = ""
            self.current_concentration["mcg_ml"] = 0
            self.app.calculator_state['prep_id'] = None
            if not self._is_initializing:
                self.update()
            return
        
        try:
            prep_id = int(self.prep_dropdown.value)
            # Save to persistent state
            self.app.calculator_state['prep_id'] = prep_id
            
            prep = self.app.manager.get_preparation_details(prep_id)
            
            if not prep:
                return
            
            # Calculate concentration
            concentration_mg_ml = prep['concentration_mg_ml']
            concentration_mcg_ml = concentration_mg_ml * 1000
            
            self.current_concentration["mcg_ml"] = concentration_mcg_ml
            
            # Update info
            self.info_container.content.controls[0].value = f"📦 {prep['product_name']}"
            self.info_container.content.controls[1].value = (
                f"Concentrazione: {concentration_mg_ml:.3f} mg/ml ({concentration_mcg_ml:.1f} mcg/ml)"
            )
            self.info_container.visible = True
            
            # Generate conversion table
            common_doses = [100, 250, 500, 750, 1000, 1500, 2000, 2500, 5000]
            self.conversions_table.rows.clear()
            
            for dose_mcg in common_doses:
                dose_ml = dose_mcg / concentration_mcg_ml
                self.conversions_table.rows.append(
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text(f"{dose_mcg} mcg")),
                        ft.DataCell(ft.Text(f"{dose_ml:.2f} ml", weight=ft.FontWeight.BOLD)),
                    ])
                )
            
            self.conversions_container.visible = True
            
            # Clear previous calculations
            self.mcg_input.value = ""
            self.ml_input.value = ""
            self.ml_result.value = ""
            self.mcg_result.value = ""
            
            if not self._is_initializing:
                self.update()
            
        except Exception as ex:
            if not self._is_initializing:
                self.app.show_snackbar(f"Errore: {ex}", error=True)
    
    def _calculate_ml(self, e):
        """Calculate ml from mcg."""
        if not self.mcg_input.value:
            self.ml_result.value = ""
            if not self._is_initializing:
                self.update()
            return
        
        try:
            concentration_mcg_ml = self.current_concentration.get("mcg_ml", 0)
            if concentration_mcg_ml <= 0:
                self.ml_result.value = "⚠️ Seleziona una preparazione o imposta parametri simulazione"
                self.ml_result.color = ft.Colors.ORANGE_400
                if not self._is_initializing:
                    self.update()
                return
            
            mcg = float(self.mcg_input.value)
            ml = mcg / concentration_mcg_ml
            
            self.ml_result.value = f"💉 Volume necessario: {ml:.2f} ml"
            self.ml_result.color = ft.Colors.GREEN_400
            
            # Check if dose exceeds remaining volume (only for active preparations)
            if self.mode_radio.value == "active" and self.prep_dropdown.value:
                prep_id = int(self.prep_dropdown.value)
                prep = self.app.manager.get_preparation_details(prep_id)
                if ml > prep['volume_remaining_ml']:
                    self.ml_result.value += f"\n⚠️ Volume insufficiente! (solo {prep['volume_remaining_ml']:.2f}ml disponibili)"
                    self.ml_result.color = ft.Colors.ORANGE_400
            
        except ValueError:
            self.ml_result.value = "❌ Inserisci un numero valido"
            self.ml_result.color = ft.Colors.RED_400
        except Exception as ex:
            self.ml_result.value = f"❌ Errore: {ex}"
            self.ml_result.color = ft.Colors.RED_400
        
        if not self._is_initializing:
            self.update()
    
    def _calculate_mcg(self, e):
        """Calculate mcg from ml."""
        if not self.ml_input.value:
            self.mcg_result.value = ""
            if not self._is_initializing:
                self.update()
            return
        
        try:
            concentration_mcg_ml = self.current_concentration.get("mcg_ml", 0)
            if concentration_mcg_ml <= 0:
                self.mcg_result.value = "⚠️ Seleziona una preparazione o imposta parametri simulazione"
                self.mcg_result.color = ft.Colors.ORANGE_400
                if not self._is_initializing:
                    self.update()
                return
            
            ml = float(self.ml_input.value)
            mcg = ml * concentration_mcg_ml
            
            self.mcg_result.value = f"💊 Dose risultante: {mcg:.0f} mcg"
            self.mcg_result.color = ft.Colors.BLUE_400
            
            # Check if volume exceeds remaining (only for active preparations)
            if self.mode_radio.value == "active" and self.prep_dropdown.value:
                prep_id = int(self.prep_dropdown.value)
                prep = self.app.manager.get_preparation_details(prep_id)
                if ml > prep['volume_remaining_ml']:
                    self.mcg_result.value += f"\n⚠️ Volume insufficiente! (solo {prep['volume_remaining_ml']:.2f}ml disponibili)"
                    self.mcg_result.color = ft.Colors.ORANGE_400
            
        except ValueError:
            self.mcg_result.value = "❌ Inserisci un numero valido"
            self.mcg_result.color = ft.Colors.RED_400
        except Exception as ex:
            self.mcg_result.value = f"❌ Errore: {ex}"
            self.mcg_result.color = ft.Colors.RED_400
        
        if not self._is_initializing:
            self.update()
    
    def _reset_calculator(self, e):
        """Reset all calculator state."""
        # Reset persistent state
        preparations = self.app.manager.get_preparations(only_active=True)
        self.app.calculator_state = {
            'mode': 'active' if preparations else 'simulate',
            'simulate_mg': '',
            'simulate_vials': '1',
            'simulate_water': '',
            'prep_id': None,
        }
        
        # Rebuild the view
        self.content = self._build_content()
        self.update()
        
        # Show confirmation
        self.app.show_snackbar("✅ Calcolatore resettato", error=False)
