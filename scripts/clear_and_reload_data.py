#!/usr/bin/env python3
"""
Clear test data and reload actual IUK grants
"""

import asyncio
import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.nlms.innovate_uk import InnovateUKNLM
import chromadb
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


async def clear_test_data():
    """Delete the test collection"""
    print("=" * 80)
    print("Clearing Test Data from ChromaDB Cloud")
    print("=" * 80)
    print()

    # Connect to ChromaCloud
    api_key = os.getenv("CHROMADB_API_KEY")
    tenant = os.getenv("CHROMADB_TENANT")
    database = os.getenv("CHROMADB_DATABASE")

    client = chromadb.CloudClient(
        api_key=api_key,
        tenant=tenant,
        database=database
    )

    # List and delete collections
    collections = client.list_collections()
    print(f"Found {len(collections)} collection(s)")

    for collection in collections:
        print(f"  Deleting collection: {collection.name}")
        client.delete_collection(collection.name)
        print(f"  ✓ Deleted")

    print()


async def load_actual_data():
    """Load actual IUK grants from iuk_grants_export.json"""
    print("=" * 80)
    print("Loading Actual IUK Grants Data")
    print("=" * 80)
    print()

    # Load the JSON file
    data_file = Path(__file__).parent.parent / "data" / "iuk_grants_export.json"

    if not data_file.exists():
        print(f"❌ Data file not found: {data_file}")
        return

    with open(data_file) as f:
        data = json.load(f)

    raw_grants = data.get("grants", [])
    print(f"Found {len(raw_grants)} grants in export file")
    print()

    # The scraped data is minimal - we need to enrich it
    # For now, let's create basic grant records from what we have
    grants = []
    for grant in raw_grants:
        competition_id = grant.get("competition_id")

        # Create a basic grant record
        enriched = {
            "grant_id": f"IUK_{competition_id}",
            "title": f"Innovate UK Competition {competition_id}",
            "description": f"Innovation funding opportunity from Innovate UK. Competition ID: {competition_id}. Visit the source URL for full details.",
            "source_url": grant.get("source_url"),
            "funding_body": "Innovate UK",
            "currency": grant.get("currency", "GBP"),
            "match_funding_required": grant.get("match_funding_required"),
            "scraped_at": grant.get("scraped_at"),
            "silo": "UK"
        }

        grants.append(enriched)

    # Remove duplicates by competition_id
    unique_grants = {}
    for grant in grants:
        comp_id = grant["grant_id"]
        if comp_id not in unique_grants:
            unique_grants[comp_id] = grant

    grants = list(unique_grants.values())
    print(f"After deduplication: {len(grants)} unique grants")
    print()

    # Initialize NLM and load
    nlm = InnovateUKNLM()
    await nlm.initialize()

    print(f"Batch indexing {len(grants)} grants...")
    grant_ids = await nlm.index_grants_batch(grants, batch_size=32)

    print()
    print(f"✅ Successfully indexed {len(grant_ids)} grants")
    print()


async def main():
    """Main function"""
    try:
        # Step 1: Clear test data
        await clear_test_data()

        # Step 2: Load actual data
        await load_actual_data()

        print("=" * 80)
        print("✅ DATA MIGRATION COMPLETE")
        print("=" * 80)
        print()
        print("Next steps:")
        print("1. Verify: python scripts/test_chromadb_connection.py")
        print("2. Test search: python main.py")
        print()

    except Exception as e:
        print()
        print("=" * 80)
        print("❌ ERROR")
        print("=" * 80)
        print(f"{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
