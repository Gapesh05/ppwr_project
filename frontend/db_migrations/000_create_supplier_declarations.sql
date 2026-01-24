-- Create supplier_declarations table
CREATE TABLE IF NOT EXISTS supplier_declarations (
    id SERIAL PRIMARY KEY,
    sku VARCHAR(100),
    material VARCHAR(100),
    filename VARCHAR(255) NOT NULL,
    stored_path VARCHAR(1000) NOT NULL,
    content_type VARCHAR(100),
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata_json JSONB,
    file_size BIGINT,
    file_data BYTEA
);

-- Indexes
CREATE INDEX IF NOT EXISTS supplier_declarations_sku_idx ON supplier_declarations (sku);
CREATE INDEX IF NOT EXISTS supplier_declarations_material_idx ON supplier_declarations (material);
CREATE INDEX IF NOT EXISTS supplier_declarations_metadata_json_gin ON supplier_declarations USING gin (metadata_json);