"""
Process existing downloaded Janoshik certificates.

This script:
1. Scans data/janoshik for PNG files
2. Extracts data using LLM (GPT-4o default)
3. Saves to database
4. Calculates supplier rankings
"""

import sys
import time
from pathlib import Path
from peptide_manager.janoshik.manager import JanoshikManager
from peptide_manager.janoshik.models import JanoshikCertificate
from peptide_manager.janoshik.llm_providers import LLMProvider

def main():
    # Setup paths
    db_path = "data/development/peptide_management.db"
    images_dir = Path("data/janoshik/images")
    
    if not images_dir.exists():
        # Try alternate location
        images_dir = Path("data/janoshik/https___janoshik.com_public__files")
    
    if not images_dir.exists():
        print(f"❌ Directory immagini non trovata!")
        print(f"   Cercato in: data/janoshik/images e data/janoshik/https___janoshik.com_public__files")
        return 1
    
    # Count images
    png_files = list(images_dir.glob("**/*.png"))
    print(f"📁 Trovati {len(png_files)} file PNG in {images_dir}")
    
    if len(png_files) == 0:
        print("❌ Nessun PNG trovato!")
        return 1
    
    # Initialize manager with GPT-4o
    print(f"\n🔧 Inizializzazione JanoshikManager con GPT-4o...")
    manager = JanoshikManager(
        db_path=db_path,
        llm_provider=LLMProvider.GPT4O
    )
    
    # Extract task numbers from filenames and check which are already in DB
    print(f"\n🔍 Verifica certificati già processati...")
    existing_tasks = set()
    try:
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT task_number FROM janoshik_certificates")
        existing_tasks = {row[0] for row in cursor.fetchall()}
        conn.close()
        print(f"   ✓ {len(existing_tasks)} certificati già nel database")
    except Exception as e:
        print(f"   ⚠️  Impossibile verificare DB: {e}")
    
    # Filter out already processed certificates
    new_png_files = []
    skipped = 0
    
    for png_file in png_files:
        # Extract task number from filename (format: TASK_HASH.png)
        filename = png_file.stem  # Without .png
        task_number = filename.split('_')[0] if '_' in filename else filename
        
        if task_number in existing_tasks:
            skipped += 1
        else:
            new_png_files.append(png_file)
    
    print(f"   📊 Da processare: {len(new_png_files)} nuovi")
    print(f"   ⏭️  Saltati: {skipped} già esistenti")
    
    if len(new_png_files) == 0:
        print("\n✅ Tutti i certificati sono già stati processati!")
        return 0
    
    # Update png_files to only new ones
    png_files = new_png_files
    
    # Process certificates
    print(f"\n🔍 Elaborazione certificati (LLM extraction + scoring)...")
    print(f"⚠️  Questo richiederà chiamate API LLM - può richiedere tempo e costi")
    
    choice = input("Continuare? (y/n): ").strip().lower()
    if choice != 'y':
        print("❌ Operazione annullata")
        return 0
    
    # Ask for batch size
    batch_str = input(f"\nQuanti certificati processare? (default={len(png_files)}, max={len(png_files)}): ").strip()
    batch_size = int(batch_str) if batch_str.isdigit() else len(png_files)
    batch_size = min(batch_size, len(png_files))
    
    print(f"\n📊 Processerò {batch_size} certificati...")
    
    # Extract data from images using manager's extractor
    image_paths = [str(f) for f in png_files[:batch_size]]
    
    print(f"\n🤖 Estrazione dati con LLM (GPT-4o)...")
    print(f"⏳ Avanzamento: ", end='', flush=True)
    
    # Progress callback with timing
    start_time = time.time()
    
    def show_progress(current, total):
        if current % 10 == 0 or current == total:
            elapsed = time.time() - start_time
            rate = current / elapsed if elapsed > 0 else 0
            remaining = (total - current) / rate if rate > 0 else 0
            
            percent = (current / total) * 100
            eta_min = remaining / 60
            
            print(f"\r⏳ {current}/{total} ({percent:.1f}%) | {rate:.1f} cert/s | ETA: {eta_min:.1f} min", end='', flush=True)
    
    extracted_data = manager.extractor.process_certificates(image_paths, progress_callback=show_progress)
    
    total_time = time.time() - start_time
    print(f"\n✅ Completato in {total_time/60:.1f} minuti ({total_time/batch_size:.1f}s per certificato)")
    
    print(f"\n💾 Salvataggio nel database...")
    # Convert to certificate objects
    cert_objects = []
    successful = 0
    failed = 0
    
    for data, img_path in zip(extracted_data, image_paths):
        try:
            # Generate a simple hash from filename
            import hashlib
            image_hash = hashlib.md5(Path(img_path).name.encode()).hexdigest()
            
            cert_obj = JanoshikCertificate.from_extracted_data(
                data,
                img_path,
                image_hash
            )
            cert_objects.append(cert_obj)
            successful += 1
        except Exception as e:
            failed += 1
            print(f"  ⚠️  Failed to create certificate from {Path(img_path).name}: {e}")
    
    # Save to database
    new_certs = manager.cert_repo.insert_many(cert_objects)
    
    print(f"\n{'='*60}")
    print(f"📊 RISULTATI ESTRAZIONE")
    print(f"{'='*60}")
    print(f"🤖 LLM Estratti: {len(extracted_data)}")
    print(f"✅ Convertiti con successo: {successful}")
    print(f"❌ Falliti conversione: {failed}")
    print(f"💾 Salvati nel DB: {new_certs}")
    
    # Calculate rankings
    if new_certs > 0:
        print(f"\n🏆 Calcolo ranking suppliers...")
        
        all_certs = manager.cert_repo.get_all_as_dicts()
        rankings_df = manager.scorer.calculate_rankings(all_certs)
        
        # Save rankings
        from peptide_manager.janoshik.models import SupplierRanking
        ranking_objects = []
        for _, row in rankings_df.iterrows():
            ranking_obj = SupplierRanking.from_scorer_output(row.to_dict())
            ranking_objects.append(ranking_obj)
        
        rankings_saved = manager.ranking_repo.insert_many(ranking_objects)
        
        print(f"\n{'='*60}")
        print(f"🏆 TOP 10 SUPPLIERS")
        print(f"{'='*60}")
        
        for i, (_, rank) in enumerate(rankings_df.head(10).iterrows(), 1):
            print(f"{i:2d}. {rank['supplier_name']:30s} | Score: {rank['total_score']:5.1f} | Certs: {rank['total_certificates']:3d} | Purity: {rank['avg_purity']:5.1f}%")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
