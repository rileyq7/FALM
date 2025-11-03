# CLAUDE CODE: FALM Production Implementation

Please implement a complete FALM (Federated Agentic LLM Mesh) production system for grant discovery and analysis. This is a distributed AI architecture where specialized agents communicate using structured protocols.

## System Overview

FALM uses multiple specialized NLMs (Nano Language Models) that communicate via SIMP (Structured Inter-Model Protocol) instead of natural language, making it 60% more efficient and 10x faster than traditional approaches.

## Core Architecture Components

1. **Orchestrator**: Routes queries to appropriate domain NLMs
2. **Domain NLMs**: Specialized agents (grants, eligibility, deadlines, applications)
3. **SIMP Protocol**: JSON-based structured messaging between agents
4. **Vector Database**: ChromaDB for semantic search across grant data
5. **Scraping Engine**: Automated data ingestion from web sources and PDFs
6. **Scheduler**: Automatic daily updates of grant sources

## Files to Create

### 1. Main API Server (`falm_production_api.py`)

Create a FastAPI server with:
- SIMP message routing between specialized NLMs
- Vector database integration using ChromaDB
- Web scraping engine with PDF extraction
- MongoDB for metadata storage
- LLM integration (Claude/OpenAI) for response synthesis
- Automatic scheduling for data updates
- Full REST API with endpoints for queries, data ingestion, and management

Key endpoints:
- `POST /api/query` - Process user queries through FALM mesh
- `POST /api/ingest/url` - Scrape and ingest grant data from URLs
- `POST /api/ingest/file` - Bulk import from JSON/CSV
- `POST /api/grants` - Add grants manually
- `POST /api/schedule/source` - Schedule automatic updates
- `GET /api/stats` - System statistics

### 2. Data Ingestion Tool (`falm_data_ingestion.py`)

Create an interactive CLI tool for:
- Loading sample grant data (UK, EU, US)
- Scraping real grant sources from the web
- Importing custom data from files
- Setting up automatic daily updates
- Manual grant entry
- System statistics viewing

Include sample data for:
- UK: Innovate UK, UKRI, Arts Council
- EU: EIC Accelerator, Horizon Europe, LIFE Programme  
- US: NSF SBIR, DOE ARPA-E

### 3. Dependencies (`requirements.txt`)

```
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
anthropic==0.40.0
openai==1.3.0
chromadb==0.4.18
sentence-transformers==2.2.2
pymongo==4.6.0
motor==3.3.2
PyPDF2==3.0.1
pdfplumber==0.10.3
beautifulsoup4==4.12.2
requests==2.31.0
aiohttp==3.9.1
lxml==4.9.3
apscheduler==3.10.4
pandas==2.1.4
numpy==1.26.2
python-dotenv==1.0.0
```

### 4. Setup Script (`setup.sh`)

Bash script that:
- Creates virtual environment
- Installs all dependencies
- Creates necessary directories (data/scraped, data/pdfs, data/silos, chroma_db, logs)
- Generates .env configuration file
- Creates startup script
- Creates test script

### 5. Environment Configuration (`.env`)

```
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
MONGODB_URL=mongodb://localhost:27017
API_HOST=0.0.0.0
API_PORT=8000
MAX_CONCURRENT_SCRAPES=5
SCRAPE_TIMEOUT=30
```

### 6. Startup Script (`start_falm.sh`)

```bash
#!/bin/bash
source venv/bin/activate
python falm_production_api.py
```

### 7. Test Suite (`test_falm.py`)

Create tests for:
- API health check
- Query processing
- Data ingestion
- Statistics retrieval

## Implementation Details

### SIMP Protocol Structure

```json
{
  "version": "1.0",
  "msg_type": "query|response|context_share|error",
  "sender": "agent_id",
  "receiver": "agent_id", 
  "intent": "search|analyze|validate",
  "context": {
    "query": "user query",
    "silos": ["UK", "EU", "US"],
    "filters": {},
    "data": {}
  },
  "embeddings": [0.1, 0.2, ...],
  "timestamp": "2025-10-31T12:00:00Z",
  "correlation_id": "abc123"
}
```

### Grant Data Model

```python
{
  "grant_id": "unique_id",
  "title": "Grant Title",
  "provider": "Provider Name",
  "silo": "UK|EU|US",
  "amount_min": 25000,
  "amount_max": 500000,
  "currency": "GBP|EUR|USD",
  "deadline": "2025-12-31",
  "sectors": ["AI", "Technology"],
  "eligibility": {
    "company_type": "Limited Company",
    "location": ["UK"],
    "min_employees": 1
  },
  "description": "Grant description",
  "application_url": "https://...",
  "supplementary_urls": [...],
  "pdf_documents": [...],
  "metadata": {}
}
```

### Scraping Engine Features

1. **Web Scraping**:
   - Follow links to supplementary pages
   - Extract eligibility requirements
   - Parse deadlines and amounts
   - Identify relevant sectors

2. **PDF Processing**:
   - Extract text from PDFs
   - Cache processed documents
   - Limit to first 10 pages for performance

3. **Link Following**:
   - Configurable depth (max_depth parameter)
   - Focus on relevant keywords (guidance, eligibility, application)
   - Concurrent fetching with rate limiting

## Usage Workflow

1. **Setup**: Run `bash setup.sh`
2. **Start API**: Run `./start_falm.sh`
3. **Load Data**: Run `python falm_data_ingestion.py`
   - Option 1: Load sample data
   - Option 2: Scrape real sources
   - Option 3: Import custom data
4. **Query System**: 
   ```bash
   curl -X POST "http://localhost:8000/api/query" \
     -H "Content-Type: application/json" \
     -d '{"query": "What AI grants are available?"}'
   ```

## Performance Targets

- Response time: <0.5s for simple queries
- Cost: ~$0.013 per query (vs $0.03 traditional)
- Concurrent NLM queries: Up to 10
- Scraping: 5 concurrent pages
- Vector search: <100ms for 10k grants

## Directory Structure

```
falm-production/
├── falm_production_api.py
├── falm_data_ingestion.py
├── requirements.txt
├── setup.sh
├── start_falm.sh
├── test_falm.py
├── .env
├── data/
│   ├── scraped/
│   ├── pdfs/
│   └── silos/
├── chroma_db/
├── logs/
└── venv/
```

## Success Criteria

The system should:
1. Successfully process natural language queries about grants
2. Route queries to appropriate specialized NLMs
3. Aggregate responses from multiple agents
4. Scrape and ingest data from real grant websites
5. Extract and process PDF documents
6. Maintain vector database for semantic search
7. Schedule automatic updates
8. Provide REST API with interactive documentation

Please implement all components following production best practices including error handling, logging, async operations, and modular design. The system should work immediately after running the setup script and be ready for real grant data.
