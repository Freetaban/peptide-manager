CREATE TABLE IF NOT EXISTS shipments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_id INTEGER NOT NULL,
    shipping_cost REAL,
    currency TEXT NOT NULL DEFAULT 'USD',
    shipping_date DATE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
);

ALTER TABLE batches ADD COLUMN shipment_id INTEGER REFERENCES shipments(id);
