"""
Esempio 2: Calcoli di diluizione
"""

from peptide_manager.calculator import DilutionCalculator

calc = DilutionCalculator()

print("=== ESEMPIO 1: Diluizione singolo peptide ===")
# Ho 5mg di BPC-157, voglio 2.5mg/ml
volume = calc.calculate_dilution(5.0, 2.5)
print(f"Volume BAC water necessario: {volume}ml")
print(f"Risultato: 5mg in {volume}ml = 2.5mg/ml")

print("\n=== ESEMPIO 2: Conversione dose ===")
# Voglio iniettare 250mcg, concentrazione 2.5mg/ml
ml_needed = calc.mcg_to_ml(250, 2.5)
print(f"Per 250mcg con 2.5mg/ml serve: {ml_needed}ml")

print("\n=== ESEMPIO 3: Calcolo dosi disponibili ===")
# Ho preparato 5mg in 2ml, dose da 250mcg
doses = calc.doses_from_preparation(5.0, 2.0, 250)
print(f"Dosi disponibili: {doses}")

print("\n=== ESEMPIO 4: Suggerimento diluizione ottimale ===")
# Ho 10mg, voglio dosi da 500mcg, preferenza 0.2ml per iniezione
suggestion = calc.suggested_dilution_for_dose(10.0, 500, 0.2)
print(f"Diluizione suggerita:")
print(f"  - Volume diluente: {suggestion['volume_diluente_ml']}ml")
print(f"  - Concentrazione: {suggestion['concentrazione_mg_ml']}mg/ml")
print(f"  - Volume per dose: {suggestion['volume_per_dose_ml']}ml")
print(f"  - Dosi totali: {suggestion['dosi_totali']}")

print("\n=== ESEMPIO 5: Blend di peptidi ===")
# BPC-157 5mg + TB-500 5mg, voglio 2.5mg/ml di ciascuno
peptides = [('BPC-157', 5.0), ('TB-500', 5.0)]
targets = {'BPC-157': 2.5, 'TB-500': 2.5}
volume = calc.calculate_blend_dilution(peptides, targets)
print(f"Volume per blend: {volume}ml")
print(f"Concentrazione finale: BPC 2.5mg/ml + TB 2.5mg/ml")
