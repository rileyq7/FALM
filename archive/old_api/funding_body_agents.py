#!/usr/bin/env python3
"""
Funding Body Nano Agents
Each funding body gets its own specialized nano agent with custom logic
"""

import asyncio
from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class FundingBodyAgent(ABC):
    """Base class for funding body-specific nano agents"""

    def __init__(self, funding_body_code: str, funding_body_name: str, silo: str):
        self.funding_body_code = funding_body_code
        self.funding_body_name = funding_body_name
        self.silo = silo
        self.vector_db = None  # Each agent has its own vector DB collection
        self.grant_cache = {}

        logger.info(f"Initialized {funding_body_code} Agent ({funding_body_name})")

    @abstractmethod
    async def scrape_source(self, url: str) -> Dict[str, Any]:
        """Custom scraping logic for this funding body's website"""
        pass

    @abstractmethod
    async def parse_grant(self, raw_data: Dict) -> Dict[str, Any]:
        """Parse grant data in this funding body's specific format"""
        pass

    @abstractmethod
    async def validate_eligibility(self, grant_id: str, user_profile: Dict) -> Dict[str, Any]:
        """Funding body-specific eligibility checking"""
        pass

    async def search(self, query: str, filters: Dict = None) -> List[Dict]:
        """Search this funding body's grants"""
        logger.info(f"{self.funding_body_code} Agent searching: {query}")

        if not self.vector_db:
            logger.warning(f"{self.funding_body_code} vector DB not initialized")
            return []

        # Search only this agent's collection
        results = await self.vector_db.search(
            query=query,
            collection=f"{self.silo}_{self.funding_body_code}",
            filters=filters
        )

        return results

    async def get_grants(self, limit: int = 50) -> List[Dict]:
        """Get all grants from this funding body"""
        # Override in subclasses for specific logic
        return []

    def get_metadata(self) -> Dict[str, Any]:
        """Return agent metadata"""
        return {
            "funding_body_code": self.funding_body_code,
            "funding_body_name": self.funding_body_name,
            "silo": self.silo,
            "grants_cached": len(self.grant_cache),
            "status": "active"
        }


# ============================================================================
# UK AGENTS
# ============================================================================

class InnovateUKAgent(FundingBodyAgent):
    """Nano agent specialized for Innovate UK grants"""

    def __init__(self):
        super().__init__("IUK", "Innovate UK", "UK")
        self.base_urls = [
            "https://apply-for-innovation-funding.service.gov.uk",
        ]

    async def scrape_source(self, url: str) -> Dict[str, Any]:
        """Custom scraping for Innovate UK competition pages"""
        # Innovate UK-specific extraction logic
        logger.info(f"IUK Agent scraping: {url}")

        return {
            "funding_body": self.funding_body_code,
            "provider": self.funding_body_name,
            "silo": self.silo,
            # Custom IUK fields
            "competition_id": self._extract_competition_id(url),
            "funding_type": "Competition",
        }

    def _extract_competition_id(self, url: str) -> str:
        """Extract competition ID from IUK URL"""
        import re
        match = re.search(r'/competition/(\d+)/', url)
        return match.group(1) if match else "unknown"

    async def parse_grant(self, raw_data: Dict) -> Dict[str, Any]:
        """Parse IUK-specific grant format"""
        # Handle IUK's specific data structure
        return {
            **raw_data,
            "currency": "GBP",
            "eligibility": {
                "company_type": "UK Limited Company",
                "location": ["UK"],
                "match_funding_required": True
            }
        }

    async def validate_eligibility(self, grant_id: str, user_profile: Dict) -> Dict[str, Any]:
        """IUK-specific eligibility rules"""
        checks = []

        # IUK requires UK registered companies
        if user_profile.get("location") == "UK":
            checks.append({"requirement": "UK Location", "passed": True})
        else:
            checks.append({"requirement": "UK Location", "passed": False})

        # Check company type
        if "Limited Company" in user_profile.get("company_type", ""):
            checks.append({"requirement": "Company Type", "passed": True})

        return {
            "agent": self.funding_body_code,
            "checks": checks,
            "eligible": all(c["passed"] for c in checks)
        }


