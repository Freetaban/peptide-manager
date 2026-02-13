"""
GUI Flet per Peptide Management System
Thin wrapper — the real app lives in gui_modular/app.py
"""

from gui_modular.app import PeptideApp, main as _main

# Backward-compat aliases for scripts that import from gui.py
PeptideGUI = PeptideApp
HAS_JANOSHIK = True  # Always available in modular version


def start_gui(db_path=None, environment=None):
    """Legacy entry point — delegates to gui_modular.app."""
    import argparse
    from pathlib import Path
    import sys

    # Get environment from args if not provided
    if environment is None:
        parser = argparse.ArgumentParser(description='Peptide Management System')
        parser.add_argument('--env', choices=['production', 'development'], default=None)
        parser.add_argument('--db', type=str, default=None)
        args, _ = parser.parse_known_args()
        environment = args.env
        db_path = db_path or args.db

    # Resolve database path via environment module
    try:
        scripts_dir = Path(__file__).parent / 'scripts'
        if scripts_dir.exists():
            sys.path.insert(0, str(scripts_dir))
        from environment import get_environment
        env = get_environment(environment)
        db_path = db_path or str(env.db_path)
        env_name = env.name
    except ImportError:
        db_path = db_path or 'peptide_management.db'
        env_name = environment or 'development'

    import flet as ft
    app = PeptideApp(db_path, env_name)
    ft.app(target=app.initialize)


if __name__ == '__main__':
    start_gui()
