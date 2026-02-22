# Migration Plan: Flet to PySide6

## Why

Flet is young and unstable for desktop use. Known issues:
- FilePicker callback doesn't trigger UI re-render (grey screen bug)
- `console=False` swallows all errors silently
- Threading model is opaque — no control over event loop
- Dialog/overlay management is fragile (see CLAUDE.md dialog integrity rule)
- PyInstaller integration has rough edges

PySide6 (Qt 6) is battle-tested over 20+ years, has native OS dialogs, a well-defined threading model (QThread + signals/slots), and excellent PyInstaller support.

## Scope

**~11,400 lines** of GUI code across 15 files. The backend (`peptide_manager/`, models, database) is **untouched** — only the presentation layer changes.

| Layer | Lines | Action |
|-------|-------|--------|
| `gui_modular/app.py` | 562 | Rewrite |
| `gui_modular/views/` (11 views) | ~7,429 | Rewrite |
| `gui_modular/components/` (4 files) | ~597 | Rewrite |
| `peptide_manager/` | ~5,000+ | No change |
| `tests/` | ~3,000+ | No change (add GUI tests) |

## Architecture: Flet vs Qt

| Concern | Flet (current) | PySide6 (target) |
|---------|---------------|-------------------|
| Layout | `ft.Row`, `ft.Column`, `expand=True` | `QHBoxLayout`, `QVBoxLayout`, stretch factors |
| Navigation | `NavigationBar` + content swap | `QStackedWidget` + `QListWidget` sidebar |
| Data tables | Custom `ft.DataTable` wrapper | `QTableView` + `QSortFilterProxyModel` |
| Dialogs | `page.overlay.append()` + manual lifecycle | `QDialog.exec()` (modal, blocking, reliable) |
| Forms | Custom `FormBuilder` → dict of controls | `QFormLayout` + `QDataWidgetMapper` |
| Notifications | `ft.SnackBar` | `QStatusBar.showMessage()` or custom toast |
| Threading | `threading.local()` per-thread SQLite | `QThread` + signals, or `QRunnable` pool |
| Theming | `ft.ThemeMode.DARK` + color constants | QSS stylesheet (CSS-like) |
| File picker | `ft.FilePicker` (async callback, buggy) | `QFileDialog.getOpenFileName()` (sync, native) |
| Icons | `ft.Icons.DASHBOARD` (Material) | `QIcon` + Material icons via `qtawesome` |

## Control Mapping Reference

| Flet | PySide6 | Notes |
|------|---------|-------|
| `ft.Text` | `QLabel` | |
| `ft.TextField` | `QLineEdit` / `QTextEdit` | |
| `ft.Dropdown` | `QComboBox` | |
| `ft.Switch` | `QCheckBox` or `QSwitch` (Qt 6.5+) | |
| `ft.RadioGroup` | `QButtonGroup` + `QRadioButton` | |
| `ft.Container` | `QFrame` / `QWidget` | |
| `ft.Row` | `QHBoxLayout` | |
| `ft.Column` | `QVBoxLayout` | |
| `ft.DataTable` | `QTableView` + `QAbstractTableModel` | Major improvement — native sort/filter |
| `ft.AlertDialog` | `QDialog` / `QMessageBox` | No more overlay bugs |
| `ft.Tabs` | `QTabWidget` | |
| `ft.Card` | `QGroupBox` or styled `QFrame` | |
| `ft.ProgressRing` | `QProgressBar` (indeterminate) | |
| `ft.Divider` | `QFrame` with `HLine` shape | |
| `ft.NavigationBar` | `QListWidget` sidebar or `QToolBar` | |
| `ft.SnackBar` | `QStatusBar` / custom overlay widget | |
| `ft.FilePicker` | `QFileDialog` | Sync, native, reliable |

## Phase Plan

### Phase 0: Setup (1 session)

Create the new GUI module alongside the old one so both can coexist during migration.

