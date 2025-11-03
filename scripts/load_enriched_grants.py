#!/usr/bin/env python3
"""
Load enriched IUK grants to ChromaDB Cloud
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


async def clear_existing_data():
    """Clear existing IUK collections"""
    print("Clearing existing collections...")

    api_key = os.getenv("CHROMADB_API_KEY")
    tenant = os.getenv("CHROMADB_TENANT")
    database = os.getenv("CHROMADB_DATABASE")

    client = chromadb.CloudClient(
        api_key=api_key,
        tenant=tenant,
        database=database
    )

    # Delete UK_innovate_uk collection if it exists
    collections = client.list_collections()
    for collection in collections:
        if collection.name == "UK_innovate_uk":
            print(f"  Deleting collection: {collection.name}")
            client.delete_collection(collection.name)
            print(f"  ✓ Deleted")


async def load_enriched_grants():
    """Load enriched grants to ChromaDB"""

    print("=" * 80)
    print("Loading Enriched IUK Grants to ChromaDB Cloud")
    print("=" * 80)
    print()

    # Load enriched data
    data_file = Path(__file__).parent.parent / "data" / "iuk_grants_full_enriched.json"

    if not data_file.exists():
        print(f"❌ Data file not found: {data_file}")
        return

    with open(data_file) as f:
        data = json.load(f)

    raw_grants = data.get("grants", [])
    print(f"Found {len(raw_grants)} enriched grants")
    print()

    # Transform to FALM grant format
    grants = []
    for grant in raw_grants:
        competition_id = grant.get("competition_id")

        # Build optimized grant record (without raw_sections to fit quota)
        # Limit description and text fields to reasonable lengths
        description = grant.get("description") or "No description available"
        if len(description) > 2000:
            description = description[:2000] + "..."

        eligibility = " ".join(grant.get("eligibility_criteria", [])) if grant.get("eligibility_criteria") else None
        if eligibility and len(eligibility) > 1500:
            eligibility = eligibility[:1500] + "..."

        scope = grant.get("scope")
        if scope and len(scope) > 1500:
            scope = scope[:1500] + "..."

        application_process = grant.get("application_process")
        if application_process and len(application_process) > 1000:
            application_process = application_process[:1000] + "..."

        enriched = {
            "grant_id": f"IUK_{competition_id}",
            "title": grant.get("title") or f"Innovate UK Competition {competition_id}",
            "description": description,
            "source_url": grant.get("source_url"),
            "funding_body": "Innovate UK",
            "currency": grant.get("currency", "GBP"),
            "silo": "UK",
            "scraped_at": grant.get("scraped_at"),

            # Eligibility
            "eligibility": eligibility,

            # Scope
            "scope": scope,

            # Dates (convert dict to string to save space)
            "deadline": str(grant.get("deadlines", {})),

            # Funding details
            "amount_min": grant.get("funding_details", {}).get("amount_min"),
            "amount_max": grant.get("funding_details", {}).get("amount_max"),
            "funding_rate": grant.get("funding_details", {}).get("funding_rate"),
            "match_funding_required": grant.get("funding_details", {}).get("match_funding_required", True),

            # Application process (truncated)
            "application_process": application_process,

            # Supporting documents (only first 5 to save space)
            "supporting_documents": json.dumps(grant.get("supporting_documents", [])[:5]) if grant.get("supporting_documents") else None,
        }

        # Clean up None values
        enriched = {k: v for k, v in enriched.items() if v is not None and v != ""}

        grants.append(enriched)

    print(f"Prepared {len(grants)} grants for indexing")
    print()

    # Initialize NLM and load
    print("Initializing Innovate UK NLM...")
    nlm = InnovateUKNLM()
    await nlm.initialize()

    print(f"Batch indexing {len(grants)} grants...")
    grant_ids = await nlm.index_grants_batch(grants, batch_size=32)

    print()
    print(f"✅ Successfully indexed {len(grant_ids)} enriched grants")
    print()

    # Show sample
    print("Sample grant details:")
    sample = grants[0]
    print(f"  ID: {sample['grant_id']}")
    print(f"  Title: {sample.get('title', 'N/A')[:80]}")
    print(f"  Description length: {len(sample.get('description', ''))} chars")
    print(f"  Eligibility length: {len(sample.get('eligibility', ''))} chars")
    print(f"  Scope length: {len(sample.get('scope', ''))} chars")
    print(f"  Supporting docs: {len(sample.get('supporting_documents', []))}")
    print()


async def main():
    """Main function"""
    try:
        # Step 1: Clear existing data
        await clear_existing_data()
        print()

        # Step 2: Load enriched data
        await load_enriched_grants()

        print("=" * 80)
        print("✅ ENRICHED DATA LOADED")
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
