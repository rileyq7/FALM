"""
SME Context Stream NLM

This NLM provides expert SME (Subject Matter Expert) context to enhance queries.
It uses an LLM to add domain knowledge and insights.

This is the "secret sauce" that makes routing smarter and more effective.
"""

from typing import Dict, List, Optional, Any
import logging
import os

from ..core.base_nlm import BaseNLM, NLMConfig
from ..core.simp import SIMPMessage, Intent, MessageType

logger = logging.getLogger(__name__)


class SMEContextNLM(BaseNLM):
    """
    SME Context Provider

    This NLM doesn't store grants - instead it provides expert insights:
    - Query enhancement
    - Domain routing hints
    - Eligibility pre-screening
    - Application guidance

    Uses LLM when available, falls back to rules-based when not.
    """

    def __init__(self, api_keys: Optional[Dict[str, str]] = None):
        config = NLMConfig(
            nlm_id="sme_context",
            name="SME Context Provider",
            domain="meta",  # Meta-domain (operates on all domains)
            silo="ALL",
            can_search=False,  # Doesn't search - provides context
            can_scrape=False,
            can_analyze=True,
            llm_provider="anthropic",  # or "openai"
            llm_model="claude-3-5-sonnet-20241022"
        )
        super().__init__(config)

        # LLM client
        self.llm_client = None
        self.api_keys = api_keys or {}

        # SME knowledge base (rules-based fallback)
        self.domain_hints = {
            "innovate_uk": {
                "keywords": ["innovation", "smart grant", "cr&d", "uk", "sme"],
                "typical_amounts": (25000, 2000000),
                "focus": "Commercial innovation, UK SMEs"
            },
            "horizon_europe": {
                "keywords": ["eic", "horizon", "european", "international", "consortium"],
                "typical_amounts": (500000, 2500000),
                "focus": "Research excellence, international collaboration"
            },
            "nihr": {
                "keywords": ["health", "clinical", "patient", "nhs", "medical"],
                "typical_amounts": (50000, 500000),
                "focus": "Health research, patient benefit"
            },
            "ukri": {
                "keywords": ["research council", "epsrc", "esrc", "fundamental research"],
                "typical_amounts": (100000, 1000000),
                "focus": "Fundamental research, academic excellence"
            }
        }

    async def on_initialize(self):
        """Initialize LLM client if API keys available"""
        # Try to initialize Anthropic client
        if "ANTHROPIC_API_KEY" in self.api_keys or os.getenv("ANTHROPIC_API_KEY"):
            try:
                import anthropic
                api_key = self.api_keys.get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
                self.llm_client = anthropic.Anthropic(api_key=api_key)
                logger.info(f"[{self.nlm_id}] LLM client initialized (Anthropic)")
            except ImportError:
                logger.warning(f"[{self.nlm_id}] Anthropic library not installed")
            except Exception as e:
                logger.warning(f"[{self.nlm_id}] LLM initialization failed: {e}")

        # Try OpenAI if Anthropic not available
        elif "OPENAI_API_KEY" in self.api_keys or os.getenv("OPENAI_API_KEY"):
            try:
                import openai
                api_key = self.api_keys.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
                self.llm_client = openai.OpenAI(api_key=api_key)
                self.config.llm_provider = "openai"
                self.config.llm_model = "gpt-4o"
                logger.info(f"[{self.nlm_id}] LLM client initialized (OpenAI)")
            except ImportError:
                logger.warning(f"[{self.nlm_id}] OpenAI library not installed")
            except Exception as e:
                logger.warning(f"[{self.nlm_id}] LLM initialization failed: {e}")

        if not self.llm_client:
            logger.warning(f"[{self.nlm_id}] No LLM available - using rules-based fallback")

    async def handle_analyze(self, message: SIMPMessage) -> SIMPMessage:
        """
        Provide SME context for a query

        Returns:
        - Enhanced query
        - Suggested domains
        - Pre-screening insights
        - Application tips
        """
        context = message.context
        query = context.get("query", "")
        filters = context.get("filters", {})

        # Get SME insights
        if self.llm_client:
            insights = await self._get_llm_insights(query, filters)
        else:
            insights = await self._get_rules_based_insights(query, filters)

        return message.create_response(
            context={
                "sme_insights": insights,
                "nlm_id": self.nlm_id
            },
            intent=Intent.ANALYZE
        )

    async def _get_llm_insights(self, query: str, filters: Dict) -> str:
        """Get insights using LLM"""
        try:
            if self.config.llm_provider == "anthropic":
                return await self._get_anthropic_insights(query, filters)
            elif self.config.llm_provider == "openai":
                return await self._get_openai_insights(query, filters)
        except Exception as e:
            logger.error(f"[{self.nlm_id}] LLM error: {e}")
            return await self._get_rules_based_insights(query, filters)

    async def _get_anthropic_insights(self, query: str, filters: Dict) -> str:
        """Get insights from Claude"""
        prompt = f"""You are an expert grant funding advisor with deep knowledge of UK and EU funding programs.

User query: {query}
Filters: {filters}

Provide brief, actionable insights:
1. Which funding bodies are most relevant?
2. Key eligibility considerations
3. Typical funding amounts to expect
4. One pro tip for application success

Keep response under 100 words."""

        response = self.llm_client.messages.create(
            model=self.config.llm_model,
            max_tokens=200,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        return response.content[0].text

    async def _get_openai_insights(self, query: str, filters: Dict) -> str:
        """Get insights from GPT"""
        prompt = f"""You are an expert grant funding advisor.

Query: {query}
Filters: {filters}

Provide brief insights:
1. Most relevant funding bodies
2. Key eligibility points
3. Typical amounts
4. Application tip

Under 100 words."""

        response = self.llm_client.chat.completions.create(
            model=self.config.llm_model,
            max_tokens=200,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        return response.choices[0].message.content

    async def _get_rules_based_insights(self, query: str, filters: Dict) -> str:
        """Fallback: rules-based insights"""
        query_lower = query.lower()

        # Match domains
        matched_domains = []
        for domain, hints in self.domain_hints.items():
            for keyword in hints["keywords"]:
                if keyword in query_lower:
                    matched_domains.append((domain, hints))
                    break

        if not matched_domains:
            return "Consider all UK funding bodies (Innovate UK, NIHR, UKRI) and Horizon Europe for international opportunities."

        # Generate insights
        insights = []
        for domain, hints in matched_domains[:2]:  # Top 2 matches
            domain_name = domain.replace("_", " ").title()
            min_amt, max_amt = hints["typical_amounts"]
            insights.append(
                f"{domain_name}: {hints['focus']}. "
                f"Typical range: £{min_amt:,}-£{max_amt:,}."
            )

        return " ".join(insights)

    def _register_default_handlers(self):
        """Register handlers"""
        super()._register_default_handlers()
        self.register_handler(Intent.ANALYZE, self.handle_analyze)


if __name__ == "__main__":
    import asyncio

    async def test():
        nlm = SMEContextNLM(api_keys={
            "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY")
        })
        await nlm.initialize()

        # Test SME insights
        from ..core.simp import SIMPMessage
        msg = SIMPMessage(
            msg_type=MessageType.QUERY,
            sender="orchestrator",
            receiver="sme_context",
            intent=Intent.ANALYZE,
            context={
                "query": "AI grants for UK startups",
                "filters": {"silo": "UK"}
            }
        )

        response = await nlm.handle_analyze(msg)
        print("SME Insights:")
        print(response.context.get("sme_insights"))

        await nlm.shutdown()

    asyncio.run(test())
