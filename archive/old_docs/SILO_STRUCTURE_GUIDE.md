# FALM Hierarchical Silo Structure Guide

## Overview

This guide explains how to organize grants data with a hierarchical silo structure:
- **Region** (UK, EU, US)
- **Funding Body** (IUK, NIHR, UKRI, etc.)
- **Sub-categories** (optional)

## Enhanced Grant Data Model

Add `funding_body` and `category` fields to your grants:

```json
{
  "grant_id": "unique_id",
  "title": "Smart Grant",
  "provider": "Innovate UK",
  "silo": "UK",
  "funding_body": "IUK",           // NEW: Sub-silo identifier
  "category": "R&D",                // NEW: Optional category
  "amount_min": 25000,
  "amount_max": 500000,
  "currency": "GBP",
  "deadline": "2025-12-31",
  "sectors": ["AI", "Technology"],
  "eligibility": {...},
  "description": "...",
  "application_url": "...",
  "metadata": {
    "source_database": "IUK_main",   // Track which sub-silo
    "last_updated": "2025-10-31"
  }
}
```

## Proposed Directory Structure

```
data/
└── silos/
    ├── UK/
    │   ├── IUK/              # Innovate UK
    │   │   ├── smart_grants/
    │   │   ├── catapult/
    │   │   └── ktn/
    │   ├── NIHR/             # National Institute for Health Research
    │   │   ├── research_grants/
    │   │   ├── fellowships/
    │   │   └── infrastructure/
    │   ├── UKRI/             # UK Research and Innovation
    │   │   ├── epsrc/
    │   │   ├── esrc/
    │   │   ├── mrc/
    │   │   └── nerc/
    │   ├── Charities/
    │   │   ├── wellcome/
    │   │   ├── cancer_research/
    │   │   └── british_heart_foundation/
    │   └── Government/
    │       ├── dcms/
    │       ├── beis/
    │       └── defra/
    │
    ├── EU/
    │   ├── EIC/              # European Innovation Council
    │   ├── Horizon/          # Horizon Europe
    │   ├── EIT/              # European Institute of Innovation
    │   └── Regional/
    │       ├── interreg/
    │       └── esf/
    │
    └── US/
        ├── NSF/              # National Science Foundation
        ├── NIH/              # National Institutes of Health
        ├── DOE/              # Department of Energy
        ├── DOD/              # Department of Defense
        └── State/            # State-level grants
            ├── california/
            └── new_york/
```

## Funding Body Codes

### UK Funding Bodies
```python
UK_FUNDING_BODIES = {
    "IUK": "Innovate UK",
    "NIHR": "National Institute for Health Research",
    "UKRI": "UK Research and Innovation",
    "EPSRC": "Engineering and Physical Sciences Research Council",
    "ESRC": "Economic and Social Research Council",
    "MRC": "Medical Research Council",
    "NERC": "Natural Environment Research Council",
    "AHRC": "Arts and Humanities Research Council",
    "BBSRC": "Biotechnology and Biological Sciences Research Council",
    "STFC": "Science and Technology Facilities Council",
    "ACE": "Arts Council England",
    "DCMS": "Department for Culture, Media and Sport",
    "BEIS": "Department for Business, Energy and Industrial Strategy",
    "DEFRA": "Department for Environment, Food and Rural Affairs",
    "Wellcome": "Wellcome Trust",
    "CRUK": "Cancer Research UK",
    "BHF": "British Heart Foundation"
}
```

### EU Funding Bodies
```python
EU_FUNDING_BODIES = {
    "EIC": "European Innovation Council",
    "Horizon": "Horizon Europe",
    "EIT": "European Institute of Innovation and Technology",
    "LIFE": "LIFE Programme",
    "CEF": "Connecting Europe Facility",
    "Interreg": "Interreg Europe",
    "ESF": "European Social Fund"
}
```

### US Funding Bodies
```python
US_FUNDING_BODIES = {
    "NSF": "National Science Foundation",
    "NIH": "National Institutes of Health",
    "DOE": "Department of Energy",
    "DOD": "Department of Defense",
    "NASA": "National Aeronautics and Space Administration",
    "USDA": "US Department of Agriculture",
    "EPA": "Environmental Protection Agency",
    "NEH": "National Endowment for the Humanities",
    "NEA": "National Endowment for the Arts"
}
```

## How to Query with Funding Bodies

### Example 1: Query specific funding body
```json
{
  "query": "AI grants",
  "silos": ["UK"],
  "filters": {
    "funding_body": "IUK"
  }
}
```

### Example 2: Query multiple funding bodies
```json
{
  "query": "Health research grants",
  "silos": ["UK"],
  "filters": {
    "funding_body": ["NIHR", "MRC", "Wellcome"]
  }
}
```

### Example 3: Query by category
```json
{
  "query": "Fellowship grants",
  "silos": ["UK", "EU"],
  "filters": {
    "category": "Fellowship"
  }
}
```

## Setting Up the Structure

### 1. Create Directory Structure
```bash
# Run this script to create all sub-folders
mkdir -p data/silos/UK/{IUK,NIHR,UKRI,Charities,Government}
mkdir -p data/silos/UK/UKRI/{epsrc,esrc,mrc,nerc,ahrc,bbsrc,stfc}
mkdir -p data/silos/UK/Charities/{wellcome,cruk,bhf}
mkdir -p data/silos/EU/{EIC,Horizon,EIT,Regional}
mkdir -p data/silos/US/{NSF,NIH,DOE,DOD,State}
```

