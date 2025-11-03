#!/usr/bin/env python3
"""
Import grants organized by hierarchical folder structure
Supports: data/silos/REGION/FUNDING_BODY/grants.json

Usage:
    python import_by_folders.py
    python import_by_folders.py --region UK
    python import_by_folders.py --funding-body IUK
"""

import json
import requests
import argparse
from pathlib import Path
import sys
from typing import List, Dict, Optional

API_URL = "http://localhost:8000"
SILOS_DIR = Path("data/silos")

def check_api_running():
    """Check if API server is running"""
    try:
        response = requests.get(f"{API_URL}/", timeout=2)
        return response.status_code == 200
    except:
        return False

def import_grant(grant: Dict, funding_body: str, region: str) -> bool:
    """Import a single grant"""
    # Ensure funding_body and silo are set
    if "funding_body" not in grant:
        grant["funding_body"] = funding_body
    if "silo" not in grant:
        grant["silo"] = region

    try:
        response = requests.post(
            f"{API_URL}/api/grants",
            json=grant,
            timeout=30
        )

        if response.status_code == 200:
            return True
        else:
            print(f"        ✗ API Error: {response.status_code} - {response.text[:100]}")
            return False
    except Exception as e:
        print(f"        ✗ Error: {e}")
        return False

def import_json_file(file_path: Path, funding_body: str, region: str) -> tuple:
    """Import grants from a JSON file"""
    try:
        with open(file_path) as f:
            data = json.load(f)

        # Ensure it's a list
        grants = data if isinstance(data, list) else [data]

        success_count = 0
        fail_count = 0

        for grant in grants:
            if import_grant(grant, funding_body, region):
                print(f"        ✓ {grant.get('title', 'Untitled')}")
                success_count += 1
            else:
                print(f"        ✗ Failed: {grant.get('title', 'Untitled')}")
                fail_count += 1

        return success_count, fail_count

    except json.JSONDecodeError as e:
        print(f"        ✗ JSON Error: {e}")
        return 0, 1
    except Exception as e:
        print(f"        ✗ Error reading file: {e}")
        return 0, 1

def import_csv_file(file_path: Path, funding_body: str, region: str) -> tuple:
    """Import grants from a CSV file"""
    try:
        import pandas as pd

        df = pd.read_csv(file_path)
        grants = df.to_dict('records')

        success_count = 0
        fail_count = 0

        for grant in grants:
            # Clean up NaN values
            grant = {k: v for k, v in grant.items() if pd.notna(v)}

            if import_grant(grant, funding_body, region):
                print(f"        ✓ {grant.get('title', 'Untitled')}")
                success_count += 1
            else:
                print(f"        ✗ Failed: {grant.get('title', 'Untitled')}")
                fail_count += 1

        return success_count, fail_count

    except Exception as e:
        print(f"        ✗ Error reading CSV: {e}")
        return 0, 1

def import_folder_structure(region_filter: Optional[str] = None,
                          funding_body_filter: Optional[str] = None):
    """Import all grants from folder structure"""

    if not SILOS_DIR.exists():
        print(f"❌ Directory not found: {SILOS_DIR}")
        print("   Creating directory structure...")
        SILOS_DIR.mkdir(parents=True, exist_ok=True)
        print("   Please add your grant data files to the data/silos/ folder")
        return

    total_success = 0
    total_fail = 0
    total_files = 0

    print("\n" + "=" * 60)
    print("IMPORTING GRANTS FROM FOLDER STRUCTURE")
    print("=" * 60)

    # Iterate through regions (UK, EU, US)
    for region_dir in sorted(SILOS_DIR.iterdir()):
        if not region_dir.is_dir():
            continue

        region = region_dir.name

        # Apply region filter if specified
        if region_filter and region.upper() != region_filter.upper():
            continue

        print(f"\n📂 Region: {region}")

        # Iterate through funding bodies (IUK, NIHR, etc.)
        for funding_body_dir in sorted(region_dir.iterdir()):
            if not funding_body_dir.is_dir():
                continue

            funding_body = funding_body_dir.name

            # Apply funding body filter if specified
            if funding_body_filter and funding_body.upper() != funding_body_filter.upper():
                continue

            print(f"  └─ 📁 Funding Body: {funding_body}")

            # Find all JSON and CSV files recursively
            data_files = list(funding_body_dir.rglob("*.json")) + \
                        list(funding_body_dir.rglob("*.csv"))

            if not data_files:
                print(f"     └─ ⚠️  No data files found")
                continue

            for data_file in sorted(data_files):
                print(f"     └─ 📄 {data_file.relative_to(funding_body_dir)}")
                total_files += 1

                if data_file.suffix == '.json':
                    success, fail = import_json_file(data_file, funding_body, region)
                elif data_file.suffix == '.csv':
                    success, fail = import_csv_file(data_file, funding_body, region)
                else:
                    continue

                total_success += success
                total_fail += fail

    # Summary
    print("\n" + "=" * 60)
    print("IMPORT SUMMARY")
    print("=" * 60)
    print(f"Files processed: {total_files}")
    print(f"✓ Successfully imported: {total_success}")
    print(f"✗ Failed: {total_fail}")

    if total_success > 0:
        print(f"\n🎉 Import complete! {total_success} grants added to the system.")
        print("\nVerify with:")
        print("  curl http://localhost:8000/api/stats")
    elif total_files == 0:
        print("\n⚠️  No data files found.")
        print("\nAdd your grant data to the folder structure:")
        print("  data/silos/UK/IUK/grants.json")
        print("  data/silos/UK/NIHR/fellowships.csv")
        print("  etc.")
    else:
        print("\n⚠️  No grants were successfully imported.")

