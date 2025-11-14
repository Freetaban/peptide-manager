# 🔮 Protocol Evolution: Template → Plan → Cycle

**Status:** 🎯 Planned Feature  
**Priority:** High  
**Impact:** Major architectural change  
**Date Created:** 15 November 2025

---

## 📋 Executive Summary

Current system treats "protocols" as a single concept, mixing:
- Reusable dosing templates
- Specific treatment instances
- Actual administration tracking

**Proposal:** Split into **3 distinct levels** for better tracking, analytics, and planning.

---

## 🔍 Current Problem

### Single `protocols` Table Issues

```sql
-- Current schema mixes concepts
CREATE TABLE protocols (
    id INTEGER PRIMARY KEY,
    name TEXT,                     -- "MT2 Summer Protocol" (reusable?) 
    dose_ml REAL,                  -- Template or instance?
    active INTEGER,                -- Is this the template or a run?
    cycle_duration_weeks INTEGER   -- Planning or tracking?
);
```

**Problems:**
1. ❌ **No Reusability**: Can't reuse "MT2 Summer Protocol" for multiple cycles
2. ❌ **No History**: Can't compare Cycle June 2025 vs Cycle August 2025
3. ❌ **No Planning**: Can't plan future cycles without creating protocol entries
4. ❌ **Ambiguous Status**: Is protocol "active" = running now or just available?
5. ❌ **Poor Analytics**: Can't answer "How much did I use in last cycle?"

---

## 💡 Proposed Solution: 3-Level Architecture

### Level 1: Protocol Template (Theoretical)

**Purpose:** Reusable dosing schema  
**Lifecycle:** Created once, reused many times  
**Example:** "Melanotan II - Summer Tanning Protocol"

```sql
CREATE TABLE protocol_templates (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    
    -- Dosing schema
    dose_ml REAL,
    frequency_per_day INTEGER,
    days_on INTEGER,
    days_off INTEGER,
    cycle_duration_weeks INTEGER,
    
    -- Target peptides (optional)
    -- Links via protocol_template_peptides
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active INTEGER DEFAULT 1,  -- Can be used?
    
    UNIQUE(name)
);

CREATE TABLE protocol_template_peptides (
    id INTEGER PRIMARY KEY,
    template_id INTEGER NOT NULL,
    peptide_id INTEGER NOT NULL,
    target_dose_mcg REAL,
    notes TEXT,
    
    FOREIGN KEY (template_id) REFERENCES protocol_templates(id) ON DELETE CASCADE,
    FOREIGN KEY (peptide_id) REFERENCES peptides(id),
    UNIQUE(template_id, peptide_id)
);
```

### Level 2: Treatment Plan (Instance)

**Purpose:** Specific cycle execution of a template  
**Lifecycle:** Created when starting a cycle, completed when finished  
**Example:** "MT2 Summer 2025 - June Cycle"

```sql
CREATE TABLE treatment_plans (
    id INTEGER PRIMARY KEY,
    protocol_template_id INTEGER,  -- NULL = ad-hoc plan
    name TEXT NOT NULL,
    description TEXT,
    
    -- Scheduling
    start_date DATE NOT NULL,
    planned_end_date DATE,
    actual_end_date DATE,
    
    -- Status tracking
    status TEXT CHECK(status IN ('planned', 'active', 'paused', 'completed', 'abandoned')) DEFAULT 'planned',
    
    -- Goals/Notes
    goals TEXT,
    notes TEXT,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    
    FOREIGN KEY (protocol_template_id) REFERENCES protocol_templates(id) ON DELETE SET NULL
);

-- Link plans to specific preparations
CREATE TABLE treatment_plan_preparations (
    id INTEGER PRIMARY KEY,
    plan_id INTEGER NOT NULL,
    preparation_id INTEGER NOT NULL,
    assigned_date DATE DEFAULT CURRENT_DATE,
    notes TEXT,
    
    FOREIGN KEY (plan_id) REFERENCES treatment_plans(id) ON DELETE CASCADE,
    FOREIGN KEY (preparation_id) REFERENCES preparations(id),
    UNIQUE(plan_id, preparation_id)
);
```

### Level 3: Administration Records (Execution)

**Purpose:** Actual injection log  
**Lifecycle:** Created per injection  
**Example:** Individual 0.5ml injection records

```sql
-- MODIFY existing table
ALTER TABLE administrations ADD COLUMN treatment_plan_id INTEGER REFERENCES treatment_plans(id);

-- Keep protocol_id temporarily for backward compatibility
-- Remove after migration complete
```

---

## 🎯 Use Cases Enabled

### 1. Template Reuse
```sql
-- Create template once
INSERT INTO protocol_templates (name, dose_ml, frequency_per_day, days_on, days_off)
VALUES ('MT2 Summer Standard', 0.5, 1, 7, 7);

-- Reuse for multiple cycles
INSERT INTO treatment_plans (protocol_template_id, name, start_date)
VALUES 
    (1, 'MT2 June 2025', '2025-06-01'),
    (1, 'MT2 August 2025', '2025-08-01');
```

### 2. Cycle Comparison
```sql
-- Compare consumption across cycles
SELECT 
    tp.name,
    COUNT(a.id) as injections,
    SUM(a.dose_ml) as total_ml,
    SUM(a.dose_mcg) as total_mcg
FROM treatment_plans tp
JOIN administrations a ON a.treatment_plan_id = tp.id
WHERE tp.protocol_template_id = 1  -- MT2 template
GROUP BY tp.id;
```

