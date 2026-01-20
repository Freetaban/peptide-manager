"""
Test basico per Treatment Planner.

Verifica:
- Creazione piano multi-fase
- Calcolo risorse
- Attivazione fase
- Transizione tra fasi
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from peptide_manager import PeptideManager
from datetime import date
import json


def test_treatment_planner():
    """Test completo flusso treatment planner."""
    
    # Usa database development
    db_path = 'data/development/peptide_management.db'
    manager = PeptideManager(db_path)
    
    print("=" * 80)
    print("TEST TREATMENT PLANNER")
    print("=" * 80)
    
    # 1. Crea piano multi-fase (Protocol 2 - GH Secretagogue)
    print("\n[1] Creazione piano multi-fase...")
    
    phases_config = [
        {
            'phase_name': 'Foundation (Weeks 1-4)',
            'duration_weeks': 4,
            'peptides': [
                {
                    'peptide_id': 1,  # Assumo CJC-1295 esista
                    'peptide_name': 'CJC-1295 without DAC',
                    'dose_mcg': 100,
                    'mg_per_vial': 5.0
                },
                {
                    'peptide_id': 2,  # Assumo Ipamorelin esista
                    'peptide_name': 'Ipamorelin',
                    'dose_mcg': 200,
                    'mg_per_vial': 5.0
                }
            ],
            'daily_frequency': 1,
            'five_two_protocol': False,
            'description': 'Foundation phase - once daily before bed'
        },
        {
            'phase_name': 'Intensification (Weeks 5-12)',
            'duration_weeks': 8,
            'peptides': [
                {
                    'peptide_id': 1,
                    'peptide_name': 'CJC-1295 without DAC',
                    'dose_mcg': 100,
                    'mg_per_vial': 5.0
                },
                {
                    'peptide_id': 2,
                    'peptide_name': 'Ipamorelin',
                    'dose_mcg': 200,
                    'mg_per_vial': 5.0
                }
            ],
            'daily_frequency': 2,  # Twice daily
            'five_two_protocol': True,  # 5 days on, 2 days off
            'description': 'Intensification - morning and evening, 5/2 protocol'
        },
        {
            'phase_name': 'Consolidation (Weeks 13-24)',
            'duration_weeks': 12,
            'peptides': [
                {
                    'peptide_id': 1,
                    'peptide_name': 'CJC-1295 without DAC',
                    'dose_mcg': 100,
                    'mg_per_vial': 5.0
                },
                {
                    'peptide_id': 2,
                    'peptide_name': 'Ipamorelin',
                    'dose_mcg': 200,
                    'mg_per_vial': 5.0
                }
            ],
            'daily_frequency': 2,
            'five_two_protocol': True,
            'description': 'Consolidation - cycling and optimization'
        }
    ]
    
    try:
        result = manager.create_treatment_plan(
            name="Protocol 2 - GH Secretagogue Body Recomp",
            start_date=date.today().isoformat(),
            phases_config=phases_config,
            description="Growth hormone secretagogue approach for body recomposition",
            calculate_resources=True
        )
        
        plan_id = result['plan_id']
        print(f" Piano creato con ID: {plan_id}")
        print(f"   Nome: {result['plan']['name']}")
        print(f"   Fasi: {len(result['phases'])}")
        print(f"   Durata totale: {result['plan']['total_planned_days']} giorni")
        
        # Mostra risorse calcolate
        if result['resources']:
            print("\n Risorse calcolate:")
            print(f"   Iniezioni totali: {result['resources']['summary']['total_injections']}")
            
            print("\n   Peptidi necessari:")
            for peptide in result['resources']['total_peptides']:
                gap = peptide.get('vials_gap', 0)
                status = "  DA ORDINARE" if gap > 0 else " Disponibile"
                print(f"   - {peptide['resource_name']}: {peptide['vials_needed']} vials "
                      f"(disponibili: {peptide.get('vials_available', 0)}) {status}")
            
            print("\n   Materiali consumabili:")
            for consumable in result['resources']['total_consumables'][:4]:  # Primi 4
                print(f"   - {consumable['resource_name']}: {consumable['quantity_needed']} "
                      f"{consumable['quantity_unit']}")
        
        # 2. Recupera piano completo
        print("\n2  Recupero piano completo...")
        full_plan = manager.get_treatment_plan(plan_id)
        
        if full_plan:
            print(f" Piano recuperato")
            print(f"   Status: {full_plan['plan']['status']}")
            print(f"   Fasi configurate: {len(full_plan['phases'])}")
            print(f"   Risorse tracciate: {len(full_plan['resources'])}")
            print(f"   Necessita ordini: {'S' if full_plan['needs_ordering'] else 'No'}")
        
        # 3. Attiva Phase 1
        print("\n3  Attivazione Phase 1...")
        activation = manager.activate_plan_phase(
            plan_id=plan_id,
            phase_number=1,
            create_cycle=True
        )
        
        print(f" Fase attivata")
        print(f"   Fase: {activation['phase']['phase_name']}")
        print(f"   Status: {activation['phase']['status']}")
        print(f"   Cycle creato: {'S' if activation['cycle_id'] else 'No'}")
        if activation['cycle_id']:
            print(f"   Cycle ID: {activation['cycle_id']}")
        
        # 4. Simula completamento e transizione
        print("\n4  Simulazione transizione a Phase 2...")
        print("   (Normalmente dopo 4 settimane, qui testiamo solo la logica)")
        
        transition = manager.transition_to_next_phase(plan_id)
        
        print(f" Transizione completata")
        print(f"   Fase completata: {transition['completed_phase']['phase_name']}")
        print(f"   Nuova fase attiva: {transition['activated_phase']['phase_name']}")
        print(f"   Nuovo cycle ID: {transition['new_cycle_id']}")
        print(f"   Piano continua: {'S' if transition['plan_continues'] else 'No'}")
        
        # 5. Lista tutti i piani
        print("\n5  Lista piani attivi...")
        active_plans = manager.list_treatment_plans(status='active')
        
        print(f" Trovati {len(active_plans)} piani attivi")
        for plan in active_plans:
            print(f"   - {plan['name']} (fasi: {plan.get('total_phases', 1)})")
        
        print("\n" + "=" * 80)
        print(" TUTTI I TEST SUPERATI!")
        print("=" * 80)
        
        return True
        
    except Exception as e:
        print(f"\n ERRORE: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        manager.close()


if __name__ == '__main__':
    success = test_treatment_planner()
    sys.exit(0 if success else 1)

