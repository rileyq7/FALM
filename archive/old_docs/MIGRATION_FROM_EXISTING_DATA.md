# Migrating Your Existing Grant Data to FALM

## Your Current Data Structure

Based on your existing system, you have grants with this structure:

```python
{
    "grant_id": "competition-123",
    "title": "Grant Title",
    "url": "https://...",
    "open_date": "2025-01-01",
    "close_date": "2025-12-31",
    "notify_date": "2026-01-15",
    "funding_min": 25000,
    "funding_max": 500000,
    "total_pot": 5000000,
    "duration_min": 12,
    "duration_max": 36,
    "text": "Full grant description and supporting documentation..."
}
```

## Mapping to FALM Format

Your data maps perfectly! Here's the conversion:

### Direct Field Mapping

| Your Field | FALM Field | Notes |
|------------|------------|-------|
| `grant_id` | `grant_id` | ✓ Direct match |
| `title` | `title` | ✓ Direct match |
| `url` | `application_url` | ✓ Rename |
| `funding_min` | `amount_min` | ✓ Direct match |
| `funding_max` | `amount_max` | ✓ Direct match |
| `close_date` | `deadline` | ✓ Rename |
| `text` | `description` | ✓ Rename |
| `open_date` | `metadata.open_date` | Move to metadata |
| `notify_date` | `metadata.notify_date` | Move to metadata |
| `total_pot` | `metadata.total_pot` | Move to metadata |
| `duration_min` | `metadata.duration_min` | Move to metadata |
| `duration_max` | `metadata.duration_max` | Move to metadata |

### New Fields to Add

```python
{
    "provider": "Innovate UK",      # NEW: Extract from context
    "silo": "UK",                    # NEW: Region
    "funding_body": "IUK",           # NEW: Sub-silo
    "currency": "GBP",               # NEW: Currency
    "sectors": ["Technology", "AI"], # NEW: Auto-extract from text
    "eligibility": {},               # NEW: Extract from text
}
```

## Automatic Conversion Script

I'll create a script to convert your existing data:

