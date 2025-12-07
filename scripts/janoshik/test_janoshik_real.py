"""
Test reale - Scraping 1 pagina Janoshik con GPT-4o
"""

from peptide_manager.janoshik import JanoshikManager, LLMProvider

print("=" * 70)
print("Test REALE - Scraping Janoshik + GPT-4o Extraction (50 Certs)")
print("=" * 70)

# Initialize manager
manager = JanoshikManager(
    db_path="data/development/peptide_management.db",
    llm_provider=LLMProvider.GPT4O
)

print("\n🌐 Avvio scraping + extraction (50 certificati per validazione)...")
print("   Questo richiederà ~3-5 minuti per processare tutte le immagini\n")

try:
    result = manager.run_full_update(max_pages=1, max_certificates=50)
    
    print("\n✓ Completato!")
    print(f"\n📊 Risultati:")
    print(f"   Certificati scraped: {result['certificates_scraped']}")
    print(f"   Certificati nuovi: {result['certificates_new']}")
    print(f"   Certificati estratti: {result['certificates_extracted']}")
    print(f"   Rankings calcolati: {result['rankings_calculated']}")
    
    if result['certificates_scraped'] == 0:
        print("\n⚠️ Nessun certificato trovato sul sito Janoshik")
        print("   Verifica connessione internet e URL del sito")
    elif result['top_supplier']:
        # Show latest rankings
        print(f"\n🏆 Top Supplier: {result['top_supplier']}")
        print("\nTop 5 Suppliers:")
        rankings = manager.get_latest_rankings(limit=5)
        for i, rank in enumerate(rankings, 1):
            print(f"   {i}. {rank.supplier_name}: {rank.total_score:.2f} punti")
            print(f"      Certificati: {rank.total_certificates}, "
                  f"Purezza: {rank.avg_purity:.1f}%, "
                  f"Giorni ultimo cert: {rank.days_since_last_cert}")
        
        # Export
        export_file = manager.export_rankings_to_csv("data/exports/janoshik_test.csv")
        print(f"\n💾 Esportato in: {export_file}")
    
except Exception as e:
    print(f"\n❌ Errore: {e}")
    import traceback
    traceback.print_exc()
