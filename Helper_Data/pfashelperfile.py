import pandas as pd
from sqlalchemy import create_engine, Column, String, Integer
from sqlalchemy.orm import declarative_base, sessionmaker
import os

# ======================
# CONFIG
# ======================
DB_USER = os.getenv('DB_USER', 'airadbuser')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'Password123')
DB_HOST = os.getenv('DB_HOST', '10.134.44.228')      # host / IP address
DB_PORT = os.getenv('DB_PORT', 5432)
DB_NAME = os.getenv('DB_NAME', 'pfasdb')

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

# ======================
# MODEL
# ======================
class PFASRegulations(Base):
    __tablename__ = 'pfas_regulations'
    cas_number = Column(String(255), primary_key=True)
    chemical_name = Column(String(500))
    molecular_formula = Column(String(255))
    structure_category_name = Column(String(255))
    australian_aics = Column(Integer)
    australian_imap_tier_2 = Column(Integer)
    canadian_dsl = Column(Integer)
    canada_pctsr_2012 = Column(Integer)
    eu_reach_pre_registered = Column(Integer)
    eu_reach_registered_ppm = Column(Integer)
    us_epa_tscainventory = Column(Integer)
    us_epa_tsca12b = Column(Integer)

Base.metadata.create_all(bind=engine)

# ======================
# LOADER FUNCTION
# ======================
def load_regulations_from_excel(filepath: str):
    session = SessionLocal()
    try:
        df = pd.read_excel(filepath, dtype=str).fillna("")

        # Normalize headers
        df.columns = [c.strip().upper().replace("-", "_").replace(" ", "_") for c in df.columns]

        # Mapping Excel -> DB field names
        col_map = {
            "cas_number": "CAS_NUMBER",
            "chemical_name": "CHEMICAL_NAME",
            "molecular_formula": "MOLECULAR_FORMULA",
            "structure_category_name": "STRUCTURE_CATEGORY_NAME",
            "australian_aics": "AUSTRALIAN_AICS",
            "australian_imap_tier_2": "AUSTRALIAN_IMAP_TIER_2",
            "canadian_dsl": "CANADIAN_DSL",
            "canada_pctsr_2012": "CANADA_PCTSR_2012",
            "eu_reach_pre_registered": "EU_REACH_PRE_REGISTERED",
            "eu_reach_registered_ppm": "EU_REACH_REGISTERED_(PPM)",
            "us_epa_tscainventory": "US_EPA_TSCA_INVENTORY",
            "us_epa_tsca12b": "US_EPA_TSCA_12B",
        }

        inserted, updated = 0, 0

        for _, row in df.iterrows():
            cas_number = row.get(col_map["cas_number"])
            if not cas_number:
                continue

            existing = session.query(PFASRegulations).filter_by(cas_number=cas_number).first()

            record_data = {field: row.get(excel_col, "") for field, excel_col in col_map.items() if field != "cas_number"}

            if existing:
                for key, value in record_data.items():
                    setattr(existing, key, value or None)
                updated += 1
            else:
                new_record = PFASRegulations(cas_number=cas_number, **record_data)
                session.add(new_record)
                inserted += 1

        session.commit()
        print(f"✅ Regulations loaded: {inserted} inserted, {updated} updated")

    except Exception as e:
        session.rollback()
        print(f"❌ Error loading regulations: {e}")

    finally:
        session.close()

# ======================
# RUN SCRIPT
# ======================
if __name__ == "__main__":
    excel_path = "Pfas_regulations.xlsx"  # <-- update to your Excel filename
    load_regulations_from_excel(excel_path)
