"""
Aggiornamento Janoshik - Script Semplificato

Esegue aggiornamento completo:
1. Scraping nuovi certificati
2. Download immagini
3. Estrazione dati (GPT-4o)
4. Calcolo ranking
5. Aggiornamento database

USO:
    python scripts/update_janoshik_data.py [--fast|--medium|--full]
    
OPZIONI:
    --fast      1 pagina, max 20 certificati (~5 min, ~$0.50)
    --medium    2 pagine, max 50 certificati (~15 min, ~$2.00)
    --full      Tutte le pagine, tutti i certificati (~60+ min, ~$20+)
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime

# Add root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from peptide_manager.janoshik import JanoshikManager, LLMProvider


def print_header(title):
    """Print header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_section(title):
    """Print section"""
    print(f"\n📌 {title}")
    print("-" * 80)


def confirm_action(mode, max_pages, max_certs, estimated_cost):
    """Ask user confirmation"""
    print_section("Conferma Operazione")
    print(f"   Modalità: {mode}")
    print(f"   Pagine da scrapare: {max_pages if max_pages else 'TUTTE'}")
    print(f"   Certificati massimi: {max_certs if max_certs else 'TUTTI'}")
    print(f"   Costo stimato API: ~${estimated_cost}")
    print(f"   Tempo stimato: ~{get_estimated_time(max_certs)}")
    
    print("\n⚠️  ATTENZIONE:")
    print("   • Verranno effettuate chiamate API a GPT-4o (costo reale)")
    print("   • Il database sarà aggiornato con nuovi certificati")
    print("   • L'operazione può richiedere diversi minuti")
    
    response = input("\n   Procedere? [s/N]: ").strip().lower()
    return response == 's'


def get_estimated_time(max_certs):
    """Estimate time based on certificates"""
    if not max_certs:
        return "30-60+ minuti"
    elif max_certs <= 20:
        return "3-5 minuti"
    elif max_certs <= 50:
        return "10-15 minuti"
    else:
        return "20-30+ minuti"


def update_janoshik(mode='fast', db_path='data/development/peptide_management.db'):
    """
    Execute Janoshik update.
    
    Args:
        mode: 'fast', 'medium', or 'full'
        db_path: Path to database
    """
    print_header("AGGIORNAMENTO JANOSHIK")
    
    # Configure based on mode
    configs = {
        'fast': {
            'max_pages': 1,
            'max_certs': 20,
            'estimated_cost': 0.50,
            'description': 'Test veloce (1 pagina, 20 certificati)'
        },
        'medium': {
            'max_pages': 2,
            'max_certs': 50,
            'estimated_cost': 2.00,
            'description': 'Aggiornamento medio (2 pagine, 50 certificati)'
        },
        'full': {
            'max_pages': None,
            'max_certs': None,
            'estimated_cost': 20.00,
            'description': 'Aggiornamento completo (tutte le pagine, tutti i certificati)'
        }
    }
    
    config = configs[mode]
    
    print(f"\n🎯 Modalità: {config['description']}")
    
    # Ask confirmation
    if not confirm_action(
        mode,
        config['max_pages'],
        config['max_certs'],
        config['estimated_cost']
    ):
        print("\n❌ Operazione annullata dall'utente.")
        return False
    
    # Verify database
    print_section("Verifica Database")
    
    if not Path(db_path).exists():
        print(f"❌ Database non trovato: {db_path}")
        print("   Esegui prima: python scripts/copy_prod_to_dev.py")
        return False
    
    print(f"   ✓ Database trovato: {db_path}")
    
    # Initialize manager
    print_section("Inizializzazione JanoshikManager")
    
    try:
        manager = JanoshikManager(
            db_path=db_path,
            llm_provider=LLMProvider.GPT4O,
            llm_api_key=None  # Auto-load from .env.development
        )
        print(f"   ✓ Manager inizializzato con GPT-4o")
    except Exception as e:
        print(f"❌ Errore inizializzazione: {e}")
        return False
    
    # Execute update
    print_section("Esecuzione Aggiornamento")
    print(f"   Inizio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Progress callback
    last_stage = None
    
    def progress_callback(stage, message):
        nonlocal last_stage
        if stage != last_stage:
            print(f"\n   [{stage.upper()}]")
            last_stage = stage
        print(f"   • {message}")
    
    try:
        import time
        start_time = time.time()
        
        result = manager.run_full_update(
            max_pages=config['max_pages'],
            max_certificates=config['max_certs'],
            progress_callback=progress_callback
        )
        
        elapsed = time.time() - start_time
        
        # Print results
        print_section("Risultati")
        print(f"   ⏱️  Tempo totale: {elapsed:.1f} secondi ({elapsed/60:.1f} minuti)")
        print(f"   📄 Certificati scrapati: {result['certificates_scraped']}")
        print(f"   ✨ Certificati nuovi: {result['certificates_new']}")
        print(f"   🔍 Certificati estratti: {result['certificates_extracted']}")
        print(f"   📊 Ranking calcolati: {result['rankings_calculated']}")
        
        if result['top_supplier']:
            print(f"   🏆 Top supplier: {result['top_supplier']}")
        
        print_section("COMPLETATO")
        print("   ✅ Aggiornamento Janoshik completato con successo!")
        
        return True
        
    except KeyboardInterrupt:
        print("\n\n❌ Operazione interrotta dall'utente (Ctrl+C)")
        return False
        
    except Exception as e:
        print(f"\n❌ ERRORE durante aggiornamento: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Aggiornamento dati Janoshik',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Esempi:
  python scripts/update_janoshik_data.py --fast      # Test veloce (5 min, ~$0.50)
  python scripts/update_janoshik_data.py --medium    # Aggiornamento medio (15 min, ~$2.00)
  python scripts/update_janoshik_data.py --full      # Aggiornamento completo (60+ min, ~$20+)

Note:
  • Usa --fast per test iniziali
  • Usa --medium per aggiornamenti settimanali
  • Usa --full solo per aggiornamenti completi mensili
        """
    )
    
    parser.add_argument(
        '--fast',
        action='store_true',
        help='Modalità veloce (1 pagina, 20 certificati)'
    )
    
    parser.add_argument(
        '--medium',
        action='store_true',
        help='Modalità media (2 pagine, 50 certificati)'
    )
    
    parser.add_argument(
        '--full',
        action='store_true',
        help='Modalità completa (tutte le pagine)'
    )
    
    parser.add_argument(
        '--db',
        type=str,
        default='data/development/peptide_management.db',
        help='Path al database (default: data/development/peptide_management.db)'
    )
    
    args = parser.parse_args()
    
    # Determine mode
    if args.full:
        mode = 'full'
    elif args.medium:
        mode = 'medium'
    else:
        mode = 'fast'  # Default
    
    # Execute update
    success = update_janoshik(mode=mode, db_path=args.db)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
