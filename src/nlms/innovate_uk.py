"""
Innovate UK NLM

Domain expert for Innovate UK grants:
- CR&D (Collaborative R&D)
- Innovation Vouchers
- Sector-specific competitions
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

from ..core.base_nlm import BaseNLM, NLMConfig
from ..core.simp import SIMPMessage, Intent

logger = logging.getLogger(__name__)


class InnovateUKNLM(BaseNLM):
    """
    Innovate UK domain expert

    Specializes in:
    - UK-based innovation grants
    - SME-focused funding
    - Technology readiness levels (TRL)
    - Sector-specific opportunities
    """

    def __init__(self, api_keys: Optional[Dict[str, str]] = None):
        config = NLMConfig(
            nlm_id="innovate_uk",
            name="Innovate UK Expert",
            domain="innovate_uk",
            silo="UK",
            can_search=True,
            can_scrape=True,
            can_analyze=True
        )
        super().__init__(config)

        # IUK-specific knowledge
        self.base_urls = [
            "https://apply-for-innovation-funding.service.gov.uk/competition/search"
        ]

        self.sectors = [
            "Advanced Manufacturing",
            "Aerospace",
            "Agriculture",
            "AI & Data",
            "Clean Energy",
            "Creative Industries",
            "Digital",
            "Electronics",
            "Health & Life Sciences",
            "Transport"
        ]

        self.grant_types = [
            "Smart Grant",
            "CR&D",
            "Innovation Voucher",
            "Knowledge Transfer Partnership",
            "SBRI"
        ]

    async def generate_search_content(self, grant_data: Dict[str, Any]) -> str:
        """
        Generate rich search content for IUK grants

        Includes:
        - Title and description
        - Sectors
        - Grant type
        - Competition scope
        - Eligibility criteria
        """
        parts = [
            grant_data.get('title', ''),
            grant_data.get('description', ''),
            grant_data.get('scope', ''),
        ]

        # Add sectors
        sectors = grant_data.get('sectors', [])
        if sectors:
            parts.append(' '.join(sectors))

        # Add grant type
        grant_type = grant_data.get('grant_type', '')
        if grant_type:
            parts.append(grant_type)

        # Add eligibility keywords
        eligibility = grant_data.get('eligibility', {})
        if eligibility:
            if isinstance(eligibility, dict):
                parts.append(' '.join(str(v) for v in eligibility.values() if v))
            else:
                parts.append(str(eligibility))

        return ' '.join(parts)

    async def on_initialize(self):
        """Custom initialization for IUK NLM"""
        logger.info(f"[{self.nlm_id}] Loading IUK-specific configurations...")

        # Could load IUK-specific embeddings or models here
        # For now, we'll use the base embedder

        logger.info(f"[{self.nlm_id}] Monitoring {len(self.base_urls)} sources")
        logger.info(f"[{self.nlm_id}] Tracking {len(self.sectors)} sectors")

    async def handle_analyze(self, message: SIMPMessage) -> SIMPMessage:
        """
        Analyze eligibility for IUK grants

        Checks:
        - Company size (SME status)
        - UK registration
        - Sector alignment
        - TRL level
        """
        context = message.context
        company_info = context.get("company_info", {})

        eligibility_checks = {
            "is_uk_registered": self._check_uk_registration(company_info),
            "is_sme": self._check_sme_status(company_info),
            "suitable_sectors": self._match_sectors(context.get("sectors", [])),
            "funding_range": self._suggest_funding_range(company_info)
        }

        return message.create_response(
            context={
                "nlm_id": self.nlm_id,
                "eligibility": eligibility_checks,
                "recommendation": self._generate_recommendation(eligibility_checks)
            },
            intent=Intent.ANALYZE
        )

    def _check_uk_registration(self, company_info: Dict) -> bool:
        """Check if company is UK-registered"""
        location = company_info.get("location", "").upper()
        return "UK" in location or "UNITED KINGDOM" in location

    def _check_sme_status(self, company_info: Dict) -> bool:
        """Check SME status (EU definition)"""
        employees = company_info.get("employees", 0)
        revenue = company_info.get("annual_revenue", 0)

        # EU SME definition: <250 employees, <€50M revenue
        return employees < 250 or revenue < 50000000

    def _match_sectors(self, company_sectors: List[str]) -> List[str]:
        """Match company sectors to IUK sectors"""
        matched = []
        for sector in company_sectors:
            sector_lower = sector.lower()
            for iuk_sector in self.sectors:
                if sector_lower in iuk_sector.lower() or iuk_sector.lower() in sector_lower:
                    matched.append(iuk_sector)
        return matched

    def _suggest_funding_range(self, company_info: Dict) -> Dict[str, int]:
        """Suggest appropriate funding range"""
        employees = company_info.get("employees", 0)

        if employees < 10:
            # Micro company
            return {
                "min": 25000,
                "max": 250000,
                "suggested_type": "Smart Grant or Innovation Voucher"
            }
        elif employees < 50:
            # Small company
            return {
                "min": 100000,
                "max": 500000,
                "suggested_type": "Smart Grant"
            }
        else:
            # Medium company
            return {
                "min": 250000,
                "max": 2000000,
                "suggested_type": "Smart Grant or CR&D"
            }

    def _generate_recommendation(self, checks: Dict) -> str:
        """Generate human-readable recommendation"""
        if not checks["is_uk_registered"]:
            return "Not eligible - must be UK-registered"

        if not checks["is_sme"]:
            return "Limited options - most IUK grants target SMEs"

        if checks["suitable_sectors"]:
            return f"Good fit! Suitable sectors: {', '.join(checks['suitable_sectors'])}"

        return "Eligible - explore cross-sector opportunities"

    # Register the analyze handler
    def _register_default_handlers(self):
        """Override to add custom handlers"""
        super()._register_default_handlers()
        self.register_handler(Intent.ANALYZE, self.handle_analyze)


if __name__ == "__main__":
    import asyncio

    async def test():
        nlm = InnovateUKNLM()
        await nlm.initialize()

        # Test grant indexing
        grant_id = await nlm.index_grant({
            "grant_id": "IUK_SMART_2025_001",
            "title": "Smart Grant: AI Innovation",
            "description": "Funding for AI-driven products and services",
            "grant_type": "Smart Grant",
            "amount_min": 25000,
            "amount_max": 2000000,
            "currency": "GBP",
            "sectors": ["AI & Data", "Digital"],
            "eligibility": {
                "company_type": "Limited Company",
                "location": "UK",
                "max_employees": 250
            },
            "deadline": "2025-12-31"
        })

        print(f"Indexed: {grant_id}")

        # Test search
        results = await nlm.search("AI innovation grants")
        print(f"Search results: {len(results)}")

        # Test eligibility analysis
        from ..core.simp import SIMPMessage, MessageType
        msg = SIMPMessage(
            msg_type=MessageType.QUERY,
            sender="test",
            receiver="innovate_uk",
            intent=Intent.ANALYZE,
            context={
                "company_info": {
                    "location": "UK",
                    "employees": 15,
                    "annual_revenue": 1000000
                },
                "sectors": ["Artificial Intelligence"]
            }
        )

        response = await nlm.handle_analyze(msg)
        print(f"Eligibility: {response.context}")

        await nlm.shutdown()

    asyncio.run(test())
