-- Migration 015: Add Vendor Pricing and Enhanced Phase Timing
-- Adds vendor product catalogs for cost estimation and intra-day timing for phases
-- ============================================================================

-- =============================================================================
-- 1. VENDOR_PRODUCTS - Listino prezzi prodotti per fornitore
-- =============================================================================
CREATE TABLE IF NOT EXISTS vendor_products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_id INTEGER NOT NULL,
    
    -- Product identification (può essere peptide o consumabile)
    product_type TEXT NOT NULL, -- 'peptide', 'syringe', 'needle', 'bac_water', 'alcohol_swab', 'sharps_container'
    peptide_id INTEGER, -- NULL se non è peptide
    product_name TEXT NOT NULL, -- Nome prodotto (es. "BPC-157 5mg", "Insulin Syringe 1ml")
    
    -- Quantity per unit
    mg_per_vial REAL, -- Solo per peptidi
    units_per_pack INTEGER DEFAULT 1, -- Per consumabili (es. 100 siringhe per box)
    
    -- Pricing
    price REAL NOT NULL,
    currency TEXT DEFAULT 'EUR',
    price_per_mg REAL, -- Calcolato: price / mg_per_vial (solo peptidi)
    
    -- Availability
    is_available BOOLEAN DEFAULT 1,
    lead_time_days INTEGER, -- Tempo consegna stimato
    minimum_order_qty INTEGER DEFAULT 1,
    
    -- Metadata
    sku TEXT, -- Codice prodotto fornitore
    url TEXT, -- Link diretto al prodotto
    notes TEXT,
    last_price_update DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id) ON DELETE CASCADE,
    FOREIGN KEY (peptide_id) REFERENCES peptides(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_vendor_products_supplier ON vendor_products(supplier_id);
CREATE INDEX IF NOT EXISTS idx_vendor_products_peptide ON vendor_products(peptide_id);
CREATE INDEX IF NOT EXISTS idx_vendor_products_type ON vendor_products(product_type);
CREATE INDEX IF NOT EXISTS idx_vendor_products_available ON vendor_products(is_available);

-- =============================================================================
-- 2. ALTER PLAN_PHASES - Aggiungere timing intra-giornaliero
-- =============================================================================

-- Timing configurazione: JSON array di orari ["morning", "evening"] o ["08:00", "20:00"]
ALTER TABLE plan_phases ADD COLUMN administration_times TEXT; -- JSON array

-- Mappatura peptide → orario: JSON {"peptide_id_1": "morning", "peptide_id_2": "evening"}
ALTER TABLE plan_phases ADD COLUMN peptide_timing TEXT; -- JSON object

-- Pattern alternativo a 5/2: giorni specifici della settimana
ALTER TABLE plan_phases ADD COLUMN weekday_pattern TEXT; -- JSON array [1,2,3,4,5] per Mon-Fri

-- Dose adjustment per singolo peptide nella fase (override del template)
ALTER TABLE plan_phases ADD COLUMN dose_adjustments TEXT; -- JSON {"peptide_id": {"dose_mcg": 150, "reason": "..."}}

-- =============================================================================
-- 3. CONSUMABLE_DEFAULTS - Prezzi default consumabili (senza vendor)
-- =============================================================================
CREATE TABLE IF NOT EXISTS consumable_defaults (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    consumable_type TEXT NOT NULL UNIQUE, -- 'syringe_1ml', 'needle_29g', 'bac_water_30ml', etc.
    display_name TEXT NOT NULL,
    default_price REAL NOT NULL,
    currency TEXT DEFAULT 'EUR',
    units_per_pack INTEGER DEFAULT 1,
    notes TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert default consumable prices
INSERT OR IGNORE INTO consumable_defaults (consumable_type, display_name, default_price, units_per_pack) VALUES
    ('syringe_1ml', 'Siringa insulina 1ml', 0.15, 1),
    ('syringe_05ml', 'Siringa insulina 0.5ml', 0.15, 1),
    ('needle_29g', 'Ago 29G x 12.7mm', 0.10, 1),
    ('needle_30g', 'Ago 30G x 8mm', 0.10, 1),
    ('needle_31g', 'Ago 31G x 6mm', 0.12, 1),
    ('bac_water_10ml', 'Acqua batteriostatica 10ml', 5.00, 1),
    ('bac_water_30ml', 'Acqua batteriostatica 30ml', 8.00, 1),
    ('alcohol_swab', 'Salvietta alcool', 0.05, 1),
    ('sharps_container', 'Contenitore aghi 1L', 3.00, 1);

-- =============================================================================
-- 4. TREATMENT_PLAN_TEMPLATES - Template completi multi-fase (da libro)
-- =============================================================================
CREATE TABLE IF NOT EXISTS treatment_plan_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Identificazione
    name TEXT NOT NULL UNIQUE,
    short_name TEXT, -- Es. "GH-Recomp", "MetRestore", "AntiAge"
    category TEXT, -- "weight_loss", "body_recomposition", "metabolic", "anti_aging"
    
    -- Profilo candidato
    candidate_profile TEXT, -- JSON con criteri (BMI range, condizioni, etc.)
    
    -- Struttura fasi: JSON array completo
    -- [{phase_number: 1, phase_name: "Foundation", duration_weeks: 4, peptides: [...], ...}]
    phases_config TEXT NOT NULL, -- JSON completo definizione fasi
    
    -- Totali
    total_duration_weeks INTEGER NOT NULL,
    total_phases INTEGER NOT NULL,
    
    -- Expected outcomes
    expected_outcomes TEXT, -- JSON array di outcome attesi
    
    -- Metadata
    source TEXT, -- Es. "Peptide Weight Loss Book", "Custom"
    is_system_template BOOLEAN DEFAULT 0, -- Template di sistema non modificabili
    is_active BOOLEAN DEFAULT 1,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_tpt_category ON treatment_plan_templates(category);
CREATE INDEX IF NOT EXISTS idx_tpt_active ON treatment_plan_templates(is_active);

-- =============================================================================
-- 5. USER_PREFERENCES - Preferenze notifiche e scheduling
-- =============================================================================
CREATE TABLE IF NOT EXISTS user_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    preference_key TEXT NOT NULL UNIQUE,
    preference_value TEXT NOT NULL,
    value_type TEXT DEFAULT 'string', -- 'string', 'int', 'bool', 'json'
    category TEXT DEFAULT 'general', -- 'notifications', 'display', 'general'
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert default notification preferences
INSERT OR IGNORE INTO user_preferences (preference_key, preference_value, value_type, category, description) VALUES
    ('notify_morning_reminder', 'true', 'bool', 'notifications', 'Reminder mattutino giornaliero'),
    ('notify_morning_time', '08:00', 'string', 'notifications', 'Orario reminder mattutino'),
    ('notify_dose_overdue', 'true', 'bool', 'notifications', 'Alert se dose mancata'),
    ('notify_overdue_hours', '4', 'int', 'notifications', 'Ore dopo le quali segnalare dose mancata'),
    ('notify_low_inventory', 'true', 'bool', 'notifications', 'Alert scorte basse'),
    ('notify_low_inventory_weeks', '2', 'int', 'notifications', 'Settimane di scorta minima'),
    ('notify_method', 'toast', 'string', 'notifications', 'Metodo notifica: toast, tray, both'),
    ('currency_default', 'EUR', 'string', 'general', 'Valuta default'),
    ('autosave_drafts', 'true', 'bool', 'general', 'Salvataggio automatico bozze');

-- =============================================================================
-- Migration Complete
-- =============================================================================
SELECT 'Migration 015 completed: Vendor pricing and enhanced phase timing' AS status;
