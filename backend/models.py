import logging
from typing import List, Dict, Any
from openai import AzureOpenAI
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, String, Numeric, Integer, DateTime, LargeBinary, JSON, Boolean, Float, Text
from sqlalchemy import text as sa_text
from datetime import datetime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from backend.config import Config

DATABASE_URL = Config.SQLALCHEMY_DATABASE_URI
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()
# ======================
# SQLAlchemy Model
# ======================
class Route(Base):
    __tablename__ = 'route'

    sku = Column(String(100), primary_key=True, nullable=False)
    route = Column(String(255), nullable=False, default='ppwr')

class PPWRBOM(Base):
    __tablename__ = 'ppwr_bom'

    material_id = Column(String(100), primary_key=True, nullable=False)
    sku = Column(String(100), nullable=True, index=True)
    product = Column(String(200), nullable=True)
    material_name = Column(String(200), nullable=True)
    supplier_name = Column(String(255), nullable=True, index=True)
    
    # Component/subcomponent columns for evaluation page
    component = Column(String(100), nullable=True)
    component_description = Column(String(500), nullable=True)
    subcomponent = Column(String(200), nullable=True)
    subcomponent_description = Column(String(500), nullable=True)
    
    ppwr_flag = Column(Boolean, nullable=True, default=False)
    uploaded_at = Column(DateTime, nullable=True, default=datetime.utcnow)

class Result(Base):
    __tablename__ = "result"

    material_id = Column(String(100), primary_key=True, nullable=False)
    material_name = Column(String(100))
    cas_number = Column(String(255))
    chemical_name = Column(String(500))
    concentration_ppm = Column(Numeric(10, 4))
    supplier_name = Column(String(255))
    reference_doc = Column(String(255))


# Supplier Declarations stored in backend Postgres (PPWR-related uploads)

# Links a declaration to a material (optionally scoped to SKU), used for fan-out mapping
class MaterialDeclarationLink(Base):
    __tablename__ = "material_declaration_links"

    id = Column(Integer, primary_key=True, autoincrement=True)
    material_id = Column(String(100), index=True, nullable=False)
    decl_id = Column(Integer, index=True, nullable=False)
    sku = Column(String(100), index=True, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class PPWRMaterialDeclarationLink(Base):
    __tablename__ = "ppwr_material_declaration_link"  # Fixed: singular to match database

    id = Column(Integer, primary_key=True, autoincrement=True)
    material_id = Column(String(100), index=True, nullable=False)
    bom_material_id = Column(String(100), index=True, nullable=True)
    decl_material_v1 = Column(Integer, index=True, nullable=False)  # Links to supplier_declaration_v1.id
    flag = Column(Boolean, nullable=True, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


def init_backend_db():
    try:
        Base.metadata.create_all(bind=engine)
        try:
            with engine.begin() as conn:
                # Ensure uploaded_at column exists in ppwr_bom
                conn.execute(sa_text("""
                    ALTER TABLE ppwr_bom
                    ADD COLUMN IF NOT EXISTS uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
                """))
        except Exception as e:
            logging.warning(f"Deferred column ensure (uploaded_at) failed: {e}")
    except Exception as e:
        logging.warning(f"Deferred DB init (create_all failed): {e}")


# ======================
# PPWR Result Model (PPWR Chemical Data)
# ======================
class PPWRResult(Base):
    __tablename__ = 'ppwr_result'

    material_id = Column(String(100), primary_key=True, nullable=False)
    cas_id = Column(String(255), nullable=True)
    supplier_name = Column(String(255), nullable=True)
    status = Column(String(100), nullable=True, index=True)
    chemical = Column(String(500), nullable=True)
    concentration = Column(Float, nullable=True)


# ======================
# Supplier Declaration V1 (PDF Storage)
# ======================
class SupplierDeclarationV1(Base):
    __tablename__ = 'supplier_declaration_v1'

    id = Column(Integer, primary_key=True, autoincrement=True)
    material_id = Column(String(100), index=True, nullable=True)
    material_name = Column(String(200), nullable=True)
    original_filename = Column(String(255), nullable=True)
    document_type = Column(String(50), nullable=True)
    file_size = Column(Integer, nullable=True)
    file_data = Column(LargeBinary, nullable=True)
    upload_date = Column(DateTime, nullable=True, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

def _ensure_tables_once():
    """Ensure all tables are created (idempotent)"""
    try:
        Base.metadata.create_all(bind=engine)
        logging.info("Backend tables ensured via create_all")
    except Exception as e:
        logging.warning(f"Deferred DB init (create_all failed): {e}")


# ======================
# Pydantic Schemas
# ======================
class MaterialSchema(BaseModel):
    material_id: str
    material_name: str = ""
    cas_number: str = ""
    chemical_name: str = ""
    quantity: str
    supplier_name: str


class IngestRequest(BaseModel):
    material_id: str


# -------------------------
# AZURE OPENAI EMBEDDER CLASS
# -------------------------
class AzureEmbedder:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.client = AzureOpenAI(
            api_key=config["api_key"],
            api_version="2023-05-15",
            azure_endpoint=config["base_url"].strip(),
            azure_deployment=config["deployment_name"]
        )
        self.model = config["model"]
        logging.info(f"Azure Embedder initialized with model: {self.model}")

    def embed(self, text: str) -> List[float]:
        """Generate embeddings for given text"""
        try:
            response = self.client.embeddings.create(
                input=text,
                model=self.model
            )
            return response.data[0].embedding
        except Exception as e:
            logging.error(f"Error generating embedding: {e}")
            raise e

# -------------------------
# AZURE OPENAI LLM CLASS
# -------------------------
class AzureLLM:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.client = AzureOpenAI(
            api_key=config["api_key"],
            api_version=config.get("model_version", "2025-01-01-preview"),
            azure_endpoint=config["base_url"].strip(),
            azure_deployment=config["deployment_name"]
        )
        self.model = config["model"]
        logging.info(f"Azure LLM initialized with model: {self.model}")

    def generate(self, prompt: str, context: str, question: str, temperature: float = 0.4, max_tokens: int = 2048) -> str:
        """Generate response using Azure OpenAI"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            logging.error(f"Error generating LLM response: {e}")
            raise e
