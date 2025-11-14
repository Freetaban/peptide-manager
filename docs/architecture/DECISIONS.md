# Architecture Decision Log

This document records significant architectural and design decisions made during the refactoring process.

## Decision Template

Each decision follows this structure:
- **Date**: When the decision was made
- **Status**: Proposed | Accepted | Rejected | Superseded
- **Context**: What problem we're solving
- **Options**: Alternatives considered
- **Decision**: What was chosen
- **Rationale**: Why this choice
- **Consequences**: Impact of this decision

---

## Decisions

### D001: Use Repository Pattern for Data Access

**Date:** 2024-01-10  
**Status:** Accepted  
**Context:** Need to separate data access logic from business logic and enable testability.

**Options:**
- **A) Keep monolithic PeptideManager**: Simple but hard to test and maintain
- **B) Use Repository Pattern**: Industry standard, testable, maintainable

**Decision:** Option B - Repository Pattern

**Rationale:** 
- Enables unit testing of data access logic
- Separates concerns (data access vs business logic)
- Makes migration incremental (one entity at a time)
- Follows SOLID principles

**Consequences:**
- Positive: Better testability, clearer structure
- Negative: More files, initial setup overhead

---

### D002: Use Adapter Pattern for Backward Compatibility

**Date:** 2024-01-10  
**Status:** Accepted  
**Context:** Need to migrate incrementally without breaking existing GUI/CLI code.

**Options:**
- **A) Big Bang Migration**: Migrate everything at once
- **B) Adapter Pattern**: Gradual migration with compatibility layer

**Decision:** Option B - Adapter Pattern

**Rationale:**
- Allows incremental migration
- Keeps system functional during transition
- Reduces risk of breaking changes
- Enables testing of new code alongside old

**Consequences:**
- Positive: Safe, incremental migration
- Negative: Temporary complexity, need to remove adapter later

---

### D003: Use Alembic for Database Migrations

**Date:** 2024-01-15  
**Status:** Proposed  
**Context:** Need versioned, repeatable database schema changes.

**Options:**
- **A) Manual SQL Files**: Continue current approach
- **B) Alembic**: Industry-standard Python migration tool

**Decision:** Option B - Alembic (pending implementation)

**Rationale:**
- Automatic version tracking
- Rollback support
- Works with SQLite
- Standard tool, well-documented
- Essential for production deployments

**Consequences:**
- Positive: Reliable migration system, versioning, rollback
- Negative: New dependency, learning curve, migration of existing SQL files

---

### D004: Use Decimal for Monetary and Precise Values

**Date:** 2024-01-10  
**Status:** Accepted (but not fully implemented)  
**Context:** Need precise calculations for prices and peptide amounts.

**Options:**
- **A) Float**: Simple but imprecise
- **B) Decimal**: Precise but requires conversion

**Decision:** Option B - Decimal

**Rationale:**
- Financial calculations require precision
- Peptide amounts need exact values
- Prevents rounding errors

**Consequences:**
- Positive: Accurate calculations
- Negative: Need conversion to/from database (SQLite stores as REAL)
- **Note:** Current implementation converts to float for storage - needs fixing

---

### D005: Soft Delete for Batches

**Date:** 2024-01-10  
**Status:** Accepted  
**Context:** Need to preserve historical data while "removing" batches.

**Options:**
- **A) Hard Delete**: Permanently remove records
- **B) Soft Delete**: Mark as deleted, preserve data

**Decision:** Option B - Soft Delete

**Rationale:**
- Preserves audit trail
- Allows recovery of accidentally deleted data
- Maintains referential integrity
- Historical data important for tracking

**Consequences:**
- Positive: Data preservation, audit trail
- Negative: Need to filter deleted records in queries, storage overhead

---

### D006: Separate GUI from Business Logic

**Date:** 2024-01-15  
**Status:** Proposed  
**Context:** Current `gui.py` is 3700+ lines mixing UI and business logic.

**Options:**
- **A) Keep Monolithic GUI**: Simple but unmaintainable
- **B) Component-Based Architecture**: Separate components, service layer

**Decision:** Option B - Component-Based (pending implementation)

**Rationale:**
- Enables testing of UI separately
- Reusable components
- Easier maintenance
- Better separation of concerns

**Consequences:**
- Positive: Maintainable, testable UI
- Negative: More files, initial refactoring effort

---

## Pending Decisions

### P001: Transaction Management Strategy
**Context:** Need to handle multi-repository operations atomically.

**Options:**
- Unit of Work pattern
- Explicit transaction context manager
- Database-level transactions only

**Status:** Under consideration

---

### P002: Error Handling Strategy
**Context:** Need consistent error handling across layers.

**Options:**
- Custom exception hierarchy
- Standard Python exceptions with context
- Result/Either pattern

**Status:** Under consideration

---

### P003: Logging Strategy
**Context:** Currently using print() statements, need proper logging.

**Options:**
- Python logging module
- Structured logging (JSON)
- Log levels and handlers

**Status:** Under consideration

---

## Superseded Decisions

*(None yet - will be added as decisions change)*

