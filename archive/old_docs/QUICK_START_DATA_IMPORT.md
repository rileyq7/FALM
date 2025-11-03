# Quick Start: Adding Your Grant Data

## Overview

This guide shows you how to add your own grant data to the FALM system with a hierarchical structure.

## Folder Structure You'll Use

```
data/silos/
├── UK/
│   ├── IUK/              ← Innovate UK grants here
│   ├── NIHR/             ← NIHR grants here
│   ├── UKRI/             ← UKRI grants here
│   │   ├── EPSRC/
│   │   ├── ESRC/
│   │   ├── MRC/
│   │   └── ...
│   └── Charities/        ← Charity grants here
│       ├── Wellcome/
│       ├── CRUK/
│       └── BHF/
├── EU/
│   ├── EIC/
│   ├── Horizon/
│   └── ...
└── US/
    ├── NSF/
    ├── NIH/
    └── ...
```

## Step-by-Step Setup

### Step 1: Create Folder Structure

```bash
./create_silo_structure.sh
```

This creates all the folders for UK (IUK, NIHR, UKRI, Charities), EU, and US funding bodies.

### Step 2: Add Your Grant Data

You have **4 options**:

#### Option A: Copy the Template (Recommended)

1. Copy the example template:
```bash
cp EXAMPLE_GRANT_TEMPLATE.json data/silos/UK/IUK/my_grants.json
```

2. Edit with your data:
```bash
nano data/silos/UK/IUK/my_grants.json
```

3. Replace the example grants with your actual data

#### Option B: Use CSV Format

Create a CSV file: `data/silos/UK/IUK/grants.csv`

```csv
grant_id,title,provider,silo,funding_body,category,amount_min,amount_max,currency,deadline,description
iuk_001,Smart Grant,Innovate UK,UK,IUK,R&D,25000,500000,GBP,2025-12-31,"Description here"
```

#### Option C: Interactive CLI

```bash
source venv/bin/activate
python falm_data_ingestion.py
```

Choose option 4 to add grants manually.

#### Option D: Direct API Call

```bash
curl -X POST "http://localhost:8000/api/grants" \
  -H "Content-Type: application/json" \
  -d @your_grant.json
```

### Step 3: Import Your Data

Once you've added files to the folder structure:

```bash
# Import ALL grants from all folders
python import_by_folders.py

# Import only UK grants
python import_by_folders.py --region UK

# Import only Innovate UK grants
python import_by_folders.py --funding-body IUK
```

### Step 4: Verify Import

```bash
# Check statistics
curl http://localhost:8000/api/stats

# Or use the CLI
python falm_data_ingestion.py
# Choose option 8 to view stats
```

## Data Format Reference

### Minimum Required Fields

```json
{
  "title": "Grant Title",
  "provider": "Provider Name",
  "silo": "UK",
  "description": "Grant description"
}
```

### Complete Format (Recommended)

```json
{
  "grant_id": "unique_identifier",
  "title": "Full Grant Title",
  "provider": "Provider Organization Name",
  "silo": "UK",
  "funding_body": "IUK",
  "category": "R&D",
  "amount_min": 25000,
  "amount_max": 500000,
  "currency": "GBP",
  "deadline": "2025-12-31",
  "sectors": ["Technology", "AI", "Innovation"],
  "eligibility": {
    "company_type": "Limited Company",
    "location": ["UK"],
    "min_employees": 1,
    "requirements": [
      "UK registered",
      "Innovative project"
    ]
  },
  "description": "Detailed description...",
  "application_url": "https://...",
  "supplementary_urls": ["https://..."],
  "pdf_documents": ["https://..."],
  "metadata": {
    "source": "Manual import",
    "last_updated": "2025-10-31"
  }
}
```

## Real-World Example Workflow

### Scenario: You have Innovate UK grants to add

1. **Create your data file:**
```bash
nano data/silos/UK/IUK/innovate_uk_grants.json
```

