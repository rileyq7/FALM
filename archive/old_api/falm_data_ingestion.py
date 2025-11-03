"""
FALM Data Ingestion Tool
Easy-to-use script for adding your grant data to the FALM system
"""

import json
import asyncio
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

API_BASE_URL = "http://localhost:8000"  # Change this if deployed elsewhere

# ============================================================================
# GRANT DATA TEMPLATES
# ============================================================================

def create_grant_template(
    title: str,
    provider: str,
    silo: str = "UK",
    amount_min: float = None,
    amount_max: float = None,
    currency: str = "GBP",
    deadline: str = None,  # ISO format: "2025-12-31"
    sectors: List[str] = None,
    eligibility_requirements: Dict = None,
    description: str = "",
    application_url: str = "",
    supplementary_urls: List[str] = None,
    pdf_documents: List[str] = None,
    metadata: Dict = None
) -> Dict:
    """
    Create a grant data template
    
    Example:
    grant = create_grant_template(
        title="Innovate UK Smart Grants",
        provider="Innovate UK",
        silo="UK",
        amount_min=25000,
        amount_max=500000,
        currency="GBP",
        deadline="2025-12-15",
        sectors=["AI", "Technology", "Innovation"],
        eligibility_requirements={
            "company_type": "UK Limited Company",
            "location": ["UK"],
            "min_employees": 1
        }
    )
    """
    import hashlib
    
    grant_id = hashlib.md5(f"{title}{provider}{silo}".encode()).hexdigest()[:12]
    
    return {
        "grant_id": grant_id,
        "title": title,
        "provider": provider,
        "silo": silo,
        "amount_min": amount_min,
        "amount_max": amount_max,
        "currency": currency,
        "deadline": deadline,
        "sectors": sectors or [],
        "eligibility": eligibility_requirements or {},
        "description": description,
        "application_url": application_url,
        "supplementary_urls": supplementary_urls or [],
        "pdf_documents": pdf_documents or [],
        "metadata": metadata or {}
    }

# ============================================================================
# DATA INGESTION FUNCTIONS
# ============================================================================

def ingest_single_grant(grant_data: Dict) -> bool:
    """Add a single grant to the system"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/grants",
            json=grant_data
        )
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"✓ Added grant: {grant_data['title']} (ID: {result.get('grant_id')})")
            return True
        else:
            logger.error(f"✗ Failed to add grant: {response.text}")
            return False
    except Exception as e:
        logger.error(f"✗ Error adding grant: {e}")
        return False

def ingest_from_url(
    url: str,
    silo: str = "UK",
    follow_links: bool = True,
    max_depth: int = 2,
    metadata: Dict = None
) -> bool:
    """Scrape and ingest grant data from a URL"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/ingest/url",
            json={
                "source_url": url,
                "source_type": "web",
                "silo": silo,
                "follow_links": follow_links,
                "max_depth": max_depth,
                "metadata": metadata or {}
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"✓ Ingested from URL: {url}")
            logger.info(f"  - Grant ID: {result.get('grant_id')}")
            logger.info(f"  - Title: {result.get('title')}")
            logger.info(f"  - Supplementary URLs found: {result.get('supplementary_urls', 0)}")
            logger.info(f"  - PDFs found: {result.get('pdfs', 0)}")
            return True
        else:
            logger.error(f"✗ Failed to ingest URL: {response.text}")
            return False
    except Exception as e:
        logger.error(f"✗ Error ingesting URL: {e}")
        return False

def ingest_bulk_file(file_path: str, silo: str = "UK") -> bool:
    """Ingest grants from a JSON or CSV file"""
    try:
        with open(file_path, 'rb') as f:
            files = {'file': (Path(file_path).name, f)}
            response = requests.post(
                f"{API_BASE_URL}/api/ingest/file",
                files=files,
                data={'silo': silo}
            )
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"✓ Bulk imported {result.get('imported', 0)} grants from {file_path}")
            return True
        else:
            logger.error(f"✗ Failed to import file: {response.text}")
            return False
    except Exception as e:
        logger.error(f"✗ Error importing file: {e}")
        return False

