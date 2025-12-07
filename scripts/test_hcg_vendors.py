"""Test vendor search per HCG"""
from peptide_manager.janoshik.analytics import JanoshikAnalytics

analytics = JanoshikAnalytics('data/production/peptide_management.db')
vendors = analytics.get_peptide_vendors(peptide_name='HCG', time_window_days=None)

print(f"✅ Vendors per HCG: {len(vendors)}")

if not vendors.empty:
    print("\n📊 Dati Vendors HCG:")
    print(vendors[['supplier_name', 'certificates', 'avg_purity', 'min_purity', 'max_purity', 'last_test']].to_string(index=False))
    print(f"\n🏆 Best vendor: {vendors.iloc[0]['supplier_name']} con avg conformity {vendors.iloc[0]['avg_purity']:.2f}%")
else:
    print("❌ Nessun vendor trovato per HCG")
