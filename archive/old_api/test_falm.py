"""
FALM System Test Script
Tests all major functionality
"""

import requests
import json
import time

API_URL = "http://localhost:8000"

def test_health():
    """Test API health"""
    print("Testing API health...")
    response = requests.get(f"{API_URL}/")
    assert response.status_code == 200
    print("✓ API is healthy")

def test_query():
    """Test query endpoint"""
    print("\nTesting query endpoint...")
    query_data = {
        "query": "What grants are available for AI startups?",
        "silos": ["UK", "EU"],
        "max_results": 5
    }
    response = requests.post(f"{API_URL}/api/query", json=query_data)
    assert response.status_code == 200
    result = response.json()
    print(f"✓ Query processed in {result.get('processing_time', 0):.2f}s")
    print(f"  Answer preview: {result.get('answer', '')[:100]}...")

def test_stats():
    """Test stats endpoint"""
    print("\nTesting stats endpoint...")
    response = requests.get(f"{API_URL}/api/stats")
    assert response.status_code == 200
    stats = response.json()
    print("✓ Stats retrieved")
    print(f"  Total grants: {stats.get('total_grants', 0)}")
    print(f"  UK: {stats.get('grants_by_silo', {}).get('UK', 0)}")
    print(f"  EU: {stats.get('grants_by_silo', {}).get('EU', 0)}")
    print(f"  US: {stats.get('grants_by_silo', {}).get('US', 0)}")

def run_tests():
    """Run all tests"""
    print("=" * 50)
    print("FALM SYSTEM TESTS")
    print("=" * 50)
    
    try:
        test_health()
        test_query()
        test_stats()
        print("\n✅ All tests passed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        print("\nMake sure the API server is running:")
        print("  ./start_falm.sh")

if __name__ == "__main__":
    run_tests()
