"""Test HCG appare nei trend peptidi dopo inclusione IU"""
from peptide_manager.janoshik.analytics import JanoshikAnalytics

analytics = JanoshikAnalytics('data/production/peptide_management.db')
trends = analytics.get_hottest_peptides(time_window_days=None, min_certificates=1, limit=50)

hcg = trends[trends['peptide_name'] == 'HCG']

print(f"✅ HCG trovato nei trends: {not hcg.empty}")

if not hcg.empty:
    print("\n📊 Dati HCG:")
    print(hcg[['peptide_name', 'test_count', 'vendor_count', 'avg_purity', 'min_purity', 'max_purity']].to_string(index=False))
    print(f"\n🎯 Avg conformity: {hcg['avg_purity'].iloc[0]:.2f}%")
    print(f"🎯 Min conformity: {hcg['min_purity'].iloc[0]:.2f}%")
    print(f"🎯 Max conformity: {hcg['max_purity'].iloc[0]:.2f}%")
else:
    print("❌ HCG non trovato nei trends - verificare query")
