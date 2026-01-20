================================================================================
Table: administrations

Columns:
  - id (INTEGER) PK
  - preparation_id (INTEGER) NOT NULL
  - protocol_id (INTEGER)
  - administration_datetime (TIMESTAMP) NOT NULL
  - dose_ml (REAL) NOT NULL
  - injection_site (TEXT)
  - notes (TEXT)
  - side_effects (TEXT)
  - created_at (TIMESTAMP) DEFAULT=CURRENT_TIMESTAMP
  - injection_method (TEXT)
  - deleted_at (TIMESTAMP) DEFAULT=NULL

Foreign keys:
  - protocol_id -> protocols.id (on_update=NO ACTION, on_delete=NO ACTION)
  - preparation_id -> preparations.id (on_update=NO ACTION, on_delete=NO ACTION)    

Indexes:
  - idx_administrations_date (administration_datetime)
  - idx_administrations_prep (preparation_id)

================================================================================    
Table: batch_composition

Columns:
  - id (INTEGER) PK
  - batch_id (INTEGER) NOT NULL
  - peptide_id (INTEGER) NOT NULL
  - mg_per_vial (REAL) NOT NULL
  - mg_amount (REAL)

Foreign keys:
  - peptide_id -> peptides.id (on_update=NO ACTION, on_delete=NO ACTION)
  - batch_id -> batches.id (on_update=NO ACTION, on_delete=CASCADE)

Indexes:
  - idx_batch_composition_batch (batch_id)
  - sqlite_autoindex_batch_composition_1 UNIQUE (batch_id, peptide_id)

================================================================================    
Table: batches

Columns:
  - id (INTEGER) PK
  - supplier_id (INTEGER) NOT NULL
  - product_name (TEXT) NOT NULL
  - batch_number (TEXT)
  - vials_count (INTEGER) NOT NULL
  - mg_per_vial (REAL) NOT NULL
  - total_price (REAL) NOT NULL
  - currency (TEXT) DEFAULT='EUR'
  - purchase_date (DATE) NOT NULL
  - expiry_date (DATE)
  - storage_location (TEXT)
  - vials_remaining (INTEGER) NOT NULL
  - notes (TEXT)
  - created_at (TIMESTAMP) DEFAULT=CURRENT_TIMESTAMP
  - deleted_at (TIMESTAMP) DEFAULT=NULL
  - manufacturing_date (DATE)
  - expiration_date (DATE)
  - price_per_vial (REAL)
  - coa_path (TEXT)

Foreign keys:
  - supplier_id -> suppliers.id (on_update=NO ACTION, on_delete=NO ACTION)

Indexes:
  - idx_batches_supplier (supplier_id)

================================================================================    
Table: certificate_details

Columns:
  - id (INTEGER) PK
  - certificate_id (INTEGER) NOT NULL
  - test_parameter (TEXT) NOT NULL
  - result_value (TEXT)
  - unit (TEXT)
  - specification (TEXT)
  - pass_fail (TEXT)

Foreign keys:
  - certificate_id -> certificates.id (on_update=NO ACTION, on_delete=CASCADE)      

================================================================================    
Table: certificates

Columns:
  - id (INTEGER) PK
  - batch_id (INTEGER) NOT NULL
  - certificate_type (TEXT) NOT NULL
  - lab_name (TEXT)
  - test_date (DATE)
  - file_path (TEXT)
  - file_name (TEXT)
  - purity_percentage (REAL)
  - endotoxin_level (TEXT)
  - notes (TEXT)
  - created_at (TIMESTAMP) DEFAULT=CURRENT_TIMESTAMP

Foreign keys:
  - batch_id -> batches.id (on_update=NO ACTION, on_delete=CASCADE)

Indexes:
  - idx_certificates_batch (batch_id)

================================================================================    
Table: peptides

Columns:
  - id (INTEGER) PK
  - name (TEXT) NOT NULL
  - description (TEXT)
  - common_uses (TEXT)
  - notes (TEXT)
  - created_at (TIMESTAMP) DEFAULT=CURRENT_TIMESTAMP
  - deleted_at (TIMESTAMP) DEFAULT=NULL

Indexes:
  - sqlite_autoindex_peptides_1 UNIQUE (name)

================================================================================    
Table: preparations

Columns:
  - id (INTEGER) PK
  - batch_id (INTEGER) NOT NULL
  - vials_used (INTEGER) NOT NULL
  - volume_ml (REAL) NOT NULL
  - diluent (TEXT) DEFAULT='BAC Water'
  - preparation_date (DATE) NOT NULL
  - expiry_date (DATE)
  - volume_remaining_ml (REAL) NOT NULL
  - storage_location (TEXT)
  - notes (TEXT)
  - created_at (TIMESTAMP) DEFAULT=CURRENT_TIMESTAMP
  - deleted_at (TIMESTAMP) DEFAULT=NULL

Foreign keys:
  - batch_id -> batches.id (on_update=NO ACTION, on_delete=NO ACTION)

Indexes:
  - idx_preparations_batch (batch_id)

================================================================================    
Table: protocol_peptides

Columns:
  - id (INTEGER) PK
  - protocol_id (INTEGER) NOT NULL
  - peptide_id (INTEGER) NOT NULL
  - target_dose_mcg (REAL) NOT NULL

Foreign keys:
  - peptide_id -> peptides.id (on_update=NO ACTION, on_delete=NO ACTION)
  - protocol_id -> protocols.id (on_update=NO ACTION, on_delete=CASCADE)

================================================================================    
Table: protocols

Columns:
  - id (INTEGER) PK
  - name (TEXT) NOT NULL
  - description (TEXT)
  - frequency_per_day (INTEGER) DEFAULT=1
  - days_on (INTEGER)
  - days_off (INTEGER) DEFAULT=0
  - cycle_duration_weeks (INTEGER)
  - notes (TEXT)
  - active (BOOLEAN) DEFAULT=1
  - created_at (TIMESTAMP) DEFAULT=CURRENT_TIMESTAMP
  - deleted_at (TIMESTAMP) DEFAULT=NULL

Note: Il dosaggio è definito a livello di peptide nella tabella protocol_peptides (mcg/giorno).
      Il volume in ml viene calcolato dinamicamente in base alla concentrazione della preparazione usata.

================================================================================    
Table: suppliers

Columns:
  - id (INTEGER) PK
  - name (TEXT) NOT NULL
  - country (TEXT)
  - website (TEXT)
  - email (TEXT)
  - notes (TEXT)
  - reliability_rating (INTEGER)
  - created_at (TIMESTAMP) DEFAULT=CURRENT_TIMESTAMP
  - deleted_at (TIMESTAMP) DEFAULT=NULL

Indexes:
  - sqlite_autoindex_suppliers_1 UNIQUE (name)