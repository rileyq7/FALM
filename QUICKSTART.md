# ⚡ QUICKSTART

Your FALM system is ready with **ChromaDB Cloud pre-configured**!

## 1️⃣ Setup (One Time)

```bash
cd /Users/rileycoleman/FALM
bash scripts/setup.sh
```

This installs all dependencies.

## 2️⃣ Activate Environment

```bash
source venv/bin/activate
```

## 3️⃣ Add Anthropic API Key (Optional but Recommended)

For SME expert insights:

```bash
# Edit .env and add your key:
nano .env

# Add this line:
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

**Or skip this** - system works without it (uses rules-based fallback)

## 4️⃣ Load Sample Data

```bash
python scripts/seed_data.py
```

This adds sample grants to your **ChromaDB Cloud** database.

You'll see:
```
Seeding 2 grants for innovate_uk...
  ✓ IUK_SMART_2025_001
  ✓ IUK_CRD_2025_001
Seeding 1 grants for horizon_europe...
  ✓ HORIZON_EIC_2025_001
...
Total grants seeded: 6
```

## 5️⃣ Start Server

```bash
python main.py
```

You'll see:
```
[innovate_uk] Connecting to ChromaDB Cloud...
[innovate_uk] ChromaDB Cloud connected successfully
[innovate_uk] Vector DB ready: UK_innovate_uk
...
INFO:     Uvicorn running on http://0.0.0.0:8000
```

## 6️⃣ Test It!

Open in browser: **http://localhost:8000/docs**

Or test with curl:

```bash
curl -X POST "http://localhost:8000/api/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "AI grants for startups"}'
```

Response:
```json
{
  "query": "AI grants for startups",
  "nlms_queried": ["innovate_uk", "horizon_europe", "ukri"],
  "total_results": 3,
  "grants": [
    {
      "title": "Smart Grants: Spring 2025",
      "amount_max": 2000000,
      "deadline": "2025-03-31"
    }
  ],
  "sme_context": "Innovate UK Smart Grants most suitable...",
  "processing_time_ms": 234.5
}
```

## 🎉 That's It!

Your system is running with:
- ✅ 4 domain NLMs (InnovateUK, Horizon, NIHR, UKRI)
- ✅ ChromaDB Cloud (shared database)
- ✅ Engagement tracking
- ✅ Dashboard management
- ✅ SME context (if API key added)

## Next Steps

### Try More Queries

```bash
# Health research
curl -X POST "http://localhost:8000/api/query" \
  -d '{"query": "health research grants"}'

# European grants
curl -X POST "http://localhost:8000/api/query" \
  -d '{"query": "European innovation funding", "silos": ["EU"]}'

# Clean energy
curl -X POST "http://localhost:8000/api/query" \
  -d '{"query": "clean energy grants UK"}'
```

### Check System Status

```bash
curl http://localhost:8000/api/status
```

### Add Your Own Grants

```bash
curl -X POST "http://localhost:8000/api/grants/index" \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "innovate_uk",
    "grant_data": {
      "title": "My Custom Grant",
      "description": "Grant for...",
      "amount_max": 500000,
      "deadline": "2025-12-31"
    }
  }'
```

### Use Dashboard Features

```bash
# Add grant to user dashboard
curl -X POST "http://localhost:8000/api/dashboard/add" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user123", "grant_id": "IUK_SMART_2025_001"}'

# Get user dashboard
curl http://localhost:8000/api/dashboard/user123

# Get urgent deadlines
curl http://localhost:8000/api/dashboard/user123/urgent?days=30
```

### Check Hot Leads

```bash
curl http://localhost:8000/api/engagement/hot-leads
```

## 📚 Learn More

- **Full features:** See [SYSTEM_COMPLETE.md](SYSTEM_COMPLETE.md)
- **ChromaDB details:** See [docs/CHROMADB_SETUP_QUICK.md](docs/CHROMADB_SETUP_QUICK.md)
- **AWS deployment:** See [docs/AWS_DEPLOYMENT.md](docs/AWS_DEPLOYMENT.md)
- **Implementation:** See [docs/IMPLEMENTATION_GUIDE.md](docs/IMPLEMENTATION_GUIDE.md)

## 🆘 Troubleshooting

### No results?
```bash
# Re-run seed data
python scripts/seed_data.py
```

### ChromaDB connection failed?
```bash
# Check .env file has credentials
cat .env | grep CHROMA
```

### Server won't start?
```bash
# Check logs
tail -f logs/falm.log

# Check if port 8000 is in use
lsof -i :8000
```

---

**You're all set!** 🚀

API running at: http://localhost:8000/docs