```
gui_qt/
  __init__.py
  app.py              # QMainWindow, navigation, theming
  style.qss           # Dark theme stylesheet
  components/
    __init__.py
    data_table.py      # QTableView + model wrapper
    dialogs.py         # QDialog helpers
    forms.py           # QFormLayout builder
  views/
    __init__.py
    base.py            # Base view class (QWidget)
```

- Install PySide6: `pip install PySide6`
- Add to requirements.txt
- Create entry point: `python gui_qt/app.py`
- Dark theme QSS stylesheet
- Basic QMainWindow with sidebar navigation + QStackedWidget
- Verify PyInstaller bundles it (`flet pack` → standard `pyinstaller`)

**Done when:** Empty app window opens with dark theme, sidebar with 11 nav items, and a blank content area. Closes cleanly.

### Phase 1: Components (1-2 sessions)

Port the 3 reusable components. These are the foundation everything else builds on.

**1a. DataTable component** (`data_table.py` — most critical)
- `QAbstractTableModel` subclass that takes a list of dicts/rows
- `QSortFilterProxyModel` for sorting + text filter (replaces custom sort logic)
- Action buttons column via `QStyledItemDelegate`
- Toolbar with title, search field, add button
- Row selection signals

**1b. DialogBuilder** (`dialogs.py`)
- `confirm_delete(parent, entity_name)` → `QMessageBox.question()`
- `show_form_dialog(parent, title, fields)` → `QDialog` with `QFormLayout`
- `show_info(parent, title, message)` → `QMessageBox.information()`
- No more overlay management — Qt handles dialog lifecycle natively

**1c. FormBuilder** (`forms.py`)
- Field types: TEXT → QLineEdit, NUMBER → QSpinBox/QDoubleSpinBox, DATE → QDateEdit, DROPDOWN → QComboBox, TEXTAREA → QTextEdit, CHECKBOX → QCheckBox
- `build_form(fields) → QFormLayout`
- `get_values(layout) → dict`
- `validate_required(layout) → list[str]`

**Done when:** Components have unit tests and a simple demo window exercises each one.

### Phase 2: Simple CRUD views (2-3 sessions)

Port the 4 simplest views that follow the same pattern: table + add/edit/delete dialogs.

Order (simplest first):
1. **Peptides** (270 lines) — minimal fields, good template
2. **Suppliers** (310 lines) — similar pattern + Janoshik score display
3. **Batches** (491 lines) — adds composition summary, search/filter
4. **Protocols** (616 lines) — adds frequency description builder

Each view follows the same pattern:
```python
class PeptidesView(BaseView):
    def __init__(self, app):
        super().__init__(app)
        self.table = DataTable(columns=[...], data=self.load_data())
        self.table.on_add.connect(self.show_add_dialog)
        self.table.on_edit.connect(self.show_edit_dialog)
        self.table.on_delete.connect(self.confirm_delete)

    def load_data(self) -> list[dict]:
        return self.app.manager.get_peptides()
```

**Done when:** All 4 views work with real data. Add, edit, delete, sort, filter all functional.

### Phase 3: Data-heavy views (2-3 sessions)

Port views with more complex data interactions:

1. **Preparations** (690 lines) — volume tracking, wastage recording, percentage display
2. **Administrations** (719 lines) — pandas DataFrame integration, date range filter, injection site tracking
3. **Calculator** (539 lines) — mode switching (radio groups), concentration math, result display

Key challenges:
- Administrations uses pandas — keep this, just render into QTableView
- Calculator has stateful mode switching — use QStackedWidget for mode panels

**Done when:** All 3 views work with real data, including the pandas-based filtering in Administrations.

### Phase 4: Complex views (3-4 sessions)

The heavy lifts:

1. **Dashboard** (874 lines) — stat cards, scheduled administrations table, expiring batches, "register" action
2. **Cycles** (1,729 lines) — 3-tab interface (active/planned/completed), status management, ramp schedules
3. **Treatment Planner** (1,906 lines) — multi-phase wizard, resource calculation, phase activation
4. **Janoshik** (942 lines) — 4-tab interface, market data, LLM integration, ranking display

