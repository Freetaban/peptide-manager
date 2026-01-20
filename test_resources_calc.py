"""Test rapido per verificare il calcolo delle risorse"""

from peptide_manager import PeptideManager
from peptide_manager.calculator import ResourcePlanner

# Connetti al database
manager = PeptideManager('data/development/peptide_management.db')
planner = ResourcePlanner(manager.db)

# Test con valori simili allo screenshot:
# BPC-157: 50mg, 10 vials necessarie, 0 stock
# Se 10 vials necessarie e 0 in stock, gap dovrebbe essere 10, non 2!

phases = [
    {
        'phase_name': 'Fase Test',
        'duration_weeks': 20,
        'frequency_per_day': 1,
        'peptides': [
            {
                'peptide_id': 1,  # BPC-157
                'peptide_name': 'BPC-157',
                'dose_mcg': 357,  # Per ottenere circa 50mg totali in 20 settimane
                'mg_per_vial': 5.0,
            }
        ]
    }
]

print("=== DEBUG: DATI PASSATI ===")
print(f"phases[0]['peptides'][0] = {phases[0]['peptides'][0]}")
print()

# Calcola fase singola per vedere i dati intermedi
phase_req = planner.calculate_phase_requirements(phases[0], inventory_check=True)
print("=== DEBUG: RISULTATO calculate_phase_requirements ===")
for p in phase_req['peptides']:
    print(f"  resource_id: {p.get('resource_id')}")
    print(f"  resource_name: {p.get('resource_name')}")
    print(f"  vials_needed: {p.get('vials_needed')}")
    print(f"  vials_available: {p.get('vials_available')}")
    print(f"  vials_gap: {p.get('vials_gap')}")
print()

# Ora calcola totale
resources = planner.calculate_total_plan_resources(phases, inventory_check=True)

print("=== DEBUG: RISULTATO calculate_total_plan_resources ===")
for p in resources['total_peptides']:
    print(f"  resource_id: {p.get('resource_id')}")
    print(f"  resource_name: {p.get('resource_name')}")
    print(f"  vials_needed: {p.get('vials_needed')}")
    print(f"  vials_available: {p.get('vials_available')}")
    print(f"  vials_gap: {p.get('vials_gap')}")
