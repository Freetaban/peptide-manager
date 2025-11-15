"""CalculatorView - Dose calculator for peptide preparations."""
import flet as ft


class CalculatorView(ft.Container):
    """Peptide dose calculator: mcg ↔ ml conversions."""
    
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.expand = True
        self.padding = 20
        
        # Build initial content
        self.content = self._build_content()
    
    def _build_content(self):
        """Build calculator view."""
        # Get active preparations
        preparations = self.app.manager.get_preparations(only_active=True)
        
        if not preparations:
            return ft.Column([
                ft.Text("Calcolatore Dosi", size=32, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.CALCULATE, size=64, color=ft.Colors.GREY_600),
                        ft.Text("Nessuna preparazione attiva", size=18, color=ft.Colors.GREY_400),
                        ft.Text("Crea una preparazione per usare il calcolatore", size=14, color=ft.Colors.GREY_600),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15),
                    alignment=ft.alignment.center,
                    padding=50,
                ),
            ])
        
        # Preparation selector
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
            width=600,
            on_change=self._on_prep_changed,
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
        
        # Build layout
        return ft.Column([
            ft.Text("Calcolatore Dosi", size=32, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            
            # Preparation selector
            ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("1. Seleziona Preparazione", size=18, weight=ft.FontWeight.BOLD),
                        self.prep_dropdown,
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
    
    def _on_prep_changed(self, e):
        """Handle preparation selection change."""
        if not self.prep_dropdown.value:
            self.info_container.visible = False
            self.conversions_container.visible = False
            self.mcg_input.value = ""
            self.ml_input.value = ""
            self.ml_result.value = ""
            self.mcg_result.value = ""
            self.update()
            return
        
        try:
            prep_id = int(self.prep_dropdown.value)
            prep = self.app.manager.get_preparation_details(prep_id)
            
            if not prep:
                return
            
            # Calculate concentration
            concentration_mg_ml = prep['concentration_mg_ml']
            concentration_mcg_ml = concentration_mg_ml * 1000
            
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
                        ft.DataCell(ft.Text(f"{dose_ml:.3f} ml", weight=ft.FontWeight.BOLD)),
                    ])
                )
            
            self.conversions_container.visible = True
            
            # Clear previous calculations
            self.mcg_input.value = ""
            self.ml_input.value = ""
            self.ml_result.value = ""
            self.mcg_result.value = ""
            
            self.update()
            
        except Exception as ex:
            self.app.show_snackbar(f"Errore: {ex}", error=True)
    
    def _calculate_ml(self, e):
        """Calculate ml from mcg."""
        if not self.prep_dropdown.value or not self.mcg_input.value:
            self.ml_result.value = ""
            self.update()
            return
        
        try:
            prep_id = int(self.prep_dropdown.value)
            prep = self.app.manager.get_preparation_details(prep_id)
            
            concentration_mcg_ml = prep['concentration_mg_ml'] * 1000
            mcg = float(self.mcg_input.value)
            ml = mcg / concentration_mcg_ml
            
            self.ml_result.value = f"💉 Volume necessario: {ml:.3f} ml"
            self.ml_result.color = ft.Colors.GREEN_400
            
            # Check if dose exceeds remaining volume
            if ml > prep['volume_remaining_ml']:
                self.ml_result.value += f"\n⚠️ Volume insufficiente! (solo {prep['volume_remaining_ml']:.1f}ml disponibili)"
                self.ml_result.color = ft.Colors.ORANGE_400
            
        except ValueError:
            self.ml_result.value = "❌ Inserisci un numero valido"
            self.ml_result.color = ft.Colors.RED_400
        except Exception as ex:
            self.ml_result.value = f"❌ Errore: {ex}"
            self.ml_result.color = ft.Colors.RED_400
        
        self.update()
    
    def _calculate_mcg(self, e):
        """Calculate mcg from ml."""
        if not self.prep_dropdown.value or not self.ml_input.value:
            self.mcg_result.value = ""
            self.update()
            return
        
        try:
            prep_id = int(self.prep_dropdown.value)
            prep = self.app.manager.get_preparation_details(prep_id)
            
            concentration_mcg_ml = prep['concentration_mg_ml'] * 1000
            ml = float(self.ml_input.value)
            mcg = ml * concentration_mcg_ml
            
            self.mcg_result.value = f"💊 Dose risultante: {mcg:.0f} mcg"
            self.mcg_result.color = ft.Colors.BLUE_400
            
            # Check if volume exceeds remaining
            if ml > prep['volume_remaining_ml']:
                self.mcg_result.value += f"\n⚠️ Volume insufficiente! (solo {prep['volume_remaining_ml']:.1f}ml disponibili)"
                self.mcg_result.color = ft.Colors.ORANGE_400
            
        except ValueError:
            self.mcg_result.value = "❌ Inserisci un numero valido"
            self.mcg_result.color = ft.Colors.RED_400
        except Exception as ex:
            self.mcg_result.value = f"❌ Errore: {ex}"
            self.mcg_result.color = ft.Colors.RED_400
        
        self.update()