### 3. Future Planning
```sql
-- Plan next cycle without starting it
INSERT INTO treatment_plans (
    protocol_template_id, 
    name, 
    start_date, 
    status
) VALUES (
    1, 
    'MT2 Next Summer 2026', 
    '2026-06-01', 
    'planned'
);
```

### 4. Mid-Cycle Adjustments
```sql
-- Pause current cycle
UPDATE treatment_plans 
SET status = 'paused', notes = 'Vacation break'
WHERE id = 42;

-- Resume later without losing history
UPDATE treatment_plans 
SET status = 'active'
WHERE id = 42;
```

---

## 📊 Data Flow Example

```
User creates template:
┌─────────────────────────────┐
│ Template: "MT2 Summer"       │
│ - 0.5ml x 1/day             │
│ - 7 days ON, 7 days OFF     │
└─────────────────────────────┘
              │
              │ User starts cycle
              ▼
┌─────────────────────────────┐
│ Plan: "MT2 June 2025"        │
│ - Based on template          │
│ - Start: 2025-06-01          │
│ - Status: active             │
│ - Prep #123 assigned         │
└─────────────────────────────┘
              │
              │ Daily injections
              ▼
┌─────────────────────────────┐
│ Administrations:             │
│ - 2025-06-01 08:00 0.5ml    │
│ - 2025-06-02 08:00 0.5ml    │
│ - ...                        │
│ - All linked to Plan ID      │
└─────────────────────────────┘
```

---

## 🔄 Migration Strategy

### Phase 1: Create New Tables ✅
```sql
-- Run migration: create protocol_templates, treatment_plans
-- Keep old protocols table intact
```

### Phase 2: Dual Write (Transition)
```sql
-- GUI writes to BOTH old and new tables
-- Allows rollback if needed
```

### Phase 3: Data Migration
```python
# Migrate existing protocols → templates
# Create plans for active protocols
# Link existing administrations to plans
```

### Phase 4: Update GUI
```python
# New views:
# - Protocol Templates library
# - Treatment Plans (past/active/planned)
# - Cycle comparison analytics
```

### Phase 5: Deprecate Old
```sql
-- Drop protocol_id from administrations
-- Archive old protocols table
```

---

## 🎨 GUI Mockups

### Protocol Templates Library
```
┌───────────────────────────────────────┐
│ 📚 Protocol Templates                 │
├───────────────────────────────────────┤
│ [+ New Template]        [Import]      │
├───────────────────────────────────────┤
│ ✓ MT2 Summer Standard                 │
│   0.5ml x 1/day, 7ON/7OFF             │
│   Used in 3 cycles                    │
│   [View] [Edit] [Create Plan]         │
├───────────────────────────────────────┤
│ ✓ BPC-157 Recovery Protocol           │
│   0.25ml x 2/day, continuous          │
│   Used in 1 cycle                     │
│   [View] [Edit] [Create Plan]         │
└───────────────────────────────────────┘
```

### Treatment Plans Dashboard
```
┌───────────────────────────────────────┐
│ 📅 Treatment Plans                    │
├───────────────────────────────────────┤
│ ACTIVE                                │
│ • MT2 June 2025                       │
│   Day 14/49 | 70% complete            │
│   [Details] [Pause] [Inject Now]      │
├───────────────────────────────────────┤
│ PLANNED                               │
│ • BPC Recovery August                 │
│   Starts in 45 days                   │
│   [Details] [Start Early] [Cancel]    │
├───────────────────────────────────────┤
│ COMPLETED                             │
│ • MT2 May 2025 ✓                      │
│   49 days | 49 injections | 24.5ml    │
│   [Analytics] [Clone] [Archive]       │
└───────────────────────────────────────┘
```

---

## 📈 Analytics Enhancements

### Per-Plan Statistics
- Total consumption (ml/mcg)
- Adherence rate (planned vs actual injections)
- Cost per cycle
- Side effects frequency
- Effectiveness rating (user input)

### Cross-Plan Comparison
- Best performing cycle
- Most cost-effective approach
- Optimal dosing patterns
- Seasonal trends

### Predictive Planning
- Estimated consumption for planned cycle
- Preparation needs forecast
- Budget projections

---

## ⚠️ Backward Compatibility

### During Migration
- Old `protocols` table remains
- Adapters maintain API compatibility
- GUI shows unified view

### After Migration
- `protocol_id` kept as deprecated column
- Old data accessible via legacy views
- No data loss

---

## ✅ Implementation Checklist

- [ ] Create database migration (Alembic)
- [ ] Implement ProtocolTemplate model + repository
- [ ] Implement TreatmentPlan model + repository
- [ ] Create adapter layer for backward compatibility
- [ ] Build GUI: Protocol Templates view
- [ ] Build GUI: Treatment Plans dashboard
- [ ] Build GUI: Cycle analytics
- [ ] Migrate existing data
- [ ] Add unit tests
- [ ] Update documentation
- [ ] Deprecate old protocols table

---

## 🔗 Related Documents

- [ARCHITECTURE.md](../architecture/ARCHITECTURE.md) - System design
- [DATABASE_SCHEMA.md](../architecture/DATABASE_SCHEMA.md) - Full schema
- [MIGRATION_GUIDE.md](../migration/MIGRATION_GUIDE.md) - Migration patterns

---

**Last Updated:** 15 November 2025  
**Estimated Effort:** 2-3 weeks  
**Dependencies:** None (refactoring complete)
