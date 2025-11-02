"""
Esempio 3: Query e report
"""

from peptide_manager import PeptideManager

manager = PeptideManager('my_peptides.db')

print("=== INVENTARIO SUMMARY ===")
summary = manager.get_inventory_summary()
print(f"Batches attivi: {summary['available_batches']}")
print(f"Valore inventario: EUR {summary['total_value']:.2f}")
print(f"Peptidi unici: {summary['unique_peptides']}")
print(f"In scadenza: {summary['expiring_soon']}")

print("\n=== CERCA BATCHES ===")
# Cerca per peptide
bpc_batches = manager.get_batches(peptide='BPC-157', only_available=True)
print(f"\nBatches con BPC-157: {len(bpc_batches)}")
for batch in bpc_batches:
    print(f"  - {batch['product_name']}: {batch['vials_remaining']} fiale")

# Cerca per fornitore
ps_batches = manager.get_batches(supplier='PeptideSciences', only_available=True)
print(f"\nBatches da PeptideSciences: {len(ps_batches)}")

print("\n=== DETTAGLI BATCH ===")
batch_details = manager.get_batch_details(1)
if batch_details:
    print(f"Prodotto: {batch_details['product_name']}")
    print(f"Composizione:")
    for comp in batch_details['composition']:
        print(f"  - {comp['name']}: {comp['mg_per_vial']}mg")
    print(f"Certificati: {len(batch_details['certificates'])}")

manager.close()
