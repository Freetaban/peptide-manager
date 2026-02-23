"""
PySide6 GUI entry point for Peptide Management System.

Task-oriented redesign: 5 sections instead of 11 entity-based views.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports when running directly
_current_dir = Path(__file__).parent
_project_root = _current_dir.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QStackedWidget,
    QTabWidget,
    QToolBar,
    QStatusBar,
    QCheckBox,
    QSizePolicy,
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon
import qtawesome as qta

from peptide_manager import PeptideManager
from peptide_manager.database import init_database
from peptide_manager.paths import (
    is_frozen,
    get_data_dir,
    ensure_data_dirs,
    ensure_db_parent,
)


# --- Section definitions ---

SECTIONS = [
    {
        "key": "today",
        "label": "Oggi",
        "icon": "mdi6.calendar-today",
        "tabs": [],  # single view, no tabs
    },
    {
        "key": "inventory",
        "label": "Inventario",
        "icon": "mdi6.package-variant-closed",
        "tabs": ["Lotti", "Preparazioni"],
    },
    {
        "key": "treatment",
        "label": "Trattamento",
        "icon": "mdi6.needle",
        "tabs": ["Cicli", "Protocolli", "Piani"],
    },
    {
        "key": "history",
        "label": "Storico",
        "icon": "mdi6.chart-line",
        "tabs": ["Somministrazioni", "Statistiche"],
    },
    {
        "key": "archive",
        "label": "Archivio",
        "icon": "mdi6.cog",
        "tabs": ["Peptidi", "Fornitori", "Janoshik", "Calcolatore"],
    },
]


class PeptideQtApp(QMainWindow):
    """Main application window — task-oriented layout."""

    def __init__(
        self,
        db_path,
        environment="development",
        backup_dir=None,
        export_dir=None,
        first_run=False,
    ):
        super().__init__()
        self.db_path = db_path
        self.environment = environment
        self.backup_dir = backup_dir
        self.export_dir = export_dir
        self.first_run = first_run
        self.edit_mode = False
        self._backup_done = False

        # Backend — direct PeptideManager (Qt is single-threaded)
        self._manager = PeptideManager(db_path)

        self._init_window()
        self._init_toolbar()
        self._init_central()
        self._init_statusbar()

        # Select first section
        self.sidebar.setCurrentRow(0)

    # --- public API --------------------------------------------------

    @property
    def manager(self):
        return self._manager

    def show_message(self, text, timeout=3000):
        """Show a transient message in the status bar."""
        self.statusBar().showMessage(text, timeout)

    def navigate_to(self, section_key):
        """Programmatically switch to a section by key."""
        for i, sec in enumerate(SECTIONS):
            if sec["key"] == section_key:
                self.sidebar.setCurrentRow(i)
                return

    # --- private init ------------------------------------------------

    def _init_window(self):
        env_suffix = (
            f" [{self.environment.upper()}]"
            if self.environment not in ("production", "unknown")
            else ""
        )
        self.setWindowTitle(f"Peptide Management System{env_suffix}")
        self.resize(1400, 900)

        # Load stylesheet
        qss_path = _current_dir / "style.qss"
        if qss_path.exists():
            self.setStyleSheet(qss_path.read_text(encoding="utf-8"))

    def _init_toolbar(self):
        toolbar = QToolBar()
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(20, 20))
        self.addToolBar(toolbar)

        # App title
        title = QLabel("  Peptide Management System")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        toolbar.addWidget(title)

        # Environment badge
        badge = QLabel(f"  {self.environment.upper()}  ")
        badge_id = f"env_badge_{self.environment}"
        badge.setObjectName(badge_id)
        toolbar.addWidget(badge)

        # Spacer
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        toolbar.addWidget(spacer)

        # Edit-mode checkbox
        self._edit_cb = QCheckBox("Edit Mode")
        self._edit_cb.setChecked(False)
        self._edit_cb.stateChanged.connect(self._on_edit_mode_changed)
        toolbar.addWidget(self._edit_cb)

    def _init_central(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Sidebar
        self.sidebar = QListWidget()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(180)
        self.sidebar.setIconSize(QSize(22, 22))
        for sec in SECTIONS:
            item = QListWidgetItem(
                qta.icon(sec["icon"], color="#aeaeae", color_active="#ffffff"),
                sec["label"],
            )
            item.setSizeHint(QSize(180, 48))
            self.sidebar.addItem(item)
        self.sidebar.currentRowChanged.connect(self._on_section_changed)
        layout.addWidget(self.sidebar)

        # Content stack
        self.stack = QStackedWidget()
        for sec in SECTIONS:
            widget = self._build_section_widget(sec)
            self.stack.addWidget(widget)
        layout.addWidget(self.stack)

    def _init_statusbar(self):
        sb = QStatusBar()
        self.setStatusBar(sb)

        # Permanent environment indicator
        env_label = QLabel(f" {self.environment.upper()} ")
        env_label.setObjectName(f"env_badge_{self.environment}")
        sb.addPermanentWidget(env_label)

    def _build_section_widget(self, section):
        """Build a QTabWidget (or single placeholder) for a section."""
        tabs = section.get("tabs", [])
        if not tabs:
            # Single-view section — use real view if available
            if section["key"] == "today":
                from gui_qt.views.today import TodayView

                return TodayView(self)
            container = QWidget()
            layout = QVBoxLayout(container)
            layout.setContentsMargins(20, 20, 20, 20)
            lbl = QLabel(f"{section['label']} — vista in arrivo")
            lbl.setObjectName("placeholder")
            lbl.setAlignment(Qt.AlignCenter)
            layout.addWidget(lbl)
            return container

        tab_widget = QTabWidget()
        for tab_name in tabs:
            page = QWidget()
            page_layout = QVBoxLayout(page)
            page_layout.setContentsMargins(20, 20, 20, 20)
            lbl = QLabel(f"{section['label']} > {tab_name} — vista in arrivo")
            lbl.setObjectName("placeholder")
            lbl.setAlignment(Qt.AlignCenter)
            page_layout.addWidget(lbl)
            tab_widget.addTab(page, tab_name)
        return tab_widget

    # --- slots -------------------------------------------------------

    def _on_section_changed(self, index):
        if 0 <= index < self.stack.count():
            self.stack.setCurrentIndex(index)
            self.show_message(f"Sezione: {SECTIONS[index]['label']}")

    def _on_edit_mode_changed(self, state):
        self.edit_mode = state == Qt.CheckState.Checked.value
        if self.edit_mode:
            self.show_message("Edit mode ATTIVA — attenzione!")
        else:
            self.show_message("Edit mode disattivata")

    # --- lifecycle ---------------------------------------------------

    def closeEvent(self, event):
        self.backup_on_exit()
        event.accept()

    def backup_on_exit(self):
        """Create a database backup. Safe to call multiple times."""
        if self._backup_done:
            return
        self._backup_done = True
        try:
            from peptide_manager.backup import DatabaseBackupManager

            if self.backup_dir:
                backup_dir = self.backup_dir
            elif self.environment == "production":
                backup_dir = "data/backups/production"
            else:
                backup_dir = f"data/backups/{self.environment}"

            backup_mgr = DatabaseBackupManager(self.db_path, backup_dir=backup_dir)
            backup_path = backup_mgr.create_backup(
                label=f"auto_exit_{self.environment}"
            )
            print(f"Backup saved: {backup_path}")

            stats = backup_mgr.cleanup_old_backups(dry_run=False)
            if stats["deleted"] > 0:
                print(f"Cleanup: {stats['deleted']} backup eliminati")
        except Exception as e:
            print(f"Backup failed: {e}")


# ---- Frozen-mode logging (same as gui_modular/app.py) ---------------


def _setup_frozen_logging(data_dir):
    log_file = data_dir / "app.log"
    if log_file.exists():
        prev = data_dir / "app.log.1"
        try:
            if prev.exists():
                prev.unlink()
            log_file.rename(prev)
        except OSError:
            pass
    try:
        fh = open(log_file, "w", encoding="utf-8", buffering=1)
        sys.stdout = fh
        sys.stderr = fh
    except OSError:
        pass


# ---- Entry point ----------------------------------------------------


def main():
    import argparse
    import atexit

    backup_dir = None
    export_dir = None
    first_run = False

    if is_frozen():
        data_dir = get_data_dir()
        dirs = ensure_data_dirs(data_dir)
        _setup_frozen_logging(data_dir)
        db_path = str(data_dir / "peptide_management.db")
        backup_dir = str(dirs["backups"])
        export_dir = str(dirs["exports"])
        environment = "production"
        first_run = not Path(db_path).exists()
        print("Running as installed application")
        print(f"Data directory: {data_dir}")
    else:
        parser = argparse.ArgumentParser(
            description="Peptide Management System — PySide6 GUI"
        )
        parser.add_argument(
            "--env",
            choices=["development", "production"],
            default="development",
            help="Environment (default: development)",
        )
        args = parser.parse_args()

        try:
            from scripts.environment import get_environment

            env = get_environment(args.env)
            db_path = str(env.db_path)
            backup_dir = str(env.backup_dir)
            environment = env.name
        except ImportError:
            print("Environment module not found, using defaults")
            db_path = "peptide_management.db"
            environment = args.env

        ensure_db_parent(db_path)

    # Ensure schema + migrations
    conn = init_database(db_path)
    conn.close()

    print(f"Environment: {environment}")
    print(f"Database: {db_path}")

    app = QApplication(sys.argv)
    window = PeptideQtApp(
        db_path,
        environment,
        backup_dir=backup_dir,
        export_dir=export_dir,
        first_run=first_run,
    )
    atexit.register(window.backup_on_exit)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
