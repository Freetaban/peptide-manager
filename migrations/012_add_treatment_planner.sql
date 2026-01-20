-- Migration 012: Add Treatment Planner Tables
-- Adds support for multi-phase treatment planning with resource calculation
-- Tables: treatment_plans, plan_phases, plan_resources, plan_simulations

-- =============================================================================
-- 0. TREATMENT_PLANS - Tabella base per piani di trattamento (se non esiste)
-- =============================================================================
CREATE TABLE IF NOT EXISTS treatment_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    start_date DATE NOT NULL,
    protocol_template_id INTEGER,  -- Can be NULL, no FK constraint
    description TEXT,
    reason TEXT,
    planned_end_date DATE,
    actual_end_date DATE,
    status TEXT DEFAULT 'active', -- 'active', 'paused', 'completed', 'abandoned', 'planned'
    total_planned_days INTEGER,
    days_completed INTEGER DEFAULT 0,
    adherence_percentage REAL DEFAULT 100.0,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_treatment_plans_status ON treatment_plans(status);
CREATE INDEX IF NOT EXISTS idx_treatment_plans_template ON treatment_plans(protocol_template_id);
CREATE INDEX IF NOT EXISTS idx_treatment_plans_dates ON treatment_plans(start_date, planned_end_date);

-- =============================================================================
-- 1. PLAN_PHASES - Fasi di un piano di trattamento
-- =============================================================================
CREATE TABLE IF NOT EXISTS plan_phases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    treatment_plan_id INTEGER NOT NULL,
    phase_number INTEGER NOT NULL, -- 1, 2, 3, 4 (Foundation, Intensification, Consolidation, Transition)
    phase_name TEXT NOT NULL, -- es. "Foundation", "Intensification", etc.
    description TEXT,
    
    -- Timing
    duration_weeks INTEGER NOT NULL, -- Durata prevista in settimane
    start_week INTEGER, -- Settimana di inizio relativa al piano (1-based, NULL se non ancora iniziata)
    
    -- Peptide configuration (JSON array)
    -- [{peptide_id: 1, dose_mcg: 100, peptide_name: "CJC-1295"}, ...]
    peptides_config TEXT NOT NULL, -- JSON array di configurazioni peptidi
    
    -- Dosing protocol
    daily_frequency INTEGER NOT NULL DEFAULT 1, -- 1x, 2x, 3x al giorno
    five_two_protocol BOOLEAN DEFAULT 0, -- 5 giorni on, 2 giorni off
    ramp_schedule TEXT, -- JSON per ramp-up/down opzionale
    
    -- Status tracking
    status TEXT DEFAULT 'planned', -- 'planned', 'active', 'completed', 'skipped'
    cycle_id INTEGER, -- Link al Cycle quando la fase viene attivata
    actual_start_date DATE,
    actual_end_date DATE,
    
    -- Notes
    notes TEXT,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP,
    
    FOREIGN KEY (treatment_plan_id) REFERENCES treatment_plans(id) ON DELETE CASCADE,
    FOREIGN KEY (cycle_id) REFERENCES cycles(id) ON DELETE SET NULL,
    
    -- Constraint: phase_number unico per treatment_plan
    UNIQUE(treatment_plan_id, phase_number)
);

CREATE INDEX IF NOT EXISTS idx_plan_phases_plan ON plan_phases(treatment_plan_id);
CREATE INDEX IF NOT EXISTS idx_plan_phases_status ON plan_phases(status);
CREATE INDEX IF NOT EXISTS idx_plan_phases_cycle ON plan_phases(cycle_id);

