"""
Innovate UK (IUK) Bespoke Scraper

Specialized scraper for Innovate UK competition pages.
Handles:
- Competition overview pages
- Funding details extraction
- Deadline parsing
- Eligibility criteria
- PDF guidance documents
- Sector tagging
"""

import re
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from urllib.parse import urljoin, urlparse
import aiohttp
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class IUKScraper:
    """Innovate UK specialized scraper"""

    BASE_URL = "https://apply-for-innovation-funding.service.gov.uk"

    def __init__(self):
        self.timeout = aiohttp.ClientTimeout(total=30)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }

    async def scrape_competition(self, url: str) -> Dict[str, Any]:
        """
        Scrape IUK competition page

        Args:
            url: Competition URL

        Returns:
            Dict with grant data
        """
        logger.info(f"[IUK Scraper] Fetching: {url}")

        try:
            html = await self._fetch_html(url)
            soup = BeautifulSoup(html, 'html.parser')

            # Check if we got blocked by auth
            if self._is_auth_required(soup):
                logger.warning(f"[IUK Scraper] Auth required for: {url}")
                # Return partial data with what we can extract from URL
                return self._create_basic_grant_data(url)

            # Extract full data
            comp_id = self._extract_competition_id(url)
            grant_data = {
                "grant_id": f"IUK_{comp_id}" if comp_id else f"IUK_{hash(url)}",
                "title": self._extract_title(soup),
                "provider": "Innovate UK",
                "funding_body": "IUK",
                "silo": "UK",
                "description": self._extract_description(soup),
                "amount_min": self._extract_funding_min(soup) or 0.0,
                "amount_max": self._extract_funding_max(soup) or 0.0,
                "currency": "GBP",
                "deadline": self._extract_deadline(soup) or "Not specified",
                "sectors": self._extract_sectors(soup),
                "eligibility": self._extract_eligibility(soup),
                "application_url": url,
                "supplementary_urls": await self._extract_links(soup, url),
                "pdf_documents": self._extract_pdfs(soup, url),
                "metadata": {
                    "competition_id": comp_id or "unknown",
                    "match_funding_required": self._check_match_funding(soup),
                    "collaboration_required": self._check_collaboration(soup),
                    "scraped_at": datetime.now().isoformat(),
                    "source_url": url
                }
            }

            logger.info(f"[IUK Scraper] Extracted: {grant_data.get('title', 'N/A')}")
            return grant_data

        except Exception as e:
            logger.error(f"[IUK Scraper] Error scraping {url}: {e}")
            return self._create_basic_grant_data(url, error=str(e))

    async def _fetch_html(self, url: str) -> str:
        """Fetch HTML content from URL"""
        async with aiohttp.ClientSession(timeout=self.timeout, headers=self.headers) as session:
            async with session.get(url) as response:
                response.raise_for_status()
                return await response.text()

    def _is_auth_required(self, soup: BeautifulSoup) -> bool:
        """Check if page requires authentication"""
        # Look for permission denied or forbidden messages
        title = soup.find('title')
        if title and ('permission' in title.text.lower() or 'forbidden' in title.text.lower()):
            return True

        # Check for body class indicating error
        body = soup.find('body')
        if body and body.get('class'):
            classes = ' '.join(body.get('class', []))
            if 'forbidden' in classes or 'error' in classes:
                return True

        return False

    def _create_basic_grant_data(self, url: str, error: Optional[str] = None) -> Dict[str, Any]:
        """Create basic grant data when full scraping fails"""
        comp_id = self._extract_competition_id(url)

        # Build metadata without None values
        metadata = {
            "competition_id": comp_id or "unknown",
            "match_funding_required": True,  # IUK default
            "collaboration_required": False,
            "scraped_at": datetime.now().isoformat(),
            "source_url": url,
            "scraping_status": "partial"
        }

        # Only add error if it exists
        if error:
            metadata["error"] = error

        return {
            "grant_id": f"IUK_{comp_id}" if comp_id else f"IUK_{hash(url)}",
            "title": f"Innovate UK Competition {comp_id}" if comp_id else "Innovate UK Grant",
            "provider": "Innovate UK",
            "funding_body": "IUK",
            "silo": "UK",
            "description": "Full details require authentication. Visit the competition page for complete information.",
            "amount_min": 0.0,
            "amount_max": 0.0,
            "currency": "GBP",
            "deadline": "Not specified",
            "sectors": [],
            "eligibility": {
                "uk_registered": True,
                "details": "See competition page for full eligibility criteria"
            },
            "application_url": url,
            "supplementary_urls": [],
            "pdf_documents": [],
            "metadata": metadata
        }

    def _extract_competition_id(self, url: str) -> Optional[str]:
        """Extract competition ID from URL"""
        match = re.search(r'/competition/(\d+)', url)
        return match.group(1) if match else None

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract competition title"""
        # Try multiple selectors
        selectors = [
            'h1.govuk-heading-xl',
            'h1.govuk-heading-l',
            'h2.govuk-heading-m',
            '.competition-title h1',
            'h1'
        ]

        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                title = elem.get_text(strip=True)
                # Filter out common non-title text
                if title and 'Innovation' not in title and 'Cookie' not in title and len(title) > 10:
                    return title

        return "Innovate UK Grant"

    def _extract_description(self, soup: BeautifulSoup) -> str:
        """Extract competition description/summary"""
        # Look for description or summary
        selectors = [
            '.wysiwyg-styles',
            '.competition-summary',
            '.govuk-body-l',
            'p.govuk-body'
        ]

        descriptions = []
        for selector in selectors:
            elems = soup.select(selector)
            for elem in elems[:3]:  # Take first 3 paragraphs
                text = elem.get_text(strip=True)
                if text and len(text) > 50:  # Meaningful text only
                    descriptions.append(text)

        return ' '.join(descriptions) if descriptions else "Competition details not available."

    def _extract_funding_min(self, soup: BeautifulSoup) -> Optional[float]:
        """Extract minimum funding amount"""
        return self._parse_funding_amount(soup, pattern=r'from\s*£([\d,]+)')

    def _extract_funding_max(self, soup: BeautifulSoup) -> Optional[float]:
        """Extract maximum funding amount"""
        return self._parse_funding_amount(soup, pattern=r'up\s*to\s*£([\d,]+)')

    def _parse_funding_amount(self, soup: BeautifulSoup, pattern: str) -> Optional[float]:
        """Parse funding amount from text"""
        text = soup.get_text()

        # Try specific pattern
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            amount_str = match.group(1).replace(',', '')
            try:
                return float(amount_str)
            except ValueError:
                pass

        # Try finding any £ amount
        matches = re.findall(r'£([\d,]+(?:\.\d{2})?)\s*(?:million|m)?', text, re.IGNORECASE)
        if matches:
            try:
                amount = float(matches[0].replace(',', ''))
                # Check if it's in millions
                if 'million' in text[text.find(matches[0]):text.find(matches[0])+50].lower():
                    amount *= 1_000_000
                return amount
            except ValueError:
                pass

        return None

    def _extract_deadline(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract application deadline"""
        # Look for deadline text
        deadline_patterns = [
            r'deadline[:\s]+(\d{1,2}\s+\w+\s+\d{4})',
            r'closes[:\s]+(\d{1,2}\s+\w+\s+\d{4})',
            r'(\d{1,2}\s+\w+\s+\d{4})\s+at\s+\d{1,2}:\d{2}'
        ]

        text = soup.get_text()
        for pattern in deadline_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)

        return None

    def _extract_sectors(self, soup: BeautifulSoup) -> List[str]:
        """Extract relevant sectors"""
        sectors = []

        # Look for sector tags or lists
        sector_elements = soup.select('.sector-tag, .tag, .govuk-tag')
        for elem in sector_elements:
            sector = elem.get_text(strip=True)
            if sector and len(sector) < 50:  # Reasonable sector name length
                sectors.append(sector)

        # Common IUK sectors from text analysis
        text = soup.get_text().lower()
        sector_keywords = {
            'healthcare': ['health', 'medical', 'clinical', 'pharmaceutical'],
            'manufacturing': ['manufactur', 'industrial', 'production'],
            'digital': ['digital', 'software', 'ai', 'data', 'cyber'],
            'energy': ['energy', 'renewable', 'solar', 'wind', 'nuclear'],
            'transport': ['transport', 'automotive', 'aerospace', 'rail'],
            'agriculture': ['agricult', 'food', 'farming', 'agritech'],
            'creative': ['creative', 'media', 'arts', 'entertainment'],
            'construction': ['construction', 'building', 'infrastructure']
        }

        for sector, keywords in sector_keywords.items():
            if any(kw in text for kw in keywords):
                if sector not in [s.lower() for s in sectors]:
                    sectors.append(sector.title())

        return sectors[:5]  # Limit to 5 most relevant

    def _extract_eligibility(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract eligibility criteria"""
        eligibility = {
            "uk_registered": True,  # IUK default
            "details": []
        }

        # Look for eligibility sections
        text = soup.get_text()

        # Common eligibility indicators
        if 'sme' in text.lower() or 'small' in text.lower():
            eligibility['sme_eligible'] = True
        if 'research' in text.lower() and 'organisation' in text.lower():
            eligibility['rto_eligible'] = True
        if 'university' in text.lower() or 'academic' in text.lower():
            eligibility['academic_eligible'] = True
        if 'collaboration' in text.lower() or 'consortium' in text.lower():
            eligibility['collaboration_required'] = True

        # Extract eligibility paragraphs
        eligibility_headers = soup.find_all(['h2', 'h3'], string=re.compile('eligibility', re.IGNORECASE))
        for header in eligibility_headers:
            next_elem = header.find_next_sibling()
            if next_elem:
                detail_text = next_elem.get_text(strip=True)
                if detail_text and len(detail_text) > 20:
                    eligibility['details'].append(detail_text)

        return eligibility

    async def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract supplementary links"""
        links = []

        # Find relevant internal links
        for link in soup.find_all('a', href=True):
            href = link['href']
            full_url = urljoin(base_url, href)

            # Filter for relevant pages (not navigation, not external)
            if (self.BASE_URL in full_url and
                'competition' in full_url and
                full_url != base_url and
                'sign' not in full_url.lower()):

                if full_url not in links:
                    links.append(full_url)

        return links[:10]  # Limit to 10 supplementary links

    def _extract_pdfs(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract PDF document links"""
        pdfs = []

        for link in soup.find_all('a', href=True):
            href = link['href']
            if href.lower().endswith('.pdf'):
                full_url = urljoin(base_url, href)
                pdfs.append(full_url)

        return pdfs

    def _check_match_funding(self, soup: BeautifulSoup) -> bool:
        """Check if match funding is required"""
        text = soup.get_text().lower()
        return 'match fund' in text or 'co-fund' in text

    def _check_collaboration(self, soup: BeautifulSoup) -> bool:
        """Check if collaboration is required"""
        text = soup.get_text().lower()
        return 'collaboration' in text or 'consortium' in text or 'partner' in text


# Convenience function for testing
async def test_scraper():
    """Test the IUK scraper"""
    scraper = IUKScraper()

    test_url = "https://apply-for-innovation-funding.service.gov.uk/competition/2313/overview"

    result = await scraper.scrape_competition(test_url)

    print("\n" + "="*60)
    print("IUK SCRAPER TEST RESULTS")
    print("="*60)
    print(f"Title: {result['title']}")
    print(f"Description: {result['description'][:100]}...")
    print(f"Funding: £{result['amount_min']} - £{result['amount_max']}")
    print(f"Deadline: {result['deadline']}")
    print(f"Sectors: {', '.join(result['sectors'])}")
    print(f"PDFs: {len(result['pdf_documents'])}")
    print(f"Supplementary URLs: {len(result['supplementary_urls'])}")
    print("="*60 + "\n")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_scraper())