class NIHRAgent(FundingBodyAgent):
    """Nano agent specialized for NIHR grants"""

    def __init__(self):
        super().__init__("NIHR", "National Institute for Health Research", "UK")
        self.base_urls = [
            "https://www.nihr.ac.uk/explore-nihr/funding-programmes/",
        ]

    async def scrape_source(self, url: str) -> Dict[str, Any]:
        """Custom scraping for NIHR programme pages"""
        logger.info(f"NIHR Agent scraping: {url}")

        return {
            "funding_body": self.funding_body_code,
            "provider": self.funding_body_name,
            "silo": self.silo,
            # NIHR-specific
            "programme_type": self._detect_programme_type(url),
            "career_stage": self._detect_career_stage(url)
        }

    def _detect_programme_type(self, url: str) -> str:
        """Detect NIHR programme type from URL"""
        url_lower = url.lower()
        if "fellowship" in url_lower:
            return "Fellowship"
        elif "grant" in url_lower:
            return "Research Grant"
        elif "infrastructure" in url_lower:
            return "Infrastructure"
        return "Programme"

    def _detect_career_stage(self, url: str) -> Optional[str]:
        """Detect career stage requirement"""
        url_lower = url.lower()
        if "advanced" in url_lower:
            return "Advanced"
        elif "doctoral" in url_lower:
            return "Doctoral"
        elif "postdoctoral" in url_lower:
            return "Postdoctoral"
        return None

    async def parse_grant(self, raw_data: Dict) -> Dict[str, Any]:
        """Parse NIHR-specific grant format"""
        return {
            **raw_data,
            "currency": "GBP",
            "sectors": ["Health", "Research", "Clinical"],
            "eligibility": {
                **raw_data.get("eligibility", {}),
                "research_focus": "Applied health or social care"
            }
        }

    async def validate_eligibility(self, grant_id: str, user_profile: Dict) -> Dict[str, Any]:
        """NIHR-specific eligibility rules"""
        checks = []

        # NIHR focuses on health research
        if "health" in str(user_profile.get("research_area", "")).lower():
            checks.append({"requirement": "Health Research Focus", "passed": True})

        # Career stage check
        career_stage = user_profile.get("career_stage")
        if career_stage:
            checks.append({"requirement": f"Career Stage: {career_stage}", "passed": True})

        return {
            "agent": self.funding_body_code,
            "checks": checks,
            "eligible": len(checks) > 0 and all(c["passed"] for c in checks)
        }


class UKRIAgent(FundingBodyAgent):
    """Nano agent specialized for UKRI grants (umbrella for research councils)"""

    def __init__(self):
        super().__init__("UKRI", "UK Research and Innovation", "UK")
        self.base_urls = [
            "https://www.ukri.org/opportunity/",
        ]
        # Sub-councils
        self.councils = ["EPSRC", "ESRC", "MRC", "NERC", "AHRC", "BBSRC", "STFC"]

    async def scrape_source(self, url: str) -> Dict[str, Any]:
        """Custom scraping for UKRI opportunities"""
        logger.info(f"UKRI Agent scraping: {url}")

        return {
            "funding_body": self.funding_body_code,
            "provider": self.funding_body_name,
            "silo": self.silo,
            # UKRI-specific
            "council": self._detect_council(url),
            "scheme_type": "Research Grant"
        }

    def _detect_council(self, url: str) -> Optional[str]:
        """Detect which research council"""
        url_lower = url.lower()
        for council in self.councils:
            if council.lower() in url_lower:
                return council
        return None

    async def parse_grant(self, raw_data: Dict) -> Dict[str, Any]:
        """Parse UKRI-specific grant format"""
        return {
            **raw_data,
            "currency": "GBP",
            "eligibility": {
                **raw_data.get("eligibility", {}),
                "organization_type": "Research Organization",
                "location": ["UK"]
            }
        }

    async def validate_eligibility(self, grant_id: str, user_profile: Dict) -> Dict[str, Any]:
        """UKRI-specific eligibility rules"""
        checks = []

        # UKRI typically requires research organizations
        org_type = user_profile.get("organization_type", "")
        if "research" in org_type.lower() or "university" in org_type.lower():
            checks.append({"requirement": "Research Organization", "passed": True})
        else:
            checks.append({"requirement": "Research Organization", "passed": False})

        return {
            "agent": self.funding_body_code,
            "checks": checks,
            "eligible": all(c["passed"] for c in checks)
        }


