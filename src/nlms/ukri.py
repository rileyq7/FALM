"""
UKRI NLM

Domain expert for UK Research and Innovation:
- Research councils (EPSRC, ESRC, NERC, etc.)
- Innovation funding
- International partnerships
"""

from typing import Dict, List, Optional, Any
import logging

from ..core.base_nlm import BaseNLM, NLMConfig

logger = logging.getLogger(__name__)


class UKRINLM(BaseNLM):
    """UKRI domain expert"""

    def __init__(self, api_keys: Optional[Dict[str, str]] = None):
        config = NLMConfig(
            nlm_id="ukri",
            name="UKRI Expert",
            domain="ukri",
            silo="UK",
            can_search=True,
            can_scrape=True,
            can_analyze=True
        )
        super().__init__(config)

        self.base_urls = [
            "https://www.ukri.org/opportunity/"
        ]

        self.councils = [
            "EPSRC",  # Engineering and Physical Sciences
            "ESRC",   # Economic and Social Research
            "MRC",    # Medical Research
            "NERC",   # Natural Environment Research
            "STFC",   # Science and Technology Facilities
            "AHRC",   # Arts and Humanities Research
            "BBSRC"   # Biotechnology and Biological Sciences
        ]

    async def generate_search_content(self, grant_data: Dict[str, Any]) -> str:
        """Generate search content for UKRI grants"""
        parts = [
            grant_data.get('title', ''),
            grant_data.get('description', ''),
        ]

        council = grant_data.get('council', '')
        if council:
            parts.append(council)

        return ' '.join(parts)

    async def on_initialize(self):
        """Custom initialization"""
        logger.info(f"[{self.nlm_id}] Covering {len(self.councils)} research councils")
