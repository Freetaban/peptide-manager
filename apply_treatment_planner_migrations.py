"""
Script to apply Treatment Planner migrations to development database.
"""
import sqlite3
from pathlib import Path

DB_PATH = "data/development/peptide_management.db"

def check_tables():
    """Check which tables exist"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [t[0] for t in cursor.fetchall()]
    conn.close()
    return tables

def apply_migration_012():
    """Migration 012: Add treatment planner base tables"""
    print("\n=== Applying Migration 012: Treatment Planner Base Tables ===")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if already exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='treatment_plans'")
    if cursor.fetchone():
        print("  treatment_plans already exists, skipping...")
        conn.close()
        return
    
    sql = """
    -- Treatment Plans table
    CREATE TABLE IF NOT EXISTS treatment_plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        start_date DATE,
        end_date DATE,
        status TEXT DEFAULT 'draft' CHECK(status IN ('draft', 'active', 'paused', 'completed', 'cancelled')),
        total_phases INTEGER DEFAULT 0,
        current_phase INTEGER DEFAULT 0,
        phases_config TEXT,  -- JSON config for all phases
        resources_summary TEXT,  -- JSON with calculated resources
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    -- Treatment Plan Phases table
    CREATE TABLE IF NOT EXISTS treatment_plan_phases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plan_id INTEGER NOT NULL,
        phase_number INTEGER NOT NULL,
        name TEXT NOT NULL,
        description TEXT,
        start_date DATE,
        end_date DATE,
        duration_weeks INTEGER DEFAULT 4,
        status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'active', 'completed', 'skipped')),
        cycle_id INTEGER,  -- Link to cycles table when activated
        config TEXT,  -- JSON with phase-specific config
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (plan_id) REFERENCES treatment_plans(id) ON DELETE CASCADE,
        FOREIGN KEY (cycle_id) REFERENCES cycles(id) ON DELETE SET NULL
    );

    -- Treatment Plan Phase Peptides (peptides used in each phase)
    CREATE TABLE IF NOT EXISTS treatment_plan_phase_peptides (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phase_id INTEGER NOT NULL,
        peptide_id INTEGER NOT NULL,
        dose_mcg REAL NOT NULL,
        frequency_per_day INTEGER DEFAULT 1,
        notes TEXT,
        FOREIGN KEY (phase_id) REFERENCES treatment_plan_phases(id) ON DELETE CASCADE,
        FOREIGN KEY (peptide_id) REFERENCES peptides(id) ON DELETE CASCADE
    );

    -- Treatment Plan Resources (calculated needs)
    CREATE TABLE IF NOT EXISTS treatment_plan_resources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plan_id INTEGER NOT NULL,
        peptide_id INTEGER NOT NULL,
        total_doses INTEGER NOT NULL,
        total_mcg REAL NOT NULL,
        total_vials_needed REAL NOT NULL,
        vials_in_stock INTEGER DEFAULT 0,
        vials_to_order INTEGER DEFAULT 0,
        estimated_cost REAL,
        FOREIGN KEY (plan_id) REFERENCES treatment_plans(id) ON DELETE CASCADE,
        FOREIGN KEY (peptide_id) REFERENCES peptides(id) ON DELETE CASCADE
    );

    -- Indexes
    CREATE INDEX IF NOT EXISTS idx_treatment_plans_status ON treatment_plans(status);
    CREATE INDEX IF NOT EXISTS idx_treatment_plan_phases_plan ON treatment_plan_phases(plan_id);
    CREATE INDEX IF NOT EXISTS idx_treatment_plan_phases_status ON treatment_plan_phases(status);
    """
    
    cursor.executescript(sql)
    conn.commit()
    conn.close()
    print("  ✅ Migration 012 applied successfully!")

def apply_migration_015():
    """Migration 015: Add vendor pricing and template tables"""
    print("\n=== Applying Migration 015: Vendor Pricing & Templates ===")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if already exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='vendor_products'")
    if cursor.fetchone():
        print("  vendor_products already exists, skipping...")
        conn.close()
        return
    
    sql = """
    -- Vendor Products (pricing per supplier)
    CREATE TABLE IF NOT EXISTS vendor_products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        supplier_id INTEGER NOT NULL,
        peptide_id INTEGER NOT NULL,
        product_name TEXT,
        price_per_vial REAL,
        price_per_mg REAL,
        vial_size_mg REAL,
        currency TEXT DEFAULT 'EUR',
        shipping_cost REAL DEFAULT 0,
        is_available INTEGER DEFAULT 1,
        last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
        notes TEXT,
        FOREIGN KEY (supplier_id) REFERENCES suppliers(id) ON DELETE CASCADE,
        FOREIGN KEY (peptide_id) REFERENCES peptides(id) ON DELETE CASCADE,
        UNIQUE(supplier_id, peptide_id)
    );

    -- Treatment Plan Templates (book protocols)
    CREATE TABLE IF NOT EXISTS treatment_plan_templates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        short_name TEXT,
        description TEXT,
        category TEXT,  -- e.g., 'GH Secretagogue', 'Metabolic', etc.
        source TEXT,  -- e.g., 'William Seeds Book'
        total_phases INTEGER DEFAULT 1,
        total_duration_weeks INTEGER,
        phases_config TEXT NOT NULL,  -- JSON with full phases configuration
        is_active INTEGER DEFAULT 1,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    -- User Preferences for Treatment Planner
    CREATE TABLE IF NOT EXISTS treatment_planner_preferences (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key TEXT NOT NULL UNIQUE,
        value TEXT,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    -- Indexes
    CREATE INDEX IF NOT EXISTS idx_vendor_products_supplier ON vendor_products(supplier_id);
    CREATE INDEX IF NOT EXISTS idx_vendor_products_peptide ON vendor_products(peptide_id);
    CREATE INDEX IF NOT EXISTS idx_templates_category ON treatment_plan_templates(category);
    """
    
    cursor.executescript(sql)
    conn.commit()
    conn.close()
    print("  ✅ Migration 015 applied successfully!")

def seed_protocol_templates():
    """Seed the protocol templates from William Seeds book"""
    print("\n=== Seeding Protocol Templates ===")
    
    import json
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if templates exist
    cursor.execute("SELECT COUNT(*) FROM treatment_plan_templates")
    count = cursor.fetchone()[0]
    if count > 0:
        print(f"  Templates already exist ({count}), skipping...")
        conn.close()
        return
    
    templates = [
        {
            "name": "Protocol 2 - GH Secretagogue Stack",
            "short_name": "GH Secretagogue",
            "description": "CJC-1295/Ipamorelin stack for GH optimization. Classic 5/2 protocol.",
            "category": "GH Optimization",
            "source": "William Seeds - Peptide Protocols",
            "total_phases": 3,
            "total_duration_weeks": 24,
            "phases_config": json.dumps([
                {
                    "phase_name": "Loading Phase",
                    "duration_weeks": 4,
                    "daily_frequency": 2,
                    "five_two_protocol": True,
                    "administration_times": ["morning", "evening"],
                    "weekday_pattern": [1, 2, 3, 4, 5],
                    "peptides": [
                        {"peptide_name": "CJC-1295 DAC", "dose_mcg": 100},
                        {"peptide_name": "Ipamorelin", "dose_mcg": 200}
                    ],
                    "description": "Initial loading to establish baseline"
                },
                {
                    "phase_name": "Optimization Phase",
                    "duration_weeks": 12,
                    "daily_frequency": 2,
                    "five_two_protocol": True,
                    "administration_times": ["morning", "evening"],
                    "weekday_pattern": [1, 2, 3, 4, 5],
                    "peptides": [
                        {"peptide_name": "CJC-1295 DAC", "dose_mcg": 100},
                        {"peptide_name": "Ipamorelin", "dose_mcg": 200}
                    ],
                    "description": "Main optimization period"
                },
                {
                    "phase_name": "Maintenance Phase",
                    "duration_weeks": 8,
                    "daily_frequency": 1,
                    "five_two_protocol": True,
                    "administration_times": ["evening"],
                    "weekday_pattern": [1, 2, 3, 4, 5],
                    "peptides": [
                        {"peptide_name": "CJC-1295 DAC", "dose_mcg": 100},
                        {"peptide_name": "Ipamorelin", "dose_mcg": 200}
                    ],
                    "description": "Reduced frequency maintenance"
                }
            ])
        },
        {
            "name": "Protocol 7 - Metabolic Restoration",
            "short_name": "Metabolic",
            "description": "Tesamorelin-based protocol for metabolic optimization and visceral fat reduction.",
            "category": "Metabolic",
            "source": "William Seeds - Peptide Protocols",
            "total_phases": 2,
            "total_duration_weeks": 16,
            "phases_config": json.dumps([
                {
                    "phase_name": "Active Phase",
                    "duration_weeks": 12,
                    "daily_frequency": 1,
                    "five_two_protocol": False,
                    "administration_times": ["morning"],
                    "weekday_pattern": [1, 2, 3, 4, 5, 6, 7],
                    "peptides": [
                        {"peptide_name": "Tesamorelin", "dose_mcg": 2000}
                    ],
                    "description": "Daily administration for metabolic reset"
                },
                {
                    "phase_name": "Consolidation Phase",
                    "duration_weeks": 4,
                    "daily_frequency": 1,
                    "five_two_protocol": True,
                    "administration_times": ["morning"],
                    "weekday_pattern": [1, 2, 3, 4, 5],
                    "peptides": [
                        {"peptide_name": "Tesamorelin", "dose_mcg": 2000}
                    ],
                    "description": "Reduced frequency to maintain results"
                }
            ])
        },
        {
            "name": "Protocol 11 - Age-Related Decline",
            "short_name": "Anti-Aging",
            "description": "Comprehensive protocol addressing multiple age-related markers.",
            "category": "Longevity",
            "source": "William Seeds - Peptide Protocols",
            "total_phases": 4,
            "total_duration_weeks": 24,
            "phases_config": json.dumps([
                {
                    "phase_name": "Foundation",
                    "duration_weeks": 4,
                    "daily_frequency": 1,
                    "five_two_protocol": True,
                    "administration_times": ["evening"],
                    "weekday_pattern": [1, 2, 3, 4, 5],
                    "peptides": [
                        {"peptide_name": "Ipamorelin", "dose_mcg": 200},
                        {"peptide_name": "CJC-1295 DAC", "dose_mcg": 100}
                    ],
                    "description": "Establish GH baseline"
                },
                {
                    "phase_name": "Enhancement",
                    "duration_weeks": 8,
                    "daily_frequency": 2,
                    "five_two_protocol": True,
                    "administration_times": ["morning", "evening"],
                    "weekday_pattern": [1, 2, 3, 4, 5],
                    "peptides": [
                        {"peptide_name": "Ipamorelin", "dose_mcg": 200},
                        {"peptide_name": "CJC-1295 DAC", "dose_mcg": 100},
                        {"peptide_name": "BPC-157", "dose_mcg": 250}
                    ],
                    "description": "Add healing peptide for tissue repair"
                },
                {
                    "phase_name": "Optimization",
                    "duration_weeks": 8,
                    "daily_frequency": 2,
                    "five_two_protocol": True,
                    "administration_times": ["morning", "evening"],
                    "weekday_pattern": [1, 2, 3, 4, 5],
                    "peptides": [
                        {"peptide_name": "Ipamorelin", "dose_mcg": 200},
                        {"peptide_name": "CJC-1295 DAC", "dose_mcg": 100}
                    ],
                    "description": "Peak optimization period"
                },
                {
                    "phase_name": "Maintenance",
                    "duration_weeks": 4,
                    "daily_frequency": 1,
                    "five_two_protocol": True,
                    "administration_times": ["evening"],
                    "weekday_pattern": [1, 2, 3, 4, 5],
                    "peptides": [
                        {"peptide_name": "Ipamorelin", "dose_mcg": 200}
                    ],
                    "description": "Long-term maintenance protocol"
                }
            ])
        }
    ]
    
    for t in templates:
        cursor.execute("""
            INSERT INTO treatment_plan_templates 
            (name, short_name, description, category, source, total_phases, total_duration_weeks, phases_config)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            t["name"], t["short_name"], t["description"], t["category"],
            t["source"], t["total_phases"], t["total_duration_weeks"], t["phases_config"]
        ))
    
    conn.commit()
    conn.close()
    print(f"  ✅ Seeded {len(templates)} protocol templates!")