class WellcomeAgent(FundingBodyAgent):
    """Nano agent specialized for Wellcome Trust"""

    def __init__(self):
        super().__init__("Wellcome", "Wellcome Trust", "UK")
        self.base_urls = [
            "https://wellcome.org/grant-funding/",
        ]

    async def scrape_source(self, url: str) -> Dict[str, Any]:
        """Custom scraping for Wellcome funding pages"""
        logger.info(f"Wellcome Agent scraping: {url}")

        return {
            "funding_body": self.funding_body_code,
            "provider": self.funding_body_name,
            "silo": self.silo,
            "category": "Charity",
            "focus": "Biomedical and health research"
        }

    async def parse_grant(self, raw_data: Dict) -> Dict[str, Any]:
        """Parse Wellcome-specific grant format"""
        return {
            **raw_data,
            "currency": "GBP",
            "sectors": ["Health", "Biomedical Research", "Life Sciences"],
            "eligibility": {
                **raw_data.get("eligibility", {}),
                "international": True,  # Wellcome funds internationally
                "focus_areas": ["Basic science", "Clinical research", "Public health"]
            }
        }

    async def validate_eligibility(self, grant_id: str, user_profile: Dict) -> Dict[str, Any]:
        """Wellcome-specific eligibility rules"""
        checks = []

        # Wellcome is more international
        checks.append({"requirement": "International applicants welcome", "passed": True})

        # Health/life sciences focus
        research_area = user_profile.get("research_area", "").lower()
        if any(kw in research_area for kw in ["health", "biomedical", "life sciences", "clinical"]):
            checks.append({"requirement": "Health/Life Sciences Focus", "passed": True})

        return {
            "agent": self.funding_body_code,
            "checks": checks,
            "eligible": len(checks) > 0
        }


# ============================================================================
# EU AGENTS
# ============================================================================

class EICAgent(FundingBodyAgent):
    """Nano agent for European Innovation Council"""

    def __init__(self):
        super().__init__("EIC", "European Innovation Council", "EU")
        self.base_urls = [
            "https://eic.ec.europa.eu/eic-funding-opportunities_en",
        ]

    async def scrape_source(self, url: str) -> Dict[str, Any]:
        """Custom scraping for EIC funding calls"""
        return {
            "funding_body": self.funding_body_code,
            "provider": self.funding_body_name,
            "silo": self.silo,
            "programme": "EIC Accelerator",
            "focus": "Deep tech and breakthrough innovation"
        }

    async def parse_grant(self, raw_data: Dict) -> Dict[str, Any]:
        """Parse EIC-specific grant format"""
        return {
            **raw_data,
            "currency": "EUR",
            "sectors": ["DeepTech", "Innovation", "Scale-up"],
            "eligibility": {
                **raw_data.get("eligibility", {}),
                "company_type": "SME",
                "location": ["EU Member State", "Associated Country"],
                "max_employees": 250
            }
        }

    async def validate_eligibility(self, grant_id: str, user_profile: Dict) -> Dict[str, Any]:
        """EIC-specific eligibility rules"""
        checks = []

        # SME requirement
        employees = user_profile.get("employees", 0)
        if employees <= 250:
            checks.append({"requirement": "SME size (<250 employees)", "passed": True})
        else:
            checks.append({"requirement": "SME size (<250 employees)", "passed": False})

        # EU location
        location = user_profile.get("location", "")
        if location in ["EU", "Associated Country"]:
            checks.append({"requirement": "EU/Associated Country", "passed": True})

        return {
            "agent": self.funding_body_code,
            "checks": checks,
            "eligible": all(c["passed"] for c in checks)
        }


# ============================================================================
# US AGENTS
# ============================================================================

