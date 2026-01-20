"""
Main Application Class
Handles navigation and app initialization with thread-safe database access
"""

import flet as ft
from typing import Optional, Dict, Type
import threading
import sys
from pathlib import Path

# Add parent directory to path for imports when running directly
_current_dir = Path(__file__).parent
_project_root = _current_dir.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from peptide_manager import PeptideManager


class ThreadSafePeptideManager:
    """Thread-safe wrapper for PeptideManager to fix SQLite threading issues"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._thread_local = threading.local()
    
    @property
    def manager(self) -> PeptideManager:
        """Get or create PeptideManager instance for current thread"""
        if not hasattr(self._thread_local, 'manager'):
            self._thread_local.manager = PeptideManager(self.db_path)
        return self._thread_local.manager


class PeptideApp:
    """Main application with modular architecture"""
    
    def __init__(self, db_path: str, environment: str = 'development'):
        self.db_path = db_path
        self.environment = environment
        self.thread_safe_manager = ThreadSafePeptideManager(db_path)
        self.page: Optional[ft.Page] = None
        self.current_view = 'dashboard'
        self.edit_mode = False
        
        # Navigation rail
        self.nav_bar: Optional[ft.NavigationBar] = None
        self.content_area: Optional[ft.Container] = None
        
        # View registry (will be populated after imports)
        self.views: Dict[str, Type] = {}
    
    @property
    def manager(self) -> PeptideManager:
        """Get thread-safe PeptideManager instance"""
        return self.thread_safe_manager.manager
    
    def initialize(self, page: ft.Page):
        """Initialize the application"""
        self.page = page
        
        # Configure page
        page.title = f"Peptide Management System ({self.environment})"
        page.theme_mode = ft.ThemeMode.DARK
        page.window_width = 1400
        page.window_height = 900
        page.window_resizable = True
        
        # Load views dynamically
        self._load_views()
        
        # Build UI
        self._build_ui()
        
        # Load initial view
        self.update_content()
    
    def _load_views(self):
        """Dynamically import and register views"""
        try:
            # Try relative imports first (when running as package)
            try:
                from gui_modular.views import (
                    DashboardView,
                    BatchesView,
                    PeptidesView,
                    SuppliersView,
                    PreparationsView,
                    ProtocolsView,
                    CyclesView,
                    AdministrationsView,
                    CalculatorView,
                    TreatmentPlannerView,
                    JanoshikView
                )
            except ImportError:
                # Fallback to direct imports (when running as script)
                from views import (
                    DashboardView,
                    BatchesView,
                    PeptidesView,
                    SuppliersView,
                    PreparationsView,
                    ProtocolsView,
                    CyclesView,
                    AdministrationsView,
                    CalculatorView,
                    TreatmentPlannerView,
                    JanoshikView
                )
            
            self.views = {
                'dashboard': DashboardView,
                'batches': BatchesView,
                'peptides': PeptidesView,
                'suppliers': SuppliersView,
                'preparations': PreparationsView,
                'protocols': ProtocolsView,
                'cycles': CyclesView,
                'administrations': AdministrationsView,
                'calculator': CalculatorView,
                'treatment_planner': TreatmentPlannerView,
                'janoshik': JanoshikView
            }
        except ImportError as e:
            print(f"⚠️  Warning: Could not load all views: {e}")
            import traceback
            traceback.print_exc()
            # Use placeholder views for development
            # Use placeholder views for development
            self.views = {
                'dashboard': lambda app: ft.Container(
                    content=ft.Text("Dashboard - To be implemented", size=20),
                    padding=20
                ),
                'batches': lambda app: ft.Container(
                    content=ft.Text("Batches - To be implemented", size=20),
                    padding=20
                ),
            }
    
    def _build_ui(self):
        """Build main UI structure"""
        # Header with edit mode toggle
        header = self._build_header()
        
        # Navigation bar (top)
        self.nav_bar = ft.NavigationBar(
            selected_index=0,
            destinations=[
                ft.NavigationBarDestination(
                    icon=ft.Icons.DASHBOARD_OUTLINED,
                    selected_icon=ft.Icons.DASHBOARD,
                    label="Dashboard"
                ),
                ft.NavigationBarDestination(
                    icon=ft.Icons.INVENTORY_2_OUTLINED,
                    selected_icon=ft.Icons.INVENTORY_2,
                    label="Lotti"
                ),
                ft.NavigationBarDestination(
                    icon=ft.Icons.SCIENCE_OUTLINED,
                    selected_icon=ft.Icons.SCIENCE,
                    label="Peptidi"
                ),
                ft.NavigationBarDestination(
                    icon=ft.Icons.BUSINESS_OUTLINED,
                    selected_icon=ft.Icons.BUSINESS,
                    label="Fornitori"
                ),
                ft.NavigationBarDestination(
                    icon=ft.Icons.MEDICATION_OUTLINED,
                    selected_icon=ft.Icons.MEDICATION,
                    label="Preparazioni"
                ),
                ft.NavigationBarDestination(
                    icon=ft.Icons.DESCRIPTION_OUTLINED,
                    selected_icon=ft.Icons.DESCRIPTION,
                    label="Protocolli"
                ),
                ft.NavigationBarDestination(
                    icon=ft.Icons.REPEAT,
                    selected_icon=ft.Icons.REPEAT_ON,
                    label="Cicli"
                ),
                ft.NavigationBarDestination(
                    icon=ft.Icons.HEALING_OUTLINED,
                    selected_icon=ft.Icons.HEALING,
                    label="Somministrazioni"
                ),
                ft.NavigationBarDestination(
                    icon=ft.Icons.CALCULATE_OUTLINED,
                    selected_icon=ft.Icons.CALCULATE,
                    label="Calcolatore"
                ),
                ft.NavigationBarDestination(
                    icon=ft.Icons.CALENDAR_MONTH_OUTLINED,
                    selected_icon=ft.Icons.CALENDAR_MONTH,
                    label="Piani"
                ),
                ft.NavigationBarDestination(
                    icon=ft.Icons.VERIFIED_OUTLINED,
                    selected_icon=ft.Icons.VERIFIED,
                    label="Janoshik"
                ),
            ],
            on_change=self._on_nav_change
        )
        
        # Content area
        self.content_area = ft.Container(
            content=ft.ProgressRing(),
            expand=True,
            padding=0
        )
        
        # Add to page
        self.page.add(
            ft.Column([
                header,
                ft.Divider(height=1),
                self.nav_bar,
                ft.Divider(height=1),
                self.content_area
            ], spacing=0, expand=True)
        )
    
    def _build_header(self) -> ft.Container:
        """Build header with environment indicator and edit mode toggle"""
        # Environment badge
        env_color = ft.Colors.GREEN_400 if self.environment == 'production' else ft.Colors.BLUE_400
        env_badge = ft.Container(
            content=ft.Text(
                self.environment.upper(),
                size=12,
                weight=ft.FontWeight.BOLD,
                color=ft.Colors.WHITE
            ),
            bgcolor=env_color,
            padding=ft.padding.symmetric(horizontal=10, vertical=5),
            border_radius=5
        )
        
        # Edit mode switch
        edit_switch = ft.Row([
            ft.Icon(
                ft.Icons.LOCK if not self.edit_mode else ft.Icons.LOCK_OPEN,
                color=ft.Colors.RED_400 if self.edit_mode else ft.Colors.GREEN_400,
                size=20
            ),
            ft.Switch(
                label="Edit Mode",
                value=self.edit_mode,
                on_change=self._toggle_edit_mode,
                active_color=ft.Colors.RED_400
            )
        ], spacing=5)
        
        return ft.Container(
            content=ft.Row([
                ft.Text(
                    "🧬 Peptide Management System",
                    size=22,
                    weight=ft.FontWeight.BOLD
                ),
                ft.Container(width=20),
                env_badge,
                ft.Container(expand=True),  # Spacer
                edit_switch
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            padding=15,
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST
        )
    
    def _on_nav_change(self, e):
        """Handle navigation changes"""
        self.nav_bar.selected_index = e.control.selected_index
        view_names = list(self.views.keys())
        if 0 <= e.control.selected_index < len(view_names):
            self.current_view = view_names[e.control.selected_index]
            self.update_content()
    
    def _toggle_edit_mode(self, e):
        """Toggle edit mode"""
        self.edit_mode = e.control.value
        
        # Show notification
        if self.edit_mode:
            self.show_snackbar("⚠️ EDIT MODE ACTIVE - Be careful!", error=True)
        else:
            self.show_snackbar("✅ Edit mode disabled", error=False)
        
        # Refresh current view
        self.update_content()
    
    def update_content(self):
        """Update content area with current view"""
        if self.current_view not in self.views:
            self.content_area.content = ft.Container(
                content=ft.Text(f"View '{self.current_view}' not found", size=20),
                padding=20
            )
            self.page.update()
            return
        
        try:
            # Get view class
            view_class = self.views[self.current_view]
            
            # Create view instance
            if callable(view_class):
                if view_class.__name__ in ['<lambda>', 'function']:
                    # Placeholder function
                    view_instance = view_class(self)
                else:
                    # Real view class
                    view_instance = view_class(self)
            else:
                view_instance = ft.Container(
                    content=ft.Text(f"Invalid view: {self.current_view}", size=20),
                    padding=20
                )
            
            self.content_area.content = view_instance
            self.page.update()
            
        except Exception as e:
            print(f"❌ Error loading view '{self.current_view}': {e}")
            import traceback
            traceback.print_exc()
            
            self.content_area.content = ft.Container(
                content=ft.Column([
                    ft.Text(f"Error loading view: {self.current_view}", size=20, color=ft.Colors.ERROR),
                    ft.Text(str(e), size=12, color=ft.Colors.ON_SURFACE_VARIANT)
                ]),
                padding=20
            )
            self.page.update()
    
    def show_snackbar(self, message: str, error: bool = False):
        """Show snackbar notification"""
        self.page.snack_bar = ft.SnackBar(
            content=ft.Text(message),
            bgcolor=ft.Colors.ERROR if error else ft.Colors.GREEN_400,
            duration=3000
        )
        self.page.snack_bar.open = True
        self.page.update()
    
    def refresh_current_view(self):
        """Refresh the current view"""
        self.update_content()


def main():
    """Main entry point"""
    import argparse
    import sys
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Peptide Management System GUI')
    parser.add_argument('--env', choices=['development', 'production'], 
                       default='development',
                       help='Environment (default: development)')
    args = parser.parse_args()
    
    # Get database path from environment
    try:
        from scripts.environment import get_environment
        env = get_environment(args.env)
        db_path = str(env.db_path)
        environment = env.name
        print(f"🌍 Environment: {environment}")
        print(f"📁 Database: {db_path}")
    except ImportError:
        print("⚠️  Environment module not found, using defaults")
        db_path = 'peptide_management.db'
        environment = args.env
    
    # Create and run app
    app = PeptideApp(db_path, environment)
    ft.app(target=app.initialize)


if __name__ == "__main__":
    main()
