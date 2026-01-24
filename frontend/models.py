from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Route(db.Model):
    __tablename__ = 'route'
    
    # Minimal routing table: only sku and route columns
    sku = db.Column(db.String(100), primary_key=True)
    route = db.Column(db.String(255), nullable=False, default='ppwr')


class PPWRBOM(db.Model):
    __tablename__ = 'ppwr_bom'

    # Minimal PPWR BOM schema, decoupled from PFAS
    # Use material_id as primary key to keep rows unique per material for PPWR flows
    material_id = db.Column(db.String(100), primary_key=True)
    # Optional fields for convenience and display
    sku = db.Column(db.String(100), nullable=True, index=True)
    material_name = db.Column(db.String(200), nullable=True)
    supplier_name = db.Column(db.String(255), nullable=True)

    # PPWR ingestion/evaluation flag
    ppwr_flag = db.Column(db.Boolean, nullable=True, default=False)

    # Upload timestamp
    uploaded_at = db.Column(db.DateTime, nullable=True, default=datetime.utcnow)


class PFASMaterialChemicals(db.Model):
    __tablename__ = 'result'

    material_id = db.Column(db.String(100), primary_key=True)
    cas_number = db.Column(db.String(255))
    material_name = db.Column(db.String(100))
    chemical_name = db.Column(db.String(500))
    concentration_ppm = db.Column(db.Numeric(10, 4))
    supplier_name = db.Column(db.String(255))
    reference_doc = db.Column(db.String(255))  # ✅ corrected name


class PFASRegulations(db.Model):
    __tablename__ = 'pfas_regulations'
    
    cas_number = db.Column(db.String(255), primary_key=True)
    chemical_name = db.Column(db.String(500))
    molecular_formula = db.Column(db.String(255))
    structure_category_name = db.Column(db.String(255))
    australian_aics = db.Column(db.Integer)
    australian_imap_tier_2 = db.Column(db.Integer)
    canadian_dsl = db.Column(db.Integer)
    canada_pctsr_2012 = db.Column(db.Integer)
    eu_reach_pre_registered = db.Column(db.Integer)
    eu_reach_registered_ppm = db.Column(db.Integer)
    us_epa_tscainventory = db.Column(db.Integer)
    us_epa_tsca12b = db.Column(db.Integer)


class PFASBOMAudit(db.Model):
    __tablename__ = 'pfas_bom_audit'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sku = db.Column(db.String(100))
    product = db.Column(db.String(200))
    component = db.Column(db.String(100))
    component_description = db.Column(db.String(200))
    subcomponent = db.Column(db.String(100))
    subcomponent_description = db.Column(db.String(200))
    material = db.Column(db.String(100))
    material_name = db.Column(db.String(200))
    action = db.Column(db.String(50))  # e.g., 'insert' or 'update' or 'skip'
    details = db.Column(db.String(1000))
    uploaded_at = db.Column(db.DateTime, nullable=True, default=datetime.utcnow)
    # PPWR-specific ingestion flag (separate from PFAS)
    ppwr_flag = db.Column(db.Boolean, default=False)

class PPWRMaterialDeclarationLink(db.Model):
    __tablename__ = 'ppwr_material_declaration_links'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    material_id = db.Column(db.String(100), index=True, nullable=False)
    # In Option B, SupplierDeclaration uses material_id as PK; link table becomes redundant.
    # Kept for backward-compat but no longer authoritative. decl_id is deprecated.
    decl_id = db.Column(db.Integer, index=True, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'material_id': self.material_id,
            'decl_id': self.decl_id,
        }
