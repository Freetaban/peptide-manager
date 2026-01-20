"""
Seed Protocol Templates
Popola treatment_plan_templates con i 3 protocolli base del libro.

Protocolli:
1. Protocol 2 - GH Secretagogue Body Recomposition
2. Metabolic Restoration Protocol  
3. Age-Related Decline Protocol

Usage:
    python scripts/seed_protocol_templates.py
    python scripts/seed_protocol_templates.py --db data/development/peptides.db
"""

import argparse
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from peptide_manager import PeptideManager
from peptide_manager.models.treatment_plan_template import TemplateBuilder


def create_gh_secretagogue_template() -> dict:
    """
    Protocol 2 - GH Secretagogue Body Recomposition
    
    Target: Body recomposition, muscle gain, fat loss
    Duration: 24 weeks (4 phases)
    """
    template = TemplateBuilder("Protocol 2 - GH Secretagogue Body Recomp") \
        .with_short_name("GH-Recomp") \
        .with_category("body_recomposition") \
        .with_source("Peptide Weight Loss Book") \
        .as_system_template() \
        .with_candidate_profile(
            goal="body_recomposition",
            bmi_range=[22, 35],
            conditions=["muscle_loss", "fat_gain", "aging"],
            contraindications=["cancer_history", "pregnancy"]
        ) \
        .with_expected_outcomes(
            "Aumento massa magra 2-5 kg",
            "Riduzione grasso corporeo 3-8%",
            "Miglioramento qualità sonno",
            "Aumento energia e recupero",
            "Miglioramento composizione corporea"
        ) \
        .add_phase(
            phase_number=1,
            phase_name="Foundation",
            duration_weeks=4,
            description="Fase iniziale per stabilizzare risposta GH e adattamento metabolico",
            peptides=[
                {"peptide_name": "CJC-1295 DAC", "dose_mcg": 1000},
                {"peptide_name": "Ipamorelin", "dose_mcg": 200},
            ],
            daily_frequency=1,
            five_two_protocol=True,
            administration_times=["evening"]
        ) \
        .add_phase(
            phase_number=2,
            phase_name="Intensification",
            duration_weeks=8,
            description="Fase di intensificazione con doppia somministrazione",
            peptides=[
                {"peptide_name": "CJC-1295 DAC", "dose_mcg": 1000},
                {"peptide_name": "Ipamorelin", "dose_mcg": 300},
                {"peptide_name": "Tesamorelin", "dose_mcg": 2000},
            ],
            daily_frequency=2,
            five_two_protocol=True,
            administration_times=["morning", "evening"]
        ) \
        .add_phase(
            phase_number=3,
            phase_name="Consolidation",
            duration_weeks=8,
            description="Consolidamento dei risultati con focus su recupero",
            peptides=[
                {"peptide_name": "CJC-1295 DAC", "dose_mcg": 1000},
                {"peptide_name": "Ipamorelin", "dose_mcg": 200},
                {"peptide_name": "BPC-157", "dose_mcg": 250},
            ],
            daily_frequency=2,
            five_two_protocol=False,
            administration_times=["morning", "evening"]
        ) \
        .add_phase(
            phase_number=4,
            phase_name="Transition",
            duration_weeks=4,
            description="Fase di transizione per mantenimento",
            peptides=[
                {"peptide_name": "Ipamorelin", "dose_mcg": 200},
            ],
            daily_frequency=1,
            five_two_protocol=True,
            administration_times=["evening"]
        ) \
        .with_notes(
            "Protocollo completo per ricomposizione corporea. "
            "Richiede allenamento di resistenza 3-4x/settimana e "
            "dieta proteica 1.6-2g/kg. Monitorare IGF-1 ogni 8 settimane."
        ) \
        .build()
    
    return template