Strategy for each:
- Dashboard: `QGridLayout` for stat cards, `QTableView` for scheduled tasks
- Cycles: `QTabWidget` with 3 tabs, each containing a DataTable
- Treatment Planner: `QWizard` for creation flow, custom widget for plan display
- Janoshik: `QTabWidget` with 4 tabs, background worker for LLM calls

**Done when:** All complex views work. Treatment planner wizard creates plans. Janoshik ranks suppliers.

### Phase 5: App shell + integration (1-2 sessions)

1. Port `app.py`:
   - `QMainWindow` with `QListWidget` sidebar + `QStackedWidget`
   - Edit mode toggle in toolbar
   - Environment badge in status bar
   - `QFileDialog` for DB import (no more grey screen bug)
   - Window close → backup (via `closeEvent` override — reliable, no atexit needed)

2. Threading:
   - Replace `ThreadSafePeptideManager` + `threading.local()` with:
     - Main thread: all UI
     - `QThread` worker for long operations (Janoshik scraping, backup)
     - SQLite connection stays on main thread (no threading issue since Qt enforces single-thread UI)

3. PyInstaller build:
   - Replace `flet pack` with standard `pyinstaller` command
   - Simpler spec file (no Flet web server bundling)
   - `console=False` still applies, but Qt apps handle errors better

**Done when:** Full app runs from `gui_qt/app.py`. All views navigable. Import, backup, first-run all work.

### Phase 6: Polish + cutover (1 session)

1. Dark theme QSS refinement — match current color scheme
2. Keyboard shortcuts (Ctrl+N for new, Ctrl+E for edit mode, etc.)
3. Window state persistence (size, position, last view)
4. Remove `gui_modular/` from the codebase
5. Update `scripts/build.py` for PyInstaller (no `flet pack`)
6. Update CLAUDE.md (remove dialog integrity rule, add Qt conventions)
7. Final test pass

## Threading Model (Qt)

```
Main Thread (QApplication event loop)
  ├── All UI rendering
  ├── SQLite connection (single connection, no threading issue)
  ├── Short DB operations (CRUD, queries)
  └── Signals ←→ Slots

Worker QThread (for long operations only)
  ├── Janoshik scraping / LLM calls
  ├── Database backup
  └── Emits signals back to main thread
```

This is simpler than the current model. No `threading.local()`, no per-thread connections. Qt's event loop ensures UI operations are single-threaded.

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Breaking existing functionality | Keep `gui_modular/` working until `gui_qt/` is complete. Both can coexist. |
| Qt learning curve | Start with simple views (Phase 2). Patterns established there carry to complex views. |
| Dark theme inconsistency | Write QSS once in Phase 0, refine in Phase 6. |
| Missing Material icons | Use `qtawesome` library (has Material Design icons). |
| PyInstaller bundle size | Qt adds ~50-80MB. Acceptable for a desktop app. |
| Test coverage | Backend tests unchanged. Add basic GUI smoke tests with `pytest-qt`. |

## Estimated Effort

| Phase | Sessions | Lines (approx) |
|-------|----------|----------------|
| 0: Setup | 1 | ~200 |
| 1: Components | 1-2 | ~600 |
| 2: Simple CRUD | 2-3 | ~1,500 |
| 3: Data-heavy | 2-3 | ~1,500 |
| 4: Complex views | 3-4 | ~4,000 |
| 5: App shell | 1-2 | ~500 |
| 6: Polish | 1 | ~200 |
| **Total** | **~11-16 sessions** | **~8,500** |

The new codebase should be ~25% smaller than the current one thanks to Qt's built-in sort/filter, native dialogs, and QSS theming replacing manual color assignments.

## Files Not Touched

- `peptide_manager/` — entire backend unchanged
- `peptide_manager/models/` — all repositories unchanged
- `peptide_manager/database.py` — unchanged
- `peptide_manager/backup.py` — unchanged
- `peptide_manager/calculator.py` — unchanged
- `peptide_manager/janoshik/` — unchanged
- `tests/` — all existing tests unchanged
- `migrations/` — unchanged
- `scripts/environment.py` — unchanged