class SupplierDeclaration(db.Model):
    __tablename__ = 'supplier_declarations'
    # Option B: Use material_id as the primary key (one row per material)
    material_id = db.Column(db.String(100), primary_key=True)
    sku = db.Column(db.String(100), index=True)

    # File naming / storage
    original_filename = db.Column(db.String(255), nullable=False)
    storage_filename = db.Column(db.String(1000), nullable=True)
    file_path = db.Column(db.String(1000), nullable=True)
    document_type = db.Column(db.String(50), nullable=True)

    # Supplier / description metadata
    supplier_name = db.Column(db.String(255), nullable=True)
    description = db.Column(db.Text, nullable=True)

    # Timestamps
    upload_date = db.Column(db.DateTime, nullable=True, default=datetime.utcnow)
    upload_timestamp = db.Column(db.Integer, nullable=True)
    upload_timestamp_ms = db.Column(db.BigInteger, nullable=True)

    # File metadata
    file_size = db.Column(db.BigInteger, nullable=True)
    file_data = db.Column(db.LargeBinary, nullable=True)

    # Flexible JSON metadata
    metadata_json = db.Column(db.JSON, nullable=True)

    # Soft-delete flag
    is_archived = db.Column(db.Boolean, nullable=False, default=False)

    def to_dict(self):
        return {
            'material_id': self.material_id,
            'sku': self.sku,
            'material': self.material_id,
            'original_filename': self.original_filename,
            'storage_filename': self.storage_filename,
            'file_path': self.file_path,
            'document_type': self.document_type,
            'supplier_name': self.supplier_name,
            'description': self.description,
            'upload_date': self.upload_date.isoformat() if self.upload_date else None,
            'upload_timestamp': self.upload_timestamp,
            'upload_timestamp_ms': self.upload_timestamp_ms,
            'file_size': self.file_size,
            'metadata': self.metadata_json,
            'is_archived': getattr(self, 'is_archived', False)
        }


class MaterialDeclarationLink(db.Model):
    __tablename__ = 'material_declaration_links'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    material_id = db.Column(db.String(100), index=True, nullable=False)
    decl_id = db.Column(db.Integer, index=True, nullable=False)
    sku = db.Column(db.String(100), index=True, nullable=True)
    created_at = db.Column(db.DateTime, nullable=True, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'material_id': self.material_id,
            'decl_id': self.decl_id,
            'sku': self.sku,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class UploadAuditLog(db.Model):
    """Record upload processing details for supplier declaration batches.

    This table provides a searchable audit trail of upload attempts and
    outcomes. It's lightweight and optional; fields are nullable to allow
    partial records when errors occur.
    """
    __tablename__ = 'supplier_declaration_audit'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    document_id = db.Column(db.Integer, nullable=True)
    sku = db.Column(db.String(100), index=True)
    filename = db.Column(db.String(1000))
    file_size = db.Column(db.BigInteger)
    file_type = db.Column(db.String(50))
    status = db.Column(db.String(50))
    success = db.Column(db.Boolean, default=False)
    error_message = db.Column(db.String(2000))
    supplier_name = db.Column(db.String(255))
    description = db.Column(db.String(2000))
    upload_date = db.Column(db.DateTime, nullable=True)
    upload_timestamp = db.Column(db.Integer, nullable=True)
    upload_timestamp_ms = db.Column(db.BigInteger, nullable=True)
    upload_iso_format = db.Column(db.String(100))
    upload_date_only = db.Column(db.String(50))
    upload_time_only = db.Column(db.String(50))
    ip_address = db.Column(db.String(100))
    user_agent = db.Column(db.String(1000))
    batch_id = db.Column(db.String(100), index=True)
    batch_position = db.Column(db.Integer)

    total_in_batch = db.Column(db.Integer)
    processing_time_ms = db.Column(db.Integer)

    def to_dict(self):
        return {
            'id': self.id,
            'document_id': self.document_id,
            'sku': self.sku,
            'filename': self.filename,
            'file_size': self.file_size,
            'status': self.status,
            'success': self.success,
            'error_message': self.error_message,
            'supplier_name': self.supplier_name,
            'description': self.description,
            'upload_date': self.upload_date.isoformat() if self.upload_date else None,
            'batch_id': self.batch_id,
            'batch_position': self.batch_position,
            'total_in_batch': self.total_in_batch,
            'processing_time_ms': self.processing_time_ms
        }
