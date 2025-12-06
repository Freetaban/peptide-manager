"""
Test nuovo algoritmo accuracy con outlier detection e penalità asimmetriche
"""
import pandas as pd
import numpy as np

# Simula diversi scenari
test_cases = [
    # (dichiarato, testato, descrizione)
    (10, 10.0, "Perfetto 0%"),
    (10, 10.5, "Positivo +5%"),
    (10, 11.0, "Positivo +10%"),
    (10, 11.5, "Positivo +15%"),
    (10, 12.0, "Positivo +20%"),
    (10, 13.0, "Positivo +30%"),
    (10, 14.0, "Positivo +40%"),
    (10, 9.95, "Negativo -0.5%"),
    (10, 9.9, "Negativo -1%"),
    (10, 9.5, "Negativo -5%"),
    (10, 9.0, "Negativo -10%"),
    (10, 8.5, "Negativo -15%"),
    (10, 8.0, "Negativo -20%"),
    (10, 7.5, "Negativo -25%"),
    (20, 50.39, "OUTLIER +152%"),
    (10, 106.64, "OUTLIER +966%"),
]

print("=" * 80)
print("TEST ALGORITMO ACCURACY - Metrica Continua")
print("=" * 80)

def calculate_accuracy_new(declared, tested):
    """Metrica continua: negativo=penalità, positivo=bonus"""
    deviation_pct = ((tested - declared) / declared) * 100
    
    # Outlier detection: ±50%
    if abs(deviation_pct) > 50:
        return None  # Escluso dal calcolo
    
    if deviation_pct == 0:
        return 100.0
    elif deviation_pct < 0:
        # Negativo: -2 punti per ogni 1%
        penalty = abs(deviation_pct) * 2
        return max(0, 100 - penalty)
    else:
        # Positivo: +1 punto per ogni 1% (cap 120)
        bonus = deviation_pct * 1
        return min(120, 100 + bonus)

print("\nRisultati:")
print("-" * 80)
for declared, tested, desc in test_cases:
    deviation_pct = ((tested - declared) / declared) * 100
    accuracy = calculate_accuracy_new(declared, tested)
    
    if accuracy is None:
        status = "❌ OUTLIER (escluso)"
        score_str = "N/A"
    elif accuracy >= 110:
        status = "🟢 OTTIMO BONUS"
        score_str = f"{accuracy:.1f}"
    elif accuracy >= 100:
        status = "✅ ECCELLENTE"
        score_str = f"{accuracy:.1f}"
    elif accuracy >= 90:
        status = "🟡 BUONO"
        score_str = f"{accuracy:.1f}"
    elif accuracy >= 80:
        status = "🟠 ACCETTABILE"
        score_str = f"{accuracy:.1f}"
    elif accuracy >= 60:
        status = "🔴 SCARSO"
        score_str = f"{accuracy:.1f}"
    else:
        status = "💀 PESSIMO"
        score_str = f"{accuracy:.1f}"
    
    print(f"{desc:30s} | {declared:5.1f}mg → {tested:7.2f}mg ({deviation_pct:+7.1f}%) | Score: {score_str:5s} {status}")

print("\n" + "=" * 80)
print("Logica Algoritmo:")
print("  • 0% scostamento = 100 punti (perfetto)")
print("  • Scostamento NEGATIVO: -2 punti per ogni 1% (-10% = 80 pts, -20% = 60 pts)")
print("  • Scostamento POSITIVO: +1 punto per ogni 1% (+10% = 110 pts, +20% = 120 pts)")
print("  • Outliers (>±50%): esclusi dal calcolo (probabili mislabeling)")
print("=" * 80)
