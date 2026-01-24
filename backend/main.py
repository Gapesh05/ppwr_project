from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from typing import List, Optional
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from pathlib import Path
from io import BytesIO
import os
import logging
import traceback
import sys
import json
import hashlib

from backend.get_data import get_file_upload_by_material_id
from backend.retriever import connect_chromadb, get_collection, retrieve_documents, extract_text_from_pdf_bytes
from backend.parse_llm import parse_llm_response
from backend.config import get_config_loader
from backend.pipeline import initialize_azure_models, run_ppwr_pipeline
from backend.models import Result, MaterialSchema, IngestRequest, SessionLocal, PPWRAssessment, PFASBOM, MaterialDeclarationLink, init_backend_db, PPWRBOM, PPWRMaterialDeclarationLink
import backend.models as models
from backend.queries import queries   # your queries dict with per-field prompts

# ======================
# Configure logger
# ======================
logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)

# ======================
# FastAPI App
# ======================
app = FastAPI(title="PFAS Auto-Ingest API")

# Allow CORS for local frontend during development (adjust origins as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5000", "http://127.0.0.1:5000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Azure models once at startup
try:
    embedder, llm = initialize_azure_models()
    logger.info("✅ Azure models initialized successfully.")
except Exception as e:
    logger.error(f"❌ Failed to initialize Azure models: {e}")
    embedder = llm = None


@app.on_event("startup")
def _startup_db_init():
    try:
        from backend.models import init_backend_db
        init_backend_db()
        logger.info("✅ Database tables ensured on startup.")
    except Exception as e:
        logger.warning(f"⚠️ Skipping DB init on startup: {e}")


@app.on_event("startup")
def _startup_init_db():
    try:
        init_backend_db()
        logger.info("✅ Backend DB metadata ensured (create_all attempted).")
    except Exception as e:
        logger.warning(f"⚠️ DB init skipped: {e}")


# ---------------------
# Simple text chunker
# ---------------------
def _chunk_text(text: str, size: int, overlap: int) -> list[str]:
    if not text:
        return []
    words = text.split()
    if not words:
        return []
    chunks = []
    step = max(size - overlap, 1)
    i = 0
    while i < len(words):
        chunks.append(" ".join(words[i:i+size]))
        i += step
    return chunks