def schedule_automatic_updates(
    url: str,
    silo: str = "UK",
    follow_links: bool = True,
    max_depth: int = 2
) -> bool:
    """Schedule a source for automatic daily updates"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/schedule/source",
            json={
                "source_url": url,
                "source_type": "web",
                "silo": silo,
                "follow_links": follow_links,
                "max_depth": max_depth
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"✓ Scheduled for updates: {url}")
            logger.info(f"  Total scheduled sources: {result.get('sources', 0)}")
            return True
        else:
            logger.error(f"✗ Failed to schedule: {response.text}")
            return False
    except Exception as e:
        logger.error(f"✗ Error scheduling: {e}")
        return False

# ============================================================================
# SAMPLE DATA SETS
# ============================================================================

def get_sample_uk_grants() -> List[Dict]:
    """Sample UK grants data"""
    return [
        create_grant_template(
            title="Innovate UK Smart Grants: January 2025",
            provider="Innovate UK",
            silo="UK",
            amount_min=25000,
            amount_max=500000,
            currency="GBP",
            deadline="2025-12-15",
            sectors=["Technology", "AI", "Innovation", "R&D"],
            eligibility_requirements={
                "company_type": "UK Limited Company",
                "location": ["UK"],
                "min_employees": 1,
                "requirements": [
                    "Must be UK registered",
                    "Innovative project",
                    "Match funding required"
                ]
            },
            description="Smart Grants funds game-changing innovations with strong commercial potential",
            application_url="https://apply-for-innovation-funding.service.gov.uk/competition/2313/overview",
            supplementary_urls=[
                "https://www.ukri.org/councils/innovate-uk/guidance-for-applicants/",
                "https://www.ukri.org/councils/innovate-uk/guidance-for-applicants/costs-we-fund/"
            ]
        ),
        
        create_grant_template(
            title="UKRI Future Leaders Fellowships",
            provider="UKRI",
            silo="UK",
            amount_min=400000,
            amount_max=1500000,
            currency="GBP",
            deadline="2025-11-30",
            sectors=["Research", "Science", "Technology", "Engineering"],
            eligibility_requirements={
                "company_type": "University or Research Organization",
                "location": ["UK"],
                "career_stage": "Early to mid-career researchers"
            },
            description="Develop the next generation of research and innovation leaders",
            application_url="https://www.ukri.org/opportunity/future-leaders-fellowships-round-9/"
        ),
        
        create_grant_template(
            title="Creative Catalyst Fund",
            provider="Arts Council England",
            silo="UK",
            amount_min=5000,
            amount_max=50000,
            currency="GBP",
            deadline="2025-10-31",
            sectors=["Creative", "Arts", "Digital", "Media"],
            eligibility_requirements={
                "company_type": "Creative Business or Freelancer",
                "location": ["England"],
                "min_employees": 0
            },
            description="Support creative businesses to innovate and grow",
            application_url="https://www.artscouncil.org.uk/funding"
        )
    ]

def get_sample_eu_grants() -> List[Dict]:
    """Sample EU grants data"""
    return [
        create_grant_template(
            title="EIC Accelerator",
            provider="European Innovation Council",
            silo="EU",
            amount_min=500000,
            amount_max=2500000,
            currency="EUR",
            deadline="2025-10-15",
            sectors=["DeepTech", "Innovation", "Scale-up"],
            eligibility_requirements={
                "company_type": "SME",
                "location": ["EU Member State", "Associated Country"],
                "max_employees": 250,
                "requirements": [
                    "High-risk innovation",
                    "Market-creating potential",
                    "Scale-up ready"
                ]
            },
            description="Support breakthrough innovations with scale-up potential",
            application_url="https://eic.ec.europa.eu/eic-funding-opportunities/eic-accelerator_en"
        ),
        
        create_grant_template(
            title="Horizon Europe - Digital and Industry",
            provider="European Commission",
            silo="EU",
            amount_min=1000000,
            amount_max=5000000,
            currency="EUR",
            deadline="2025-11-20",
            sectors=["Digital", "AI", "Robotics", "Manufacturing"],
            eligibility_requirements={
                "company_type": "Consortium (min 3 partners)",
                "location": ["EU Member State", "Associated Country"],
                "consortium_requirements": "3+ partners from different countries"
            },
            description="Collaborative research for digital transformation",
            application_url="https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-search"
        ),
        
        create_grant_template(
            title="LIFE Programme - Climate Action",
            provider="European Commission",
            silo="EU",
            amount_min=500000,
            amount_max=10000000,
            currency="EUR",
            deadline="2025-09-30",
            sectors=["Environment", "Climate", "Sustainability", "Green Tech"],
            eligibility_requirements={
                "company_type": "Any legal entity",
                "location": ["EU Member State"],
                "focus": "Climate mitigation or adaptation"
            },
            description="Support environmental and climate projects",
            application_url="https://cinea.ec.europa.eu/programmes/life_en"
        )
    ]

def get_sample_us_grants() -> List[Dict]:
    """Sample US grants data"""
    return [
        create_grant_template(
            title="SBIR Phase I - NSF",
            provider="National Science Foundation",
            silo="US",
            amount_min=225000,
            amount_max=275000,
            currency="USD",
            deadline="2025-12-01",
            sectors=["Technology", "Innovation", "R&D"],
            eligibility_requirements={
                "company_type": "Small Business",
                "location": ["United States"],
                "max_employees": 500,
                "requirements": [
                    "US-based small business",
                    "Majority US-owned",
                    "Principal investigator employed by company"
                ]
            },
            description="Seed funding for proof of concept",
            application_url="https://seedfund.nsf.gov/"
        ),
        
        create_grant_template(
            title="DOE ARPA-E Open",
            provider="Department of Energy",
            silo="US",
            amount_min=500000,
            amount_max=10000000,
            currency="USD",
            deadline="2025-11-15",
            sectors=["Energy", "CleanTech", "Advanced Materials"],
            eligibility_requirements={
                "company_type": "Any US Entity",
                "location": ["United States"],
                "technology_readiness": "TRL 3-7"
            },
            description="Transformative energy technologies",
            application_url="https://arpa-e.energy.gov/technologies/open"
        )
    ]

# ============================================================================
# REAL DATA SOURCES (URLs to scrape)
# ============================================================================

REAL_GRANT_SOURCES = {
    "UK": [
        {
            "url": "https://apply-for-innovation-funding.service.gov.uk/competition/2313/overview",
            "name": "Innovate UK Smart Grants"
        },
        {
            "url": "https://www.ukri.org/opportunity/",
            "name": "UKRI Opportunities"
        },
        {
            "url": "https://www.gov.uk/business-finance-support",
            "name": "UK Government Business Support"
        }
    ],
    "EU": [
        {
            "url": "https://eic.ec.europa.eu/eic-funding-opportunities_en",
            "name": "EIC Funding"
        },
        {
            "url": "https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/home",
            "name": "EU Funding Portal"
        }
    ],
    "US": [
        {
            "url": "https://seedfund.nsf.gov/",
            "name": "NSF SBIR"
        },
        {
            "url": "https://www.sbir.gov/sbirsearch/topic/current",
            "name": "SBIR.gov"
        },
        {
            "url": "https://www.grants.gov/search-grants",
            "name": "Grants.gov"
        }
    ]
}

# ============================================================================
# MAIN INGESTION WORKFLOWS
# ============================================================================

def load_sample_data():
    """Load all sample grant data"""
    logger.info("=" * 60)
    logger.info("LOADING SAMPLE GRANT DATA")
    logger.info("=" * 60)
    
    # Load UK grants
    logger.info("\n🇬🇧 Loading UK Grants...")
    uk_grants = get_sample_uk_grants()
    for grant in uk_grants:
        ingest_single_grant(grant)
    
    # Load EU grants
    logger.info("\n🇪🇺 Loading EU Grants...")
    eu_grants = get_sample_eu_grants()
    for grant in eu_grants:
        ingest_single_grant(grant)
    
    # Load US grants
    logger.info("\n🇺🇸 Loading US Grants...")
    us_grants = get_sample_us_grants()
    for grant in us_grants:
        ingest_single_grant(grant)
    
    logger.info("\n✅ Sample data loading complete!")
    logger.info(f"Total grants added: {len(uk_grants) + len(eu_grants) + len(us_grants)}")

def scrape_real_sources(silo: str = None):
    """Scrape real grant sources from the web"""
    logger.info("=" * 60)
    logger.info("SCRAPING REAL GRANT SOURCES")
    logger.info("=" * 60)
    
    silos_to_scrape = [silo] if silo else ["UK", "EU", "US"]
    
    for current_silo in silos_to_scrape:
        logger.info(f"\n📡 Scraping {current_silo} sources...")
        
        for source in REAL_GRANT_SOURCES.get(current_silo, []):
            logger.info(f"\nProcessing: {source['name']}")
            ingest_from_url(
                url=source['url'],
                silo=current_silo,
                follow_links=True,
                max_depth=2,
                metadata={"source_name": source['name']}
            )
    
    logger.info("\n✅ Real source scraping complete!")

def setup_automatic_updates():
    """Setup automatic daily updates for all sources"""
    logger.info("=" * 60)
    logger.info("SETTING UP AUTOMATIC UPDATES")
    logger.info("=" * 60)
    
    for silo, sources in REAL_GRANT_SOURCES.items():
        for source in sources:
            logger.info(f"Scheduling: {source['name']} ({silo})")
            schedule_automatic_updates(
                url=source['url'],
                silo=silo,
                follow_links=True,
                max_depth=2
            )
    
    logger.info("\n✅ Automatic updates configured!")

def import_custom_data(file_path: str, silo: str = "UK"):
    """Import your custom grant data from a file"""
    logger.info("=" * 60)
    logger.info("IMPORTING CUSTOM DATA")
    logger.info("=" * 60)
    
    logger.info(f"Importing from: {file_path}")
    logger.info(f"Target silo: {silo}")
    
    ingest_bulk_file(file_path, silo)
    
    logger.info("\n✅ Custom data import complete!")

# ============================================================================
# EXAMPLE JSON FILE FORMAT
# ============================================================================

def create_example_json_file():
    """Create an example JSON file showing the expected format"""
    example_grants = [
        {
            "title": "Your Grant Title Here",
            "provider": "Grant Provider Name",
            "amount_min": 10000,
            "amount_max": 100000,
            "currency": "GBP",
            "deadline": "2025-12-31",
            "sectors": ["Technology", "Innovation"],
            "eligibility": {
                "company_type": "Limited Company",
                "location": ["UK"],
                "min_employees": 5
            },
            "description": "Description of the grant",
            "application_url": "https://example.com/apply"
        }
    ]
    
    with open("example_grants.json", "w") as f:
        json.dump(example_grants, f, indent=2)
    
    logger.info("Created example_grants.json - Edit this file with your data!")

# ============================================================================
# INTERACTIVE CLI
# ============================================================================

def main():
    """Interactive CLI for data ingestion"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║              FALM DATA INGESTION TOOL                       ║