```python
#!/usr/bin/env python3
"""
Convert existing grant data to FALM format
Handles competition-*.json files and extracts metadata
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Any
import hashlib

def extract_provider(text: str, url: str) -> tuple[str, str, str]:
    """
    Extract provider, silo, and funding_body from text/URL
    Returns: (provider, silo, funding_body)
    """
    text_lower = text.lower() + " " + url.lower()

    # UK providers
    uk_providers = {
        "innovate uk": ("Innovate UK", "UK", "IUK"),
        "ukri": ("UKRI", "UK", "UKRI"),
        "epsrc": ("EPSRC", "UK", "UKRI"),
        "esrc": ("ESRC", "UK", "UKRI"),
        "mrc": ("Medical Research Council", "UK", "UKRI"),
        "nihr": ("NIHR", "UK", "NIHR"),
        "wellcome": ("Wellcome Trust", "UK", "Charities"),
        "cancer research uk": ("Cancer Research UK", "UK", "Charities"),
        "british heart foundation": ("British Heart Foundation", "UK", "Charities"),
        "arts council": ("Arts Council England", "UK", "ACE"),
    }

    # EU providers
    eu_providers = {
        "horizon europe": ("Horizon Europe", "EU", "Horizon"),
        "eic": ("European Innovation Council", "EU", "EIC"),
        "european innovation council": ("European Innovation Council", "EU", "EIC"),
        "life programme": ("LIFE Programme", "EU", "LIFE"),
    }

    # US providers
    us_providers = {
        "nsf": ("National Science Foundation", "US", "NSF"),
        "national science foundation": ("National Science Foundation", "US", "NSF"),
        "nih": ("National Institutes of Health", "US", "NIH"),
        "national institutes of health": ("National Institutes of Health", "US", "NIH"),
        "doe": ("Department of Energy", "US", "DOE"),
        "sbir": ("SBIR", "US", "NSF"),
    }

    all_providers = {**uk_providers, **eu_providers, **us_providers}

    for keyword, (provider, silo, funding_body) in all_providers.items():
        if keyword in text_lower:
            return provider, silo, funding_body

    # Default if not found
    return "Unknown Provider", "UK", "Unknown"

def extract_sectors(text: str) -> List[str]:
    """Extract relevant sectors from grant text"""
    sector_keywords = {
        "AI": ["artificial intelligence", "ai ", "machine learning", "deep learning"],
        "Technology": ["technology", "tech ", "digital", "software", "hardware"],
        "Health": ["health", "medical", "clinical", "healthcare", "wellbeing"],
        "Research": ["research", "r&d", "innovation", "study", "investigation"],
        "Manufacturing": ["manufacturing", "production", "industrial"],
        "Energy": ["energy", "renewable", "sustainability", "green"],
        "Creative": ["creative", "arts", "culture", "media", "design"],
        "Agriculture": ["agriculture", "farming", "food", "agri"],
        "Engineering": ["engineering", "construction", "infrastructure"],
        "Science": ["science", "scientific", "fundamental research"],
    }

    text_lower = text.lower()
    sectors = []

    for sector, keywords in sector_keywords.items():
        if any(kw in text_lower for kw in keywords):
            sectors.append(sector)

    return sectors[:5]  # Limit to top 5

def extract_eligibility(text: str) -> Dict[str, Any]:
    """Extract eligibility requirements from text"""
    eligibility = {}
    text_lower = text.lower()

    # Company type detection
    if "sme" in text_lower or "small and medium" in text_lower:
        eligibility["company_type"] = "SME"
    elif "limited company" in text_lower:
        eligibility["company_type"] = "Limited Company"
    elif "university" in text_lower or "research institution" in text_lower:
        eligibility["company_type"] = "Research Organization"

    # Location detection
    locations = []
    if "uk " in text_lower or "united kingdom" in text_lower or "uk-based" in text_lower:
        locations.append("UK")
    if "eu " in text_lower or "european" in text_lower:
        locations.append("EU")
    if locations:
        eligibility["location"] = locations

    # Extract key requirements using simple patterns
    requirements = []

    # Look for bullet points or numbered lists
    requirement_patterns = [
        r"(?:must|should|need to|required to) ([^\.]+)",
        r"eligible (?:if|when) ([^\.]+)",
        r"applicants (?:must|should) ([^\.]+)",
    ]

    for pattern in requirement_patterns:
        matches = re.findall(pattern, text_lower, re.IGNORECASE)
        requirements.extend([m.strip() for m in matches[:3]])

    if requirements:
        eligibility["requirements"] = requirements[:5]

    return eligibility

def determine_currency(text: str, url: str, silo: str) -> str:
    """Determine currency based on context"""
    text_lower = text.lower() + " " + url.lower()

    if "€" in text or "eur" in text_lower or "euro" in text_lower:
        return "EUR"
    elif "$" in text or "usd" in text_lower or "dollar" in text_lower:
        return "USD"
    elif "£" in text or "gbp" in text_lower or "sterling" in text_lower:
        return "GBP"

    # Default by silo
    defaults = {"UK": "GBP", "EU": "EUR", "US": "USD"}
    return defaults.get(silo, "GBP")

def convert_grant(old_grant: Dict) -> Dict:
    """Convert old format grant to FALM format"""

    # Extract provider info
    provider, silo, funding_body = extract_provider(
        old_grant.get("text", ""),
        old_grant.get("url", "")
    )

    # Extract sectors
    sectors = extract_sectors(old_grant.get("text", ""))

    # Extract eligibility
    eligibility = extract_eligibility(old_grant.get("text", ""))

    # Determine currency
    currency = determine_currency(
        old_grant.get("text", ""),
        old_grant.get("url", ""),
        silo
    )

    # Build FALM format
    falm_grant = {
        "grant_id": old_grant.get("grant_id", f"grant_{hashlib.md5(old_grant.get('title', '').encode()).hexdigest()[:8]}"),
        "title": old_grant.get("title", "Untitled Grant"),
        "provider": provider,
        "silo": silo,
        "funding_body": funding_body,
        "amount_min": old_grant.get("funding_min"),
        "amount_max": old_grant.get("funding_max"),
        "currency": currency,
        "deadline": old_grant.get("close_date"),
        "sectors": sectors,
        "eligibility": eligibility,
        "description": old_grant.get("text", "")[:2000],  # Truncate very long descriptions
        "application_url": old_grant.get("url", ""),
        "supplementary_urls": [],
        "pdf_documents": [],
        "metadata": {
            "open_date": old_grant.get("open_date"),
            "notify_date": old_grant.get("notify_date"),
            "total_pot": old_grant.get("total_pot"),
            "duration_min": old_grant.get("duration_min"),
            "duration_max": old_grant.get("duration_max"),
            "full_text_length": len(old_grant.get("text", "")),
            "migrated_from": "legacy_system"
        }
    }

    return falm_grant

def convert_file(input_path: Path, output_path: Path):
    """Convert a single file"""
    print(f"Converting: {input_path.name}")

    with open(input_path, 'r', encoding='utf-8') as f:
        # Handle both JSON and JSONL
        if input_path.suffix == '.jsonl':
            old_grants = [json.loads(line) for line in f if line.strip()]
        else:
            old_grants = json.load(f)
            if not isinstance(old_grants, list):
                old_grants = [old_grants]

    # Convert each grant
    falm_grants = [convert_grant(g) for g in old_grants]

    # Save to output
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(falm_grants, f, indent=2, ensure_ascii=False)

    print(f"  ✓ Converted {len(falm_grants)} grants")
    print(f"  → {output_path}")

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Convert existing grant data to FALM format"
    )
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Input directory or file (competition-*.json or *.jsonl)"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/silos"),
        help="Output directory for FALM format (default: data/silos)"
    )

    args = parser.parse_args()

    input_path = args.input
    output_dir = args.output

    if input_path.is_file():
        # Convert single file
        # Determine output path based on extracted info
        output_path = output_dir / "converted" / input_path.name
        output_path.parent.mkdir(parents=True, exist_ok=True)
        convert_file(input_path, output_path)

    elif input_path.is_dir():
        # Convert all JSON/JSONL files
        json_files = list(input_path.glob("competition-*.json")) + \
                    list(input_path.glob("*.jsonl"))

        print(f"\nFound {len(json_files)} files to convert\n")

        for json_file in json_files:
            output_path = output_dir / "converted" / json_file.name
            output_path.parent.mkdir(parents=True, exist_ok=True)
            convert_file(json_file, output_path)

        print(f"\n✅ Conversion complete!")
        print(f"Converted files are in: {output_dir / 'converted'}")
        print(f"\nNext steps:")
        print(f"1. Review the converted files")
        print(f"2. Move them to appropriate folders:")
        print(f"   data/silos/UK/IUK/")
        print(f"   data/silos/UK/NIHR/")
        print(f"   etc.")
        print(f"3. Run: python import_by_folders.py")
    else:
        print(f"Error: {input_path} not found")

if __name__ == "__main__":
    main()
```

