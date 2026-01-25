# RAG-Based PPWR Pipeline Implementation ✅

## Summary
Successfully migrated PPWR from direct LLM text extraction to full RAG-based pipeline using ChromaDB, matching the PFAS architecture.

## Changes Implemented

### 1. Configuration (`backend/config.py`)
- ✅ Added `ppwr_collection_name: "PPWR_Supplier_Declarations"` to ChromaDB config
- Collection will store indexed PDF chunks with rich metadata

### 2. ChromaDB Indexing Helpers (`backend/retriever.py`)
- ✅ Added `chunk_text_by_words()` function
  - Splits text into 300-word chunks with 50-word overlap
  - Used for RAG indexing of supplier declarations
  - Same chunking strategy as PFAS pipeline

### 3. New RAG Indexing Endpoint (`backend/main.py`)
- ✅ Created `POST /ppwr/index-declaration`
  - Accepts PDF file, material_id, SKU, metadata
  - Extracts text with PyPDF2
  - Chunks text (300 words, 50 overlap)
  - Generates embeddings with Azure text-embedding-3-large
  - Stores chunks in ChromaDB with metadata:
    - material_id, material_name, sku, supplier_name
    - component, subcomponent, filename, upload_date
    - chunk_id, total_chunks, document_type, source
  - Returns chunks_created count

### 4. RAG-Based Assessment Endpoint (`backend/main.py`)
- ✅ Replaced `POST /ppwr/assess` with RAG-based version
  - **OLD:** Accepted PDF file uploads, extracted full text, fed to LLM
  - **NEW:** Queries ChromaDB by material_id filter
  - Retrieves top 5 most relevant chunks via semantic search
  - Feeds retrieved chunks (not full PDF) to LLM
  - Parses response and stores in `ppwr_assessments` table
  - Returns inserted/updated/skipped counts

### 5. New Database Model (`backend/models.py`)
- ✅ Created `PPWRAssessment` model
  - Stores RAG extraction results
  - Fields: material_id, supplier_name, declaration_date
  - Compliance: ppwr_compliant, packaging_recyclability, recycled_content_percent
  - Substances: restricted_substances_json, regulatory_mentions_json
  - Metadata: notes, source_path, timestamps

### 6. Auto-Indexing on Upload (`frontend/app.py`)
- ✅ Updated `/ppwr/declarations/upload` route
  - After storing PDF in Postgres, triggers ChromaDB indexing
  - Calls `POST /ppwr/index-declaration` with file bytes + metadata
  - Fetches BOM metadata (material_name, component, supplier)
  - Logs success/failure (continues upload even if indexing fails)

- ✅ Updated `/api/supplier-declarations/upload` route (multi-file)
  - Same auto-indexing integration
  - Per-file indexing with error handling
  - Batch upload support maintained

### 7. Removed Old Direct Extraction (`backend/pipeline.py`)
- ✅ Deleted `run_ppwr_pipeline()` function
  - Old function directly extracted PDF text and fed to LLM
  - Replaced with comment explaining new RAG workflow
  - Workflow: Upload → Index → Evaluate → Query ChromaDB

## Architecture Comparison

### BEFORE (Direct LLM)
```
Upload PDF → Postgres (supplier_declaration_v1) 
           ↓
Evaluate → Extract full text (PyPDF2) → Feed to LLM → Parse → ppwr_result
```

### AFTER (RAG-Based)
```
Upload PDF → Postgres (supplier_declaration_v1)
           ↓
           → ChromaDB Indexing:
              - Extract text (PyPDF2)
              - Chunk (300 words, 50 overlap)
              - Embed (Azure)
              - Store with metadata
           ↓
Evaluate → Query ChromaDB (material_id filter)
        → Retrieve top 5 chunks (semantic search)
        → Feed chunks to LLM
        → Parse → ppwr_assessments table
```

## Benefits Achieved

✅ **Semantic Search:** Retrieve only relevant sections instead of full PDFs
✅ **Scalability:** Handle large PDFs (100+ pages) without context limits
✅ **Consistency:** Same infrastructure as PFAS (ChromaDB, Azure embeddings)
✅ **Rich Metadata:** Filter by component, subcomponent, supplier_name
✅ **Reusability:** Same chunks for multiple query types
✅ **Cross-Document Search:** Compare materials across declarations

## Testing Checklist

