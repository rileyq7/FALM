# Bespoke Scrapers Per Node

## Current Status ✅

**The 422 validation error is FIXED!**

- ✅ All 30 URLs successfully ingested into IUK node
- ✅ Federated architecture working: 3 nodes (IUK, NIHR, Wellcome)
- ✅ Each node has isolated data: `data/nodes/UK_IUK/`, `data/nodes/UK_NIHR/`, etc.
- ✅ Auto-detection working: URLs automatically routed to correct nodes

## Current Architecture

Each node is **completely self-contained**:

```
data/nodes/UK_IUK/
├── chroma_db/      ← IUK's own vector database
├── cache/          ← IUK's own cache
└── logs/           ← IUK's own logs
```

## Why Bespoke Scrapers?

Each funding body has **different page structures**:

### Innovate UK (IUK)
- Competition pages with structured sections
- Guidance documents in tabs
- PDF eligibility documents
- Multi-page application flows

### NIHR
- Research programs with different formats
- Complex eligibility matrices
- Academic focus (different keywords)
- Call documents with specific structures

### Wellcome Trust
- Fellowship programs
- Different funding streams
- Researcher profiles
- Science-focused content

## How to Add Bespoke Scrapers

### 1. Each Node Has Its Own Scraper

The `scrape_source()` method is overridden per node:

```python
class InnovateUKNode(FederatedNode):
    async def scrape_source(self, url: str) -> Dict[str, Any]:
        """IUK-specific scraping logic"""

        # 1. Fetch the page
        html = await self._fetch_html(url)
        soup = BeautifulSoup(html, 'html.parser')

        # 2. IUK-SPECIFIC extraction
        grant_data = {
            "title": soup.select_one('.competition-title').text,
            "competition_id": self._extract_competition_id(url),
            "funding_amount": self._parse_iuk_funding(soup),
            "deadline": self._parse_iuk_deadline(soup),
            "sectors": self._extract_iuk_sectors(soup),
            "eligibility": self._parse_iuk_eligibility(soup),
            # ... IUK-specific fields
        }

        return grant_data
```

### 2. Node-Specific Scraper Files

Each node should have its own scraper module:

```
federated_nodes/
├── base_node.py           ← FederatedNode base class
├── iuk_node.py            ← InnovateUKNode with IUK scraper
├── nihr_node.py           ← NIHRNode with NIHR scraper
├── wellcome_node.py       ← WellcomeNode with Wellcome scraper
└── scrapers/
    ├── iuk_scraper.py     ← IUK scraping logic
    ├── nihr_scraper.py    ← NIHR scraping logic
    └── wellcome_scraper.py ← Wellcome scraping logic
```

### 3. Current Implementation Status

**Currently**: Basic stubs that store URL metadata

```python
async def scrape_source(self, url: str) -> Dict[str, Any]:
    """Basic stub - returns minimal data"""
    return {
        "funding_body": self.funding_body_code,
        "silo": self.silo,
        "source_url": url,
        "scraped_at": datetime.utcnow().isoformat()
    }
```

**What's Needed**: Full HTML parsing with bespoke extractors

## Implementation Plan

### Phase 1: Create Scraper Modules (Per Node)

Create specialized scrapers for each funding body:

```python
# scrapers/iuk_scraper.py
class IUKScraper:
    """Innovate UK specialized scraper"""

    def __init__(self):
        self.base_selectors = {
            'title': '.competition-title h1',
            'summary': '.competition-summary',
            'funding': '.funding-details',
            'deadline': '.deadline-info'
        }

    async def scrape_competition(self, url: str) -> Dict[str, Any]:
        """Extract competition data from IUK page"""
        html = await self._fetch(url)
        soup = BeautifulSoup(html, 'html.parser')

        return {
            "title": self._extract_title(soup),
            "summary": self._extract_summary(soup),
            "funding_min": self._extract_funding_min(soup),
            "funding_max": self._extract_funding_max(soup),
            "deadline": self._extract_deadline(soup),
            "competition_id": self._extract_competition_id(url),
            "eligibility": self._extract_eligibility(soup),
            "sectors": self._extract_sectors(soup),
            "application_url": url,
            "guidance_pdfs": self._extract_pdfs(soup, url),
            "supplementary_urls": self._extract_links(soup, url)
        }

    def _extract_title(self, soup):
        """IUK-specific title extraction"""
        elem = soup.select_one('.competition-title h1')
        return elem.text.strip() if elem else "N/A"

    def _extract_funding_min(self, soup):
        """Parse IUK funding amounts"""
        # IUK-specific parsing logic
        pass

    # ... more IUK-specific methods
```

### Phase 2: Integrate into Nodes

Update each node to use its scraper:

```python
# In federated_nodes.py
from scrapers.iuk_scraper import IUKScraper

class InnovateUKNode(FederatedNode):
    def __init__(self):
        super().__init__(
            funding_body_code="IUK",
            funding_body_name="Innovate UK",
            silo="UK",
            base_urls=[...]
        )
        # Add bespoke scraper
        self.scraper = IUKScraper()

    async def scrape_source(self, url: str) -> Dict[str, Any]:
        """Use IUK-specific scraper"""
        return await self.scraper.scrape_competition(url)
```

### Phase 3: Add Selectors Config

Each node can have a config file for easy updates:

```json
// scrapers/iuk_selectors.json
{
  "competition_page": {
    "title": ".competition-title h1",
    "summary": ".competition-summary p",
    "funding": {
      "min": ".funding-range .min-amount",
      "max": ".funding-range .max-amount"
    },
    "deadline": ".deadline-date",
    "eligibility": ".eligibility-criteria ul li",
    "sectors": ".sector-tags .tag",
    "guidance_links": ".guidance-documents a[href$='.pdf']"
  }
}
```

