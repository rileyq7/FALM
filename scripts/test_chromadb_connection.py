#!/usr/bin/env python3
"""
Test ChromaDB Cloud Connection

Verifies connection to ChromaDB Cloud and shows your collections
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import chromadb
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_cloud_connection():
    """Test connection to ChromaDB Cloud"""

    print("=" * 80)
    print("ChromaDB Cloud Connection Test")
    print("=" * 80)
    print()

    # Get credentials from environment
    api_key = os.getenv("CHROMADB_API_KEY")
    tenant = os.getenv("CHROMADB_TENANT")
    database = os.getenv("CHROMADB_DATABASE")

    print(f"API Key: {api_key[:20]}..." if api_key else "API Key: NOT SET")
    print(f"Tenant: {tenant}")
    print(f"Database: {database}")
    print()

    try:
        # Connect using CloudClient (ChromaCloud)
        print(f"Connecting to ChromaCloud...")
        print(f"Tenant: {tenant}")
        print(f"Database: {database}")

        client = chromadb.CloudClient(
            api_key=api_key,
            tenant=tenant,
            database=database
        )

        print("✅ Connected successfully!")
        print()

        # List collections
        print("Fetching collections...")
        collections = client.list_collections()

        if collections:
            print(f"✅ Found {len(collections)} collection(s):")
            print()

            for collection in collections:
                print(f"📁 Collection: {collection.name}")

                # Get count
                count = collection.count()
                print(f"   Items: {count}")

                # Get metadata
                metadata = collection.metadata
                print(f"   Metadata: {metadata}")
                print()

        else:
            print("⚠️  No collections found yet.")
            print("   Collections will be created when you load grants.")
            print()

        # Test heartbeat
        print("Testing heartbeat...")
        heartbeat = client.heartbeat()
        print(f"✅ Heartbeat: {heartbeat}")
        print()

        print("=" * 80)
        print("✅ ChromaDB Cloud is READY!")
        print("=" * 80)
        print()
        print("Next steps:")
        print("1. Load grants: python scripts/load_grants.py --source example --nlm innovate_uk --count 100")
        print("2. Start system: python main.py")
        print("3. Query grants: curl -X POST http://localhost:8000/api/query ...")
        print()

        return True

    except Exception as e:
        print()
        print("=" * 80)
        print("❌ Connection FAILED")
        print("=" * 80)
        print(f"Error: {e}")
        print()
        print("Troubleshooting:")
        print("1. Check your .env file has correct credentials")
        print("2. Verify API key is active in ChromaDB Cloud dashboard")
        print("3. Ensure tenant and database names are correct")
        print()
        return False


if __name__ == "__main__":
    success = test_cloud_connection()
    sys.exit(0 if success else 1)
