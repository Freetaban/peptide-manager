"""
Test views logic con dati reali.
Verifica che tutti i metodi funzionino prima dell'integrazione GUI.
"""

from peptide_manager.janoshik.views_logic import JanoshikViewsLogic, TimeWindow

def main():
    logic = JanoshikViewsLogic("data/development/peptide_management.db")
    
    print("\n" + "="*80)
    print("🧪 TEST JANOSHIK VIEWS LOGIC")
    print("="*80)
    
    # ==================== VIEW 1: SUPPLIER RANKINGS ====================
    print("\n" + "="*80)
    print("📊 VIEW 1: SUPPLIER RANKINGS")
    print("="*80)
    
    for window in [TimeWindow.MONTH, TimeWindow.QUARTER, TimeWindow.ALL]:
        print(f"\n🕐 {window.label}")
        print("-" * 80)
        
        suppliers = logic.get_supplier_rankings(
            time_window=window,
            min_certificates=2,
            limit=10
        )
        
        stats = logic.get_supplier_ranking_stats(window)
        print(f"Total Vendors: {stats['total_vendors']} | Total Certificates: {stats['total_certificates']} | Avg Purity: {stats['market_avg_purity']:.2f}%")
        print()
        
        if not suppliers:
            print("   ❌ Nessun dato disponibile")
            continue
        
        for s in suppliers[:5]:  # Top 5
            print(f"{s.rank:2d}. {s.supplier_name[:40]:40s} | {s.quality_badge:15s} | {s.activity_badge:12s}")
            print(f"    Certs: {s.total_certificates:3d} | Purity: {s.avg_purity:.2f}% [{s.min_purity:.2f}-{s.max_purity:.2f}]")
            print()
    
    # ==================== VIEW 2: PEPTIDE RANKINGS ====================
    print("\n" + "="*80)
    print("🔬 VIEW 2: PEPTIDE RANKINGS (TRENDING)")
    print("="*80)
    
    for window in [TimeWindow.MONTH, TimeWindow.QUARTER]:
        print(f"\n🕐 {window.label}")
        print("-" * 80)
        
        peptides = logic.get_peptide_rankings(
            time_window=window,
            min_certificates=2,
            limit=10
        )
        
        stats = logic.get_peptide_ranking_stats(window)
        print(f"Unique Peptides: {stats['unique_peptides']} | Total Tests: {stats['total_tests']} | Avg Tests/Peptide: {stats['avg_tests_per_peptide']:.1f}")
        print()
        
        if not peptides:
            print("   ❌ Nessun dato disponibile")
            continue
        
        for p in peptides[:5]:  # Top 5
            print(f"{p.rank:2d}. {p.peptide_name:25s} | {p.popularity_badge:18s}")
            print(f"    Tests: {p.test_count:3d} | Vendors: {p.vendor_count:2d} | Avg Purity: {p.avg_purity:.2f}%")
            print(f"    Most Recent: {logic.format_date_ago(p.most_recent)}")
            print()
    
    # ==================== VIEW 3: VENDOR SEARCH ====================
    print("\n" + "="*80)
    print("🔍 VIEW 3: VENDOR SEARCH PER PEPTIDE")
    print("="*80)
    
    # Test con peptidi comuni
    test_peptides = ["Tirzepatide", "Semaglutide", "Retatrutide", "BPC"]
    
    for peptide in test_peptides:
        print(f"\n🔬 Searching: {peptide}")
        print("-" * 80)
        
        result = logic.search_vendors_for_peptide(
            peptide_name=peptide,
            time_window=TimeWindow.QUARTER
        )
        
        stats = result['stats']
        print(f"Vendors: {stats['total_vendors']} | Certificates: {stats['total_certificates']} | Market Avg: {stats['market_avg_purity']:.2f}%")
        
        if result['best_vendor']:
            best = result['best_vendor']
            print(f"\n🥇 BEST VENDOR: {best['supplier_name']}")
            print(f"   Certificates: {best['certificates']} | Avg Purity: {best['avg_purity']:.2f}%")
            print(f"   Most Recent: {logic.format_date_ago(best['most_recent_test'])}")
        
        print(f"\n📊 All Vendors (top 3):")
        for v in result['all_vendors'][:3]:
            rec_score = v.recommendation_score
            print(f"   {v.rank}. {v.supplier_name[:35]:35s} | Score: {rec_score:5.1f}/100")
            print(f"      Certs: {v.certificates:2d} | Purity: {v.avg_purity:.2f}% | Last: {logic.format_date_ago(v.last_test)}")
        
        print()
    
    # ==================== AUTOCOMPLETE TEST ====================
    print("\n" + "="*80)
    print("💡 AUTOCOMPLETE TEST")
    print("="*80)
    
    test_inputs = ["Tir", "Sem", "BPC", "Ret"]
    
    for inp in test_inputs:
        suggestions = logic.get_peptide_suggestions(inp, limit=5)
        print(f"\nInput: '{inp}' → Suggestions: {', '.join(suggestions) if suggestions else 'None'}")
    
    print("\n" + "="*80)
    print("✅ TEST COMPLETATO")
    print("="*80)


if __name__ == "__main__":
    main()