### 2. Organize Your Data Files

Store JSON/CSV files in appropriate folders:
```
data/silos/UK/IUK/smart_grants_2025.json
data/silos/UK/NIHR/fellowships_2025.json
data/silos/UK/UKRI/epsrc_grants.json
```

### 3. Import with Funding Body Tag

When importing, include the funding_body in your data:

**JSON Format:**
```json
{
  "title": "Smart Grant",
  "provider": "Innovate UK",
  "silo": "UK",
  "funding_body": "IUK",
  "category": "R&D",
  ...
}
```

**CSV Format:**
```csv
title,provider,silo,funding_body,category,amount_min,amount_max,currency,deadline
Smart Grant,Innovate UK,UK,IUK,R&D,25000,500000,GBP,2025-12-31
```

## Bulk Import from Folder Structure

Create this helper script: `import_by_folders.py`

```python
#!/usr/bin/env python3
"""
Import grants organized by folder structure
"""

import json
import requests
from pathlib import Path

API_URL = "http://localhost:8000"
SILOS_DIR = Path("data/silos")

def import_folder_structure():
    """Import all grants from folder structure"""

    for region_dir in SILOS_DIR.iterdir():
        if not region_dir.is_dir():
            continue

        region = region_dir.name  # UK, EU, US
        print(f"\n📂 Processing {region} grants...")

        for funding_body_dir in region_dir.iterdir():
            if not funding_body_dir.is_dir():
                continue

            funding_body = funding_body_dir.name  # IUK, NIHR, etc.
            print(f"  └─ {funding_body}")

            # Import all JSON files in this funding body folder
            for json_file in funding_body_dir.rglob("*.json"):
                print(f"     └─ {json_file.name}")

                with open(json_file) as f:
                    grants = json.load(f)

                # Ensure it's a list
                if not isinstance(grants, list):
                    grants = [grants]

                # Add funding_body to each grant if not present
                for grant in grants:
                    if "funding_body" not in grant:
                        grant["funding_body"] = funding_body
                    if "silo" not in grant:
                        grant["silo"] = region

                    # Import grant
                    response = requests.post(
                        f"{API_URL}/api/grants",
                        json=grant
                    )

                    if response.status_code == 200:
                        print(f"        ✓ {grant['title']}")
                    else:
                        print(f"        ✗ Failed: {response.text[:100]}")

if __name__ == "__main__":
    import_folder_structure()
```

Run it:
```bash
python import_by_folders.py
```

## Enhanced Search with Funding Bodies

The vector database will automatically index the funding_body field, allowing:

1. **Broad regional search**: "Show me UK grants"
2. **Specific funding body**: "Show me Innovate UK grants"
3. **Cross-funding body**: "Show me NIHR and MRC health grants"
4. **Category-based**: "Show me all fellowship grants across UK research councils"

## Example Data Files

### UK/IUK/smart_grants.json
```json
[
  {
    "grant_id": "iuk_smart_2025_001",
    "title": "Smart Grants: January 2025 Competition",
    "provider": "Innovate UK",
    "silo": "UK",
    "funding_body": "IUK",
    "category": "R&D",
    "amount_min": 25000,
    "amount_max": 500000,
    "currency": "GBP",
    "deadline": "2025-12-15",
    "sectors": ["Technology", "AI", "Innovation"],
    "eligibility": {
      "company_type": "UK Limited Company",
      "location": ["UK"],
      "min_employees": 1
    },
    "description": "Game-changing and commercially viable R&D innovation",
    "application_url": "https://apply-for-innovation-funding.service.gov.uk/",
    "metadata": {
      "competition_id": "2313",
      "source_database": "IUK_main"
    }
  }
]
```

### UK/NIHR/fellowships.json
```json
[
  {
    "grant_id": "nihr_fellow_2025_001",
    "title": "NIHR Advanced Fellowship",
    "provider": "National Institute for Health Research",
    "silo": "UK",
    "funding_body": "NIHR",
    "category": "Fellowship",
    "amount_min": 250000,
    "amount_max": 1000000,
    "currency": "GBP",
    "deadline": "2025-11-30",
    "sectors": ["Health", "Research", "Clinical"],
    "eligibility": {
      "career_stage": "Post-doctoral researchers",
      "location": ["UK"],
      "requirements": [
        "Clinical or non-clinical health researchers",
        "Evidence of research potential"
      ]
    },
    "description": "Support outstanding researchers to develop their careers",
    "application_url": "https://www.nihr.ac.uk/explore-nihr/funding-programmes/",
    "metadata": {
      "programme": "Advanced Fellowship",
      "source_database": "NIHR_fellowships"
    }
  }
]
```

## Migration Steps

1. **Create folder structure** (see script above)
2. **Organize existing data** into appropriate folders
3. **Add funding_body field** to all grants
4. **Run bulk import** using the script
5. **Verify** with queries filtering by funding_body

This hierarchical structure allows you to:
- Keep data organized by source
- Track which funding body each grant comes from
- Filter and search at multiple levels of granularity
- Easily update specific funding bodies without affecting others
- Scale as you add more funding bodies

Would you like me to create the enhanced import script or modify the API to better support this structure?