## SIMP Protocol Enhancement

Your data doesn't need changes for SIMP! The SIMP protocol works at the **communication layer** between agents, not the data layer:

```
┌──────────────────────────────────────────┐
│          Your Grant Data (MongoDB)       │
│  - Stored in your existing format        │
│  - Plus new fields (provider, silo, etc) │
└──────────────┬───────────────────────────┘
               │
               │ Agents query data
               ▼
┌──────────────────────────────────────────┐
│      Vector Database (ChromaDB)          │
│  - Embeddings of grant descriptions      │
│  - Metadata for filtering                │
└──────────────┬───────────────────────────┘
               │
               │ SIMP messages
               ▼
┌──────────────────────────────────────────┐
│          Agent Communication Layer       │
│                                          │
│  Orchestrator → GrantsNLM (search)       │
│  Orchestrator → EligibilityNLM (check)   │
│  Orchestrator → DeadlineNLM (prioritize) │
│                                          │
│  SIMP Message Format:                    │
│  {                                       │
│    "msg_type": "query",                  │
│    "sender": "orchestrator",             │
│    "receiver": "grants_nlm",             │
│    "intent": "search",                   │
│    "context": {                          │
│      "query": "AI grants",               │
│      "filters": {...}                    │
│    }                                     │
│  }                                       │
└──────────────────────────────────────────┘
```

The SIMP protocol enhances efficiency by:
1. **Structured messages** instead of natural language between agents
2. **Embeddings attached** to avoid regenerating
3. **Intent-based routing** to the right specialized agent
4. **Context sharing** without redundant LLM calls

Your grant data remains the same - it's just how agents **talk to each other** that changes!

## Usage Example

### Convert Your Existing Data

```bash
# Convert all your competition JSON files
python convert_existing_data.py \
  --input data/supporting/json \
  --output data/silos/converted

# Review converted files
ls data/silos/converted/

# Move to appropriate funding body folders
mv data/silos/converted/competition-iuk-*.json data/silos/UK/IUK/
mv data/silos/converted/competition-nihr-*.json data/silos/UK/NIHR/

# Import
python import_by_folders.py
```

### Your Hybrid Index Still Works!

You can keep your existing `hybrid_index.pkl` and BM25 search as a **complementary** search method:

```python
# In your queries, combine:
# 1. FALM semantic search (ChromaDB)
# 2. Your existing BM25 index
# 3. Keyword matching

results_falm = await vector_db.search(query, silos)
results_bm25 = your_existing_bm25_search(query)

# Combine and re-rank
combined = merge_and_rank(results_falm, results_bm25)
```

## Summary

✅ **Your existing data structure works!**
✅ **SIMP protocol is for agent communication, not data storage**
✅ **Easy migration script available**
✅ **Keep your hybrid index if you want**
✅ **New structure supports hierarchical silos (IUK, NIHR, etc.)**

The FALM system **extends** your existing work, it doesn't replace it!
