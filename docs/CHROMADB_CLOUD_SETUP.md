# ChromaDB Cloud Setup Guide

## Overview

Your FALM system now supports **both local and cloud ChromaDB**:

- **Local** (default): Good for development, data stored locally
- **Cloud**: Production-ready, managed ChromaDB service

Each NLM has its own ChromaDB collection:
- `UK_innovate_uk` - InnovateUK grants
- `EU_horizon_europe` - Horizon Europe grants
- `UK_nihr` - NIHR grants
- `UK_ukri` - UKRI grants

## Step 1: Create ChromaDB Cloud Account

1. Go to https://www.trychroma.com/
2. Sign up for an account
3. Create a new project
4. Note your credentials:
   - **Instance URL**: `your-instance.chromadb.io`
   - **API Key**: `chroma_xxx...`
   - **Tenant**: Usually `default_tenant`
   - **Database**: Usually `default_database`

## Step 2: Configure FALM

Edit your `.env` file:

```bash
# Change mode to cloud
CHROMADB_MODE=cloud

# Add your ChromaDB Cloud credentials
CHROMADB_CLOUD_URL=your-instance.chromadb.io
CHROMADB_API_KEY=chroma_xxx...
CHROMADB_TENANT=default_tenant
CHROMADB_DATABASE=default_database
```

## Step 3: Test Connection

```bash
# Restart your FALM server
python main.py
```

You should see in logs:
```
[innovate_uk] Connecting to ChromaDB Cloud...
[innovate_uk] ChromaDB Cloud connected: your-instance.chromadb.io
[innovate_uk] Vector DB ready: UK_innovate_uk
```

## Step 4: Migrate Existing Data (Optional)

If you have local data you want to migrate:

### Option A: Re-index from Source

```bash
# Your grants are in data/grants/
# Just re-run the indexing with cloud mode enabled
python scripts/seed_data.py
```

### Option B: Export/Import (Advanced)

```python
# export_local.py
import chromadb
import json

# Connect to local
local_client = chromadb.PersistentClient(path="data/nlms/innovate_uk/chroma_db")
collection = local_client.get_collection("UK_innovate_uk")

# Export
results = collection.get()
with open("export.json", "w") as f:
    json.dump(results, f)

# import_cloud.py
import chromadb
import json
import os

# Connect to cloud
cloud_client = chromadb.HttpClient(
    host=os.getenv("CHROMADB_CLOUD_URL"),
    port=443,
    ssl=True,
    headers={"Authorization": f"Bearer {os.getenv('CHROMADB_API_KEY')}"}
)

# Import
with open("export.json") as f:
    data = json.load(f)

collection = cloud_client.get_or_create_collection("UK_innovate_uk")
collection.add(
    ids=data["ids"],
    embeddings=data["embeddings"],
    documents=data["documents"],
    metadatas=data["metadatas"]
)
```

## Architecture

### Local Mode (Development)

```
┌────────────────────────┐
│  FALM Container        │
│  ┌──────────────────┐  │
│  │ InnovateUK NLM   │  │
│  │   ↓              │  │
│  │ ChromaDB         │  │  ← Local filesystem
│  │ (Persistent)     │  │     /data/nlms/
│  └──────────────────┘  │
└────────────────────────┘
```

**Pros:**
- Fast (no network)
- Free
- Good for dev

**Cons:**
- Not shared across containers
- No backups
- Single server only

### Cloud Mode (Production)

```
┌────────────────────────┐     HTTPS
│  FALM Container        ├──────────────┐
│  ┌──────────────────┐  │              │
│  │ InnovateUK NLM   │  │              │
│  │   ↓              │  │              ▼
│  │ ChromaDB Client  │  │    ┌─────────────────────┐
│  │ (HTTP)           │  │    │  ChromaDB Cloud     │
│  └──────────────────┘  │    │                     │
└────────────────────────┘    │  ┌───────────────┐  │
                              │  │ UK_innovate_uk│  │
┌────────────────────────┐    │  │ EU_horizon... │  │
│  FALM Container 2      │───▶│  │ UK_nihr       │  │
│  (Auto-scaled)         │    │  │ UK_ukri       │  │
└────────────────────────┘    │  └───────────────┘  │
                              │                     │
                              │  • Managed service  │
                              │  • Auto backups     │
                              │  • High availability│
                              └─────────────────────┘
```

**Pros:**
- Shared across all containers
- Auto-scaled
- Managed backups
- Multi-region

**Cons:**
- Network latency (~10-50ms)
- Costs money (but cheap)

## Collections Structure

