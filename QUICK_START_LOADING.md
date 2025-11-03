# 🚀 Quick Start: Loading Grants

## 1️⃣ Load Test Data (Fastest Way)

```bash
# Load 100 example grants to test the system
python scripts/load_grants.py --source example --nlm innovate_uk --count 100
```

**Output**:
```
Loading grants from example: 100
Initializing NLM: innovate_uk_nlm
[innovate_uk_nlm] Batch indexing 100 grants...
[innovate_uk_nlm] Generating embeddings...
100%|████████████████████████| 100/100
[innovate_uk_nlm] Writing to vector DB...
[innovate_uk_nlm] Bulk indexed 100 grants in 8.5s (11.8 grants/sec)
✅ Successfully indexed 100 grants
```

---

## 2️⃣ Load from JSON File

```bash
# Load provided example file
python scripts/load_grants.py --source data/example_grants.json --nlm innovate_uk
```

**Your JSON format**:
```json
[
  {
    "title": "Grant Title",
    "description": "Grant description...",
    "amount_max": 500000,
    "deadline": "2025-12-31",
    "sectors": ["AI & Data", "Healthcare"]
  }
]
```

---

## 3️⃣ Load from CSV File

```bash
# Load from CSV
python scripts/load_grants.py --source data/example_grants.csv --nlm innovate_uk
```

**Your CSV format**:
```csv
title,description,amount_max,deadline,sectors
"AI Grant","Funding for AI...",500000,2025-12-31,"AI & Data,Healthcare"
```

---

## 4️⃣ Programmatic Loading (Python)

```python
import asyncio
from src.nlms.innovate_uk import InnovateUKNLM

async def load_grants():
    # Initialize
    nlm = InnovateUKNLM()
    await nlm.initialize()

    # Your grants
    grants = [
        {"title": "Grant 1", "description": "...", "amount_max": 500000},
        {"title": "Grant 2", "description": "...", "amount_max": 1000000},
        # ... more grants
    ]

    # Batch load (FAST!)
    grant_ids = await nlm.index_grants_batch(grants)
    print(f"✅ Loaded {len(grant_ids)} grants")

asyncio.run(load_grants())
```

---

## 5️⃣ Verify Loading

### Test via CLI:
```bash
# Start the system
python main.py

# In another terminal, query:
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "AI grants", "max_results": 5}'
```

### Test via Python:
```python
import asyncio
from src.nlms.innovate_uk import InnovateUKNLM

async def test():
    nlm = InnovateUKNLM()
    await nlm.initialize()

    # Search
    results = await nlm.search("AI healthcare", max_results=5)

    for grant in results:
        print(f"✓ {grant['title']}")
        print(f"  Relevance: {grant['relevance_score']:.3f}")

asyncio.run(test())
```

---

## 📊 Performance Tips

| Grants | Recommended Method | Expected Time |
|--------|-------------------|---------------|
| 1-10 | Single indexing | <1 second |
| 10-100 | Batch indexing | 2-5 seconds |
| 100-1000 | Batch indexing | 15-30 seconds |
| 1000+ | Batch indexing + batches | 2-5 minutes |

**Always use batch indexing for >10 grants!**

---

## 🎯 Which NLM?

| Grant Source | Use NLM |
|-------------|---------|
| Innovate UK grants | `innovate_uk` |
| Horizon Europe grants | `horizon_europe` |
| NIHR health grants | `nihr` |
| UKRI research grants | `ukri` |

---

## 🆘 Quick Troubleshooting

**No results found?**
→ Load grants first: `python scripts/load_grants.py --source example --nlm innovate_uk`

**Too slow?**
→ Use batch indexing: `nlm.index_grants_batch(grants)` not `nlm.index_grant(grant)`

**Import error?**
→ Run from project root: `cd /Users/rileycoleman/FALM && python scripts/load_grants.py ...`

---

## 📚 Full Guide

See **[LOADING_GRANTS_GUIDE.md](LOADING_GRANTS_GUIDE.md)** for:
- Complete data format specifications
- Advanced parsing examples
- Database import guides
- Web scraping integration
- Troubleshooting details

---

## ✅ Quick Checklist

- [ ] Loaded test grants: `python scripts/load_grants.py --source example --nlm innovate_uk --count 100`
- [ ] Started system: `python main.py`
- [ ] Tested query: `curl -X POST http://localhost:8000/api/query ...`
- [ ] Got results with hybrid scores ✨

**You're ready to load real grants!** 🎉
