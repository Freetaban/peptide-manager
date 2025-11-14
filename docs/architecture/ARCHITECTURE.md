# Architecture Documentation

This document tracks the architecture decisions and current state of the Peptide Management System.

## Current Architecture

### Overview
The system is in a **transitional state**, migrating from a monolithic architecture to a modular, repository-based architecture.

### Architecture Layers

```
┌─────────────────────────────────────┐
│         Presentation Layer          │
│  (GUI - Flet, CLI - Click, TUI)     │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│      Adapter Layer (Temporary)       │
│    PeptideManager (Hybrid)           │
└──────────────┬──────────────────────┘
               │
       ┌───────┴───────┐
       │               │
┌──────▼──────┐  ┌─────▼─────────┐
│   New       │  │   Legacy       │
│ Repository  │  │   models_legacy│
│ Pattern     │  │   (Deprecated) │
└──────┬──────┘  └────────────────┘
       │
┌──────▼──────────────────────────────┐
│      Database Layer (SQLite)        │
│    DatabaseManager + Connections     │
└──────────────────────────────────────┘
```

### Module Status

#### ✅ Migrated (New Architecture)
- **Suppliers**: `peptide_manager/models/supplier.py`
- **Peptides**: `peptide_manager/models/peptide.py`
- **Batches**: `peptide_manager/models/batch.py`
- **BatchComposition**: `peptide_manager/models/batch_composition.py`

#### ⚠️ In Progress
- Database migrations (Alembic setup)

#### ❌ Not Yet Migrated (Legacy)
- **Preparations**: Still in `models_legacy.py`
- **Protocols**: Still in `models_legacy.py`
- **Administrations**: Still in `models_legacy.py`
- **Certificates**: Still in `models_legacy.py`

### Design Patterns

#### Repository Pattern
Each entity has a dedicated repository class:
- `SupplierRepository`
- `PeptideRepository`
- `BatchRepository`
- `BatchCompositionRepository`

#### Adapter Pattern
`PeptideManager` acts as an adapter, routing calls to:
- New repositories (for migrated modules)
- Legacy code (for non-migrated modules)

This allows incremental migration without breaking existing code.

### Database Schema

#### Current State
- SQLite database
- Manual migrations in `migrations/` directory
- Foreign keys enabled via `PRAGMA foreign_keys = ON`

#### Target State
- Alembic-managed migrations
- Versioned schema changes
- Automated migration application

### Key Design Decisions

See `DECISIONS.md` for detailed decision log.

## Migration Strategy

### Phase 1: Database Foundation ✅ (In Progress)
- [x] Repository pattern established
- [ ] Alembic setup and baseline
- [ ] SQLite configuration (WAL, timeouts)

### Phase 2: Complete Repository Migration
- [ ] Migrate Preparations
- [ ] Migrate Protocols
- [ ] Migrate Administrations
- [ ] Migrate Certificates

### Phase 3: Remove Legacy Code
- [ ] Remove `models_legacy.py`
- [ ] Remove adapter fallbacks
- [ ] Clean up imports

### Phase 4: UI Refactoring
- [ ] Split `gui.py` into components
- [ ] Create service layer
- [ ] Implement proper state management
- [ ] Improve error handling

## File Organization

```
peptide-management-system/
├── peptide_manager/          # Core package
│   ├── __init__.py           # Adapter (temporary)
│   ├── database.py           # DatabaseManager
│   ├── models/               # New architecture
│   │   ├── base.py          # BaseModel, Repository
│   │   ├── supplier.py      # ✅ Migrated
│   │   ├── peptide.py       # ✅ Migrated
│   │   ├── batch.py         # ✅ Migrated
│   │   └── batch_composition.py  # ✅ Migrated
│   ├── models_legacy.py     # ⚠️ To be removed
│   └── ...
├── cli/                      # CLI interface
├── gui.py                    # ⚠️ Needs refactoring
├── migrations/               # Database migrations
└── tests/                    # Test suite
```

## Conventions

### Naming
- Models: PascalCase (e.g., `Supplier`, `Batch`)
- Repositories: `{Model}Repository` (e.g., `SupplierRepository`)
- Methods: snake_case
- Private methods: `_method_name`

### Code Style
- Type hints required for all functions
- Docstrings in Google style
- Dataclasses for models
- Repository pattern for data access

### Testing
- Unit tests for each repository method
- Integration tests for workflows
- Test fixtures for database setup

## Future Considerations

### Scalability
- Current: Single-user, local SQLite
- Future: May need multi-user support
- Future: May need remote database

### Performance
- Current: Direct SQLite access
- Future: Connection pooling if needed
- Future: Query optimization if dataset grows

### Features
- [ ] API layer (REST/GraphQL)
- [ ] Multi-user support
- [ ] Cloud sync
- [ ] Mobile app

## Notes

- The adapter pattern is temporary and will be removed once all modules are migrated
- GUI refactoring should happen after database migration is complete
- All migrations must be backward-compatible during transition period

