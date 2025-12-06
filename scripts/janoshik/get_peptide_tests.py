#!/usr/bin/env python3
"""
Helper function to query all test types for a specific peptide from a supplier.

Use case: "Show me all tests for Ipamorelin from peptidegurus.com"
"""

from peptide_manager.janoshik.repositories import JanoshikCertificateRepository
from typing import Dict, List
import json


def get_peptide_test_summary(
    peptide_name: str,
    supplier_name: str,
    db_path: str = "data/development/peptide_management.db"
) -> Dict:
    """
    Recupera tutti i test per un peptide specifico da un supplier.
    
    Args:
        peptide_name: Nome peptide (es. "Ipamorelin", "BPC-157")
        supplier_name: Nome supplier normalizzato (es. "peptidegurus.com")
        db_path: Path al database
        
    Returns:
        Dict con test categorizzati per tipo
    """
    repo = JanoshikCertificateRepository(db_path)
    
    # Query tutti i certificati per peptide + supplier
    all_certs = repo.get_all()
    
    # Normalizza supplier_name (lowercase, no protocol/www)
    supplier_name_normalized = supplier_name.lower().strip()
    for prefix in ['https://', 'http://', 'www.']:
        if supplier_name_normalized.startswith(prefix):
            supplier_name_normalized = supplier_name_normalized[len(prefix):]
    supplier_name_normalized = supplier_name_normalized.rstrip('/')
    
    # Filtra per peptide + supplier
    matching_certs = [
        c for c in all_certs
        if peptide_name.lower() in c.peptide_name.lower()
        and supplier_name_normalized in c.supplier_name.lower()
    ]
    
    if not matching_certs:
        return {
            'peptide_name': peptide_name,
            'supplier_name': supplier_name,
            'found': False,
            'message': f'No certificates found for {peptide_name} from {supplier_name}'
        }
    
    # Categorizza per test_type
    purity_tests = []
    endotoxin_tests = []
    heavy_metal_tests = []
    microbiology_tests = []
    
    for cert in matching_certs:
        test_cat = cert.test_category or 'purity'
        
        test_info = {
            'task_number': cert.task_number,
            'batch_number': cert.batch_number,
            'test_date': cert.test_date.strftime('%Y-%m-%d') if cert.test_date else None,
            'verification_key': cert.verification_key
        }
        
        if test_cat == 'purity' or cert.purity_percentage:
            test_info['purity_%'] = cert.purity_percentage
            test_info['quantity_mg'] = cert.quantity_tested_mg
            purity_tests.append(test_info)
        
        if test_cat == 'endotoxin' or cert.endotoxin_level:
            test_info['endotoxin_EU_per_mg'] = cert.endotoxin_level
            endotoxin_tests.append(test_info)
        
        if test_cat == 'heavy_metals' or cert.heavy_metals_result:
            if cert.heavy_metals_result:
                test_info['heavy_metals'] = json.loads(cert.heavy_metals_result)
            heavy_metal_tests.append(test_info)
        
        if test_cat == 'microbiology' or cert.microbiology_tamc or cert.microbiology_tymc:
            test_info['TAMC_CFU_per_g'] = cert.microbiology_tamc
            test_info['TYMC_CFU_per_g'] = cert.microbiology_tymc
            microbiology_tests.append(test_info)
    
    return {
        'peptide_name': peptide_name,
        'supplier_name': supplier_name,
        'found': True,
        'total_certificates': len(matching_certs),
        'tests': {
            'purity': {
                'count': len(purity_tests),
                'tests': purity_tests
            },
            'endotoxin': {
                'count': len(endotoxin_tests),
                'tests': endotoxin_tests
            },
            'heavy_metals': {
                'count': len(heavy_metal_tests),
                'tests': heavy_metal_tests
            },
            'microbiology': {
                'count': len(microbiology_tests),
                'tests': microbiology_tests
            }
        },
        'testing_completeness': {
            'has_purity': len(purity_tests) > 0,
            'has_endotoxin': len(endotoxin_tests) > 0,
            'has_heavy_metals': len(heavy_metal_tests) > 0,
            'has_microbiology': len(microbiology_tests) > 0,
            'completeness_score': (
                50 +  # Base
                (15 if len(endotoxin_tests) > 0 else 0) +
                (15 if len(heavy_metal_tests) > 0 else 0) +
                (15 if len(microbiology_tests) > 0 else 0) +
                (5 if len(purity_tests) > 0 and len(endotoxin_tests) > 0 and len(heavy_metal_tests) > 0 and len(microbiology_tests) > 0 else 0)
            )
        }
    }


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python get_peptide_tests.py <peptide_name> <supplier_name>")
        print("\nExample:")
        print("  python get_peptide_tests.py Ipamorelin peptidegurus.com")
        print("  python get_peptide_tests.py BPC-157 reta-peptide.com")
        sys.exit(1)
    
    peptide = sys.argv[1]
    supplier = sys.argv[2]
    
    result = get_peptide_test_summary(peptide, supplier)
    
    if not result['found']:
        print(f"❌ {result['message']}")
        sys.exit(0)
    
    print(f"\n🔬 Test Summary: {result['peptide_name']} from {result['supplier_name']}")
    print(f"{'=' * 80}")
    print(f"Total Certificates: {result['total_certificates']}")
    print()
    
    tests = result['tests']
    
    print(f"📊 Purity Tests: {tests['purity']['count']}")
    for t in tests['purity']['tests'][:3]:  # Show first 3
        print(f"   • Task {t['task_number']}: {t['purity_%']:.2f}% purity, {t['quantity_mg']:.2f}mg (batch: {t['batch_number']})")
    
    print(f"\n💉 Endotoxin Tests: {tests['endotoxin']['count']}")
    for t in tests['endotoxin']['tests'][:3]:
        print(f"   • Task {t['task_number']}: {t['endotoxin_EU_per_mg']} EU/mg (batch: {t['batch_number']})")
    
    print(f"\n⚗️  Heavy Metals Tests: {tests['heavy_metals']['count']}")
    for t in tests['heavy_metals']['tests'][:3]:
        metals = t.get('heavy_metals', {})
        print(f"   • Task {t['task_number']}: {metals} (batch: {t['batch_number']})")
    
    print(f"\n🦠 Microbiology Tests: {tests['microbiology']['count']}")
    for t in tests['microbiology']['tests'][:3]:
        print(f"   • Task {t['task_number']}: TAMC={t['TAMC_CFU_per_g']}, TYMC={t['TYMC_CFU_per_g']} (batch: {t['batch_number']})")
    
    comp = result['testing_completeness']
    print(f"\n✅ Testing Completeness: {comp['completeness_score']}/100")
    print(f"   Purity: {'✅' if comp['has_purity'] else '❌'}")
    print(f"   Endotoxin: {'✅' if comp['has_endotoxin'] else '❌'}")
    print(f"   Heavy Metals: {'✅' if comp['has_heavy_metals'] else '❌'}")
    print(f"   Microbiology: {'✅' if comp['has_microbiology'] else '❌'}")
