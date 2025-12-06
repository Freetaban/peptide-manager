"""
Test veloce - Solo extraction con GPT-4o su immagine test
"""

from pathlib import Path
from peptide_manager.janoshik import JanoshikExtractor, LLMProvider
from peptide_manager.janoshik.llm_providers import get_llm_extractor

print("=" * 70)
print("Test VELOCE - GPT-4o Extraction su immagine test")
print("=" * 70)

# Verifica se esiste già un'immagine di test
test_images = list(Path("data/janoshik/images").glob("*.jpg"))
if not test_images:
    test_images = list(Path("data/janoshik/images").glob("*.png"))

if test_images:
    print(f"\n📁 Trovate {len(test_images)} immagini in data/janoshik/images/")
    test_image = test_images[0]
    print(f"   Usando: {test_image.name}\n")
    
    # Initialize extractor
    print("[1] Inizializzazione GPT-4o Extractor...")
    llm = get_llm_extractor(LLMProvider.GPT4O)
    extractor = JanoshikExtractor(llm)
    print("✓ Extractor pronto\n")
    
    # Test extraction
    print("[2] Extraction dati certificato...")
    print(f"   (Questo costerà ~$0.002 per 1 immagine)")
    try:
        result = extractor.process_certificates([test_image])
        
        if result:
            print("\n✓ Extraction completata!")
            print(f"\n📊 Dati estratti:")
            for key, value in result[0].items():
                print(f"   {key}: {value}")
        else:
            print("\n❌ Nessun dato estratto")
            
    except Exception as e:
        print(f"\n❌ Errore durante extraction: {e}")
        import traceback
        traceback.print_exc()
else:
    print("\n⚠️ Nessuna immagine trovata in data/janoshik/images/")
    print("   Per testare l'extraction:")
    print("   1. Scarica manualmente un certificato Janoshik")
    print("   2. Salvalo in data/janoshik/images/test.jpg")
    print("   3. Riesegui questo script")
    print("\n   OPPURE:")
    print("   Attendi che lo scraping completi (richiede ~2-3 minuti)")
