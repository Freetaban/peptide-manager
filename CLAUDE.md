# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

#CLAUDE.md — 12-rule template

These rules apply to every task in this project unless explicitly overridden.
Bias: caution over speed on non-trivial work. Use judgment on trivial tasks.


## Rule 1 — Think Before Coding

State assumptions explicitly. If uncertain, ask rather than guess.
Present multiple interpretations when ambiguity exists.
Push back when a simpler approach exists.
Stop when confused. Name what's unclear.

## Rule 2 — Simplicity First

Minimum code that solves the problem. Nothing speculative.
No features beyond what was asked. No abstractions for single-use code.
Test: would a senior engineer say this is overcomplicated? If yes, simplify.


## Rule 3 — Surgical Changes

Touch only what you must. Clean up only your own mess.
Don't "improve" adjacent code, comments, or formatting.
Don't refactor what isn't broken. Match existing style.


## Rule 4 — Goal-Driven Execution

Define success criteria. Loop until verified.
Don't follow steps. Define success and iterate.
Strong success criteria let you loop independently.


## Rule 5 — Use the model only for judgment calls

Use me for: classification, drafting, summarization, extraction.
Do NOT use me for: routing, retries, deterministic transforms.
If code can answer, code answers.


## Rule 6 — Token budgets are not advisory

Per-task: 4,000 tokens. Per-session: 30,000 tokens.
If approaching budget, summarize and start fresh.
Surface the breach. Do not silently overrun.


## Rule 7 — Surface conflicts, don't average them

If two patterns contradict, pick one (more recent / more tested).
Explain why. Flag the other for cleanup.
Don't blend conflicting patterns.

## Rule 8 — Read before you write

Before adding code, read exports, immediate callers, shared utilities.
"Looks orthogonal" is dangerous. If unsure why code is structured a way, ask.

## Rule 9 — Tests verify intent, not just behavior

Tests must encode WHY behavior matters, not just WHAT it does.
A test that can't fail when business logic changes is wrong.

## Rule 10 — Checkpoint after every significant step

Summarize what was done, what's verified, what's left.
Don't continue from a state you can't describe back.
If you lose track, stop and restate.

## Rule 11 — Match the codebase's conventions, even if you disagree

Conformance > taste inside the codebase.
If you genuinely think a convention is harmful, surface it. Don't fork silently.

## Rule 12 — Fail loud

"Completed" is wrong if anything was skipped silently.
"Tests pass" is wrong if any were skipped.
Default to surfacing uncertainty, not hiding it.

## Project Overview

Peptide Management System — a Python desktop application for managing peptide inventory, protocols, administrations, and supplier quality analysis. Built with a PySide6 (Qt) GUI, SQLite database, and an optional CLI/TUI interface.

## Commands

```bash
# Run the GUI application
python gui.py
# or directly:
python gui_qt/app.py

# Run all tests
python -m pytest tests/ -v

# Run a single test file
python -m pytest tests/test_adapter.py -v

# Smoke test the GUI (non-interactive import + backend validation)
python scripts/smoke_test_gui.py

# Build standalone Windows exe
python scripts/build.py

# Format code
black .

# Lint
flake8 .

# Install pre-commit hooks
python scripts/install_hooks.py
```

## Architecture

```
Presentation (PySide6 Qt GUI, CLI)
        ↓
Adapter (PeptideManager in peptide_manager/__init__.py)
        ↓
    Repositories (peptide_manager/models/*.py)
        ↓
    SQLite (data/development/ or data/production/)
```

**Key architectural components:**

- **`gui.py`** — Root entry point. Thin wrapper that delegates to `gui_qt/app.py`.
- **`gui_qt/app.py`** — Qt main window (`PeptideQtApp`). Task-oriented layout: 5 sections (Oggi, Inventario, Trattamento, Storico, Archivio) in a sidebar + stacked widget. Single-threaded — uses `PeptideManager` directly (no thread-safe wrapper needed).
- **`gui_qt/views/`** — One module per section. `today.py`, `inventory.py`, `treatment*.py` (5 sub-modules), `history.py`, `archive.py`, `purchase_history.py`.
- **`gui_qt/components/`** — Reusable Qt components: `DataTable`, `dialogs`, `forms`.
- **`gui_qt/style.qss`** — Application stylesheet.
- **`peptide_manager/__init__.py`** — The `PeptideManager` adapter class. Central hub for all data operations. All GUI and CLI code talks to this class.
- **`peptide_manager/database.py`** — Initializes the SQLite connection (`PRAGMA foreign_keys = ON`) and instantiates repository objects.
- **`peptide_manager/models/`** — Repository classes (one per entity: supplier, peptide, batch, preparation, protocol, administration, certificate, etc.) with CRUD + domain logic.
- **`peptide_manager/janoshik/`** — Supplier quality ranking subsystem (Janoshik certificate scraping + LLM scoring via OpenAI, Anthropic, Google).
- **`peptide_manager/calculator.py`** — Dilution/reconstitution calculator.
- **`gui_modular/`** — Legacy Flet GUI. Retained for reference only; not used.

## Critical Rules

### Dialog Pattern (Qt)

Qt dialogs use the standard pattern — no overlay dance:

```python
dlg = QDialog(parent)
# ... build UI ...
if dlg.exec() == QDialog.Accepted:
    # handle result
```

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
- Commit size warnings (>200 lines)

## Database

SQLite with manual SQL migrations in `migrations/`. Schema is initialized in `database.py`. Key pragmas: `foreign_keys = ON`, row factory set to `sqlite3.Row`.

- Dev DB: `data/development/peptide_management.db`
- Prod DB: `data/production/peptide_management.db`

When modifying schema: create a migration script in `migrations/`, test on the dev database first, and provide rollback SQL.

## Testing

pytest with config in `pytest.ini`. Tests live in `tests/` with model-specific tests in `tests/test_models/`. Key test files:

- `test_gui_dialogs.py` — Qt GUI integrity checks (syntax, sections, entry point)
- `test_adapter.py` — PeptideManager adapter behavior
- `test_calculator.py` — Dilution calculator math
- `test_database.py` — Schema initialization

## Environment

Python 3.8+. Dependencies in `requirements.txt`. Key frameworks: PySide6 (Qt GUI), qtawesome (icons), Click (CLI), Rich (terminal formatting), pandas/matplotlib (data), LLM clients (openai, anthropic, google-generativeai) for Janoshik analysis. Virtual environment expected at `venv/`.