-- =============================================================================
-- 2. PLAN_RESOURCES - Risorse calcolate per fase o piano completo
-- =============================================================================
CREATE TABLE IF NOT EXISTS plan_resources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Scope: fase specifica o piano completo
    treatment_plan_id INTEGER NOT NULL,
    plan_phase_id INTEGER, -- NULL = risorse per intero piano, altrimenti per fase specifica
    
    -- Resource identification
    resource_type TEXT NOT NULL, -- 'peptide', 'syringe', 'needle', 'consumable'
    resource_id INTEGER, -- peptide_id, NULL per consumabili generici
    resource_name TEXT NOT NULL, -- Nome descrittivo
    
    -- Quantities
    quantity_needed REAL NOT NULL, -- Quantità totale richiesta
    quantity_unit TEXT NOT NULL, -- 'vials', 'mg', 'ml', 'units'
    
    -- Inventory check (snapshot al momento del calcolo)
    quantity_available REAL DEFAULT 0,
    quantity_gap REAL, -- quantity_needed - quantity_available (può essere negativo)
    
    -- Acquisition planning
    needs_ordering BOOLEAN DEFAULT 0, -- Flag se serve ordinare
    order_by_week INTEGER, -- Settimana entro cui ordinare (relativa a inizio piano)
    estimated_cost REAL, -- Costo stimato per acquisto gap
    currency TEXT DEFAULT 'EUR',
    
    -- Calculation metadata
    calculation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    calculation_params TEXT, -- JSON con parametri usati per calcolo
    
    -- Notes
    notes TEXT,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (treatment_plan_id) REFERENCES treatment_plans(id) ON DELETE CASCADE,
    FOREIGN KEY (plan_phase_id) REFERENCES plan_phases(id) ON DELETE CASCADE,
    FOREIGN KEY (resource_id) REFERENCES peptides(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_plan_resources_plan ON plan_resources(treatment_plan_id);
CREATE INDEX IF NOT EXISTS idx_plan_resources_phase ON plan_resources(plan_phase_id);
CREATE INDEX IF NOT EXISTS idx_plan_resources_type ON plan_resources(resource_type);
CREATE INDEX IF NOT EXISTS idx_plan_resources_ordering ON plan_resources(needs_ordering);

-- =============================================================================
-- 3. PLAN_SIMULATIONS - Simulazioni what-if salvate
-- =============================================================================
CREATE TABLE IF NOT EXISTS plan_simulations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Simulation metadata
    name TEXT NOT NULL,
    description TEXT,
    base_plan_id INTEGER, -- Piano originale da cui deriva la simulazione (può essere NULL)
    
    -- Configuration snapshot (JSON)
    -- Salva intera configurazione fasi + parametri per riproducibilità
    simulation_config TEXT NOT NULL, -- JSON completo della simulazione
    
    -- Results summary (JSON)
    -- Salva risultati calcolati: risorse totali, costi, timeline
    results_summary TEXT, -- JSON con risultati aggregati
    
    -- Comparison metadata (se deriva da piano esistente)
    comparison_notes TEXT, -- Note sulle differenze vs piano base
    
    -- Status
    is_archived BOOLEAN DEFAULT 0,
    converted_to_plan BOOLEAN DEFAULT 0, -- Se simulazione è diventata piano reale
    converted_plan_id INTEGER, -- ID del piano creato da questa simulazione
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP,
    
    FOREIGN KEY (base_plan_id) REFERENCES treatment_plans(id) ON DELETE SET NULL,
    FOREIGN KEY (converted_plan_id) REFERENCES treatment_plans(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_plan_simulations_base ON plan_simulations(base_plan_id);
CREATE INDEX IF NOT EXISTS idx_plan_simulations_converted ON plan_simulations(converted_to_plan);

-- =============================================================================
-- 4. ALTER TREATMENT_PLANS - Aggiungere campi per supporto planner
-- =============================================================================

-- Aggiungi colonna per indicare se piano è multi-fase
-- (backwards compatible: piani esistenti senza fasi funzionano come prima)
ALTER TABLE treatment_plans ADD COLUMN is_multi_phase BOOLEAN DEFAULT 0;

-- Link a simulazione originale (se piano deriva da simulazione)
ALTER TABLE treatment_plans ADD COLUMN simulation_id INTEGER REFERENCES plan_simulations(id) ON DELETE SET NULL;

-- Phase tracking
ALTER TABLE treatment_plans ADD COLUMN current_phase_id INTEGER REFERENCES plan_phases(id) ON DELETE SET NULL;
ALTER TABLE treatment_plans ADD COLUMN total_phases INTEGER DEFAULT 1;

-- Resource summary snapshot
ALTER TABLE treatment_plans ADD COLUMN resources_summary TEXT; -- JSON con summary risorse calcolate

CREATE INDEX IF NOT EXISTS idx_treatment_plans_multi_phase ON treatment_plans(is_multi_phase);
CREATE INDEX IF NOT EXISTS idx_treatment_plans_current_phase ON treatment_plans(current_phase_id);

-- =============================================================================
-- 5. ALTER CYCLES - Aggiungere link a plan_phase
-- =============================================================================

-- Link diretto alla fase del piano da cui il ciclo deriva
-- NOTA: Questa colonna potrebbe già esistere se migration 012 già applicata
-- ALTER TABLE cycles ADD COLUMN plan_phase_id INTEGER REFERENCES plan_phases(id) ON DELETE SET NULL;

-- CREATE INDEX IF NOT EXISTS idx_cycles_plan_phase ON cycles(plan_phase_id);

-- =============================================================================
-- Migration Complete
-- =============================================================================

-- Verifica integrità
SELECT 'Migration 012 completed: Treatment Planner tables created' AS status;
