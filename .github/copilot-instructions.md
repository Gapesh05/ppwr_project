# Copilot Instructions for PFAS/PPWR

Concise guidance for AI agents working in this repo. Stick to current patterns and file structure; prefer environment overrides over source edits.

## Architecture
- Backend FastAPI: [backend/main.py](../backend/main.py)
  - PFAS: `/ingest` runs retrieval with Chroma + Azure LLM, parses fields, upserts to Postgres. See [backend/retriever.py](../backend/retriever.py), [backend/queries.py](../backend/queries.py), [backend/parse_llm.py](../backend/parse_llm.py), [backend/pipeline.py](../backend/pipeline.py).
  - PPWR: supplier declaration upload/list/map/assess endpoints; results in `ppwr_assessments`. Handlers in [backend/main.py](../backend/main.py).
- Frontend Flask UI: [frontend/app.py](../frontend/app.py)
  - Talks to backend via [frontend/fastapi_client.py](../frontend/fastapi_client.py). SQLAlchemy models in [frontend/models.py](../frontend/models.py).
- Storage: Postgres via [backend/config.py](../backend/config.py) / [frontend/config.py](../frontend/config.py); Chroma via `storage.chroma` in [backend/config.py](../backend/config.py). Prompts in [backend/Prompts/](../backend/Prompts).

## Run
- Docker (recommended): [docker-compose.yml](../docker-compose.yml) runs `pfas_fastapi` on 8000 and `pfas_flask` on 5000.
  ```bash
  docker compose up --build
  ```
- Local (ensure DB/Chroma reachable):
  ```bash
  uvicorn backend.main:app --reload --port 8000
  python frontend/app.py
  ```
  Frontend auto-detects `http://127.0.0.1:8000`; override via `FASTAPI_BASE_URL`.

## Config & Env
- Backend DB: set `DATABASE_URL` to override [backend/config.py](../backend/config.py) `SQLALCHEMY_DATABASE_URI`.
- Frontend DBs: `DATABASE_URL` (primary) and `SUPPLIER_DATABASE_URL` for supplier bind (see [frontend/config.py](../frontend/config.py)).
- API base: set `FASTAPI_BASE_URL` for the frontend client.
- Azure/Chroma: values live in [backend/config.py](../backend/config.py). Avoid committing secrets; set envs and update config before running if needed.

## Core Flows
- PFAS ingestion (`/ingest`):
  - Resolve file/collection via [backend/get_data.py](../backend/get_data.py) and `material_id`.
  - Embed query ([backend/pipeline.py](../backend/pipeline.py)), retrieve chunks ([backend/retriever.py](../backend/retriever.py)), prompt per field ([backend/queries.py](../backend/queries.py)), parse JSON-only output ([backend/parse_llm.py](../backend/parse_llm.py)), upsert `result` via [backend/models.py](../backend/models.py).
- PPWR pipeline:
  - Upload: `/ppwr/supplier-declarations/upload`, Map: `/ppwr/supplier-declarations/map`, Assess: `/ppwr/assess/from-declaration` (normalized into `ppwr_assessments`). Frontend proxies via [frontend/fastapi_client.py](../frontend/fastapi_client.py).

## Conventions
- Duplicated models: frontend vs backend; declaration tables differ by design (`supplier_declarations` vs `supplier_declarations_backend`, link table `ppwr_material_declaration_links`).
- Prompts: add new fields under [backend/Prompts/](../backend/Prompts) and extend maps in [backend/queries.py](../backend/queries.py). LLM must return JSON-only.
- Chroma: `collection_name` comes from upload mapping; default `PFAS_10110_PFAS` in config.

## Migrations & Setup
- Backend: tables ensured at startup via `init_backend_db()` in [backend/models.py](../backend/models.py).
- Frontend: migrations in [frontend/db_migrations/](../frontend/db_migrations) with runner [frontend/run_migrations.py](../frontend/run_migrations.py). Many tables also created on app start.

## Useful Scripts
- Frontend smokes: [frontend/scripts/smoke_test_supplier_upload.py](../frontend/scripts/smoke_test_supplier_upload.py), [frontend/scripts/smoke_test_ppwr_upload_ui.py](../frontend/scripts/smoke_test_ppwr_upload_ui.py).
- Root helpers: [scripts/smoke_test_ppwr.py](../scripts/smoke_test_ppwr.py), [scripts/run_ppwr_migration.py](../scripts/run_ppwr_migration.py).

## Pitfalls
- Secrets in config: do not commit changes with secrets; prefer env overrides.
- Cross-service URLs: `FASTAPI_BASE_URL` must match how backend runs (Docker host vs localhost).
- Chroma empties: verify `storage.chroma.host/port` and `collection_name` in [backend/config.py](../backend/config.py).
- PPWR mapping: supply correct `material_id` or map explicitly to avoid assessment fallback.
