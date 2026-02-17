# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Peptide Management System — a Python desktop application for managing peptide inventory, protocols, administrations, and supplier quality analysis. Built with a Flet GUI, SQLite database, and an optional CLI/TUI interface.

## Commands

```bash
# Run the GUI application
python gui_modular/app.py

# Run all tests
python -m pytest tests/ -v

# Run a single test file
python -m pytest tests/test_adapter.py -v

# Run a specific test
python -m pytest tests/test_gui_dialogs.py::test_add_preparation_dialog_has_alertdialog -v

# Smoke test the GUI (non-interactive validation)
python scripts/smoke_test_gui.py

# Format code
black .

# Lint
flake8 .

# Install pre-commit hooks
python scripts/install_hooks.py
```

## Architecture

The system is in a **transitional state** from monolithic to modular repository-based architecture:

```
Presentation (Flet GUI, CLI)
        ↓
Adapter (PeptideManager in peptide_manager/__init__.py)
        ↓
    ┌───────────────┬──────────────┐
    │ Repositories   │ Legacy code  │
    │ (models/*.py)  │ (fallback)   │
    └───────┬───────┴──────────────┘
            ↓
    SQLite (data/development/ or data/production/)
```

**Key architectural components:**

- **`peptide_manager/__init__.py`** — The `PeptideManager` adapter class (~3500 lines). This is the central hub that routes all data operations. It delegates to repository classes for migrated entities and falls back to legacy code for others. All GUI and CLI code talks to this class.
- **`peptide_manager/database.py`** — `DatabaseManager` initializes the SQLite connection (with `PRAGMA foreign_keys = ON`) and instantiates all repository objects.
- **`peptide_manager/models/`** — Repository classes following the Repository Pattern. Each entity (supplier, peptide, batch, preparation, protocol, administration, certificate, etc.) has its own file with a repository class containing CRUD + domain logic.
- **`gui_modular/app.py`** — Flet GUI entry point. Uses `ThreadSafePeptideManager` wrapper because SQLite connections are not thread-safe.
- **`gui_modular/views/`** — Individual page views (dashboard, suppliers, peptides, batches, etc.). Each view is a self-contained module.
- **`gui_modular/components/`** — Reusable UI components (dialogs, forms, cards, data tables).
- **`peptide_manager/janoshik/`** — Supplier quality ranking subsystem that scrapes Janoshik certificates and scores suppliers using LLM providers (OpenAI, Anthropic, Google).
- **`peptide_manager/calculator.py`** — Dilution/reconstitution calculator with automatic concentration computations.

## Critical Rules

### Dialog Integrity (from past incident)
All `show_*_dialog()` functions in the GUI **must** follow this complete pattern:
```python
dialog = ft.AlertDialog(title=..., content=..., actions=...)
self.page.overlay.append(dialog)
dialog.open = True
self.page.update()
```
Missing any of these lines breaks the dialog silently. The test file `tests/test_gui_dialogs.py` validates this pattern. Always run it after GUI changes.

### Floating Point
Always use explicit rounding for volumes and monetary values:
```python
volume = round(calculated_volume, 2)
```

### Multi-Prep Distribution
Uses FIFO ordering by `preparation_date` (not expiry_date). Check `volume_remaining_ml > 0.01` and account for `wastage_ml`.

### Atomic Commits
One problem = one commit. Never mix bug fixes with refactoring. If a commit touches >100 lines, consider splitting.

### Before Committing
```bash
python -m pytest tests/ -v                # Always
python scripts/smoke_test_gui.py          # If GUI was modified
```

### Pre-Commit Hooks
The project has pre-commit hooks (install via `python scripts/install_hooks.py`) that validate:
- Python syntax
- Dialog completeness in GUI code
- Commit size warnings (>200 lines)

## Database

SQLite with manual SQL migrations in `migrations/`. Schema is initialized in `database.py`. Key pragmas: `foreign_keys = ON`, row factory set to `sqlite3.Row`.

- Dev DB: `data/development/peptide_management.db`
- Prod DB: `data/production/peptide_management.db`

When modifying schema: create a migration script in `migrations/`, test on the dev database first, and provide rollback SQL.

## Testing

pytest with config in `pytest.ini`. Tests live in `tests/` with model-specific tests in `tests/test_models/`. Key test files:
- `test_gui_dialogs.py` — Safety-critical dialog integrity checks
- `test_adapter.py` — PeptideManager adapter behavior
- `test_calculator.py` — Dilution calculator math
- `test_database.py` — Schema initialization

## Environment

Python 3.8+. Dependencies in `requirements.txt`. Key frameworks: Flet (GUI), Click (CLI), Rich (terminal formatting), pandas/matplotlib (data), LLM clients (openai, anthropic, google-generativeai) for Janoshik analysis. Virtual environment expected at `venv/`.
