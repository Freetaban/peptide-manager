"""
Test script for blend and replicate extraction from Janoshik certificates.
Tests the three specific certificates mentioned:
- Task #93546 (GLOW 70 blend)
- Task #83375 (BPC+TB blend)
- Task #70497 (SLU-PP-332 replicates)
"""

import sys
from pathlib import Path
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from peptide_manager.janoshik.llm_providers import LLMProvider, get_llm_extractor
from peptide_manager.janoshik.models import JanoshikCertificate

def test_certificate_extraction(task_number: str, image_path: Path, expected_type: str):
    """
    Test extraction on a single certificate.

    Args:
        task_number: Task number (e.g., "93546")
        image_path: Path to certificate image
        expected_type: "blend" or "replicate"
    """
    print(f"\n{'='*80}")
    print(f"Testing Task #{task_number} - Expected: {expected_type.upper()}")
    print(f"{'='*80}")

    # Initialize LLM provider (using GPT-4o)
    provider = get_llm_extractor(LLMProvider.GPT4O)

    # Extract data
    print(f"Extracting from: {image_path.name}")
    extracted = provider.extract_certificate_data(str(image_path))

    # Display raw extracted data
    print("\n[Raw LLM Output]")
    print(json.dumps(extracted, indent=2, default=str))

    # Parse into model
    cert = JanoshikCertificate.from_extracted_data(
        extracted=extracted,
        image_file=str(image_path),
        image_hash=image_path.stem.split('_')[1] if '_' in image_path.stem else 'test'
    )

    # Display parsed model
    print("\n[Parsed Model]")
    print(f"Task Number: {cert.task_number}")
    print(f"Peptide Name: {cert.peptide_name_std}")
    print(f"Is Blend: {cert.is_blend}")
    print(f"Has Replicates: {cert.has_replicates}")
    print(f"Protocol Name: {cert.protocol_name}")
    print(f"Verification Key: {cert.verification_key}")

    # Display blend components if present
    if cert.is_blend:
        components = cert.get_blend_components()
        print(f"\n[Blend Components] ({len(components)} components)")
        for i, comp in enumerate(components, 1):
            print(f"  {i}. {comp.get('peptide', 'Unknown')}: {comp.get('quantity', 'N/A')} {comp.get('unit', 'mg')}")

        # Show all peptides
        all_peptides = cert.get_all_peptides()
        print(f"\nAll Peptides: {', '.join(all_peptides)}")

    # Display replicate measurements if present
    if cert.has_replicates:
        measurements = cert.get_replicate_measurements()
        stats = cert.get_replicate_statistics()

        print(f"\n[Replicate Measurements] ({len(measurements)} measurements)")
        for i, value in enumerate(measurements, 1):
            print(f"  {i}. {value}")

        print(f"\n[Statistics]")
        print(f"  Mean: {stats.get('mean', 'N/A')}")
        print(f"  Std Dev: {stats.get('std_dev', 'N/A')}")
        print(f"  CV%: {stats.get('cv_percent', 'N/A')}")
        print(f"  N: {stats.get('n', 'N/A')}")

    # Verification
    print(f"\n[Verification]")
    if expected_type == "blend":
        if cert.is_blend:
            print("[OK] Correctly detected as BLEND")
        else:
            print("[ERROR] Should be detected as BLEND but is_blend=False")
    elif expected_type == "replicate":
        if cert.has_replicates:
            print("[OK] Correctly detected as REPLICATES")
        else:
            print("[ERROR] Should be detected as REPLICATES but has_replicates=False")

    return cert


def main():
    """Run all tests."""

    images_dir = Path("data/janoshik/images")

    # Test 1: GLOW 70 blend (3 components)
    cert1 = test_certificate_extraction(
        task_number="93546",
        image_path=images_dir / "93546_2690ea75.png",
        expected_type="blend"
    )

    # Test 2: BPC+TB blend (2 components)
    cert2 = test_certificate_extraction(
        task_number="83375",
        image_path=images_dir / "83375_d2fd6234.png",
        expected_type="blend"
    )

    # Test 3: SLU-PP-332 replicates
    cert3 = test_certificate_extraction(
        task_number="70497",
        image_path=images_dir / "70497_fb92b61b.png",
        expected_type="replicate"
    )

    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    print(f"Task #93546 (GLOW 70): is_blend={cert1.is_blend}, components={len(cert1.get_blend_components()) if cert1.is_blend else 0}")
    print(f"Task #83375 (BPC+TB): is_blend={cert2.is_blend}, components={len(cert2.get_blend_components()) if cert2.is_blend else 0}")
    print(f"Task #70497 (SLU-PP-332): has_replicates={cert3.has_replicates}, measurements={len(cert3.get_replicate_measurements()) if cert3.has_replicates else 0}")


if __name__ == "__main__":
    main()