2. **Add your grants** (using the template as reference):
```json
[
  {
    "grant_id": "iuk_smart_2025_q1_001",
    "title": "Smart Grants Q1 2025",
    "provider": "Innovate UK",
    "silo": "UK",
    "funding_body": "IUK",
    "amount_max": 500000,
    "currency": "GBP",
    "deadline": "2025-03-31",
    "description": "Your description here..."
  },
  {
    "grant_id": "iuk_smart_2025_q1_002",
    "title": "Another Grant",
    ...
  }
]
```

3. **Import:**
```bash
python import_by_folders.py --funding-body IUK
```

4. **Test queries:**
```bash
curl -X POST "http://localhost:8000/api/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What Innovate UK grants are available?",
    "filters": {"funding_body": "IUK"}
  }'
```

## Organizing Multiple Funding Bodies

### Example: UKRI Structure

UKRI has multiple research councils. Organize like this:

```
data/silos/UK/UKRI/
├── EPSRC/
│   └── engineering_grants.json
├── ESRC/
│   └── social_science_grants.json
├── MRC/
│   └── medical_grants.json
└── NERC/
    └── environment_grants.json
```

Import all UKRI grants:
```bash
python import_by_folders.py --funding-body UKRI
```

### Example: Charities

```
data/silos/UK/Charities/
├── Wellcome/
│   ├── career_awards.json
│   └── fellowships.json
├── CRUK/
│   └── research_grants.json
└── BHF/
    └── project_grants.json
```

## Querying with Funding Bodies

Once imported, you can query by funding body:

```bash
# All Innovate UK grants
curl -X POST "http://localhost:8000/api/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "AI grants",
    "filters": {"funding_body": "IUK"}
  }'

# All NIHR grants
curl -X POST "http://localhost:8000/api/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "health research grants",
    "filters": {"funding_body": "NIHR"}
  }'

# Multiple funding bodies
curl -X POST "http://localhost:8000/api/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "research grants",
    "filters": {"funding_body": ["NIHR", "MRC", "Wellcome"]}
  }'
```

## Web Scraping (Advanced)

If you have grant URLs, you can scrape them:

```bash
curl -X POST "http://localhost:8000/api/ingest/url" \
  -H "Content-Type: application/json" \
  -d '{
    "source_url": "https://apply-for-innovation-funding.service.gov.uk/competition/2313",
    "silo": "UK",
    "follow_links": true,
    "max_depth": 2,
    "metadata": {
      "funding_body": "IUK",
      "source": "Innovate UK website"
    }
  }'
```

## Automatic Updates

Schedule automatic updates for URLs:

```bash
curl -X POST "http://localhost:8000/api/schedule/source" \
  -H "Content-Type: application/json" \
  -d '{
    "source_url": "https://your-grant-source.com",
    "silo": "UK",
    "metadata": {
      "funding_body": "IUK"
    }
  }'
```

## Tips

1. **Start small**: Import a few grants from one funding body first
2. **Use consistent naming**: Keep funding_body codes consistent (IUK, NIHR, etc.)
3. **Include metadata**: Add source, last_updated, etc. for tracking
4. **Test queries**: After importing, test with queries to ensure data is searchable
5. **Organize by source**: Keep each funding body's data in separate folders

## Troubleshooting

### Import fails
```bash
# Check API is running
curl http://localhost:8000/

# Check your JSON is valid
python -m json.tool your_file.json
```

### No grants showing in queries
```bash
# Check stats to see if they were imported
curl http://localhost:8000/api/stats

# Check specific funding body
curl "http://localhost:8000/api/grants?funding_body=IUK"
```

### Can't find imported grants
- Make sure `silo` field matches region (UK, EU, US)
- Check `funding_body` is set correctly
- Verify embeddings were generated (check logs)

## Next Steps

1. ✅ Create folder structure: `./create_silo_structure.sh`
2. ✅ Add your grant data to appropriate folders
3. ✅ Import: `python import_by_folders.py`
4. ✅ Test: Query the system to verify data is searchable
5. ✅ Iterate: Add more grants as you collect them

Your grants will be:
- ✓ Stored in MongoDB
- ✓ Indexed in ChromaDB for semantic search
- ✓ Searchable via natural language queries
- ✓ Filterable by funding body, region, sector, etc.

Happy importing! 🚀
