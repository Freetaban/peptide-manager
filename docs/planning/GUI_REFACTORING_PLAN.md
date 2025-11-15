# 🔧 GUI Refactoring Plan - Flet to PyQt6 Migration

## 📊 Current State Analysis

### File Stats
- **Total Lines**: 3,705
- **Main Class**: `PeptideGUI`
- **Build Methods**: 9 (dashboard, batches, peptides, suppliers, preparations, protocols, administrations, calculator, header)
- **Dialog Methods**: 20+ (show_*_dialog, show_*_details)

### Architecture Issues

1. **Monolithic Structure** (3,705 lines in one file)
   - All views in single class
   - Repeated patterns (DataTable, Forms, Dialogs)
   - Hard to maintain and test

2. **Duplication Patterns**
   - Each entity has similar CRUD dialogs (~200 lines each)
   - DataTable creation repeated 8 times
   - Form validation duplicated across dialogs
   - Detail views follow same pattern

3. **Threading Issues**
   - SQLite connection created in main thread
   - Flet uses worker threads for UI events
   - Error: `SQLite objects created in a thread can only be used in that same thread`

4. **Tight Coupling**
   - UI logic mixed with business logic
   - Direct database calls from UI
   - Hard to migrate to different framework

## 🎯 Refactoring Strategy (Phase 1: Flet Optimization)

### Step 1: Extract Reusable Components (Keep Flet)
**Goal**: Reduce from 3,705 to ~1,500 lines + components

#### 1.1 Create `gui/components/` Module
```
gui/
├── __init__.py
├── app.py                    # Main app (300 lines)
├── components/
│   ├── __init__.py
│   ├── data_table.py        # Reusable DataTable (150 lines)
│   ├── forms.py             # Form builders (200 lines)
│   ├── dialogs.py           # Dialog templates (150 lines)
│   └── cards.py             # Stats cards (100 lines)
└── views/
    ├── __init__.py
    ├── dashboard.py         # Dashboard view (200 lines)
    ├── batches.py           # Batches CRUD (300 lines)
    ├── peptides.py          # Peptides CRUD (300 lines)
    ├── suppliers.py         # Suppliers CRUD (250 lines)
    ├── preparations.py      # Preparations CRUD (350 lines)
    ├── protocols.py         # Protocols CRUD (300 lines)
    ├── administrations.py   # Administrations CRUD (300 lines)
    └── calculator.py        # Calculator view (200 lines)
```

**Benefits**:
- ✅ Each view becomes maintainable (~300 lines)
- ✅ Components reusable across views
- ✅ Easier to test individual components
- ✅ Still using Flet (no breaking changes)

#### 1.2 Component Specifications

**DataTable Component** (`components/data_table.py`):
```python
class DataTable:
    """Reusable data table with CRUD buttons"""
    def __init__(self, columns, data_source, actions):
        pass
    
    def build(self):
        """Returns ft.DataTable with pagination"""
        pass
```

**FormBuilder** (`components/forms.py`):
```python
class FormBuilder:
    """Dynamic form generation from field specs"""
    def __init__(self, fields, on_submit):
        pass
    
    def build(self):
        """Returns form with validation"""
        pass
```

**DialogBuilder** (`components/dialogs.py`):
```python
class DialogBuilder:
    """Standard dialogs (confirm, form, details)"""
    @staticmethod
    def confirm_delete(entity_name, on_confirm):
        pass
    
    @staticmethod
    def form_dialog(title, form_builder):
        pass
```

### Step 2: Fix Threading Issues

**Problem**: SQLite connection not thread-safe in Flet

**Solution Options**:

**Option A: Connection per thread** (Quick fix)
```python
import threading

class ThreadSafePeptideManager:
    def __init__(self, db_path):
        self.db_path = db_path
        self._thread_local = threading.local()
    
    @property
    def manager(self):
        if not hasattr(self._thread_local, 'manager'):
            self._thread_local.manager = PeptideManager(self.db_path)
        return self._thread_local.manager
```

