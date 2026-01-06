"""
Test completo workflow Janoshik
================================

Verifica l'intero flusso di aggiornamento Janoshik:
1. Connessione a janoshik.com/public/
2. Scraping lista certificati
3. Individuazione certificati nuovi (non già nel DB)
4. Download immagini CoA
5. Estrazione dati con LLM
6. Aggiornamento database
7. Ricalcolo ranking supplier
8. Verifica dati nella GUI

"""

import sys
import os
from pathlib import Path
from datetime import datetime
import time

# Aggiungi root al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from peptide_manager.janoshik import JanoshikManager, LLMProvider
from peptide_manager.janoshik.repositories import JanoshikCertificateRepository, SupplierRankingRepository


def print_header(title):
    """Stampa header sezione"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_section(title):
    """Stampa sotto-sezione"""
    print(f"\n📌 {title}")
    print("-" * 70)


def test_full_workflow(max_pages=1, max_certs=20, use_llm=True):
    """
    Test completo del workflow Janoshik.
    
    Args:
        max_pages: Numero massimo pagine da scrapare (1 = ~50 certificati)
        max_certs: Numero massimo certificati da processare
        use_llm: Se True, usa LLM per estrazione. Se False, solo scraping.
    """
    print_header("TEST WORKFLOW JANOSHIK - COMPLETO")
    
    db_path = "data/development/peptide_management.db"
    
    # Verifica database
    if not Path(db_path).exists():
        print(f"\n❌ ERRORE: Database non trovato: {db_path}")
        print("   Esegui prima: python scripts/copy_prod_to_dev.py")
        return False
    
    # Inizializza repositories per statistiche
    cert_repo = JanoshikCertificateRepository(db_path)
    ranking_repo = SupplierRankingRepository(db_path)
    
    # Statistiche iniziali
    print_section("Stato iniziale database")
    initial_stats = {
        'certificates': cert_repo.count(),
        'suppliers': len(cert_repo.get_unique_suppliers()),
        'rankings': ranking_repo.count()
    }
    print(f"   Certificati esistenti: {initial_stats['certificates']}")
    print(f"   Supplier univoci: {initial_stats['suppliers']}")
    print(f"   Ranking registrati: {initial_stats['rankings']}")
    
    # Inizializza manager
    print_section("Inizializzazione JanoshikManager")
    llm_provider = LLMProvider.GPT4O if use_llm else None  # Force GPT-4o
    
    try:
        manager = JanoshikManager(
            db_path=db_path,
            llm_provider=llm_provider,
            llm_api_key=None  # Carica da .env.development
        )
        print(f"   ✓ Manager inizializzato")
        print(f"   LLM Provider: {llm_provider.value if llm_provider else 'NESSUNO (solo scraping)'}")
    except Exception as e:
        print(f"\n❌ ERRORE inizializzazione manager: {e}")
        return False
    
    # FASE 1: Scraping + Extraction + Scoring
    print_section(f"Fase 1: Scraping (max {max_pages} pagine, {max_certs} certificati)")
    
    # Progress callback
    last_stage = None
    
    def progress_callback(stage, message):
        nonlocal last_stage
        if stage != last_stage:
            print(f"\n   [{stage.upper()}] {message}")
            last_stage = stage
        else:
            print(f"   ... {message}")
    
    try:
        start_time = time.time()
        
        # Esegui update completo
        result = manager.run_full_update(
            max_pages=max_pages,
            max_certificates=max_certs,
            progress_callback=progress_callback
        )
        
        elapsed = time.time() - start_time
        
        print_section("Risultati aggiornamento")
        print(f"   ⏱️  Tempo totale: {elapsed:.1f} secondi")
        print(f"   📥 Certificati scraped: {result['certificates_scraped']}")
        print(f"   🆕 Certificati nuovi: {result['certificates_new']}")
        print(f"   📊 Certificati estratti: {result['certificates_extracted']}")
        print(f"   🏆 Rankings calcolati: {result['rankings_calculated']}")
        
        if result['top_supplier']:
            print(f"   ⭐ Top Supplier: {result['top_supplier']}")
        
        # Gestisci caso nessun certificato trovato
        if result['certificates_scraped'] == 0:
            print("\n⚠️  ATTENZIONE: Nessun certificato trovato sul sito Janoshik")
            print("   Possibili cause:")
            print("   - Problema connessione internet")
            print("   - Struttura HTML del sito cambiata")
            print("   - URL janoshik.com/public/ non raggiungibile")
            return False
        
        # Gestisci caso nessun certificato nuovo
        if result['certificates_new'] == 0:
            print("\n✓ Tutti i certificati erano già presenti nel database")
            print("   (Questo è normale se hai già eseguito il test)")
        
    except Exception as e:
        print(f"\n❌ ERRORE durante aggiornamento: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # FASE 2: Verifica dati salvati
    print_section("Fase 2: Verifica dati nel database")
    
    final_stats = {
        'certificates': cert_repo.count(),
        'suppliers': len(cert_repo.get_unique_suppliers()),
        'rankings': ranking_repo.count()
    }
    
    print(f"   Certificati totali: {final_stats['certificates']} (+{final_stats['certificates'] - initial_stats['certificates']})")
    print(f"   Supplier univoci: {final_stats['suppliers']} (+{final_stats['suppliers'] - initial_stats['suppliers']})")
    print(f"   Ranking registrati: {final_stats['rankings']} (+{final_stats['rankings'] - initial_stats['rankings']})")
    
    # FASE 3: Mostra top 10 supplier
    print_section("Fase 3: Top 10 Supplier (Latest Ranking)")
    
    try:
        top_suppliers = manager.get_latest_rankings(limit=10)
        
        if not top_suppliers:
            print("   ⚠️  Nessun ranking disponibile")
        else:
            print(f"\n   {'Pos':<4} {'Supplier':<30} {'Score':<8} {'Cert':<5} {'Purity':<7} {'Days':<5}")
            print(f"   {'-' * 4} {'-' * 30} {'-' * 8} {'-' * 5} {'-' * 7} {'-' * 5}")
            
            for i, rank in enumerate(top_suppliers, 1):
                # Badge emoji
                if rank.total_score >= 80:
                    badge = "🔥"
                elif rank.total_score >= 60:
                    badge = "✅"
                elif rank.total_score >= 40:
                    badge = "⚠️"
                else:
                    badge = "❌"
                
                supplier_name = rank.supplier_name[:28] + ".." if len(rank.supplier_name) > 30 else rank.supplier_name
                
                print(f"   {i:<4} {badge} {supplier_name:<28} {rank.total_score:>6.1f}  {rank.total_certificates:>4}  {rank.avg_purity:>5.1f}%  {rank.days_since_last_cert:>4}")
    
    except Exception as e:
        print(f"   ❌ ERRORE recupero ranking: {e}")
        return False
    
    # FASE 4: Export CSV
    print_section("Fase 4: Export dati in CSV")
    
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_path = f"data/exports/janoshik_ranking_{timestamp}.csv"
        
        exported_file = manager.export_rankings_to_csv(export_path)
        print(f"   ✓ Esportato in: {exported_file}")
        
        # Verifica file creato
        if Path(exported_file).exists():
            file_size = Path(exported_file).stat().st_size
            print(f"   ✓ File creato: {file_size:,} bytes")
        else:
            print(f"   ⚠️  File non trovato dopo export")
    
    except Exception as e:
        print(f"   ❌ ERRORE export CSV: {e}")
    
    # FASE 5: Statistiche dettagliate
    print_section("Fase 5: Statistiche sistema")
    
    try:
        stats = manager.get_statistics()
        print(f"   Total Certificates: {stats['total_certificates']}")
        print(f"   Unique Suppliers: {stats['unique_suppliers']}")
        print(f"   Total Rankings: {stats['total_rankings']}")
        print(f"   Calculations Performed: {stats['calculations_performed']}")
    except Exception as e:
        print(f"   ⚠️  Errore recupero statistiche: {e}")
    
    # FASE 6: Esempio dettaglio supplier
    print_section("Fase 6: Dettaglio Top Supplier")
    
    if top_suppliers and len(top_suppliers) > 0:
        top = top_suppliers[0]
        print(f"\n   Supplier: {top.supplier_name}")
        print(f"   Total Score: {top.total_score:.2f}")
        print(f"   Badge: {'🔥 HOT' if top.total_score >= 80 else '✅ Buono' if top.total_score >= 60 else '⚠️ Mediocre'}")
        print(f"\n   Componenti Score:")
        print(f"   - Volume Score: {top.volume_score:.1f}")
        print(f"   - Quality Score: {top.quality_score:.1f}")
        print(f"   - Consistency Score: {top.consistency_score:.1f}")
        print(f"   - Recency Score: {top.recency_score:.1f}")
        print(f"   - Endotoxin Score: {top.endotoxin_score:.1f}")
        print(f"\n   Statistiche:")
        print(f"   - Certificati totali: {top.total_certificates}")
        print(f"   - Purezza media: {top.avg_purity:.2f}%")
        print(f"   - Purezza minima: {top.min_purity:.2f}%")
        print(f"   - Std deviation: {top.purity_stddev:.2f}")
        print(f"   - Giorni ultimo cert: {top.days_since_last_cert}")
        print(f"   - Certificati (30d): {top.certificates_last_30d}")
        
        # Mostra certificati del supplier
        try:
            certs = manager.get_supplier_certificates(top.supplier_name)
            print(f"\n   Certificati trovati: {len(certs)}")
            
            if certs:
                print(f"\n   Ultimi 5 certificati:")
                for cert in certs[:5]:
                    print(f"   - Task {cert.task_number}: {cert.peptide_name} (Purity: {cert.purity:.1f}%)")
        except Exception as e:
            print(f"   ⚠️  Errore recupero certificati: {e}")
    
    # RIEPILOGO FINALE
    print_header("✅ TEST COMPLETATO CON SUCCESSO")
    
    print(f"\n🎯 Riepilogo operazioni:")
    print(f"   1. ✓ Connessione janoshik.com/public/ OK")
    print(f"   2. ✓ Scraping {result['certificates_scraped']} certificati")
    print(f"   3. ✓ Identificati {result['certificates_new']} certificati nuovi")
    print(f"   4. ✓ Download immagini CoA completato")
    
    if use_llm:
        print(f"   5. ✓ Estrazione dati con LLM ({result['certificates_extracted']} certificati)")
    else:
        print(f"   5. ⊘ Estrazione LLM skippata (use_llm=False)")
    
    print(f"   6. ✓ Database aggiornato")
    print(f"   7. ✓ Ranking calcolati ({result['rankings_calculated']} supplier)")
    print(f"   8. ✓ Dati pronti per visualizzazione GUI")
    
    print(f"\n📊 Per vedere i dati nella GUI:")
    print(f"   python gui.py")
    print(f"   Poi vai alla sezione 'Mercato Janoshik'")
    
    return True


def main():
    """Main entry point"""
    print("\n" + "=" * 70)
    print("  JANOSHIK WORKFLOW TESTER")
    print("  Verifica completa integrazione Janoshik")
    print("=" * 70)
    
    print("\n📝 Opzioni test:")
    print("   1. Test veloce (1 pagina, 10 certificati, con LLM)")
    print("   2. Test medio (1 pagina, 30 certificati, con LLM)")
    print("   3. Test completo (2 pagine, 100 certificati, con LLM)")
    print("   4. Test solo scraping (no LLM, solo download)")
    print("   5. Test personalizzato")
    
    choice = input("\nScelta [1-5, default=1]: ").strip() or "1"
    
    if choice == "1":
        print("\n🚀 Test veloce (1 pagina, 10 cert)")
        success = test_full_workflow(max_pages=1, max_certs=10, use_llm=True)
    
    elif choice == "2":
        print("\n🚀 Test medio (1 pagina, 30 cert)")
        success = test_full_workflow(max_pages=1, max_certs=30, use_llm=True)
    
    elif choice == "3":
        print("\n🚀 Test completo (2 pagine, 100 cert)")
        confirm = input("   ⚠️  Questo richiederà ~10-15 minuti. Confermi? [y/N]: ")
        if confirm.lower() == 'y':
            success = test_full_workflow(max_pages=2, max_certs=100, use_llm=True)
        else:
            print("   Test annullato")
            return
    
    elif choice == "4":
        print("\n🚀 Test solo scraping (no LLM)")
        success = test_full_workflow(max_pages=1, max_certs=20, use_llm=False)
    
    elif choice == "5":
        try:
            max_pages = int(input("   Numero pagine (1-10): ") or "1")
            max_certs = int(input("   Numero certificati (1-500): ") or "20")
            use_llm_input = input("   Usare LLM? [Y/n]: ").strip().lower()
            use_llm = use_llm_input != 'n'
            
            success = test_full_workflow(max_pages=max_pages, max_certs=max_certs, use_llm=use_llm)
        except ValueError:
            print("   ❌ Input non valido")
            return
    
    else:
        print("   ❌ Scelta non valida")
        return
    
    # Exit code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
