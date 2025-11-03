#!/usr/bin/env python3
"""
Auto-Scrape: Intelligent grant scraping with automatic funding body detection
Just provide a URL, and it figures out the rest!
"""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import requests
import argparse
from funding_body_detector import FundingBodyDetector

API_URL = "http://localhost:8000"

def auto_scrape_url(url: str, max_depth: int = 2, verbose: bool = True):
    """
    Automatically scrape a URL with intelligent detection
    """
    # Detect funding body from URL
    silo, funding_body_code, provider_name = FundingBodyDetector.detect_from_url(url)

    if verbose:
        print(f"\n🔍 Auto-detected:")
        print(f"   Region (Silo): {silo}")
        print(f"   Funding Body: {funding_body_code}")
        print(f"   Provider: {provider_name}")
        print(f"\n🌐 Scraping: {url}")
        print(f"   Max depth: {max_depth}")
        print("")

    # Scrape via API
    try:
        response = requests.post(
            f"{API_URL}/api/ingest/url",
            json={
                "source_url": url,
                "silo": silo,
                "provider": provider_name,
                "follow_links": True,
                "max_depth": max_depth,
                "metadata": {
                    "funding_body": funding_body_code,
                    "auto_detected": True
                }
            },
            timeout=120
        )

        if response.status_code == 200:
            result = response.json()

            if verbose:
                print("✅ Successfully scraped!")
                print(f"\n📄 Grant Details:")
                print(f"   ID: {result.get('grant_id', 'N/A')}")
                print(f"   Title: {result.get('title', 'N/A')}")
                print(f"   Supplementary URLs: {result.get('supplementary_urls', 0)}")
                print(f"   PDFs found: {result.get('pdfs', 0)}")
                print(f"\n💾 Stored in:")
                print(f"   Silo: {silo}")
                print(f"   Funding Body: {funding_body_code}")
                print(f"\n🔎 Now searchable via queries!")

            return result
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"   {response.text[:500]}")
            return None

    except Exception as e:
        print(f"❌ Error scraping: {e}")
        return None


def batch_scrape(url_file: str):
    """Scrape multiple URLs from a file"""
    print(f"\n📋 Batch scraping from: {url_file}")
    print("=" * 60)

    try:
        with open(url_file, 'r') as f:
            urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]

        print(f"Found {len(urls)} URLs to scrape\n")

        results = []
        for i, url in enumerate(urls, 1):
            print(f"\n[{i}/{len(urls)}] Processing: {url}")
            print("-" * 60)
            result = auto_scrape_url(url, verbose=True)
            results.append({
                "url": url,
                "success": result is not None,
                "grant_id": result.get('grant_id') if result else None
            })

        # Summary
        print("\n" + "=" * 60)
        print("BATCH SCRAPING SUMMARY")
        print("=" * 60)
        successful = sum(1 for r in results if r['success'])
        print(f"✓ Successful: {successful}/{len(urls)}")
        print(f"✗ Failed: {len(urls) - successful}/{len(urls)}")

        if successful > 0:
            print(f"\n🎉 {successful} grants added to the system!")

    except FileNotFoundError:
        print(f"❌ File not found: {url_file}")
    except Exception as e:
        print(f"❌ Error: {e}")


def list_funding_bodies():
    """List all known funding bodies"""
    print("\n📚 Known Funding Bodies:")
    print("=" * 60)

    all_bodies = FundingBodyDetector.get_all_bodies()

    for silo, bodies in all_bodies.items():
        print(f"\n🌍 {silo} Region:")
        for code, info in bodies.items():
            print(f"   {code:12} - {info['name']}")
            if info['domains']:
                print(f"               Domains: {', '.join(info['domains'][:2])}")


def main():
    parser = argparse.ArgumentParser(
        description="Auto-scrape grant URLs with intelligent detection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scrape a single URL (auto-detects funding body)
  python auto_scrape.py https://apply-for-innovation-funding.service.gov.uk/competition/2313/overview

  # Scrape with custom depth
  python auto_scrape.py https://www.nihr.ac.uk/funding/ --depth 3

  # Batch scrape from file
  python auto_scrape.py --batch urls.txt

  # List all known funding bodies
  python auto_scrape.py --list-bodies
        """
    )

    parser.add_argument(
        "url",
        nargs="?",
        help="URL to scrape"
    )
    parser.add_argument(
        "--depth",
        type=int,
        default=2,
        help="Max depth for link following (default: 2)"
    )
    parser.add_argument(
        "--batch",
        type=str,
        help="File containing URLs to scrape (one per line)"
    )
    parser.add_argument(
        "--list-bodies",
        action="store_true",
        help="List all known funding bodies and exit"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress verbose output"
    )

    args = parser.parse_args()

    # Check API is running
    try:
        response = requests.get(f"{API_URL}/", timeout=2)
        if response.status_code != 200:
            print("❌ API server not responding!")
            print("   Start it with: ./start_falm.sh")
            sys.exit(1)
    except:
        print("❌ Cannot connect to API server!")
        print("   Start it with: ./start_falm.sh")
        sys.exit(1)

    # List bodies
    if args.list_bodies:
        list_funding_bodies()
        return

    # Batch mode
    if args.batch:
        batch_scrape(args.batch)
        return

    # Single URL
    if args.url:
        auto_scrape_url(args.url, max_depth=args.depth, verbose=not args.quiet)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
