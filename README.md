# PFAS/PPWR Assessment Application

A comprehensive application for PFAS and PPWR (Packaging and Packaging Waste Regulation) assessment using RAG (Retrieval-Augmented Generation) technology.

## Architecture

- **Backend**: FastAPI application with ChromaDB RAG pipeline and Azure OpenAI integration
- **Frontend**: Flask application with web interface for document management
- **Database**: PostgreSQL for data storage
- **Vector Store**: ChromaDB for document embeddings

## Setup Instructions

### Prerequisites

- Docker and Docker Compose
- Python 3.11+
- PostgreSQL database
- ChromaDB instance
- Azure OpenAI API access

### Configuration

1. **Backend Configuration** (`backend/config.py`):
   - Copy `backend/config.py.template` to `backend/config.py`
   - Update the following settings:
     - `storage.chroma.host` - Your ChromaDB host
     - `storage.postgresql.*` - Your PostgreSQL connection details
     - `embeddings.azure.api_key` - Your Azure OpenAI API key
     - `embeddings.azure.base_url` - Your Azure OpenAI endpoint
     - `llms.azure.api_key` - Your Azure OpenAI API key
     - `llms.azure.base_url` - Your Azure OpenAI endpoint

2. **Frontend Configuration** (`frontend/config.py`):
   - Copy `frontend/config.py.template` to `frontend/config.py`
   - Update the following settings:
     - `DB_USER` - Your PostgreSQL username
     - `DB_PASSWORD` - Your PostgreSQL password
     - `DB_HOST` - Your PostgreSQL host
     - `DB_NAME` - Your PostgreSQL database name

3. **Docker Compose** (`docker-compose.yml`):
   - Copy `docker-compose.yml.template` to `docker-compose.yml`
   - Modify environment variables if needed

### Running the Application

```bash
# Build and start containers
docker-compose up --build

# Access the application
# Frontend: http://localhost:5000
# Backend API: http://localhost:8000
# API Documentation: http://localhost:8000/docs
```

### Database Setup

Run migrations (if needed):
```bash
# From frontend directory
python run_migrations.py
```

## Features

- **PFAS Assessment**: Analyze documents for PFAS content
- **PPWR Compliance**: Evaluate packaging against PPWR regulations
- **Document Upload**: Support for PDF documents
- **RAG Pipeline**: Intelligent document retrieval and analysis
- **Bulk Operations**: Process multiple documents
- **OCR Support**: Extract text from images using EasyOCR

## API Endpoints

### Backend (FastAPI - Port 8000)
- `POST /upload-pdf` - Upload and process PDF documents
- `POST /assess-ppwr` - Assess PPWR compliance
- `GET /health` - Health check

### Frontend (Flask - Port 5000)
- `/` - Main dashboard
- `/assessment` - Assessment interface
- `/ppwr_evaluation` - PPWR evaluation interface

## Security Notes

⚠️ **Important**: Never commit the following files to version control:
- `backend/config.py` (contains API keys and database credentials)
- `frontend/config.py` (contains database credentials)
- `docker-compose.yml` (may contain sensitive environment variables)
- `.env` files

These files are excluded via `.gitignore`. Use the `.template` versions as reference.

## Template Files

Configuration templates are provided for reference:
- `backend/config.py.template` - Backend configuration template
- `frontend/config.py.template` - Frontend configuration template
- `docker-compose.yml.template` - Docker Compose template

Copy these templates and fill in your actual values.

## License

Internal use only.
