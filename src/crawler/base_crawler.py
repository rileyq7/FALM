"""
Base Crawler for Grant Discovery

Crawls grant websites and extracts structured data
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
import asyncio
from pathlib import Path

import aiohttp
from bs4 import BeautifulSoup
import PyPDF2
from io import BytesIO

logger = logging.getLogger(__name__)


class BaseCrawler:
    """Base crawler class with common functionality"""

    def __init__(self, crawler_id: str, name: str):
        self.crawler_id = crawler_id
        self.name = name
        self.session: Optional[aiohttp.ClientSession] = None

        # Config
        self.timeout = 30
        self.max_depth = 2
        self.user_agent = f"FALM-Crawler/{crawler_id}"

        # Stats
        self.stats = {
            "pages_crawled": 0,
            "grants_found": 0,
            "errors": 0
        }

    async def initialize(self):
        """Initialize crawler session"""
        self.session = aiohttp.ClientSession(
            headers={"User-Agent": self.user_agent}
        )
        logger.info(f"[{self.crawler_id}] Crawler initialized")

    async def crawl_url(self, url: str) -> Dict[str, Any]:
        """Crawl a single URL"""
        try:
            async with self.session.get(url, timeout=self.timeout) as response:
                html = await response.text()
                self.stats["pages_crawled"] += 1

                # Parse HTML
                soup = BeautifulSoup(html, 'html.parser')

                # Extract grant data (override in subclasses)
                grant_data = await self.parse_grant_page(soup, url)

                return grant_data

        except Exception as e:
            logger.error(f"[{self.crawler_id}] Error crawling {url}: {e}")
            self.stats["errors"] += 1
            return {}

    async def parse_grant_page(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """Parse grant data from HTML - override in subclasses"""
        raise NotImplementedError

    async def shutdown(self):
        """Shutdown crawler"""
        if self.session:
            await self.session.close()
        logger.info(f"[{self.crawler_id}] Crawler shutdown")
