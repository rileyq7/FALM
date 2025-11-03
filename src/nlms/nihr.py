"""
NIHR NLM

Domain expert for National Institute for Health Research:
- Research grants
- Fellowships
- Programme grants
- Clinical trials funding
"""

from typing import Dict, List, Optional, Any
import logging

from ..core.base_nlm import BaseNLM, NLMConfig
from ..core.simp import SIMPMessage, Intent

logger = logging.getLogger(__name__)


class NIHRNLM(BaseNLM):
    """NIHR domain expert for health research funding"""

    def __init__(self, api_keys: Optional[Dict[str, str]] = None):
        config = NLMConfig(
            nlm_id="nihr",
            name="NIHR Expert",
            domain="nihr",
            silo="UK",
            can_search=True,
            can_scrape=True,
            can_analyze=True
        )
        super().__init__(config)

        self.base_urls = [
            "https://www.nihr.ac.uk/explore-nihr/funding-programmes/"
        ]

        self.funding_streams = [
            "Research for Patient Benefit",
            "Health Technology Assessment",
            "Programme Grants for Applied Research",
            "Efficacy and Mechanism Evaluation",
            "Health Services and Delivery Research",
            "Public Health Research",
            "Advanced Fellowships",
            "Career Development Fellowships"
        ]

    async def generate_search_content(self, grant_data: Dict[str, Any]) -> str:
        """Generate search content for NIHR grants"""
        parts = [
            grant_data.get('title', ''),
            grant_data.get('description', ''),
            grant_data.get('research_area', ''),
        ]

        stream = grant_data.get('funding_stream', '')
        if stream:
            parts.append(stream)

        return ' '.join(parts)

    async def on_initialize(self):
        """Custom initialization"""
        logger.info(f"[{self.nlm_id}] Tracking {len(self.funding_streams)} funding streams")


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
