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
from backend.pipeline import initialize_azure_models, run_ppwr_pipeline, extract_regulatory_mentions_windows
from backend.models import Result, MaterialSchema, IngestRequest, SessionLocal, PPWRResult, PFASBOM, MaterialDeclarationLink, init_backend_db, PPWRBOM, PPWRMaterialDeclarationLink, SupplierDeclarationV1
import backend.models as models
from backend.queries import queries   # your queries dict with per-field prompts

# Import PPWR queries with fallback
try:
    from backend.queries import ppwr_queries
except (ImportError, AttributeError):
    logging.warning("⚠️ ppwr_queries not found in queries.py, using default prompts")
    ppwr_queries = {
        'system': 'You are a PPWR compliance extraction assistant.',
        'flags': 'Extract compliance flags: ppwr_compliant (boolean), packaging_recyclability, recycled_content_percent.',
        'notes': 'Extract any compliance notes or observations.',
        'mentions': 'Find regulatory mentions: PPWD 94/62/EC, Lead, Cadmium, Hexavalent Chromium.'
    }

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

# Health check endpoint for Docker container monitoring
@app.get("/health")
def health_check():
    """Health check endpoint for container orchestration."""
    try:
        # Verify database connection
        session = SessionLocal()
        session.execute("SELECT 1")
        session.close()
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "service": "pfas_fastapi",
            "database": "connected"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "service": "pfas_fastapi",
                "error": str(e)
            }
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