@app.post("/ingest", summary="Auto-extract and save material data using multi-query pipeline")
def ingest_data(request: IngestRequest):
    logger.info(f"🚀 Starting ingestion for material_id: {request.material_id}")

    if not embedder or not llm:
        logger.error("❌ Azure models not initialized")
        raise HTTPException(status_code=503, detail="Azure models not initialized. Check logs.")

    try:
        # ----------------------
        # STEP 1: Lookup file record
        # ----------------------
        material_id = request.material_id
        file_record = get_file_upload_by_material_id(material_id)
        if not file_record:
            logger.warning(f"⚠️ No file record found for material_id: {material_id}")
            return {
                "flag": False,
                "success": True,
                "message": f"No file record found for material_id {material_id}.",
                "saved_materials": []
            }

        filename = file_record.get("filename", "")
        collection_name = file_record["collection-name"]
        logger.info(f"✅ Found collection_name: {collection_name} for material_id: {material_id}")

        # ----------------------
        # STEP 2: Runtime config
        # ----------------------
        config_loader = get_config_loader()
        runtime_config = {
            "embedder": embedder,
            "llm": llm,
            "chroma_host": config_loader.get("storage", "chroma", "host"),
            "chroma_port": config_loader.get("storage", "chroma", "port"),
            "max_results": config_loader.get("generation", "max_results", default=5),
            "temperature": config_loader.get("generation", "temperature", default=0.4),
            "max_tokens": config_loader.get("generation", "max_tokens", default=2048)
        }

        # ----------------------
        # Connect to ChromaDB
        # ----------------------
        logger.info(f"📡 Connecting to ChromaDB at {runtime_config['chroma_host']}:{runtime_config['chroma_port']}")
        client = connect_chromadb(runtime_config["chroma_host"], runtime_config["chroma_port"])
        collection = get_collection(client, collection_name)
        logger.info(f"📂 Using ChromaDB collection: {collection_name}")

        # ----------------------
        # STEP 3: Run loop over all queries and collect parsed responses
        # ----------------------
        fieldwise_results = {}  # field -> list[dict]

        for field, config in queries.items():
            query_text = config["query"]
            field_prompt = config["prompt"]

            logger.info(f"🧠 Running retrieval + LLM for field '{field}': {query_text}")

            # Generate embedding and retrieve relevant chunks
            try:
                embedding = embedder.embed(query_text)
            except Exception as e_embed:
                logger.error(f"❌ Embedding failed for field '{field}': {e_embed}")
                fieldwise_results[field] = []
                continue

            results = retrieve_documents(
                collection=collection,
                embedding=embedding,
                filter_values=None,
                where_filter="",
                where_document="",
                max_results=runtime_config["max_results"],
                full_document_search="No"
            )

            # Extract and log chunks
            retrieved_chunks = []
            context_texts = []
            if results and "documents" in results:
                for i, doc_list in enumerate(results["documents"]):
                    for j, doc in enumerate(doc_list):
                        chunk_info = {
                            "document": doc,
                            "metadata": results["metadatas"][i][j] if results.get("metadatas") else {},
                            "distance": results["distances"][i][j] if results.get("distances") else None
                        }
                        retrieved_chunks.append(chunk_info)
                        context_texts.append(doc)

            # Log retrieved chunks
            logger.info(f"🧩 Retrieved {len(retrieved_chunks)} chunk(s) for query '{field}':")
            for idx, chunk in enumerate(retrieved_chunks):
                logger.info(f"  Chunk {idx + 1}:")
                logger.info(f"    Distance: {chunk.get('distance', 'N/A')}")
                logger.info(f"    Metadata: {chunk.get('metadata', {})}")
                snippet = (chunk['document'][:200] + '...') if len(chunk['document']) > 200 else chunk['document']
                logger.info(f"    Snippet: {snippet}")

            # FIXED: Create isolated context for each field
            field_context = "\n\n".join(context_texts)
            
            # FIXED: Content-filter safe prompt
            isolated_prompt = f"""You are a data extraction assistant specializing in document analysis.

Please analyze the following document content and extract the requested information.

Document Content:
{field_context}

Task: Extract {field} information
Query: {query_text}

Instructions:
{field_prompt}

Please focus on extracting the {field} data from the document above."""

            # FIXED: Call LLM with empty context to prevent contamination
            try:
                llm_response = llm.generate(
                    prompt=isolated_prompt,
                    context="",  # Empty context prevents contamination
                    question=query_text,
                    temperature=runtime_config["temperature"],
                    max_tokens=runtime_config["max_tokens"]
                )
                logger.info(f"💬 Raw LLM response for {field}: {llm_response}")
            except Exception as e_llm:
                logger.error(f"❌ LLM generation failed for field '{field}': {e_llm}")
                fieldwise_results[field] = []
                continue

            # Parse LLM output
            try:
                parsed_result = parse_llm_response(llm_response) or []
                logger.info(f"🧩 Parsed result for {field}: {parsed_result}")
            except Exception as e_parse:
                logger.error(f"❌ Parsing LLM response failed for field '{field}': {e_parse}")
                parsed_result = []

            fieldwise_results[field] = parsed_result

        # ----------------------
        # STEP 4: Consolidate field-wise results into material records
        # ----------------------
        any_parsed = any(len(v) for v in fieldwise_results.values())
        if not any_parsed:
            return {
                "flag": False,
                "success": True,
                "message": "No materials extracted from document.",
                "saved_materials": []
            }

        max_len = max(len(v) for v in fieldwise_results.values() if v)
        consolidated = []
        for i in range(max_len):
            rec = {}
            for field, values in fieldwise_results.items():
                if i < len(values) and isinstance(values[i], dict):
                    rec.update(values[i])
            if rec:
                consolidated.append(rec)

        # Log consolidated data
        logger.info(f"🗃️ Consolidated Material Records ({len(consolidated)} total):")
        for idx, rec in enumerate(consolidated):
            logger.info(f"  Record {idx + 1}: {rec}")

        # ----------------------
        # STEP 5: Validate & Save/Update all consolidated materials
        # ----------------------
        session = models.SessionLocal()
        saved_materials = []
        saved_count = 0
        total_consolidated = len(consolidated)
        result_dicts = []

        try:
            for mat_dict in consolidated:
                try:
                    validated = MaterialSchema(**mat_dict)
                except Exception as e_val:
                    logger.warning(f"⚠️ Skipping invalid material: {mat_dict} | Error: {e_val}")
                    continue

                ppm_value = None
                if validated.quantity:
                    qstr = str(validated.quantity).lower().replace("ppm", "").strip()
                    try:
                        ppm_value = float(qstr) if qstr != "" else None
                    except ValueError:
                        logger.warning(f"⚠️ Could not parse quantity to float for material {validated.material_id}: '{validated.quantity}'")

                new_record = Result(
                    material_id=validated.material_id,
                    material_name=validated.material_name,
                    cas_number=validated.cas_number,
                    chemical_name=validated.chemical_name,
                    concentration_ppm=ppm_value,
                    supplier_name=validated.supplier_name,
                    reference_doc=filename
                )

                existing = session.query(Result).filter_by(material_id=validated.material_id).first()
                if existing:
                    logger.info(f"🔄 Updating existing record for material_id: {validated.material_id}")
                    for key, value in new_record.__dict__.items():
                        if key != "_sa_instance_state":
                            setattr(existing, key, value)
                    session.flush()
                    saved_materials.append(existing)
                else:
                    logger.info(f"🆕 Inserting new record for material_id: {validated.material_id}")
                    session.add(new_record)
                    session.flush()
                    saved_materials.append(new_record)

                # Build result_dicts while session is still open
                d = {
                    "material_id": new_record.material_id,
                    "material_name": new_record.material_name,
                    "cas_number": new_record.cas_number,
                    "chemical_name": new_record.chemical_name,
                    "quantity": f"{float(new_record.concentration_ppm)} ppm" if new_record.concentration_ppm is not None else "",
                    "supplier_name": new_record.supplier_name
                }
                result_dicts.append(d)
                saved_count += 1

                # Log saved material
                logger.info(f"💾 Saved Record: {d}")

            session.commit()
            logger.info("✅ Database commit successful")
        except Exception as e_db:
            session.rollback()
            logger.error(f"❌ Database save error: {e_db}\n{traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=f"Database save error: {str(e_db)}")
        finally:
            session.close()

        # ----------------------
        # Build final response
        # ----------------------
        flag = (saved_count == total_consolidated and total_consolidated > 0)

        return {
            "flag": flag,
            "success": True,
            "message": f"{saved_count} materials processed and saved.",
            "saved_materials": result_dicts
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"🔥 Ingestion failed: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@app.post("/ppwr/supplier-declarations/upload", summary="Deprecated: Storage moved to Flask-only")
async def ppwr_supplier_declarations_upload(
    file: UploadFile = File(...),
    sku: str = Form(None),
    material_id: str = Form(None),
    supplier_name: str = Form(None),
    description: str = Form(None),
    index_chunks: str = Form('true')
):
        """This endpoint is deprecated. Use Flask /api/supplier-declarations/upload instead."""
        return JSONResponse(status_code=410, content={"success": False, "error": "Supplier declaration storage moved to Flask. Use /api/supplier-declarations/upload"})

@app.post("/ppwr/admin/reset-mappings", summary="Admin: Clear all declaration-to-material mappings and links")
def ppwr_admin_reset_mappings():
    try:
        session = models.SessionLocal()
        try:
            # Delete all mapping link rows (PPWR). Declaration storage moved to Flask.
            session.query(PPWRMaterialDeclarationLink).delete()
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Reset mappings failed: {e}", exc_info=True)
            return JSONResponse(status_code=500, content={"success": False, "error": str(e)})
        finally:
            session.close()
        return JSONResponse(status_code=200, content={"success": True, "message": "All mappings cleared"})
    except Exception as e:
        logger.error(f"Admin reset endpoint error: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

 

@app.get("/ppwr/supplier-declarations", summary="Deprecated: Declarations moved to Flask")
def ppwr_supplier_declarations_list(sku: str | None = None, material_id: str | None = None, include_archived: bool = False):
    return JSONResponse(status_code=410, content={'success': False, 'error': 'Supplier declarations moved to Flask. Use frontend /api/supplier-declarations/... endpoints.'})


@app.get("/ppwr/bom-materials", summary="List distinct BOM materials (optionally by SKU)")
def ppwr_bom_materials(sku: Optional[str] = None):
    try:
        session = models.SessionLocal()
        q = session.query(PPWRBOM)
        if sku:
            q = q.filter(PPWRBOM.sku == sku)
        rows = q.all()
        materials = {}
        for r in rows:
            m = (r.material_id or '').strip()
            if not m:
                continue
            materials[m] = materials.get(m, 0) + 1
        items = [{ 'material': k, 'count': v } for k, v in sorted(materials.items())]
        return JSONResponse(status_code=200, content={ 'success': True, 'materials': items })
    except Exception as e:
        logger.error(f"BOM materials list failed: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={'success': False, 'error': str(e)})
    finally:
        try:
            session.close()
        except Exception:
            pass

# Map a declaration to a material_id and optionally fan-out to duplicates
@app.post("/ppwr/supplier-declarations/map", summary="Deprecated: Mapping handled in Flask")
def ppwr_supplier_declarations_map(
    decl_id: int = Form(...),
    material_id: str = Form(...),
    apply_to_duplicates: str = Form('false'),
    scope: str = Form('sku')
):
    return JSONResponse(status_code=410, content={'success': False, 'error': 'Mapping moved to Flask. Use frontend /api/ppwr/supplier-declarations/map.'})


@app.post("/ppwr/assess/from-declaration", summary="Deprecated: Use /ppwr/assess with uploaded files")
async def ppwr_assess_from_declaration(
    decl_id: int = Form(...),
    material_id: str = Form(...)
):
    return JSONResponse(status_code=410, content={'success': False, 'error': 'Use /ppwr/assess with uploaded files. Declaration storage moved to Flask.'})


@app.post("/ppwr/assess", summary="Upload BOM + supplier declarations and run PPWR pipeline")
async def ppwr_assess(
    bom_material_ids: str = Form(..., description="Comma-separated material_id values from BOM"),
    files: List[UploadFile] = File(...)
):
    try:
        bom_ids = [s.strip() for s in (bom_material_ids or '').split(',') if s.strip()]
        pdfs = []
        for uf in files:
            contents = await uf.read()
            pdfs.append({'filename': uf.filename, 'bytes': contents})
        result = run_ppwr_pipeline(bom_material_ids=bom_ids, pdfs=pdfs)
        return JSONResponse(status_code=200, content={'success': True, 'result': result})
    except Exception as e:
        logger.error(f"PPWR assess failed: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={'success': False, 'error': str(e)})


@app.get("/ppwr/assessments", summary="Fetch PPWR assessments by material_id")
def get_ppwr_assessments(material_id: Optional[str] = None):
    try:
        session = models.SessionLocal()
        q = session.query(PPWRAssessment)
        if material_id:
            q = q.filter(PPWRAssessment.material_id == material_id)
        rows = q.all()
        items = []
        def _safe_json(val):
            try:
                return json.loads(val) if isinstance(val, str) else val
            except Exception:
                return val

        for r in rows:
            items.append({
                'material_id': r.material_id,
                'supplier_name': r.supplier_name,
                'declaration_date': r.declaration_date,
                'ppwr_compliant': r.ppwr_compliant,
                'packaging_recyclability': r.packaging_recyclability,
                'recycled_content_percent': r.recycled_content_percent,
                'restricted_substances': _safe_json(r.restricted_substances_json),
                'notes': r.notes,
                'source_path': r.source_path,
                'regulatory_mentions': _safe_json(r.regulatory_mentions_json),
                'created_at': r.created_at.isoformat() if r.created_at else None,
            })
        return JSONResponse(status_code=200, content={'success': True, 'assessments': items})
    except Exception as e:
        logger.error(f"PPWR assessments fetch failed: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={'success': False, 'error': str(e)})
    finally:
        try:
            session.close()
        except Exception:
            pass


@app.get("/ppwr/evaluation/summary", summary="Summary cards + rows for PPWR evaluation UI")
def ppwr_evaluation_summary():
    session = models.SessionLocal()
    try:
        assessments = session.query(PPWRAssessment).all()
        total_files = len(assessments)
        files_downloaded = total_files
        conformance = sum(1 for a in assessments if a.ppwr_compliant)
        non_conformance = sum(1 for a in assessments if a.ppwr_compliant is False)

        rows = []
        for a in assessments:
            chem = session.query(Result).filter(Result.material_id == a.material_id).first()
            rows.append({
                'component': None,
                'sub_component': None,
                'material': a.material_id,
                'supplier': a.supplier_name,
                'chemical': chem.chemical_name if chem else None,
                'cas_number': chem.cas_number if chem and chem.cas_number else None,
                'concentration': f"{float(chem.concentration_ppm)} ppm" if chem and chem.concentration_ppm is not None else None,
                'status': 'Compliance' if a.ppwr_compliant else 'Non-Conformance',
            })

        return JSONResponse(status_code=200, content={
            'success': True,
            'stats': {
                'total_files': total_files,
                'files_downloaded': files_downloaded,
                'conformance': conformance,
                'non_conformance': non_conformance,
            },
            'rows': rows,
        })
    except Exception as e:
        logger.error(f"PPWR evaluation summary failed: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={'success': False, 'error': str(e)})
    finally:
        try:
            session.close()
        except Exception:
            pass

@app.get("/ppwr/supplier-declarations/download/{decl_id}", summary="Deprecated: Download via Flask frontend")
def ppwr_supplier_declarations_download(decl_id: int):
    return JSONResponse(status_code=410, content={'success': False, 'error': 'Download moved to Flask. Use /api/supplier-declarations/download/<material_id> on frontend.'})