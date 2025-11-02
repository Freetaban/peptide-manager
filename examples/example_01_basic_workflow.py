"""
Esempio 1: Workflow base - Aggiungere un acquisto
"""

from peptide_manager import PeptideManager
from peptide_manager.database import init_database

# Inizializza database
init_database('my_peptides.db')

# Crea manager
manager = PeptideManager('my_peptides.db')

# 1. Aggiungi fornitore
supplier_id = manager.add_supplier(
    name='PeptideSciences',
    country='USA',
    website='https://peptidesciences.com',
    rating=5
)

# 2. Aggiungi peptidi al catalogo
manager.add_peptide('BPC-157', 'Body Protection Compound', 'Healing, tissue repair')
manager.add_peptide('TB-500', 'Thymosin Beta-4', 'Recovery, inflammation')

# 3. Registra acquisto (blend)
batch_id = manager.add_batch(
    supplier_name='PeptideSciences',
    product_name='BPC-157 + TB-500 Blend 10mg',
    vials_count=10,
    mg_per_vial=10.0,
    total_price=180.00,
    purchase_date='2024-10-30',
    composition=[
        ('BPC-157', 5.0),
        ('TB-500', 5.0)
    ],
    expiry_date='2026-10-30',
    storage_location='Frigo A'
)

# 4. Aggiungi certificato
cert_id = manager.add_certificate(
    batch_id=batch_id,
    certificate_type='manufacturer',
    lab_name='PeptideSciences QC Lab',
    test_date='2024-10-25',
    purity_percentage=98.5,
    details=[
        {'parameter': 'Purity (HPLC)', 'value': '98.5', 'unit': '%', 
         'specification': '>95%', 'pass_fail': 'pass'},
        {'parameter': 'Endotoxin', 'value': '<0.5', 'unit': 'EU/mg',
         'specification': '<1.0', 'pass_fail': 'pass'}
    ]
)

print("✓ Acquisto registrato con successo!")

# 5. Visualizza inventario
manager.print_inventory(detailed=True)

manager.close()
