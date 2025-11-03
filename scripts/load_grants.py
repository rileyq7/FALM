#!/usr/bin/env python3
"""
Grant Loader Script

Load grants from various sources (JSON, CSV, API) and index them
using batch indexing for 10-100x faster performance.

Usage:
    python scripts/load_grants.py --source grants.json --nlm innovate_uk
    python scripts/load_grants.py --source grants.csv --nlm horizon_europe
"""

import asyncio
import json
import csv
import sys
from pathlib import Path
from typing import List, Dict
import logging

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.nlms import InnovateUKNLM, HorizonEuropeNLM, NIHRNLM, UKRINLM

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# GRANT PARSERS
# ============================================================================

def parse_json_file(file_path: str) -> List[Dict]:
    """
    Parse grants from JSON file

    Expected format:
    [
        {
            "title": "Grant Title",
            "description": "Grant description",
            "amount_min": 25000,
            "amount_max": 2000000,
            "deadline": "2025-12-31",
            "sectors": ["AI & Data", "Healthcare"],
            "url": "https://...",
            ...
        }
    ]
    """
    logger.info(f"Loading grants from JSON: {file_path}")

    with open(file_path, 'r') as f:
        grants = json.load(f)

    logger.info(f"Loaded {len(grants)} grants from JSON")
    return grants


def parse_csv_file(file_path: str) -> List[Dict]:
    """
    Parse grants from CSV file

    Expected columns:
    - title
    - description
    - amount_min
    - amount_max
    - deadline
    - sectors (comma-separated)
    - url
    """
    logger.info(f"Loading grants from CSV: {file_path}")

    grants = []
    with open(file_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Parse sectors (comma-separated string to list)
            if 'sectors' in row and row['sectors']:
                row['sectors'] = [s.strip() for s in row['sectors'].split(',')]

            # Convert numeric fields
            if 'amount_min' in row and row['amount_min']:
                row['amount_min'] = int(row['amount_min'])
            if 'amount_max' in row and row['amount_max']:
                row['amount_max'] = int(row['amount_max'])

            grants.append(row)

    logger.info(f"Loaded {len(grants)} grants from CSV")
    return grants


def parse_scraped_data(data_dir: str = "data/grants") -> List[Dict]:
    """
    Parse grants from scraped HTML/JSON files in data directory

    Looks for files like:
    - data/grants/innovate_uk/*.json
    - data/grants/horizon_europe/*.json
    """
    logger.info(f"Loading grants from directory: {data_dir}")

    grants = []
    data_path = Path(data_dir)

    # Find all JSON files
    for json_file in data_path.rglob("*.json"):
        try:
            with open(json_file, 'r') as f:
                grant_data = json.load(f)

                # Handle both single grant and list of grants
                if isinstance(grant_data, list):
                    grants.extend(grant_data)
                else:
                    grants.append(grant_data)

        except Exception as e:
            logger.warning(f"Failed to load {json_file}: {e}")

    logger.info(f"Loaded {len(grants)} grants from scraped data")
    return grants


# ============================================================================
# GRANT ENRICHMENT
# ============================================================================

def enrich_grant(grant: Dict, domain: str) -> Dict:
    """
    Enrich grant with required metadata

    Ensures each grant has:
    - grant_id
    - domain
    - indexed_at (added automatically by NLM)
    """
    # Generate grant_id if missing
    if 'grant_id' not in grant or not grant['grant_id']:
        # Use title hash or URL as ID
        title = grant.get('title', 'unknown')
        grant['grant_id'] = f"{domain}_{hash(title) & 0xFFFFFFFF}"

    # Ensure required fields exist
    grant.setdefault('title', 'Untitled Grant')
    grant.setdefault('description', '')
    grant.setdefault('sectors', [])
    grant.setdefault('deadline', '2099-12-31')

    return grant


# ============================================================================
# BATCH LOADING
# ============================================================================

async def load_grants_to_nlm(nlm_name: str, grants: List[Dict]) -> List[str]:
    """
    Load grants to specified NLM using batch indexing

    Args:
        nlm_name: Name of NLM (innovate_uk, horizon_europe, nihr, ukri)
        grants: List of grant dictionaries

    Returns:
        List of grant IDs that were indexed
    """
    # Initialize NLM
    nlm_map = {
        'innovate_uk': InnovateUKNLM(),
        'horizon_europe': HorizonEuropeNLM(),
        'nihr': NIHRNLM(),
        'ukri': UKRINLM()
    }

    if nlm_name not in nlm_map:
        raise ValueError(f"Unknown NLM: {nlm_name}. Choose from: {list(nlm_map.keys())}")

    nlm = nlm_map[nlm_name]
    logger.info(f"Initializing NLM: {nlm.nlm_id}")
    await nlm.initialize()

    # Enrich grants
    enriched_grants = [enrich_grant(g, nlm.domain) for g in grants]

    # Batch index (FAST!)
    logger.info(f"Batch indexing {len(enriched_grants)} grants to {nlm.nlm_id}...")
    grant_ids = await nlm.index_grants_batch(enriched_grants, batch_size=32)

    logger.info(f"✅ Successfully indexed {len(grant_ids)} grants to {nlm.nlm_id}")

    return grant_ids


# ============================================================================
# EXAMPLE GRANT DATA
# ============================================================================

def create_example_grants(count: int = 100) -> List[Dict]:
    """Create example grants for testing"""
    logger.info(f"Creating {count} example grants...")

    grants = []
    sectors_list = [
        ["AI & Data", "Technology"],
        ["Healthcare", "MedTech"],
        ["Clean Energy", "Sustainability"],
        ["Manufacturing", "Advanced Materials"],
        ["AgriTech", "Food & Drink"]
    ]

    for i in range(count):
        grant = {
            "grant_id": f"EXAMPLE_{i}",
            "title": f"Innovation Grant {i}: AI & Digital Transformation",
            "description": f"Funding for innovative projects in AI, machine learning, and digital transformation. "
                          f"This is example grant number {i} with realistic content for testing purposes.",
            "amount_min": 25000,
            "amount_max": 500000 + (i * 10000),
            "deadline": f"2025-{(i % 12) + 1:02d}-{min((i % 28) + 1, 28):02d}",
            "sectors": sectors_list[i % len(sectors_list)],
            "eligibility": "UK SME with <250 employees",
            "url": f"https://example.com/grants/{i}",
            "funding_body": "Innovate UK"
        }
        grants.append(grant)

    return grants


# ============================================================================
# CLI INTERFACE
# ============================================================================

async def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Load grants into FALM system")
    parser.add_argument('--source', help='Source file (JSON/CSV) or "example" for test data')
    parser.add_argument('--nlm', required=True,
                       choices=['innovate_uk', 'horizon_europe', 'nihr', 'ukri'],
                       help='Target NLM')
    parser.add_argument('--count', type=int, default=100,
                       help='Number of example grants (if source=example)')

    args = parser.parse_args()

    # Load grants
    if args.source == 'example':
        grants = create_example_grants(args.count)
    elif args.source.endswith('.json'):
        grants = parse_json_file(args.source)
    elif args.source.endswith('.csv'):
        grants = parse_csv_file(args.source)
    elif Path(args.source).is_dir():
        grants = parse_scraped_data(args.source)
    else:
        logger.error(f"Unknown source format: {args.source}")
        return

    # Load to NLM
    grant_ids = await load_grants_to_nlm(args.nlm, grants)

    logger.info("=" * 80)
    logger.info(f"✅ LOADING COMPLETE")
    logger.info(f"   NLM: {args.nlm}")
    logger.info(f"   Grants indexed: {len(grant_ids)}")
    logger.info("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