@app.post("/ppwr/index-declaration", summary="Index supplier declaration PDF into ChromaDB for RAG")
async def ppwr_index_declaration(
    file: UploadFile = File(...),
    material_id: str = Form(...),
    sku: str = Form(...),
    metadata: str = Form(None)
):
    """Extract text from PDF, chunk, embed, and store in ChromaDB with rich metadata."""
    try:
        logger.info(f"🔄 Starting ChromaDB indexing for material_id={material_id}, sku={sku}")
        
        # Read PDF bytes
        file_bytes = await file.read()
        if not file_bytes:
            return JSONResponse(status_code=400, content={'success': False, 'error': 'Empty file'})
        
        # Extract text using PyPDF2
        from backend.retriever import extract_text_from_pdf_bytes, chunk_text_by_words
        text_content = extract_text_from_pdf_bytes(file_bytes)
        if not text_content or len(text_content.strip()) < 50:
            return JSONResponse(status_code=400, content={'success': False, 'error': 'No extractable text in PDF'})
        
        logger.info(f"📄 Extracted {len(text_content)} characters from {file.filename}")
        
        # Parse BOM metadata
        bom_meta = {}
        try:
            if metadata:
                bom_meta = json.loads(metadata)
        except Exception:
            bom_meta = {}
        
        # Initialize Azure models and ChromaDB
        embedder, llm = initialize_azure_models()
        config_loader = get_config_loader()
        
        chroma_host = config_loader.get("storage", "chroma", "host")
        chroma_port = config_loader.get("storage", "chroma", "port")
        ppwr_collection_name = config_loader.get("storage", "chroma", "ppwr_collection_name", default="PPWR_Supplier_Declarations")
        
        client = connect_chromadb(chroma_host, chroma_port)
        collection = client.get_or_create_collection(name=ppwr_collection_name)
        
        logger.info(f"📂 Using ChromaDB collection: {ppwr_collection_name}")
        
        # Chunk text (300 words, 50 overlap)
        chunk_size = config_loader.get("storage", "chunking", "size", default=300)
        chunk_overlap = config_loader.get("storage", "chunking", "overlap", default=50)
        
        chunks = chunk_text_by_words(text_content, size=chunk_size, overlap=chunk_overlap)
        logger.info(f"✂️ Created {len(chunks)} chunks from PDF")
        
        # Embed chunks and upsert to ChromaDB
        chunks_created = 0
        upload_timestamp = datetime.utcnow().isoformat()
        
        for i, chunk_text in enumerate(chunks):
            try:
                # Generate embedding
                embedding = embedder.embed(chunk_text)
                
                # Build rich metadata
                chunk_metadata = {
                    "material_id": material_id,
                    "material_name": bom_meta.get("material_name", ""),
                    "sku": sku,
                    "supplier_name": bom_meta.get("supplier_name", ""),
                    "component": bom_meta.get("component", ""),
                    "subcomponent": bom_meta.get("subcomponent", ""),
                    "filename": file.filename,
                    "upload_date": upload_timestamp,
                    "chunk_id": i,
                    "total_chunks": len(chunks),
                    "document_type": "supplier_declaration",
                    "source": "ppwr_portal_upload"
                }
                
                # Unique ID: material_id + chunk sequence
                chunk_id = f"{material_id}_chunk_{i}"
                
                # Upsert to ChromaDB (overwrites if exists)
                collection.upsert(
                    documents=[chunk_text],
                    embeddings=[embedding],
                    metadatas=[chunk_metadata],
                    ids=[chunk_id]
                )
                
                chunks_created += 1
                
            except Exception as e_chunk:
                logger.warning(f"⚠️ Failed to index chunk {i} for {material_id}: {e_chunk}")
                continue
        
        logger.info(f"✅ Successfully indexed {chunks_created}/{len(chunks)} chunks for {material_id}")
        
        return JSONResponse(status_code=200, content={
            'success': True,
            'chunks_created': chunks_created,
            'total_chunks': len(chunks),
            'collection_name': ppwr_collection_name,
            'material_id': material_id,
            'sku': sku
        })
        
    except Exception as e:
        logger.error(f"❌ ChromaDB indexing failed: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={'success': False, 'error': str(e)})


@app.post("/ppwr/assess", summary="RAG-based PPWR assessment using ChromaDB retrieval")
async def ppwr_assess_rag(
    bom_material_ids: str = Form(..., description="Comma-separated material IDs")
):
    """Query ChromaDB for each material's chunks, retrieve relevant context, feed to LLM."""
    try:
        bom_ids = [s.strip() for s in (bom_material_ids or '').split(',') if s.strip()]
        
        if not bom_ids:
            return JSONResponse(status_code=400, content={'success': False, 'error': 'No material IDs provided'})
        
        logger.info(f"🔍 Starting RAG-based PPWR assessment for {len(bom_ids)} materials")
        
        # Initialize models and ChromaDB
        embedder, llm = initialize_azure_models()
        config_loader = get_config_loader()
        
        chroma_host = config_loader.get("storage", "chroma", "host")
        chroma_port = config_loader.get("storage", "chroma", "port")
        ppwr_collection_name = config_loader.get("storage", "chroma", "ppwr_collection_name", default="PPWR_Supplier_Declarations")
        
        client = connect_chromadb(chroma_host, chroma_port)
        collection = client.get_or_create_collection(name=ppwr_collection_name)
        
        logger.info(f"📂 Connected to ChromaDB collection: {ppwr_collection_name}")
        
        # Process each material
        session = SessionLocal()
        inserted = updated = skipped = 0
        skipped_reasons = []
        
        for material_id in bom_ids:
            try:
                logger.info(f"🔍 Processing material_id: {material_id}")
                
                # Query ChromaDB for this material's chunks
                query_text = f"Extract PPWR compliance data, material composition, packaging recyclability, and restricted substances for material {material_id}"
                query_embedding = embedder.embed(query_text)
                
                # Retrieve top 5 most relevant chunks
                results = collection.query(
                    query_embeddings=[query_embedding],
                    n_results=5,
                    where={"material_id": material_id}
                )
                
                if not results or not results.get('documents') or not results['documents'][0]:
                    logger.warning(f"⚠️ No chunks found in ChromaDB for {material_id}")
                    skipped += 1
                    skipped_reasons.append({'material_id': material_id, 'reason': 'no_indexed_chunks'})
                    continue
                
                # Build context from retrieved chunks
                retrieved_chunks = results['documents'][0]
                context = "\n\n".join(retrieved_chunks)
                
                logger.info(f"📄 Retrieved {len(retrieved_chunks)} chunks ({len(context)} chars) for {material_id}")
                
                # Feed context to LLM with PPWR prompts
                system_prompt = ppwr_queries.get('system', '')
                flags_prompt = ppwr_queries.get('flags', '')
                notes_prompt = ppwr_queries.get('notes', '')
                mentions_prompt = ppwr_queries.get('mentions', '')
                
                combined_prompt = f"""You are a PPWR compliance extraction assistant.

Extract the following from the supplier declaration context:
1. Material identification (material_id, supplier_name)
2. Compliance flags (ppwr_compliant: true/false)
3. Packaging data (recyclability, recycled_content_percent)
4. Restricted substances (list with concentrations)
5. Regulatory mentions (keywords like PPWD 94/62/EC, Lead, Cadmium)

Context:
{context}

{flags_prompt}

{notes_prompt}

{mentions_prompt}

Return JSON only."""
                
                llm_resp = llm.generate(
                    prompt=combined_prompt,
                    context="",
                    question=query_text,
                    temperature=0.2,
                    max_tokens=1024
                )
                
                logger.info(f"💬 LLM response for {material_id}: {llm_resp[:200]}...")
                
                # Parse LLM response
                items = parse_llm_response(llm_resp)
                normalized = parse_ppwr_output(items)
                
                # Extract regulatory mentions using regex patterns
                fallback_mentions = extract_regulatory_mentions_windows(context, line_window=50)
                
                if not normalized:
                    normalized = [{
                        'material_id': material_id,
                        'supplier_name': None,
                        'ppwr_compliant': None,
                        'restricted_substances': [],
                        'regulatory_mentions': fallback_mentions
                    }]
                else:
                    # Merge LLM mentions with regex-detected mentions
                    for rec in normalized:
                        existing_mentions = rec.get('regulatory_mentions', []) or []
                        merged_mentions = []
                        seen = set()
                        for m in existing_mentions + fallback_mentions:
                            if isinstance(m, dict):
                                key = (str(m.get('keyword', '')).lower(), str(m.get('text', ''))[:50])
                                if key not in seen:
                                    merged_mentions.append(m)
                                    seen.add(key)
                        rec['regulatory_mentions'] = merged_mentions
                
                # Upsert to ppwr_result table (unified RAG + manual data)
                for rec in normalized:
                    mid = rec.get('material_id') or material_id
                    
                    # Schema mapping: complex PPWRAssessment → simple ppwr_result
                    # Join restricted substances array to comma-separated string
                    restricted_list = rec.get('restricted_substances', []) or []
                    chemical = ', '.join(restricted_list) if restricted_list else rec.get('chemical')
                    
                    # Map ppwr_compliant boolean to status enum
                    ppwr_compliant = rec.get('ppwr_compliant')
                    if ppwr_compliant is None:
                        ppwr_compliant = False if len(restricted_list) > 0 else True
                    status = 'Compliant' if ppwr_compliant else 'Non-Compliant'
                    
                    # Extract concentration (use recycled_content_percent or direct concentration)
                    concentration = rec.get('concentration') or rec.get('recycled_content_percent')
                    
                    # Log regulatory mentions (not stored in ppwr_result)
                    reg_mentions = rec.get('regulatory_mentions', []) or []
                    if reg_mentions:
                        logger.info(f"📋 Regulatory mentions for {mid}: {len(reg_mentions)} items")
                    
                    existing = session.query(PPWRResult).filter_by(material_id=mid).first()
                    
                    payload = {
                        'material_id': mid,
                        'supplier_name': rec.get('supplier_name'),
                        'cas_id': rec.get('cas_id'),
                        'chemical': chemical,
                        'concentration': float(concentration) if concentration is not None else None,
                        'status': status
                    }
                    
                    if existing:
                        for k, v in payload.items():
                            setattr(existing, k, v)
                        updated += 1
                    else:
                        session.add(PPWRResult(**payload))
                        inserted += 1
                
                session.commit()
                logger.info(f"✅ Processed {material_id} successfully")
                
            except Exception as e_mat:
                logger.error(f"❌ Failed to process {material_id}: {e_mat}", exc_info=True)
                skipped += 1
                skipped_reasons.append({'material_id': material_id, 'reason': str(e_mat)})
                continue
        
        return JSONResponse(status_code=200, content={
            'success': True,
            'inserted': inserted,
            'updated': updated,
            'skipped': skipped,
            'skipped_reasons': skipped_reasons
        })
        
    except Exception as e:
        logger.error(f"❌ RAG-based PPWR assessment failed: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={'success': False, 'error': str(e)})


@app.get("/ppwr/assessments", summary="Fetch PPWR results by material_id")
def get_ppwr_assessments(material_id: Optional[str] = None):
    try:
        session = models.SessionLocal()
        q = session.query(PPWRResult)
        if material_id:
            q = q.filter(PPWRResult.material_id == material_id)
        rows = q.all()
        items = []

        for r in rows:
            items.append({
                'material_id': r.material_id,
                'supplier_name': r.supplier_name,
                'cas_id': r.cas_id,
                'chemical': r.chemical,
                'concentration': r.concentration,
                'status': r.status,
            })
        return JSONResponse(status_code=200, content={'success': True, 'assessments': items})
    except Exception as e:
        logger.error(f"PPWR results fetch failed: {e}", exc_info=True)
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
        # Join PPWRResult + PPWRBOM to get complete evaluation data
        results = session.query(
            PPWRBOM.component,
            PPWRBOM.subcomponent,
            PPWRBOM.material_id,
            PPWRResult.supplier_name,
            PPWRResult.chemical,
            PPWRResult.cas_id,
            PPWRResult.concentration,
            PPWRResult.status
        ).join(
            PPWRResult, PPWRBOM.material_id == PPWRResult.material_id, isouter=True
        ).all()
        
        total_files = len(results)
        files_downloaded = sum(1 for r in results if r.chemical is not None)
        conformance = sum(1 for r in results if r.status and 'compli' in r.status.lower())
        non_conformance = sum(1 for r in results if r.status and 'non' in r.status.lower())

        rows = []
        for r in results:
            rows.append({
                'component': r.component,
                'sub_component': r.subcomponent,
                'material': r.material_id,
                'supplier': r.supplier_name,
                'chemical': r.chemical,
                'cas_number': r.cas_id,
                'concentration': f"{float(r.concentration):.2f}" if r.concentration is not None else None,
                'status': r.status or 'Unknown',
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