# 📑 FALM Documentation Index

**Your complete grant discovery system with ChromaDB Cloud!**

## 🎯 Start Here

| Document | When to Read | Time |
|----------|-------------|------|
| **[READY_TO_USE.md](READY_TO_USE.md)** ⭐ | **RIGHT NOW** - Your system is configured! | 2 min |
| **[QUICKSTART.md](QUICKSTART.md)** | Quick 5-step guide to get running | 5 min |
| [START_HERE.md](START_HERE.md) | Overview and orientation | 2 min |

## 📚 Main Documentation

### Getting Started
- [QUICKSTART.md](QUICKSTART.md) - 5-minute quick start
- [GETTING_STARTED.md](GETTING_STARTED.md) - Comprehensive getting started guide
- [README.md](README.md) - Full system overview

### System Information
- [SYSTEM_COMPLETE.md](SYSTEM_COMPLETE.md) - Complete feature list and what's been built
- [READY_TO_USE.md](READY_TO_USE.md) - Your ChromaDB Cloud is configured and ready!

### Technical Documentation
- [docs/IMPLEMENTATION_GUIDE.md](docs/IMPLEMENTATION_GUIDE.md) - Technical deep-dive
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - System architecture
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) - Deployment options

### ChromaDB Cloud
- **[docs/CHROMADB_SETUP_QUICK.md](docs/CHROMADB_SETUP_QUICK.md)** - Your ChromaDB Cloud setup ✅
- [docs/CHROMADB_CLOUD_SETUP.md](docs/CHROMADB_CLOUD_SETUP.md) - Detailed ChromaDB Cloud guide

### Deployment
- [docs/AWS_DEPLOYMENT.md](docs/AWS_DEPLOYMENT.md) - Deploy to AWS ECS Fargate
- [docs/SCRAPERS.md](docs/SCRAPERS.md) - Web scraping documentation

## 🚀 Quick Commands

### First Time Setup
```bash
cd /Users/rileycoleman/FALM
bash scripts/setup.sh
source venv/bin/activate
```

### Load Sample Data (to ChromaDB Cloud)
```bash
python scripts/seed_data.py
```

### Start Server
```bash
python main.py
# Open http://localhost:8000/docs
```

### Docker Deployment
```bash
bash scripts/deploy.sh
```

### AWS Deployment
```bash
cd deploy/terraform
terraform init
terraform apply
```

## 📊 Your Configuration

### ChromaDB Cloud ✅
```
Mode: cloud
API Key: ck-DaH...rpD1
Tenant: b159342c-e9b0-4841-b8e7-e0d8ce36ecc7
Database: ailsa-tech
Status: ✅ CONFIGURED
```

### Collections (after seeding)
- `UK_innovate_uk` - InnovateUK grants
- `EU_horizon_europe` - Horizon Europe grants
- `UK_nihr` - NIHR health research grants
- `UK_ukri` - UKRI research council grants

## 🎯 Common Tasks

### Test the System
```bash
curl -X POST "http://localhost:8000/api/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "AI grants for startups"}'
```

### Check System Status
```bash
curl http://localhost:8000/api/status
```

### View API Documentation
Open: http://localhost:8000/docs

### Add Your Own Grants
```bash
curl -X POST "http://localhost:8000/api/grants/index" \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "innovate_uk",
    "grant_data": {
      "title": "My Grant",
      "description": "...",
      "amount_max": 500000
    }
  }'
```

## 📁 Project Structure

```
FALM/
├── main.py                     # ⭐ Main entry point
├── .env                        # ⭐ Your config (ChromaDB Cloud configured!)
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
│
├── src/
│   ├── core/                   # Core system
│   │   ├── simp.py            # SIMP protocol
│   │   ├── base_nlm.py        # Base NLM (ChromaDB Cloud integrated)
│   │   └── orchestrator.py    # Query routing
│   │
│   ├── nlms/                   # Domain experts
│   │   ├── innovate_uk.py     # InnovateUK NLM
│   │   ├── horizon_europe.py  # Horizon Europe NLM
│   │   ├── nihr.py            # NIHR NLM
│   │   ├── ukri.py            # UKRI NLM
│   │   └── sme_context.py     # Expert insights
│   │
│   ├── api/app.py             # FastAPI application
│   ├── crawler/               # Web crawlers
│   ├── tracking/              # Analytics
│   └── utils/                 # Utilities
│
├── scripts/
│   ├── setup.sh               # ⭐ Run first
│   ├── seed_data.py           # ⭐ Load sample data
│   └── deploy.sh              # Docker deploy
│
├── deploy/terraform/          # AWS deployment
└── docs/                      # Documentation
```

## 🎓 Learning Path

### Day 1: Local Setup
1. Read [READY_TO_USE.md](READY_TO_USE.md)
2. Run [QUICKSTART.md](QUICKSTART.md) steps
3. Explore http://localhost:8000/docs

### Day 2: Understand the System
1. Read [SYSTEM_COMPLETE.md](SYSTEM_COMPLETE.md)
2. Read [docs/IMPLEMENTATION_GUIDE.md](docs/IMPLEMENTATION_GUIDE.md)
3. Review [docs/CHROMADB_SETUP_QUICK.md](docs/CHROMADB_SETUP_QUICK.md)

### Week 1: Customize
1. Add real grant data
2. Configure domain-specific crawlers
3. Add Anthropic API key for enhanced SME context

### Week 2: Deploy
1. Test with Docker: `bash scripts/deploy.sh`
2. Deploy to AWS: Follow [docs/AWS_DEPLOYMENT.md](docs/AWS_DEPLOYMENT.md)
3. Set up monitoring

## ✅ System Status

| Component | Status | Details |
|-----------|--------|---------|
| Core System | ✅ Complete | SIMP, Orchestrator, Base NLM |
| Domain NLMs | ✅ Complete | 4 NLMs (IUK, Horizon, NIHR, UKRI) |
| ChromaDB Cloud | ✅ Configured | Connected to ailsa-tech database |
| SME Context | ✅ Complete | Rules-based + LLM optional |
| Engagement Tracking | ✅ Complete | Hot lead detection |
| Dashboard Manager | ✅ Complete | User collections |
| REST API | ✅ Complete | Auto-documented |
| Docker | ✅ Complete | Full containerization |
| AWS Terraform | ✅ Complete | ECS Fargate templates |
| Documentation | ✅ Complete | 7 guides + API docs |

## 🆘 Need Help?

| Issue | Solution |
|-------|----------|
| **How do I start?** | Read [READY_TO_USE.md](READY_TO_USE.md) |
| **Quick test?** | Run steps in [QUICKSTART.md](QUICKSTART.md) |
| **ChromaDB not connecting?** | Check `.env` has your credentials |
| **No results?** | Run `python scripts/seed_data.py` |
| **Server won't start?** | Check `logs/falm.log` |
| **Need AWS help?** | See [docs/AWS_DEPLOYMENT.md](docs/AWS_DEPLOYMENT.md) |

## 🎉 You're Ready!

Everything is configured and ready to use!

**Next step:** Open [READY_TO_USE.md](READY_TO_USE.md) and start the system!

---

**Quick Start Command:**
```bash
source venv/bin/activate && python scripts/seed_data.py && python main.py
```

Then open: **http://localhost:8000/docs** 🚀