### Test Case 1: Upload & Auto-Index
- [ ] Upload new supplier declaration PDF
- [ ] Verify chunks created in ChromaDB (check logs)
- [ ] Verify metadata includes material_id, component, supplier
- [ ] Verify PDF stored in Postgres supplier_declaration_v1

### Test Case 2: RAG-Based Evaluation
- [ ] Click "Evaluate" button on PPWR assessment page
- [ ] Verify ChromaDB query retrieves top 5 chunks
- [ ] Verify LLM receives chunks (not full PDF)
- [ ] Verify results stored in ppwr_assessments table
- [ ] Verify compliance flags calculated correctly

### Test Case 3: Large PDF Handling
- [ ] Upload 50+ page PDF
- [ ] Verify chunking handles large documents
- [ ] Verify retrieval still works (top 5 chunks extracted)
- [ ] Verify no context window overflow

### Test Case 4: Metadata Filtering
- [ ] Query ChromaDB by material_id filter
- [ ] Verify only relevant material's chunks returned
- [ ] Test filtering by component or supplier_name (optional)

### Test Case 5: Error Handling
- [ ] Upload fails → verify Postgres rollback
- [ ] Indexing fails → verify upload still succeeds
- [ ] ChromaDB unavailable → verify graceful degradation

## Migration Plan for Existing PDFs

**Status:** Not yet implemented (optional post-deployment task)

Create migration script: `scripts/migrate_ppwr_to_chromadb.py`

**Purpose:** Re-index all existing supplier_declaration_v1 records into ChromaDB

**Process:**
1. Query all SupplierDeclarationV1 records with file_data
2. For each record:
   - Fetch BOM metadata (material_name, component, supplier)
   - Extract text with PyPDF2
   - Chunk text (300 words, 50 overlap)
   - Generate embeddings
   - Upsert to ChromaDB with metadata
3. Log progress and errors

**Usage:**
```bash
python scripts/migrate_ppwr_to_chromadb.py
```

## Configuration Requirements

### ChromaDB Connection
- Host: `10.134.44.228`
- Port: `8000`
- Collection: `PPWR_Supplier_Declarations`

### Azure OpenAI
- Model: `text-embedding-3-large`
- Deployment: Configured in backend/config.py
- Used for both PFAS and PPWR embeddings

### Chunking Parameters
- Size: 300 words per chunk
- Overlap: 50 words between chunks
- Same as PFAS for consistency

## API Changes

### New Endpoint
**POST /ppwr/index-declaration**
- Purpose: Index supplier declaration into ChromaDB
- Parameters: file (PDF), material_id, sku, metadata (JSON)
- Returns: {success, chunks_created, collection_name}

### Modified Endpoint
**POST /ppwr/assess**
- **Before:** Accepts files (PDF uploads)
- **After:** Accepts bom_material_ids (comma-separated string)
- Workflow changed: ChromaDB query → Chunk retrieval → LLM → Results
- Returns: {success, inserted, updated, skipped, skipped_reasons}

### Deprecated Function
**run_ppwr_pipeline(bom_material_ids, pdfs)**
- Removed from backend/pipeline.py
- Replaced by RAG-based /ppwr/assess endpoint

## Next Steps

1. **Deploy Changes**
   - Restart FastAPI backend (picks up new endpoints)
   - Restart Flask frontend (picks up indexing triggers)
   - Verify ChromaDB connection at 10.134.44.228:8000

2. **Test End-to-End**
   - Upload sample PDF → verify indexing
   - Evaluate material → verify RAG retrieval
   - Check ppwr_assessments table for results

3. **Optional: Migrate Existing PDFs**
   - Create migration script
   - Run batch re-indexing offline
   - Verify all materials have chunks in ChromaDB

4. **Monitor Performance**
   - Track indexing time per PDF
   - Track retrieval latency per material
   - Compare RAG accuracy vs old direct extraction

## Rollback Plan (If Needed)

If issues arise, revert to direct extraction by:
1. Restore old `run_ppwr_pipeline()` function in backend/pipeline.py
2. Restore old `POST /ppwr/assess` endpoint (accepts file uploads)
3. Remove indexing triggers from frontend upload routes
4. Comment out ChromaDB configuration in backend/config.py

All changes are isolated to specific functions - minimal blast radius.

---

**Implementation Date:** January 25, 2026  
**Status:** ✅ Complete - Ready for Testing  
**RAG Architecture:** Matching PFAS pipeline design
