#!/usr/bin/env python3
"""
Test parser with specific test types certificates.

Tests:
- 76739: Endotoxin test
- 76738: Heavy metals test  
- 76740: Microbiology (TAMC+TYMC) test
"""

from peptide_manager.janoshik.manager import JanoshikManager
from peptide_manager.janoshik.llm_providers import LLMProvider
import json

def test_special_certificates():
    """Test parsing of endotoxin, heavy metals, and microbiology certificates"""
    
    # Task numbers to test with full URLs
    test_tasks = {
        '76739': {'type': 'endotoxin', 'url': 'https://www.janoshik.com/tests/76739-Tesamorelin_Y7BX23PQIS43'},
        '76738': {'type': 'heavy_metals', 'url': 'https://www.janoshik.com/tests/76738-Tesamorelin_F8RVRG9R5Q7N'},
        '76740': {'type': 'microbiology', 'url': 'https://www.janoshik.com/tests/76740-Tesamorelin_WO8KVZFBXVD3'}
    }
    
    print("🔬 Testing Parser with Special Certificate Types")
    print("=" * 80)
    
    manager = JanoshikManager(
        db_path="data/development/peptide_management.db",
        llm_provider=LLMProvider.GPT4O  # Use GPT-4o instead of Gemini
    )
    
    results = {}
    
    for task_num, info in test_tasks.items():
        test_type = info['type']
        test_url = info['url']
        
        print(f"\n📋 Task {task_num} ({test_type})")
        print(f"   URL: {test_url}")
        print("-" * 80)
        
        try:
            # Check if file already exists locally
            from pathlib import Path
            temp_dir = Path("data/janoshik/temp")
            temp_dir.mkdir(parents=True, exist_ok=True)
            image_path = temp_dir / f"test_{task_num}_{test_type}.png"
            
            if image_path.exists():
                print(f"  ✅ Using existing file: {image_path}")
            else:
                # Try to download certificate image
                print(f"  Downloading certificate image...")
                cert_png_url = f"{test_url}/certificate.png"
                
                import requests
                try:
                    response = requests.get(cert_png_url, timeout=30)
                    response.raise_for_status()
                    
                    with open(image_path, 'wb') as f:
                        f.write(response.content)
                    
                    print(f"  ✅ Downloaded to {image_path}")
                except requests.exceptions.RequestException as e:
                    print(f"  ❌ Download failed: {e}")
                    print(f"  💡 Please manually save certificate PNG to: {image_path}")
                    results[task_num] = {'status': 'failed', 'reason': 'download_failed', 'error': str(e)}
                    continue
            
            # Extract with LLM
            print(f"  Extracting data with LLM...")
            extracted = manager.extractor.process_single_certificate(image_path)
            
            # Check extracted data
            print(f"\n  ✅ Extracted Data:")
            print(f"     Task: {extracted.get('task_number')}")
            print(f"     Test Type: {extracted.get('test_type')}")
            print(f"     Test Category: {extracted.get('test_category', 'NOT SET')}")
            print(f"     Sample: {extracted.get('sample')}")
            print(f"     Batch: {extracted.get('batch')}")
            
            # Type-specific checks
            if test_type == 'endotoxin':
                endo = extracted.get('endotoxin_level')
                print(f"     Endotoxin Level: {endo} EU/mg")
                if endo is None:
                    print(f"     ⚠️  WARNING: endotoxin_level is None!")
            
            elif test_type == 'heavy_metals':
                metals = extracted.get('heavy_metals')
                print(f"     Heavy Metals: {metals}")
                if metals:
                    for metal, value in metals.items():
                        print(f"        {metal}: {value} ppm")
                else:
                    print(f"     ⚠️  WARNING: heavy_metals is None!")
            
            elif test_type == 'microbiology':
                tamc = extracted.get('microbiology_tamc')
                tymc = extracted.get('microbiology_tymc')
                print(f"     TAMC: {tamc} CFU/g")
                print(f"     TYMC: {tymc} CFU/g")
                if tamc is None and tymc is None:
                    print(f"     ⚠️  WARNING: Both TAMC and TYMC are None!")
            
            print(f"\n     Results: {extracted.get('results')}")
            
            results[task_num] = {
                'status': 'success',
                'extracted': extracted,
                'image_path': str(image_path)
            }
            
        except Exception as e:
            print(f"  ❌ Error: {str(e)}")
            results[task_num] = {'status': 'error', 'error': str(e)}
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)
    
    success_count = sum(1 for r in results.values() if r.get('status') == 'success')
    print(f"✅ Successfully parsed: {success_count}/{len(test_tasks)}")
    
    for task_num, info in test_tasks.items():
        test_type = info['type']
        result = results.get(task_num, {})
        status = result.get('status', 'unknown')
        
        if status == 'success':
            extracted = result['extracted']
            test_cat = extracted.get('test_category', 'NOT SET')
            expected_cat = 'endotoxin' if test_type == 'endotoxin' else ('heavy_metals' if test_type == 'heavy_metals' else 'microbiology')
            
            if test_cat == expected_cat:
                print(f"  ✅ {task_num} ({test_type}): test_category = '{test_cat}' ✓")
            else:
                print(f"  ⚠️  {task_num} ({test_type}): test_category = '{test_cat}' (expected '{expected_cat}')")
        else:
            print(f"  ❌ {task_num} ({test_type}): {status}")
    
    return results

if __name__ == "__main__":
    results = test_special_certificates()
    
    # Save full results to JSON for inspection
    output_file = "data/exports/test_special_certs_results.json"
    with open(output_file, 'w') as f:
        # Convert to serializable format
        serializable = {}
        for task, data in results.items():
            serializable[task] = {
                'status': data.get('status'),
                'extracted': data.get('extracted'),
                'error': data.get('error'),
                'image_path': data.get('image_path')
            }
        json.dump(serializable, f, indent=2)
    
    print(f"\n💾 Full results saved to: {output_file}")