class NSFAgent(FundingBodyAgent):
    """Nano agent for National Science Foundation"""

    def __init__(self):
        super().__init__("NSF", "National Science Foundation", "US")
        self.base_urls = [
            "https://seedfund.nsf.gov/",
            "https://www.nsf.gov/funding/",
        ]

    async def scrape_source(self, url: str) -> Dict[str, Any]:
        """Custom scraping for NSF programs"""
        return {
            "funding_body": self.funding_body_code,
            "provider": self.funding_body_name,
            "silo": self.silo,
            "programme": self._detect_nsf_program(url)
        }

    def _detect_nsf_program(self, url: str) -> str:
        """Detect NSF program type"""
        if "sbir" in url.lower():
            return "SBIR"
        elif "sttr" in url.lower():
            return "STTR"
        return "Research Grant"

    async def parse_grant(self, raw_data: Dict) -> Dict[str, Any]:
        """Parse NSF-specific grant format"""
        return {
            **raw_data,
            "currency": "USD",
            "eligibility": {
                **raw_data.get("eligibility", {}),
                "location": ["United States"],
                "us_owned": True
            }
        }

    async def validate_eligibility(self, grant_id: str, user_profile: Dict) -> Dict[str, Any]:
        """NSF-specific eligibility rules"""
        checks = []

        # US location requirement
        if user_profile.get("location") == "US":
            checks.append({"requirement": "US-based", "passed": True})
        else:
            checks.append({"requirement": "US-based", "passed": False})

        # Majority US-owned for SBIR/STTR
        if user_profile.get("us_owned", False):
            checks.append({"requirement": "Majority US-owned", "passed": True})

        return {
            "agent": self.funding_body_code,
            "checks": checks,
            "eligible": all(c["passed"] for c in checks)
        }


# ============================================================================
# AGENT REGISTRY
# ============================================================================

class AgentRegistry:
    """Registry of all funding body agents"""

    def __init__(self):
        self.agents: Dict[str, FundingBodyAgent] = {}
        self._initialize_agents()

    def _initialize_agents(self):
        """Initialize all nano agents"""
        # UK Agents
        self.agents["IUK"] = InnovateUKAgent()
        self.agents["NIHR"] = NIHRAgent()
        self.agents["UKRI"] = UKRIAgent()
        self.agents["Wellcome"] = WellcomeAgent()

        # EU Agents
        self.agents["EIC"] = EICAgent()

        # US Agents
        self.agents["NSF"] = NSFAgent()

        logger.info(f"Initialized {len(self.agents)} funding body agents")

    def get_agent(self, funding_body_code: str) -> Optional[FundingBodyAgent]:
        """Get agent by funding body code"""
        return self.agents.get(funding_body_code)

    def get_agents_by_silo(self, silo: str) -> List[FundingBodyAgent]:
        """Get all agents for a silo"""
        return [agent for agent in self.agents.values() if agent.silo == silo]

    def list_agents(self) -> List[Dict[str, Any]]:
        """List all available agents"""
        return [agent.get_metadata() for agent in self.agents.values()]

    async def route_query(self, query: str, funding_bodies: List[str] = None, silos: List[str] = None) -> Dict[str, Any]:
        """Route query to appropriate agents"""
        # Determine which agents to query
        target_agents = []

        if funding_bodies:
            # Specific funding bodies requested
            for fb in funding_bodies:
                agent = self.get_agent(fb)
                if agent:
                    target_agents.append(agent)
        elif silos:
            # Query by silo
            for silo in silos:
                target_agents.extend(self.get_agents_by_silo(silo))
        else:
            # Query all agents
            target_agents = list(self.agents.values())

        # Query each agent concurrently
        tasks = [agent.search(query) for agent in target_agents]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Aggregate results
        all_grants = []
        for agent, result in zip(target_agents, results):
            if isinstance(result, list):
                all_grants.extend(result)

        return {
            "query": query,
            "agents_queried": [a.funding_body_code for a in target_agents],
            "grants": all_grants,
            "total_results": len(all_grants)
        }


# Global registry instance
agent_registry = AgentRegistry()


if __name__ == "__main__":
    # Test the agent registry
    print("FALM Funding Body Agents")
    print("=" * 60)

    agents = agent_registry.list_agents()
    for agent_info in agents:
        print(f"\n{agent_info['funding_body_code']:12} - {agent_info['funding_body_name']}")
        print(f"              Silo: {agent_info['silo']}")
