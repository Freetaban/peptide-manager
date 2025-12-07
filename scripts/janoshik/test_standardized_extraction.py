#!/usr/bin/env python3
"""
Test script per verificare l'estrazione dei nuovi campi standardizzati.
Processa un singolo certificato per validare il flusso end-to-end.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from peptide_manager.janoshik.models.janoshik_certificate import JanoshikCertificate
from peptide_manager.janoshik.llm_providers import LLMProvider, get_llm_extractor
from peptide_manager import PeptideManager
import json


def test_single_certificate():
    """
    Testa l'estrazione con i nuovi campi standardizzati su un certificato.
    """
    print("🧪 Test Estrazione Campi Standardizzati\n")
    print("=" * 60)
    
    # Test image
    test_image = Path("data/janoshik/images/40741_cc145e68.png")
    
    if not test_image.exists():
        print(f"❌ Immagine di test non trovata: {test_image}")
        return
    
    print(f"📁 Immagine test: {test_image.name}\n")
    
    # Initialize LLM provider
    print("🔧 Inizializzazione LLM provider...")
    llm = get_llm_extractor(LLMProvider.GPT4O)
    
    # Extract certificate data
    print("🔍 Estrazione dati certificato...")
    try:
        extracted_data = llm.extract_certificate_data(str(test_image))
        
        if not extracted_data:
            print("❌ Nessun dato estratto")
            return
        
        print("✅ Dati estratti con successo!\n")
        
        # Show raw LLM response for standardized fields
        print("📋 Campi standardizzati estratti dall'LLM:")
        print(f"  - peptide_name: {extracted_data.get('peptide_name', 'N/A')}")
        print(f"  - quantity_nominal: {extracted_data.get('quantity_nominal', 'N/A')}")
        print(f"  - unit_of_measure: {extracted_data.get('unit_of_measure', 'N/A')}")
        print(f"  - sample (raw): {extracted_data.get('sample', 'N/A')}")
        print()
        
        # Create certificate object
        print("🏗️  Creazione oggetto JanoshikCertificate...")
        cert = JanoshikCertificate.from_extracted_data(
            extracted_data,
            image_file=str(test_image),
            image_hash="test_hash_123"
        )
        
        print("✅ Certificato creato!\n")
        
        # Show certificate fields
        print("📄 Dati certificato:")
        print(f"  - Task Number: {cert.task_number}")
        print(f"  - Supplier: {cert.supplier_name}")
        print(f"  - Product Name (raw): {cert.peptide_name}")
        print(f"  - Test Date: {cert.test_date}")
        print(f"  - Purity: {cert.purity_percentage}%")
        print(f"  - Quantity Tested: {cert.quantity_tested_mg} mg")
        print()
        
        print("✨ Campi standardizzati nel modello:")
        print(f"  - peptide_name_std: {cert.peptide_name_std}")
        print(f"  - quantity_nominal: {cert.quantity_nominal}")
        print(f"  - unit_of_measure: {cert.unit_of_measure}")
        print()
        
        # Convert to dict for DB insert
        cert_dict = cert.to_dict()
        
        print("💾 Dati per DB insert (to_dict):")
        print(f"  - product_name: {cert_dict.get('product_name')}")
        print(f"  - peptide_name_std: {cert_dict.get('peptide_name_std')}")
        print(f"  - quantity_nominal: {cert_dict.get('quantity_nominal')}")
        print(f"  - unit_of_measure: {cert_dict.get('unit_of_measure')}")
        print()
        
        # Validation checks
        print("✅ Validazione:")
        checks = []
        
        if cert.peptide_name_std:
            checks.append("✓ peptide_name_std popolato")
        else:
            checks.append("✗ peptide_name_std vuoto")
        
        if cert.quantity_nominal is not None:
            checks.append("✓ quantity_nominal popolato")
        else:
            checks.append("✗ quantity_nominal vuoto")
        
        if cert.unit_of_measure:
            checks.append("✓ unit_of_measure popolato")
        else:
            checks.append("✗ unit_of_measure vuoto")
        
        # Check DB dict has new fields
        if 'peptide_name_std' in cert_dict:
            checks.append("✓ peptide_name_std nel dict DB")
        else:
            checks.append("✗ peptide_name_std mancante nel dict DB")
        
        for check in checks:
            print(f"  {check}")
        
        print()
        print("=" * 60)
        
        # Summary
        all_ok = all('✓' in c for c in checks)
        if all_ok:
            print("✅ TEST SUPERATO - Tutti i campi standardizzati funzionano!")
        else:
            print("⚠️  TEST PARZIALE - Alcuni campi non popolati")
        
        # Show full extracted data for debugging
        print("\n📝 Full LLM Response (JSON):")
        print(json.dumps(extracted_data, indent=2, default=str))
        
    except Exception as e:
        print(f"❌ Errore durante test: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_single_certificate()