║          Easy Grant Data Management System                  ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    while True:
        print("\n📋 OPTIONS:")
        print("1. Load sample grant data")
        print("2. Scrape real grant sources (web)")
        print("3. Import custom data from file (JSON/CSV)")
        print("4. Add single grant manually")
        print("5. Setup automatic daily updates")
        print("6. Create example JSON template")
        print("7. Test specific URL scraping")
        print("8. View system statistics")
        print("0. Exit")
        
        choice = input("\n👉 Select option (0-8): ").strip()
        
        if choice == "0":
            print("👋 Goodbye!")
            break
            
        elif choice == "1":
            load_sample_data()
            
        elif choice == "2":
            silo = input("Enter silo (UK/EU/US or blank for all): ").strip().upper()
            scrape_real_sources(silo if silo else None)
            
        elif choice == "3":
            file_path = input("Enter file path (JSON or CSV): ").strip()
            silo = input("Enter silo (UK/EU/US): ").strip().upper() or "UK"
            import_custom_data(file_path, silo)
            
        elif choice == "4":
            print("\n📝 Enter grant details:")
            grant = create_grant_template(
                title=input("Title: "),
                provider=input("Provider: "),
                silo=input("Silo (UK/EU/US): ").upper() or "UK",
                amount_min=float(input("Min amount (or 0): ") or 0),
                amount_max=float(input("Max amount (or 0): ") or 0),
                currency=input("Currency (GBP/EUR/USD): ").upper() or "GBP",
                deadline=input("Deadline (YYYY-MM-DD or blank): ") or None,
                sectors=input("Sectors (comma-separated): ").split(","),
                description=input("Description: "),
                application_url=input("Application URL: ")
            )
            ingest_single_grant(grant)
            
        elif choice == "5":
            setup_automatic_updates()
            
        elif choice == "6":
            create_example_json_file()
            
        elif choice == "7":
            url = input("Enter URL to scrape: ").strip()
            silo = input("Enter silo (UK/EU/US): ").strip().upper() or "UK"
            ingest_from_url(url, silo)
            
        elif choice == "8":
            try:
                response = requests.get(f"{API_BASE_URL}/api/stats")
                if response.status_code == 200:
                    stats = response.json()
                    print("\n📊 SYSTEM STATISTICS:")
                    print(f"Total grants: {stats.get('total_grants', 0)}")
                    print(f"UK grants: {stats.get('grants_by_silo', {}).get('UK', 0)}")
                    print(f"EU grants: {stats.get('grants_by_silo', {}).get('EU', 0)}")
                    print(f"US grants: {stats.get('grants_by_silo', {}).get('US', 0)}")
                    print(f"Scheduled sources: {stats.get('scheduled_sources', 0)}")
            except Exception as e:
                logger.error(f"Error getting stats: {e}")

if __name__ == "__main__":
    # Check if API is running
    try:
        response = requests.get(f"{API_BASE_URL}/")
        if response.status_code != 200:
            print("⚠️  WARNING: API server not responding. Make sure falm_production_api.py is running!")
            print(f"   Run: python falm_production_api.py")
    except:
        print("⚠️  WARNING: Cannot connect to API server at", API_BASE_URL)
        print("   Make sure falm_production_api.py is running first!")
        print(f"   Run: python falm_production_api.py")
        exit(1)
    
    # Run interactive CLI
    main()
