-- Create PPWR-specific BOM table, decoupled from PFAS
CREATE TABLE IF NOT EXISTS ppwr_bom (
    material_id VARCHAR(100) PRIMARY KEY,
    sku VARCHAR(100),
    material_name VARCHAR(200),
    supplier_name VARCHAR(255),
    ppwr_flag BOOLEAN DEFAULT FALSE,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ppwr_bom_sku ON ppwr_bom (sku);

-- Create PPWR-specific material-declaration link table
CREATE TABLE IF NOT EXISTS ppwr_material_declaration_links (
    id SERIAL PRIMARY KEY,
    material_id VARCHAR(100) NOT NULL,
    decl_id INTEGER NOT NULL,
    sku VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ppwr_links_material ON ppwr_material_declaration_links (material_id);
CREATE INDEX IF NOT EXISTS idx_ppwr_links_decl ON ppwr_material_declaration_links (decl_id);
