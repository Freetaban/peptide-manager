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
from peptide_manager.database import init_database
from peptide_manager.paths import (
    is_frozen, get_data_dir, ensure_data_dirs, ensure_db_parent,
)


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
    
    def __init__(
        self,
        db_path: str,
        environment: str = 'development',
        backup_dir: Optional[str] = None,
        export_dir: Optional[str] = None,
        first_run: bool = False,
    ):
        self.db_path = db_path
        self.environment = environment
        self.backup_dir = backup_dir
        self.export_dir = export_dir
        self.first_run = first_run
        self.thread_safe_manager = ThreadSafePeptideManager(db_path)
        self._backup_done = False
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
        env_suffix = f" [{self.environment.upper()}]" if self.environment not in ('production', 'unknown') else ""
        page.title = f"Peptide Management System{env_suffix}"
        page.theme_mode = ft.ThemeMode.DARK
        page.window_width = 1600
        page.window_height = 1000
        page.window_resizable = True

        # Auto-backup on window close
        page.on_window_event = lambda e: self._on_window_close() if e.data == "close" else None

        # Load views dynamically
        self._load_views()

        # Build UI
        self._build_ui()

        # Load initial view
        self.update_content()

        # First-run prompt (frozen installs with a fresh DB)
        if self.first_run:
            self._show_first_run_dialog()
    
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
            self.views = {
                'dashboard': lambda app: ft.Container(
                    content=ft.Text(f"Error loading views: {e}", size=20),
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
            view_class = self.views[self.current_view]
            print(f"[view] loading {self.current_view}...")
            view_instance = view_class(self)
            self.content_area.content = view_instance
            self.page.update()
            print(f"[view] {self.current_view} loaded ok")

        except Exception as e:
            print(f"[view] {self.current_view} FAILED: {e}")
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

    def close_dialog(self, dialog=None):
        """Chiude dialog corrente usando page.overlay."""
        if dialog:
            dialog.open = False
            if dialog in self.page.overlay:
                self.page.overlay.remove(dialog)
        elif self.page.overlay:
            for item in reversed(self.page.overlay):
                if isinstance(item, ft.AlertDialog):
                    item.open = False
                    self.page.overlay.remove(item)
                    break
        self.page.update()

    def _show_first_run_dialog(self):
        """Show welcome dialog on first launch (fresh DB, frozen mode)."""
        def _dismiss(e):
            self.close_dialog(dialog)

        def _import_picker(e):
            self.close_dialog(dialog)
            self._import_database_picker()

        dialog = ft.AlertDialog(
            title=ft.Text("Welcome to Peptide Manager"),
            content=ft.Text(
                "No existing database was found.\n\n"
                "You can start fresh or import an existing database file."
            ),
            actions=[
                ft.TextButton("Start Fresh", on_click=_dismiss),
                ft.TextButton("Import Existing Database", on_click=_import_picker),
            ],
        )
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()

    def _import_database_picker(self):
        """Open a file picker to import an existing .db file."""
        import shutil

        def _on_result(e: ft.FilePickerResultEvent):
            if not e.files:
                return
            src = e.files[0].path
            print(f"[import] selected: {src}")

            # Close existing DB connections before overwriting the file
            try:
                self.thread_safe_manager.manager.conn.close()
                print("[import] closed existing connection")
            except Exception as ex:
                print(f"[import] close connection skipped: {ex}")

            try:
                shutil.copy2(src, self.db_path)
                print(f"[import] copied to {self.db_path}")
                # Flet doesn't re-render properly after a FilePicker callback,
                # so we ask the user to restart instead of trying to reload in-place.
                self._show_restart_dialog()
            except Exception as exc:
                print(f"[import] FAILED: {exc}")
                import traceback
                traceback.print_exc()
                self.show_snackbar(f"Import failed: {exc}", error=True)

        picker = ft.FilePicker(on_result=_on_result)
        self.page.overlay.append(picker)
        self.page.update()
        picker.pick_files(
            dialog_title="Select database file",
            allowed_extensions=["db"],
        )

    def _show_restart_dialog(self):
        """Show a dialog telling the user to restart after DB import."""
        def _close_app(e):
            self.page.window_close()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Import completato"),
            content=ft.Text(
                "Database importato con successo.\n\n"
                "Riavvia l'applicazione per caricare i dati."
            ),
            actions=[
                ft.TextButton("Chiudi", on_click=_close_app),
            ],
        )
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()

    def _on_window_close(self):
        """Auto-backup database on window close."""
        self.backup_on_exit()

    def backup_on_exit(self):
        """Create a database backup. Safe to call multiple times (idempotent via flag)."""
        if self._backup_done:
            return
        self._backup_done = True

        try:
            from peptide_manager.backup import DatabaseBackupManager

            if self.backup_dir:
                backup_dir = self.backup_dir
            elif self.environment == 'production':
                backup_dir = "data/backups/production"
            else:
                backup_dir = f"data/backups/{self.environment}"

            backup_mgr = DatabaseBackupManager(self.db_path, backup_dir=backup_dir)
            backup_path = backup_mgr.create_backup(label=f"auto_exit_{self.environment}")
            print(f"Backup saved: {backup_path}")

            stats = backup_mgr.cleanup_old_backups(dry_run=False)
            if stats["deleted"] > 0:
                print(f"Cleanup: {stats['deleted']} backup eliminati")
        except Exception as e:
            print(f"Backup failed: {e}")


def _setup_frozen_logging(data_dir: Path):
    """Redirect stdout/stderr to a log file in frozen mode (no console)."""
    log_file = data_dir / "app.log"
    # Rotate: keep previous log as app.log.1
    if log_file.exists():
        prev = data_dir / "app.log.1"
        try:
            if prev.exists():
                prev.unlink()
            log_file.rename(prev)
        except OSError:
            pass
    try:
        fh = open(log_file, "w", encoding="utf-8", buffering=1)  # line-buffered
        sys.stdout = fh
        sys.stderr = fh
    except OSError:
        pass  # if we can't open the log, proceed without logging


def main():
    """Main entry point"""
    import argparse
    import sys

    backup_dir = None
    export_dir = None
    first_run = False

    if is_frozen():
        # --- Frozen (PyInstaller) mode ---
        data_dir = get_data_dir()
        dirs = ensure_data_dirs(data_dir)
        _setup_frozen_logging(data_dir)
        db_path = str(data_dir / "peptide_management.db")
        backup_dir = str(dirs["backups"])
        export_dir = str(dirs["exports"])
        environment = "production"
        first_run = not Path(db_path).exists()
        print(f"Running as installed application")
        print(f"Data directory: {data_dir}")
    else:
        # --- Source mode (unchanged) ---
        parser = argparse.ArgumentParser(description='Peptide Management System GUI')
        parser.add_argument('--env', choices=['development', 'production'],
                           default='development',
                           help='Environment (default: development)')
        args = parser.parse_args()

        try:
            from scripts.environment import get_environment
            env = get_environment(args.env)
            db_path = str(env.db_path)
            backup_dir = str(env.backup_dir)
            environment = env.name
        except ImportError:
            print("Environment module not found, using defaults")
            db_path = 'peptide_management.db'
            environment = args.env

        ensure_db_parent(db_path)

    # Ensure schema + migrations are applied (idempotent)
    conn = init_database(db_path)
    conn.close()

    print(f"Environment: {environment}")
    print(f"Database: {db_path}")

    # Create and run app
    app = PeptideApp(
        db_path,
        environment,
        backup_dir=backup_dir,
        export_dir=export_dir,
        first_run=first_run,
    )
    import atexit
    atexit.register(app.backup_on_exit)

    ft.app(target=app.initialize)


if __name__ == "__main__":
    main()
