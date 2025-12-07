"""Test get_peptide_rankings da views_logic"""
import sys
sys.path.insert(0, 'scripts')
from peptide_manager.janoshik.views_logic import JanoshikViewsLogic, TimeWindow
from environment import get_environment

env = get_environment()
logic = JanoshikViewsLogic(env.db_path)

print("=" * 70)
print("TEST: JanoshikViewsLogic.get_peptide_rankings()")
print("=" * 70)

# Test TimeWindow.ALL
print("\n1️⃣  TimeWindow.ALL")
print("-" * 70)
rankings = logic.get_peptide_rankings(TimeWindow.ALL, limit=30)
print(f"Peptidi trovati: {len(rankings)}")
if rankings:
    print("\nTop 10:")
    for item in rankings[:10]:
        print(f"#{item.rank:2d} {item.peptide_name:20s} - {item.test_count:3d} test, {item.vendor_count:2d} vendors, {item.popularity_badge}")
else:
    print("❌ NESSUN RISULTATO!")

# Test TimeWindow.YEAR
print("\n\n2️⃣  TimeWindow.YEAR (365 giorni)")
print("-" * 70)
rankings = logic.get_peptide_rankings(TimeWindow.YEAR, limit=30)
print(f"Peptidi trovati: {len(rankings)}")
if rankings:
    print("\nTop 10:")
    for item in rankings[:10]:
        print(f"#{item.rank:2d} {item.peptide_name:20s} - {item.test_count:3d} test")

# Test TimeWindow.QUARTER (default nella GUI)
print("\n\n3️⃣  TimeWindow.QUARTER (90 giorni) - DEFAULT GUI")
print("-" * 70)
rankings = logic.get_peptide_rankings(TimeWindow.QUARTER, limit=30)
print(f"Peptidi trovati: {len(rankings)}")
if rankings:
    print("\nTop 10:")
    for item in rankings[:10]:
        print(f"#{item.rank:2d} {item.peptide_name:20s} - {item.test_count:3d} test")
else:
    print("❌ NESSUN RISULTATO!")

print("\n" + "=" * 70)