def create_metabolic_restoration_template() -> dict:
    """
    Metabolic Restoration Protocol
    
    Target: Metabolic dysfunction, insulin resistance, weight loss
    Duration: 16 weeks (3 phases)
    """
    template = TemplateBuilder("Metabolic Restoration Protocol") \
        .with_short_name("MetRestore") \
        .with_category("metabolic") \
        .with_source("Peptide Weight Loss Book") \
        .as_system_template() \
        .with_candidate_profile(
            goal="metabolic_health",
            bmi_range=[25, 40],
            conditions=["insulin_resistance", "metabolic_syndrome", "obesity"],
            contraindications=["type1_diabetes", "pregnancy"]
        ) \
        .with_expected_outcomes(
            "Perdita peso 5-15% del peso iniziale",
            "Miglioramento sensibilità insulinica",
            "Riduzione circonferenza vita",
            "Normalizzazione profilo lipidico",
            "Riduzione infiammazione sistemica"
        ) \
        .add_phase(
            phase_number=1,
            phase_name="Metabolic Reset",
            duration_weeks=4,
            description="Reset metabolico iniziale con focus su sensibilità insulinica",
            peptides=[
                {"peptide_name": "Semaglutide", "dose_mcg": 250},
                {"peptide_name": "BPC-157", "dose_mcg": 250},
            ],
            daily_frequency=1,
            five_two_protocol=False,
            administration_times=["morning"]
        ) \
        .add_phase(
            phase_number=2,
            phase_name="Dose Escalation",
            duration_weeks=8,
            description="Incremento graduale per massimizzare perdita peso",
            peptides=[
                {"peptide_name": "Semaglutide", "dose_mcg": 500},
                {"peptide_name": "Tesamorelin", "dose_mcg": 2000},
                {"peptide_name": "BPC-157", "dose_mcg": 250},
            ],
            daily_frequency=1,
            five_two_protocol=False,
            administration_times=["morning"]
        ) \
        .add_phase(
            phase_number=3,
            phase_name="Maintenance",
            duration_weeks=4,
            description="Mantenimento risultati e transizione",
            peptides=[
                {"peptide_name": "Semaglutide", "dose_mcg": 500},
            ],
            daily_frequency=1,
            five_two_protocol=False,
            administration_times=["morning"]
        ) \
        .with_notes(
            "Protocollo per disfunzione metabolica. "
            "Richiede deficit calorico moderato (500 kcal/giorno) e "
            "attività fisica aerobica 150 min/settimana. "
            "Monitorare HbA1c e profilo lipidico ogni 4 settimane."
        ) \
        .build()
    
    return template


def create_anti_aging_template() -> dict:
    """
    Age-Related Decline Protocol
    
    Target: Aging, cognitive decline, energy, longevity
    Duration: 20 weeks (4 phases)
    """
    template = TemplateBuilder("Age-Related Decline Protocol") \
        .with_short_name("AntiAge") \
        .with_category("anti_aging") \
        .with_source("Peptide Weight Loss Book") \
        .as_system_template() \
        .with_candidate_profile(
            goal="longevity",
            age_range=[40, 75],
            conditions=["aging", "cognitive_decline", "fatigue", "low_energy"],
            contraindications=["cancer_history", "pregnancy", "autoimmune_active"]
        ) \
        .with_expected_outcomes(
            "Miglioramento energia e vitalità",
            "Miglioramento cognitivo e memoria",
            "Miglioramento qualità pelle",
            "Aumento massa muscolare",
            "Miglioramento qualità sonno",
            "Riduzione markers infiammatori"
        ) \
        .add_phase(
            phase_number=1,
            phase_name="Cellular Repair",
            duration_weeks=4,
            description="Avvio riparazione cellulare e riduzione infiammazione",
            peptides=[
                {"peptide_name": "BPC-157", "dose_mcg": 250},
                {"peptide_name": "Thymosin Beta-4", "dose_mcg": 750},
            ],
            daily_frequency=1,
            five_two_protocol=False,
            administration_times=["morning"]
        ) \
        .add_phase(
            phase_number=2,
            phase_name="GH Optimization",
            duration_weeks=8,
            description="Ottimizzazione asse GH per effetti anti-aging",
            peptides=[
                {"peptide_name": "CJC-1295 DAC", "dose_mcg": 1000},
                {"peptide_name": "Ipamorelin", "dose_mcg": 200},
                {"peptide_name": "BPC-157", "dose_mcg": 250},
            ],
            daily_frequency=2,
            five_two_protocol=True,
            administration_times=["morning", "evening"]
        ) \
        .add_phase(
            phase_number=3,
            phase_name="Cognitive Enhancement",
            duration_weeks=4,
            description="Focus su funzione cognitiva e neuroprotezione",
            peptides=[
                {"peptide_name": "Selank", "dose_mcg": 300},
                {"peptide_name": "Semax", "dose_mcg": 600},
                {"peptide_name": "BPC-157", "dose_mcg": 250},
            ],
            daily_frequency=2,
            five_two_protocol=False,
            administration_times=["morning", "afternoon"]
        ) \
        .add_phase(
            phase_number=4,
            phase_name="Maintenance",
            duration_weeks=4,
            description="Protocollo di mantenimento a lungo termine",
            peptides=[
                {"peptide_name": "CJC-1295 DAC", "dose_mcg": 1000},
                {"peptide_name": "BPC-157", "dose_mcg": 250},
            ],
            daily_frequency=1,
            five_two_protocol=True,
            administration_times=["evening"]
        ) \
        .with_notes(
            "Protocollo anti-aging completo. "
            "Combinare con stile di vita ottimale: sonno 7-8h, "
            "esercizio misto (resistenza + aerobico), dieta mediterranea. "
            "Monitorare IGF-1, markers infiammatori e profilo ormonale ogni 8 settimane."
        ) \
        .build()
    
    return template


