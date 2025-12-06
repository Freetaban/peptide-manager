"""Test scoring completo con 6 componenti"""
import sys
from pathlib import Path

# Add project root to path
root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root))
sys.path.insert(0, str(root / 'scripts'))

from peptide_manager.janoshik.analytics import JanoshikAnalytics
from environment import get_environment

# Usa development DB
env = get_environment('development')
analytics = JanoshikAnalytics(str(env.db_path))

print("="*80)
print("TEST SCORING COMPLETO (6 COMPONENTI)")
print("="*80)
print("\nComponenti:")
print("  • Volume (20%): Numero certificati + attività recente")
print("  • Quality (25%): Purezza media e minima")
print("  • Accuracy (20%): Accuratezza quantità dichiarata vs testata")
print("  • Consistency (15%): Variabilità purezza")
print("  • Recency (10%): Attività recente")
print("  • Testing Completeness (10%): Test completi\n")

# Carica top vendors
print("🔄 Caricamento top 10 vendors (min 3 certificati)...\n")
rankings = analytics.get_top_vendors(time_window_days=None, min_certificates=3, limit=10)

if rankings.empty:
    print("❌ Nessun vendor trovato")
else:
    print(f"✅ {len(rankings)} vendors trovati\n")
    print("="*80)
    print("TOP 10 SUPPLIERS")
    print("="*80)
    
    for idx, row in rankings.iterrows():
        print(f"\n#{int(idx+1)} - {row['supplier_name']}")
        print(f"  📊 Score Totale: {row['composite_score']:.1f}/100")
        print(f"  📦 Certificati: {int(row['total_certificates'])}")
        print(f"  ✨ Purezza: {row['avg_purity']:.2f}% (min: {row['min_purity']:.2f}%, max: {row['max_purity']:.2f}%)")
        
        # Mostra componenti score se disponibili
        if 'volume_score' in row:
            print(f"  🔢 Volume: {row['volume_score']:.1f}/100")
        if 'quality_score' in row:
            print(f"  💎 Quality: {row['quality_score']:.1f}/100")
        if 'accuracy_score' in row:
            print(f"  🎯 Accuracy: {row['accuracy_score']:.1f}/100")
        if 'consistency_score' in row:
            print(f"  📈 Consistency: {row['consistency_score']:.1f}/100")
        if 'recency_score' in row:
            print(f"  ⏰ Recency: {row['recency_score']:.1f}/100")
        if 'testing_completeness_score' in row:
            print(f"  🧪 Testing: {row['testing_completeness_score']:.1f}/100")
        
        print(f"  🗓️  Ultimo test: {row['days_since_last_test']:.0f} giorni fa")

print("\n" + "="*80)
