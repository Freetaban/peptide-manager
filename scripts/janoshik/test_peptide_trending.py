"""Test peptidi trending con nuova query"""
import sys
sys.path.insert(0, 'scripts')
from peptide_manager.janoshik.analytics import JanoshikAnalytics
from environment import get_environment

env = get_environment()
analytics = JanoshikAnalytics(env.db_path)

print("=" * 70)
print("TEST: Peptidi Trending con finestre temporali diverse")
print("=" * 70)

# Test 1: Tutti i tempi
print("\n1️⃣  TUTTI I TEMPI (time_window_days=None)")
print("-" * 70)
df = analytics.get_hottest_peptides(time_window_days=None, min_certificates=2, limit=30)
print(f"Peptidi trovati: {len(df)}")
print("\nTop 15:")
for idx, row in df.head(15).iterrows():
    print(f"#{idx+1:2d} {row['peptide_name']:20s} - {row['test_count']:3d} test, {row['vendor_count']:2d} vendors, {row['avg_purity']:.2f}% purezza")

# Test 2: Ultimo trimestre (90 giorni)
print("\n\n2️⃣  ULTIMO TRIMESTRE (90 giorni)")
print("-" * 70)
df = analytics.get_hottest_peptides(time_window_days=90, min_certificates=2, limit=30)
print(f"Peptidi trovati: {len(df)}")
print("\nTop 10:")
for idx, row in df.head(10).iterrows():
    print(f"#{idx+1:2d} {row['peptide_name']:20s} - {row['test_count']:3d} test, {row['vendor_count']:2d} vendors")

# Test 3: Ultimo mese
print("\n\n3️⃣  ULTIMO MESE (30 giorni)")
print("-" * 70)
df = analytics.get_hottest_peptides(time_window_days=30, min_certificates=2, limit=30)
print(f"Peptidi trovati: {len(df)}")
if not df.empty:
    print("\nTop 10:")
    for idx, row in df.head(10).iterrows():
        print(f"#{idx+1:2d} {row['peptide_name']:20s} - {row['test_count']:3d} test")
else:
    print("❌ Nessun peptide trovato nell'ultimo mese (pochi certificati recenti)")

print("\n" + "=" * 70)
print("✅ Test completato!")
print("=" * 70)