def create_example_structure():
    """Create example folder structure with sample files"""
    print("\n📁 Creating example folder structure...")

    # UK funding bodies
    uk_bodies = ["IUK", "NIHR", "UKRI", "Charities"]
    for body in uk_bodies:
        path = SILOS_DIR / "UK" / body
        path.mkdir(parents=True, exist_ok=True)
        print(f"  Created: {path}")

    # EU funding bodies
    eu_bodies = ["EIC", "Horizon", "EIT"]
    for body in eu_bodies:
        path = SILOS_DIR / "EU" / body
        path.mkdir(parents=True, exist_ok=True)
        print(f"  Created: {path}")

    # US funding bodies
    us_bodies = ["NSF", "NIH", "DOE"]
    for body in us_bodies:
        path = SILOS_DIR / "US" / body
        path.mkdir(parents=True, exist_ok=True)
        print(f"  Created: {path}")

    # Create example JSON file
    example_grant = [
        {
            "grant_id": "example_001",
            "title": "Example Grant - Replace with Your Data",
            "provider": "Example Provider",
            "silo": "UK",
            "funding_body": "IUK",
            "amount_min": 25000,
            "amount_max": 500000,
            "currency": "GBP",
            "deadline": "2025-12-31",
            "sectors": ["Technology", "AI"],
            "eligibility": {
                "company_type": "Limited Company",
                "location": ["UK"]
            },
            "description": "This is an example grant. Replace with your actual data.",
            "application_url": "https://example.com"
        }
    ]

    example_file = SILOS_DIR / "UK" / "IUK" / "example_grants.json"
    with open(example_file, 'w') as f:
        json.dump(example_grant, f, indent=2)

    print(f"\n✓ Created example file: {example_file}")
    print("\n📝 Edit this file with your grant data, then run:")
    print("   python import_by_folders.py")

def main():
    parser = argparse.ArgumentParser(
        description="Import grants from hierarchical folder structure"
    )
    parser.add_argument(
        "--region",
        help="Filter by region (UK, EU, US)",
        type=str
    )
    parser.add_argument(
        "--funding-body",
        help="Filter by funding body (IUK, NIHR, etc.)",
        type=str
    )
    parser.add_argument(
        "--create-structure",
        action="store_true",
        help="Create example folder structure"
    )

    args = parser.parse_args()

    # Create structure if requested
    if args.create_structure:
        create_example_structure()
        return

    # Check if API is running
    print("🔍 Checking API server...")
    if not check_api_running():
        print("❌ ERROR: FALM API server is not running!")
        print("\nPlease start the server first:")
        print("   ./start_falm.sh")
        print("\nOr in another terminal:")
        print("   python falm_production_api.py")
        sys.exit(1)

    print("✓ API server is running")

    # Import grants
    import_folder_structure(
        region_filter=args.region,
        funding_body_filter=args.funding_body
    )

if __name__ == "__main__":
    main()