## Example: Complete IUK Scraper

Here's what a full IUK scraper would look like:

```python
import aiohttp
from bs4 import BeautifulSoup
from datetime import datetime
import re

class IUKScraper:
    """Innovate UK Competition Scraper"""

    BASE_URL = "https://apply-for-innovation-funding.service.gov.uk"

    async def scrape_competition(self, url: str) -> Dict[str, Any]:
        """Scrape IUK competition page"""

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                html = await response.text()

        soup = BeautifulSoup(html, 'html.parser')

        # Extract all data
        grant_data = {
            "grant_id": self._extract_competition_id(url),
            "title": self._extract_title(soup),
            "provider": "Innovate UK",
            "funding_body": "IUK",
            "silo": "UK",
            "summary": self._extract_summary(soup),
            "description": self._extract_description(soup),
            "amount_min": self._extract_funding_min(soup),
            "amount_max": self._extract_funding_max(soup),
            "currency": "GBP",
            "deadline": self._extract_deadline(soup),
            "sectors": self._extract_sectors(soup),
            "eligibility": self._extract_eligibility(soup),
            "application_url": url,
            "supplementary_urls": self._extract_links(soup, url),
            "pdf_documents": self._extract_pdfs(soup, url),
            "metadata": {
                "competition_id": self._extract_competition_id(url),
                "match_funding_required": self._check_match_funding(soup),
                "collaboration_required": self._check_collaboration(soup),
                "scraped_at": datetime.utcnow().isoformat()
            }
        }

        return grant_data

    def _extract_competition_id(self, url: str) -> str:
        """Extract competition ID from URL"""
        match = re.search(r'/competition/(\d+)/', url)
        return f"IUK_{match.group(1)}" if match else None

    def _extract_title(self, soup) -> str:
        """Extract competition title"""
        title_elem = soup.select_one('h1.govuk-heading-xl')
        return title_elem.text.strip() if title_elem else "N/A"

    def _extract_funding_min(self, soup) -> float:
        """Extract minimum funding amount"""
        funding_text = soup.select_one('.funding-amount')
        if funding_text:
            match = re.search(r'£([\d,]+)', funding_text.text)
            if match:
                return float(match.group(1).replace(',', ''))
        return None

    # ... more extraction methods
```

## Benefits of Bespoke Scrapers

### 1. Accuracy
- Each scraper knows exactly where to find data on its funding body's pages
- No generic "one-size-fits-all" that misses important fields

### 2. Maintainability
- If IUK changes their page structure, only update `iuk_scraper.py`
- NIHR changes don't affect IUK scraper

### 3. Extensibility
- Easy to add new funding bodies
- Just create new scraper module and node class

### 4. Specialization
- IUK scraper can extract "competition_id", "match_funding", etc.
- NIHR scraper can extract "research_area", "career_stage", etc.
- Each gets exactly the fields it needs

## Next Steps

### Option A: Implement Scrapers Gradually
1. Start with IUK (since you have 30 IUK URLs)
2. Test and refine IUK scraper
3. Move to NIHR when ready
4. Add more funding bodies

### Option B: Use LLM-Assisted Scraping
- Each node can use Claude to extract structured data from HTML
- More flexible, adapts to page changes
- Already integrated with SIMP protocol

### Recommended: Hybrid Approach
```python
class InnovateUKNode(FederatedNode):
    async def scrape_source(self, url: str) -> Dict[str, Any]:
        """Hybrid scraping approach"""

        # 1. Try structured scraping first
        try:
            return await self.scraper.scrape_competition(url)
        except Exception as e:
            logger.warning(f"Structured scraping failed: {e}")

        # 2. Fall back to LLM extraction
        html = await self._fetch_html(url)
        return await self._llm_extract(html)

    async def _llm_extract(self, html: str) -> Dict[str, Any]:
        """Use Claude to extract data when structured scraping fails"""
        prompt = f"""Extract grant information from this HTML:

        {html[:5000]}  # Truncate to fit context

        Return JSON with: title, funding_amount, deadline, eligibility, etc.
        """
        # Use Anthropic API or OpenAI
        pass
```

## Testing Your Scrapers

Test each scraper individually:

```python
# test_iuk_scraper.py
import asyncio
from scrapers.iuk_scraper import IUKScraper

async def test():
    scraper = IUKScraper()

    url = "https://apply-for-innovation-funding.service.gov.uk/competition/2313/overview"

    result = await scraper.scrape_competition(url)

    print(f"Title: {result['title']}")
    print(f"Funding: £{result['amount_min']} - £{result['amount_max']}")
    print(f"Deadline: {result['deadline']}")
    print(f"Sectors: {result['sectors']}")

asyncio.run(test())
```

## Current Working System

**What's working now**:
- ✅ 30 grants stored in IUK node's database
- ✅ Auto-routing URLs to correct nodes
- ✅ Federated architecture with isolated data
- ✅ SIMP protocol for inter-node communication
- ✅ Scheduling capability (can schedule daily scrapes)

**What needs enhancement**:
- 🔨 Detailed data extraction (bespoke scrapers)
- 🔨 PDF parsing for guidance documents
- 🔨 Link following for supplementary pages
- 🔨 LLM-assisted extraction fallback

Would you like me to:
1. **Implement the IUK scraper first** (since you have 30 IUK URLs to test with)
2. **Create a hybrid LLM+scraper approach** (more flexible)
3. **Build the scraper module structure** (all funding bodies)

Let me know what you'd like to tackle first!
