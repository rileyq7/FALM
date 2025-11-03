# ChromaDB Cloud Quick Setup

## Your ChromaDB Cloud is Ready! ✅

Your `.env` file has been configured with your ChromaDB Cloud credentials.

## Configuration

```bash
CHROMADB_MODE=cloud
CHROMADB_API_KEY=ck-DaHPv1enX6SRxTaNMDF4eX3JuwrpJ2YQv2Ah547MrpD1
CHROMADB_TENANT=b159342c-e9b0-4841-b8e7-e0d8ce36ecc7
CHROMADB_DATABASE=ailsa-tech
```

## Test It Now

```bash
# 1. Activate environment
source venv/bin/activate

# 2. Seed sample data (this will go to ChromaDB Cloud)
python scripts/seed_data.py

# 3. Start server
python main.py
```

## What Will Happen

When you start the server, you'll see:

```
[innovate_uk] Connecting to ChromaDB Cloud...
[innovate_uk] Tenant: b159342c-e9b0-4841-b8e7-e0d8ce36ecc7, Database: ailsa-tech
[innovate_uk] ChromaDB Cloud connected successfully
[innovate_uk] Vector DB ready: UK_innovate_uk

[horizon_europe] Connecting to ChromaDB Cloud...
[horizon_europe] Tenant: b159342c-e9b0-4841-b8e7-e0d8ce36ecc7, Database: ailsa-tech
[horizon_europe] ChromaDB Cloud connected successfully
[horizon_europe] Vector DB ready: EU_horizon_europe

[nihr] Connecting to ChromaDB Cloud...
[nihr] Tenant: b159342c-e9b0-4841-b8e7-e0d8ce36ecc7, Database: ailsa-tech
[nihr] ChromaDB Cloud connected successfully
[nihr] Vector DB ready: UK_nihr

[ukri] Connecting to ChromaDB Cloud...
[ukri] Tenant: b159342c-e9b0-4841-b8e7-e0d8ce36ecc7, Database: ailsa-tech
[ukri] ChromaDB Cloud connected successfully
[ukri] Vector DB ready: UK_ukri
```

## Collections Created in Your ChromaDB Cloud

Your database `ailsa-tech` will contain:

1. **UK_innovate_uk** - InnovateUK grants
2. **EU_horizon_europe** - Horizon Europe grants
3. **UK_nihr** - NIHR grants
4. **UK_ukri** - UKRI grants

## Verify in ChromaDB Cloud Dashboard

1. Go to your ChromaDB Cloud dashboard
2. Select tenant: `b159342c-e9b0-4841-b8e7-e0d8ce36ecc7`
3. Select database: `ailsa-tech`
4. You should see 4 collections after running `seed_data.py`

## Query Your Data

```bash
curl -X POST "http://localhost:8000/api/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "AI grants for startups"}'
```

This will:
1. Search all 4 collections in ChromaDB Cloud
2. Return matching grants
3. Include SME context (if you add ANTHROPIC_API_KEY)

## Switch to Local Mode (Optional)

If you want to test locally instead:

```bash
# Edit .env
CHROMADB_MODE=local
```

Restart server - it will use local ChromaDB in `data/nlms/` instead.

## Architecture

```
Your FALM API
    ↓
4 NLMs (InnovateUK, Horizon, NIHR, UKRI)
    ↓
ChromaDB Cloud
    ├─ Tenant: b159342c-e9b0-4841-b8e7-e0d8ce36ecc7
    └─ Database: ailsa-tech
        ├─ Collection: UK_innovate_uk
        ├─ Collection: EU_horizon_europe
        ├─ Collection: UK_nihr
        └─ Collection: UK_ukri
```

## Benefits of Cloud Mode

✅ **Shared across containers** - All your ECS tasks access same data
✅ **Persistent** - Data survives container restarts
✅ **Scalable** - Auto-scales with your needs
✅ **Managed backups** - ChromaDB handles this
✅ **Multi-region** - Can access from anywhere

## Cost

Your current usage (4 collections, ~400 documents):
- **Well within ChromaDB Cloud free tier!** ✅

## Next Steps

1. ✅ ChromaDB Cloud configured
2. ✅ Run `python scripts/seed_data.py`
3. ✅ Run `python main.py`
4. ✅ Test at http://localhost:8000/docs
5. 🚀 Deploy to AWS (optional) - see [AWS_DEPLOYMENT.md](AWS_DEPLOYMENT.md)

---

**Your ChromaDB Cloud integration is complete!** 🎉

Data will be stored in the cloud, shared across all deployments.