def seed_templates(db_path: str, force: bool = False):
    """
    Seed protocol templates into database.
    
    Args:
        db_path: Path to database
        force: If True, replace existing templates
    """
    print(f"🌱 Seeding protocol templates to {db_path}")
    
    manager = PeptideManager(db_path)
    
    templates = [
        create_gh_secretagogue_template(),
        create_metabolic_restoration_template(),
        create_anti_aging_template(),
    ]
    
    cursor = manager.db.conn.cursor()
    
    for template in templates:
        # Check if exists
        cursor.execute(
            "SELECT id FROM treatment_plan_templates WHERE name = ?",
            (template.name,)
        )
        existing = cursor.fetchone()
        
        if existing:
            if force:
                # Update existing
                cursor.execute("""
                    UPDATE treatment_plan_templates SET
                        short_name = ?,
                        category = ?,
                        candidate_profile = ?,
                        phases_config = ?,
                        total_duration_weeks = ?,
                        total_phases = ?,
                        expected_outcomes = ?,
                        source = ?,
                        is_system_template = ?,
                        is_active = ?,
                        notes = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE name = ?
                """, (
                    template.short_name,
                    template.category,
                    template.candidate_profile,
                    template.phases_config,
                    template.total_duration_weeks,
                    template.total_phases,
                    template.expected_outcomes,
                    template.source,
                    template.is_system_template,
                    template.is_active,
                    template.notes,
                    template.name
                ))
                print(f"  ♻️  Updated: {template.name}")
            else:
                print(f"  ⏭️  Skipped (exists): {template.name}")
        else:
            # Insert new
            cursor.execute("""
                INSERT INTO treatment_plan_templates (
                    name, short_name, category, candidate_profile,
                    phases_config, total_duration_weeks, total_phases,
                    expected_outcomes, source, is_system_template,
                    is_active, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                template.name,
                template.short_name,
                template.category,
                template.candidate_profile,
                template.phases_config,
                template.total_duration_weeks,
                template.total_phases,
                template.expected_outcomes,
                template.source,
                template.is_system_template,
                template.is_active,
                template.notes
            ))
            print(f"  ✅ Created: {template.name}")
    
    manager.db.conn.commit()
    
    # Verify
    cursor.execute("SELECT COUNT(*) FROM treatment_plan_templates WHERE is_system_template = 1")
    count = cursor.fetchone()[0]
    print(f"\n✅ Total system templates: {count}")
    
    # Show summary
    cursor.execute("""
        SELECT name, short_name, category, total_phases, total_duration_weeks
        FROM treatment_plan_templates
        WHERE is_system_template = 1
        ORDER BY name
    """)
    
    print("\n📋 System Templates:")
    print("-" * 80)
    for row in cursor.fetchall():
        print(f"  {row[0]}")
        print(f"    Short: {row[1]} | Category: {row[2]}")
        print(f"    Phases: {row[3]} | Duration: {row[4]} weeks")
        print()


def main():
    parser = argparse.ArgumentParser(description="Seed protocol templates")
    parser.add_argument(
        "--db",
        default="data/development/peptides.db",
        help="Path to database"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace existing templates"
    )
    
    args = parser.parse_args()
    
    seed_templates(args.db, args.force)


if __name__ == "__main__":
    main()