def main():
    print("=" * 60)
    print("Treatment Planner Migration Script")
    print("=" * 60)
    
    # Check current state
    print("\n1. Checking current database state...")
    tables = check_tables()
    print(f"   Found {len(tables)} tables")
    print(f"   treatment_plans: {'✅' if 'treatment_plans' in tables else '❌'}")
    print(f"   vendor_products: {'✅' if 'vendor_products' in tables else '❌'}")
    print(f"   treatment_plan_templates: {'✅' if 'treatment_plan_templates' in tables else '❌'}")
    
    # Apply migrations
    print("\n2. Applying migrations...")
    apply_migration_012()
    apply_migration_015()
    
    # Seed templates
    print("\n3. Seeding templates...")
    seed_protocol_templates()
    
    # Final check
    print("\n4. Final verification...")
    tables = check_tables()
    print(f"   treatment_plans: {'✅' if 'treatment_plans' in tables else '❌'}")
    print(f"   vendor_products: {'✅' if 'vendor_products' in tables else '❌'}")
    print(f"   treatment_plan_templates: {'✅' if 'treatment_plan_templates' in tables else '❌'}")
    
    # Check templates count
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM treatment_plan_templates")
    count = cursor.fetchone()[0]
    conn.close()
    print(f"   Templates count: {count}")
    
    print("\n" + "=" * 60)
    print("✅ Migration completed successfully!")
    print("=" * 60)

if __name__ == "__main__":
    main()
