# 👋 START HERE

Welcome to your **FALM (Federated Agentic Language Model)** system!

## What is this?

A **production-ready grant discovery system** that:
- Searches across multiple funding bodies (InnovateUK, Horizon Europe, NIHR, UKRI)
- Uses AI to provide expert insights
- Tracks user engagement and identifies hot leads
- Manages user dashboards with deadline tracking
- Fully containerized and ready for AWS deployment

## 🚀 Get Started in 5 Minutes

```bash
# 1. Setup
cd /Users/rileycoleman/FALM
bash scripts/setup.sh

# 2. Activate
source venv/bin/activate

# 3. Add API key (optional but recommended)
echo 'ANTHROPIC_API_KEY=your-key-here' >> .env

# 4. Load sample data
python scripts/seed_data.py

# 5. Start server
python main.py
```

**Done!** Open http://localhost:8000/docs

## 📚 Read Next

| If you want to... | Read this |
|-------------------|-----------|
| **Use the system locally** | [GETTING_STARTED.md](GETTING_STARTED.md) |
| **Set up ChromaDB Cloud** | [docs/CHROMADB_CLOUD_SETUP.md](docs/CHROMADB_CLOUD_SETUP.md) |
| **Deploy to AWS** | [docs/AWS_DEPLOYMENT.md](docs/AWS_DEPLOYMENT.md) |
| **Understand the code** | [docs/IMPLEMENTATION_GUIDE.md](docs/IMPLEMENTATION_GUIDE.md) |
| **See what's built** | [SYSTEM_COMPLETE.md](SYSTEM_COMPLETE.md) |

## 🎯 Quick Test

```bash
# Query the API
curl -X POST "http://localhost:8000/api/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "AI grants for startups"}'
```

## ✅ System Status

- ✅ **Core System:** Complete
- ✅ **4 Domain NLMs:** Complete
- ✅ **SME Context:** Complete
- ✅ **Engagement Tracking:** Complete
- ✅ **Dashboard Manager:** Complete
- ✅ **API:** Complete
- ✅ **Docker:** Complete
- ✅ **AWS Terraform:** Complete
- ✅ **ChromaDB Cloud:** Integrated
- ✅ **Documentation:** Complete

**Everything is ready to use!** 🎉

## 💡 Key Features

1. **Multi-Domain Search** - Query all funding bodies at once
2. **AI Insights** - Claude/GPT-powered expert context
3. **Hot Lead Detection** - Automatically flag engaged users
4. **Smart Dashboards** - User grant collections with reminders
5. **Production Ready** - Docker + AWS + ChromaDB Cloud

## 🆘 Need Help?

1. **Quick start:** See [GETTING_STARTED.md](GETTING_STARTED.md)
2. **Problems?** Check logs: `tail -f logs/falm.log`
3. **API docs:** http://localhost:8000/docs (when running)

## 📞 Support

- **Docs:** See files above
- **API:** Interactive docs at `/docs`
- **Tests:** `pytest tests/`

---

**Ready? Run:** `bash scripts/setup.sh`
