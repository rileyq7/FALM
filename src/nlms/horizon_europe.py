"""
Horizon Europe NLM

Domain expert for EU Horizon Europe program:
- EIC Accelerator
- EIC Pathfinder
- Horizon collaborations
- Marie Skłodowska-Curie Actions
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

from ..core.base_nlm import BaseNLM, NLMConfig
from ..core.simp import SIMPMessage, Intent

logger = logging.getLogger(__name__)


class HorizonEuropeNLM(BaseNLM):
    """
    Horizon Europe domain expert

    Specializes in:
    - EU framework funding
    - International collaborations
    - Research & Innovation
    - EIC support
    """

    def __init__(self, api_keys: Optional[Dict[str, str]] = None):
        config = NLMConfig(
            nlm_id="horizon_europe",
            name="Horizon Europe Expert",
            domain="horizon_europe",
            silo="EU",
            can_search=True,
            can_scrape=True,
            can_analyze=True
        )
        super().__init__(config)

        self.base_urls = [
            "https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/home",
            "https://eic.ec.europa.eu/eic-funding-opportunities/calls-proposals_en"
        ]

        self.programs = [
            "EIC Accelerator",
            "EIC Pathfinder",
            "EIC Transition",
            "Horizon Collaborations",
            "Marie Skłodowska-Curie Actions",
            "European Research Council"
        ]

        self.eligible_countries = [
            "Austria", "Belgium", "Bulgaria", "Croatia", "Cyprus",
            "Czech Republic", "Denmark", "Estonia", "Finland", "France",
            "Germany", "Greece", "Hungary", "Ireland", "Italy", "Latvia",
            "Lithuania", "Luxembourg", "Malta", "Netherlands", "Poland",
            "Portugal", "Romania", "Slovakia", "Slovenia", "Spain",
            "Sweden", "United Kingdom"  # Associated country
        ]

    async def generate_search_content(self, grant_data: Dict[str, Any]) -> str:
        """Generate search content for Horizon grants"""
        parts = [
            grant_data.get('title', ''),
            grant_data.get('description', ''),
            grant_data.get('scope', ''),
            grant_data.get('expected_impact', ''),
        ]

        # Add program type
        program = grant_data.get('program', '')
        if program:
            parts.append(program)

        # Add topics
        topics = grant_data.get('topics', [])
        if topics:
            parts.append(' '.join(topics))

        # Add TRL range
        trl_min = grant_data.get('trl_min', '')
        trl_max = grant_data.get('trl_max', '')
        if trl_min or trl_max:
            parts.append(f"TRL {trl_min}-{trl_max}")

        return ' '.join(parts)

    async def on_initialize(self):
        """Custom initialization for Horizon NLM"""
        logger.info(f"[{self.nlm_id}] Loading Horizon Europe configurations...")
        logger.info(f"[{self.nlm_id}] Covering {len(self.eligible_countries)} countries")
        logger.info(f"[{self.nlm_id}] Tracking {len(self.programs)} programs")

    async def handle_analyze(self, message: SIMPMessage) -> SIMPMessage:
        """
        Analyze eligibility for Horizon Europe

        Checks:
        - Country eligibility
        - Organization type
        - TRL level
        - Consortium requirements
        """
        context = message.context
        org_info = context.get("organization_info", {})

        eligibility_checks = {
            "country_eligible": self._check_country_eligibility(org_info),
            "org_type_suitable": self._check_org_type(org_info),
            "trl_match": self._match_trl(org_info.get("trl", 0)),
            "consortium_guidance": self._get_consortium_guidance(org_info)
        }

        return message.create_response(
            context={
                "nlm_id": self.nlm_id,
                "eligibility": eligibility_checks,
                "recommendation": self._generate_recommendation(eligibility_checks)
            },
            intent=Intent.ANALYZE
        )

    def _check_country_eligibility(self, org_info: Dict) -> Dict[str, Any]:
        """Check country eligibility"""
        country = org_info.get("country", "")

        is_eligible = country in self.eligible_countries

        return {
            "eligible": is_eligible,
            "country": country,
            "status": "Eligible" if is_eligible else "Check associated country status"
        }

    def _check_org_type(self, org_info: Dict) -> Dict[str, Any]:
        """Check organization type suitability"""
        org_type = org_info.get("type", "").lower()

        suitable_types = {
            "sme": "EIC Accelerator, EIC Pathfinder",
            "startup": "EIC Accelerator",
            "university": "All programs",
            "research": "EIC Pathfinder, ERC, MSCA",
            "large enterprise": "Horizon Collaborations"
        }

        matching = []
        for type_key, programs in suitable_types.items():
            if type_key in org_type:
                matching.append(programs)

        return {
            "organization_type": org_type,
            "suitable_programs": matching[0] if matching else "Horizon Collaborations"
        }

    def _match_trl(self, trl: int) -> Dict[str, Any]:
        """Match TRL to appropriate programs"""
        if trl <= 4:
            return {
                "trl": trl,
                "stage": "Early stage",
                "recommended": ["EIC Pathfinder", "ERC"]
            }
        elif trl <= 6:
            return {
                "trl": trl,
                "stage": "Mid stage",
                "recommended": ["EIC Transition", "Horizon Collaborations"]
            }
        else:
            return {
                "trl": trl,
                "stage": "Market-ready",
                "recommended": ["EIC Accelerator"]
            }

    def _get_consortium_guidance(self, org_info: Dict) -> str:
        """Provide consortium guidance"""
        org_type = org_info.get("type", "").lower()

        if "sme" in org_type or "startup" in org_type:
            return "EIC Accelerator: Solo applications accepted. Collaborations optional."

        return "Most Horizon programs require multi-partner consortia (3+ countries)"

    def _generate_recommendation(self, checks: Dict) -> str:
        """Generate recommendation"""
        if not checks["country_eligible"]["eligible"]:
            return "Check associated country status - may still be eligible"

        trl_info = checks["trl_match"]
        programs = trl_info.get("recommended", [])

        return f"Suitable for: {', '.join(programs)} (TRL {trl_info['trl']})"

    def _register_default_handlers(self):
        """Add custom handlers"""
        super()._register_default_handlers()
        self.register_handler(Intent.ANALYZE, self.handle_analyze)


if __name__ == "__main__":
    import asyncio

    async def test():
        nlm = HorizonEuropeNLM()
        await nlm.initialize()

        # Test grant indexing
        grant_id = await nlm.index_grant({
            "grant_id": "HORIZON_EIC_2025_001",
            "title": "EIC Accelerator 2025",
            "description": "Support for high-risk, high-impact innovations",
            "program": "EIC Accelerator",
            "amount_min": 500000,
            "amount_max": 2500000,
            "currency": "EUR",
            "topics": ["AI", "Quantum", "Biotech"],
            "trl_min": 5,
            "trl_max": 8,
            "deadline": "2025-06-30"
        })

        print(f"Indexed: {grant_id}")

        # Test search
        results = await nlm.search("EIC Accelerator AI")
        print(f"Search results: {len(results)}")

        await nlm.shutdown()

    asyncio.run(test())