Each NLM creates its own collection:

```python
# InnovateUK NLM
Collection: UK_innovate_uk
├── Document: "Smart Grants: Spring 2025 Support for game-changing..."
│   ├── ID: IUK_SMART_2025_001
│   ├── Embedding: [0.123, 0.456, ...]  (384 dimensions)
│   └── Metadata: {
│         "title": "Smart Grants: Spring 2025",
│         "amount_max": "2000000",
│         "deadline": "2025-03-31",
│         "sectors": "[\"AI & Data\", \"Clean Energy\"]"
│       }
├── Document: "Collaborative R&D Grant..."
└── ...

# Horizon Europe NLM
Collection: EU_horizon_europe
├── Document: "EIC Accelerator 2025..."
└── ...
```

## Monitoring

### Check Collection Status

```bash
curl -X POST http://localhost:8000/api/status
```

Response includes:
```json
{
  "nlms": [
    {
      "nlm_id": "innovate_uk",
      "stats": {
        "grants_indexed": 28
      }
    }
  ]
}
```

### View ChromaDB Cloud Dashboard

1. Login to https://www.trychroma.com/
2. View your project
3. See collections, document counts, storage usage

## Troubleshooting

### Connection Failed

**Error:**
```
[innovate_uk] ChromaDB Cloud credentials missing, falling back to local
```

**Fix:**
```bash
# Check .env file
cat .env | grep CHROMA

# Should show:
CHROMADB_MODE=cloud
CHROMADB_CLOUD_URL=your-instance.chromadb.io
CHROMADB_API_KEY=chroma_xxx...
```

### Authentication Error

**Error:**
```
chromadb.errors.AuthorizationError: Invalid API key
```

**Fix:**
1. Check API key in ChromaDB Cloud dashboard
2. Regenerate if needed
3. Update `.env`

### Slow Queries

**Symptom:** Queries taking >500ms

**Solutions:**
1. **Use local dev mode** for development
2. **Check region**: Use ChromaDB region closest to your ECS cluster
3. **Batch queries**: NLMs query in parallel (already optimized)

### Data Not Appearing

**Problem:** Indexed grants not showing in searches

**Debug:**
```bash
# Check if grants were indexed
curl http://localhost:8000/api/status

# Should show grants_indexed > 0

# Try re-indexing
python scripts/seed_data.py
```

## Best Practices

### Development
```bash
# .env
CHROMADB_MODE=local
```
- Fast iteration
- No API costs
- Offline development

### Staging
```bash
# .env
CHROMADB_MODE=cloud
CHROMADB_CLOUD_URL=staging-instance.chromadb.io
```
- Test cloud integration
- Shared team database
- Pre-production testing

### Production
```bash
# .env
CHROMADB_MODE=cloud
CHROMADB_CLOUD_URL=prod-instance.chromadb.io
CHROMADB_TENANT=production
```
- Auto-scaling
- Managed backups
- High availability

## Cost Estimates

ChromaDB Cloud pricing (approximate):

- **Free Tier**: 10k documents, 1GB storage
- **Starter**: $29/mo - 100k documents
- **Pro**: $99/mo - 1M documents

**Your Usage:**
- 4 NLMs × 100 grants avg = 400 documents
- Well within free tier! ✅

## Security

### API Key Security

**❌ Don't:**
```bash
# Hard-code in code
client = chromadb.HttpClient(
    headers={"Authorization": "Bearer chroma_abc123"}  # BAD!
)
```

**✅ Do:**
```bash
# Use environment variables
client = chromadb.HttpClient(
    headers={"Authorization": f"Bearer {os.getenv('CHROMADB_API_KEY')}"}
)
```

### Network Security

- ChromaDB Cloud uses HTTPS (TLS 1.3)
- API keys are encrypted in transit
- No public access without valid key

### Backup Strategy

1. **ChromaDB Cloud** handles backups automatically
2. **Also keep S3 backup** of grant JSONs:
   ```
   s3://your-bucket/grants/
   ├── iuk/
   ├── horizon/
   ├── nihr/
   └── ukri/
   ```
3. **MongoDB** for metadata and queries

## Next Steps

1. ✅ Configure `.env` with ChromaDB Cloud credentials
2. ✅ Test connection: `python main.py`
3. ✅ Index sample data: `python scripts/seed_data.py`
4. ✅ Query to verify: `curl -X POST http://localhost:8000/api/query ...`
5. 🚀 Deploy to AWS ECS (see AWS_DEPLOYMENT.md)

---

**Ready for Production:** ChromaDB Cloud integration complete! ✅