**Option B: Queue-based** (More robust)
```python
import queue
import threading

class AsyncPeptideManager:
    """Execute DB operations in dedicated thread"""
    def __init__(self, db_path):
        self.db_path = db_path
        self.queue = queue.Queue()
        self.worker = threading.Thread(target=self._worker, daemon=True)
        self.worker.start()
    
    def _worker(self):
        manager = PeptideManager(self.db_path)
        while True:
            func, args, kwargs, result_queue = self.queue.get()
            try:
                result = func(manager, *args, **kwargs)
                result_queue.put(('ok', result))
            except Exception as e:
                result_queue.put(('error', e))
    
    def execute(self, func, *args, **kwargs):
        result_queue = queue.Queue()
        self.queue.put((func, args, kwargs, result_queue))
        status, result = result_queue.get()
        if status == 'error':
            raise result
        return result
```

**Recommendation**: Use **Option A** for now (simpler), plan **Option B** for PyQt6 migration.

### Step 3: Migration Milestones

**Week 1-2: Component Extraction**
- [ ] Create `gui/components/` module structure
- [ ] Extract DataTable component
- [ ] Extract FormBuilder component
- [ ] Extract DialogBuilder component
- [ ] Extract Card components
- [ ] Add unit tests for components

**Week 3: View Separation**
- [ ] Create `gui/views/` module
- [ ] Split Dashboard view
- [ ] Split Batches view  
- [ ] Split Peptides view
- [ ] Split remaining views
- [ ] Update main app.py to use views

**Week 4: Testing & Polish**
- [ ] Fix threading issues (Option A)
- [ ] Integration testing
- [ ] Performance optimization
- [ ] Documentation

## 🚀 Phase 2: PyQt6 Migration (Future)

### Why PyQt6?
- ✅ Native look & feel per platform
- ✅ Better performance
- ✅ More mature ecosystem
- ✅ Better threading support
- ✅ Easier packaging (.exe)
- ✅ No threading issues with SQLite

### Migration Strategy
With modular structure from Phase 1:
1. Each Flet view → PyQt6 QWidget
2. DataTable component → QTableWidget wrapper
3. FormBuilder → QForm wrapper
4. Dialogs → QDialog wrappers

**Estimated effort**: 2-3 weeks (vs 2-3 months without refactoring)

## 📋 Implementation Checklist

### Immediate Actions
- [x] Analyze current codebase (DONE)
- [x] Document refactoring plan (DONE)
- [ ] Create feature branch `feature/gui-modular-flet`
- [ ] Set up component module structure
- [ ] Extract first component (DataTable)
- [ ] Extract first view (Dashboard)
- [ ] Test and iterate

### Success Metrics
- **Code Reduction**: 3,705 lines → ~1,500 lines main + ~600 lines components + ~2,000 lines views
- **Testability**: Each component/view testable in isolation
- **Maintainability**: No file > 400 lines
- **Reusability**: Components used in 3+ views
- **Migration Ready**: Clear mapping to PyQt6 widgets

## 🛠️ Technical Decisions

### Keep for Now (Flet Phase)
- ✅ Flet framework (0.28.3)
- ✅ Material Design
- ✅ Current UI/UX patterns
- ✅ Existing navigation

### Prepare for Future (PyQt6 Phase)
- 🎯 Modular architecture
- 🎯 Separated concerns
- 🎯 Component-based design
- 🎯 Thread-safe patterns
- 🎯 Testable code

## 📝 Notes
- **Priority**: Modular architecture over framework migration
- **Risk**: Low (incremental refactoring, can rollback)
- **Timeline**: 4 weeks for Flet optimization, 2-3 weeks for PyQt6 migration
- **Team**: Can be done incrementally by 1 developer

---

**Next Step**: Create feature branch and start with DataTable component extraction
