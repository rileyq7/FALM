#!/usr/bin/env python3
"""
Comprehensive Innovate UK Grant Scraper

Scrapes all sections of IUK competition pages:
- Summary/Overview
- Eligibility
- Scope
- Dates
- How to Apply
- Supporting Information (including document links)
"""

import asyncio
import sys
import json
import aiohttp
from pathlib import Path
from bs4 import BeautifulSoup
from datetime import datetime
from typing import Dict, List, Optional
import re

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class IUKGrantScraper:
    """Scrapes comprehensive grant data from Innovate UK competition pages"""

    def __init__(self):
        self.base_url = "https://apply-for-innovation-funding.service.gov.uk"
        self.sections = [
            "summary",  # Default overview
            "eligibility",
            "scope",
            "dates",
            "how-to-apply",
            "supporting-information"
        ]

    async def scrape_competition(self, session: aiohttp.ClientSession, url: str) -> Dict:
        """Scrape all sections of a competition page"""

        # Extract competition ID from URL
        match = re.search(r'/competition/(\d+)/', url)
        if not match:
            print(f"  ❌ Could not extract competition ID from {url}")
            return None

        competition_id = match.group(1)
        print(f"\n📋 Scraping Competition {competition_id}...")

        grant_data = {
            "competition_id": competition_id,
            "source_url": url,
            "funding_body": "Innovate UK",
            "currency": "GBP",
            "silo": "UK",
            "scraped_at": datetime.utcnow().isoformat(),
            "sections": {}
        }

        # Extract competition title from the main page
        try:
            async with session.get(url, timeout=30) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')

                    # Try to get title from h1 tag first
                    h1_tag = soup.find('h1')
                    if h1_tag:
                        title_text = h1_tag.get_text(separator=' ', strip=True)
                        # Remove "Funding competition" prefix if present
                        title_text = re.sub(r'^Funding\s*competition\s*', '', title_text, flags=re.IGNORECASE).strip()
                        grant_data["page_title"] = title_text
                    else:
                        # Fallback to HTML title tag
                        title_tag = soup.find('title')
                        if title_tag:
                            title_text = title_tag.get_text(strip=True).split('|')[0].strip()
                            # Remove "Funding competition" prefix if present
                            title_text = re.sub(r'^Funding\s*competition\s*', '', title_text, flags=re.IGNORECASE).strip()
                            grant_data["page_title"] = title_text
        except Exception as e:
            print(f"  ⚠️  Could not extract page title: {str(e)[:50]}")

        # Scrape each section
        for section in self.sections:
            section_data = await self._scrape_section(session, url, section)
            if section_data:
                grant_data["sections"][section] = section_data
                print(f"  ✓ {section}")

        # Extract structured data from sections
        structured_data = self._extract_structured_data(grant_data["sections"])

        # Override title with page_title if available
        if grant_data.get("page_title"):
            structured_data["title"] = grant_data["page_title"]

        grant_data.update(structured_data)

        return grant_data

    async def _scrape_section(self, session: aiohttp.ClientSession,
                              base_url: str, section: str) -> Optional[Dict]:
        """Scrape a specific section of the competition page"""

        # Build section URL (for non-summary sections, add hash)
        if section == "summary":
            section_url = base_url
        else:
            section_url = f"{base_url}#{section}"

        try:
            async with session.get(base_url, timeout=30) as response:
                if response.status != 200:
                    print(f"    ⚠️  HTTP {response.status} for {section}")
                    return None

                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')

                # Find the section content
                # IUK uses section tags or divs with specific IDs
                section_content = None

                if section == "summary":
                    # Summary is usually in the main content area
                    section_content = soup.find('section', {'id': 'summary'}) or \
                                    soup.find('div', {'class': 'competition-summary'})
                else:
                    # Other sections have IDs matching their name
                    section_content = soup.find('section', {'id': section}) or \
                                    soup.find('div', {'id': section})

                if not section_content:
                    # Try to find any section containing this text
                    all_sections = soup.find_all(['section', 'div'])
                    for s in all_sections:
                        if section.replace('-', ' ').lower() in (s.get_text().lower()[:200]):
                            section_content = s
                            break

                if section_content:
                    data = self._parse_section_content(section, section_content)

                    # For supporting-information, extract document links
                    if section == "supporting-information":
                        data["documents"] = self._extract_document_links(section_content)

                    return data
                else:
                    return {"text": "Section not found", "html": ""}

        except asyncio.TimeoutError:
            print(f"    ⚠️  Timeout for {section}")
            return None
        except Exception as e:
            print(f"    ⚠️  Error scraping {section}: {str(e)[:100]}")
            return None

    def _parse_section_content(self, section_name: str, content) -> Dict:
        """Parse section content into structured data"""

        # Extract all text
        text = content.get_text(separator='\n', strip=True)

        # Extract headings
        headings = []
        for heading in content.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            headings.append({
                "level": heading.name,
                "text": heading.get_text(strip=True)
            })

        # Extract lists (often contain key info)
        lists = []
        for ul in content.find_all(['ul', 'ol']):
            items = [li.get_text(strip=True) for li in ul.find_all('li')]
            if items:
                lists.append(items)

        # Extract tables (may contain dates, amounts, etc.)
        tables = []
        for table in content.find_all('table'):
            table_data = []
            for row in table.find_all('tr'):
                cells = [cell.get_text(strip=True) for cell in row.find_all(['td', 'th'])]
                if cells:
                    table_data.append(cells)
            if table_data:
                tables.append(table_data)

        # Extract paragraphs
        paragraphs = []
        for p in content.find_all('p'):
            p_text = p.get_text(strip=True)
            if p_text:
                paragraphs.append(p_text)

        return {
            "text": text,
            "headings": headings,
            "lists": lists,
            "tables": tables,
            "paragraphs": paragraphs
        }

    def _extract_document_links(self, content) -> List[Dict]:
        """Extract all document/resource links from content"""

        documents = []
        for link in content.find_all('a', href=True):
            href = link['href']
            text = link.get_text(strip=True)

            # Check if it's a document link (PDF, DOC, etc.)
            if any(ext in href.lower() for ext in ['.pdf', '.doc', '.docx', '.xls', '.xlsx']):
                documents.append({
                    "title": text,
                    "url": href if href.startswith('http') else f"{self.base_url}{href}",
                    "type": href.split('.')[-1].upper()
                })
            # Also include links to guidance pages
            elif 'guidance' in href.lower() or 'support' in href.lower():
                documents.append({
                    "title": text,
                    "url": href if href.startswith('http') else f"{self.base_url}{href}",
                    "type": "LINK"
                })

        return documents

    def _extract_structured_data(self, sections: Dict) -> Dict:
        """Extract structured fields from section content"""

        structured = {
            "title": "",
            "description": "",
            "eligibility_criteria": [],
            "scope": "",
            "funding_details": {},
            "deadlines": {},
            "application_process": "",
            "supporting_documents": []
        }

        # Extract title (usually in summary headings)
        if "summary" in sections and sections["summary"].get("headings"):
            structured["title"] = sections["summary"]["headings"][0].get("text", "")

        # Extract description (summary paragraphs)
        if "summary" in sections and sections["summary"].get("paragraphs"):
            structured["description"] = "\n\n".join(sections["summary"]["paragraphs"])

        # Extract eligibility criteria
        if "eligibility" in sections:
            if sections["eligibility"].get("lists"):
                structured["eligibility_criteria"] = [
                    item for sublist in sections["eligibility"]["lists"]
                    for item in sublist
                ]
            else:
                structured["eligibility_criteria"] = sections["eligibility"].get("paragraphs", [])

        # Extract scope
        if "scope" in sections:
            structured["scope"] = sections["scope"].get("text", "")

        # Extract dates
        if "dates" in sections:
            dates_text = sections["dates"].get("text", "")
            # Try to parse dates from text/tables
            structured["deadlines"] = self._parse_dates(sections["dates"])

        # Extract funding details
        structured["funding_details"] = self._parse_funding_details(sections)

        # Extract application process
        if "how-to-apply" in sections:
            structured["application_process"] = sections["how-to-apply"].get("text", "")

        # Extract supporting documents
        if "supporting-information" in sections:
            structured["supporting_documents"] = sections["supporting-information"].get("documents", [])

        return structured

    def _parse_dates(self, dates_section: Dict) -> Dict:
        """Parse dates from dates section"""

        dates = {}

        # Look in tables first
        if dates_section.get("tables"):
            for table in dates_section["tables"]:
                for row in table:
                    if len(row) >= 2:
                        key = row[0].lower().replace(' ', '_')
                        value = row[1]
                        dates[key] = value

        # Look in text for common patterns
        text = dates_section.get("text", "")

        patterns = {
            "competition_opens": r"opens[:\s]+([0-9]{1,2}\s+\w+\s+\d{4})",
            "deadline": r"deadline[:\s]+([0-9]{1,2}\s+\w+\s+\d{4})",
            "competition_closes": r"closes[:\s]+([0-9]{1,2}\s+\w+\s+\d{4})",
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                dates[key] = match.group(1)

        return dates

    def _parse_funding_details(self, sections: Dict) -> Dict:
        """Parse funding amounts and details"""

        funding = {}

        # Search all sections for funding info
        all_text = ""
        for section_data in sections.values():
            if isinstance(section_data, dict):
                all_text += " " + section_data.get("text", "")

        # Look for funding amounts
        amount_patterns = [
            r"£([\d,]+)\s*(?:to|[-–])\s*£([\d,]+)",  # Range
            r"up to £([\d,]+)",  # Max only
            r"funding of £([\d,]+)",  # Specific amount
        ]

        for pattern in amount_patterns:
            match = re.search(pattern, all_text, re.IGNORECASE)
            if match:
                if len(match.groups()) == 2:
                    funding["amount_min"] = int(match.group(1).replace(',', ''))
                    funding["amount_max"] = int(match.group(2).replace(',', ''))
                else:
                    funding["amount_max"] = int(match.group(1).replace(',', ''))
                break

        # Look for funding rate/percentage
        rate_match = re.search(r'(\d+)%\s*(?:of|funding)', all_text)
        if rate_match:
            funding["funding_rate"] = f"{rate_match.group(1)}%"

        # Look for match funding requirement
        if any(term in all_text.lower() for term in ['match funding', 'co-funding', 'matched funding']):
            funding["match_funding_required"] = True

        return funding


async def scrape_all_grants(urls: List[str], output_file: str):
    """Scrape all grants and save to JSON"""

    print("=" * 80)
    print("Innovate UK Comprehensive Grant Scraper")
    print("=" * 80)
    print(f"\nScraping {len(urls)} competition URLs...")
    print()

    scraper = IUKGrantScraper()
    grants = []

    # Create aiohttp session
    async with aiohttp.ClientSession() as session:
        for i, url in enumerate(urls, 1):
            print(f"[{i}/{len(urls)}] {url}")

            grant_data = await scraper.scrape_competition(session, url)
            if grant_data:
                grants.append(grant_data)
                print(f"  ✅ Scraped successfully")
            else:
                print(f"  ❌ Failed to scrape")

            # Be polite - small delay between requests
            await asyncio.sleep(1)

    # Save to JSON
    output_path = Path(output_file)
    output_data = {
        "funding_body": "IUK",
        "node": "UK_IUK",
        "total_grants": len(grants),
        "scraped_at": datetime.utcnow().isoformat(),
        "grants": grants
    }

    with open(output_path, 'w') as f:
        json.dump(output_data, f, indent=2)

    print()
    print("=" * 80)
    print(f"✅ Scraping Complete!")
    print(f"   Total grants: {len(grants)}")
    print(f"   Output file: {output_file}")
    print("=" * 80)


async def main():
    """Main function"""

    # Load URLs from file
    urls_file = Path(__file__).parent.parent / "data" / "my_grant_urls.txt"

    if not urls_file.exists():
        print(f"❌ URLs file not found: {urls_file}")
        sys.exit(1)

    with open(urls_file) as f:
        urls = [line.strip() for line in f if line.strip() and line.startswith('http')]

    # Filter only IUK URLs
    iuk_urls = [url for url in urls if 'apply-for-innovation-funding.service.gov.uk' in url]

    print(f"Found {len(iuk_urls)} Innovate UK competition URLs")

    if not iuk_urls:
        print("❌ No IUK URLs found")
        sys.exit(1)

    # Scrape and save
    output_file = "data/iuk_grants_full_enriched.json"
    await scrape_all_grants(iuk_urls, output_file)


if __name__ == "__main__":
    asyncio.run(main())
