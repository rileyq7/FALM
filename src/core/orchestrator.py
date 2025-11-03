"""
Orchestrator - Smart Router for NLM Mesh

The orchestrator:
1. Routes user queries to appropriate NLMs
2. Aggregates results from multiple NLMs
3. Coordinates multi-step workflows
4. Manages SME context streaming
"""

from typing import Dict, List, Optional, Any, Set
from datetime import datetime
import logging
import asyncio

from .simp import SIMPMessage, SIMPProtocol, MessageType, Intent, create_search_query
from .base_nlm import BaseNLM

logger = logging.getLogger(__name__)


class RoutingStrategy:
    """Base class for routing strategies"""

    async def select_nlms(self,
                         query: str,
                         available_nlms: Dict[str, BaseNLM],
                         filters: Dict = None) -> List[BaseNLM]:
        """Select which NLMs should handle this query"""
        raise NotImplementedError


class SiloRoutingStrategy(RoutingStrategy):
    """Route based on geographic silo (UK, EU, US)"""

    async def select_nlms(self,
                         query: str,
                         available_nlms: Dict[str, BaseNLM],
                         filters: Dict = None) -> List[BaseNLM]:
        filters = filters or {}
        target_silos = filters.get("silos", [])
        target_domains = filters.get("domains", [])

        selected = []
        for nlm in available_nlms.values():
            # Check silo filter
            if target_silos and nlm.silo not in target_silos:
                continue

            # Check domain filter
            if target_domains and nlm.domain not in target_domains:
                continue

            selected.append(nlm)

        return selected if selected else list(available_nlms.values())


class KeywordRoutingStrategy(RoutingStrategy):
    """Route based on keywords in query"""

    DOMAIN_KEYWORDS = {
        "innovate_uk": ["innovate uk", "iuk", "smart grant", "cr&d"],
        "horizon_europe": ["horizon", "eic", "european", "eu funding"],
        "nihr": ["nihr", "health research", "clinical"],
        "ukri": ["ukri", "research council", "epsrc", "esrc", "nerc"]
    }

    async def select_nlms(self,
                         query: str,
                         available_nlms: Dict[str, BaseNLM],
                         filters: Dict = None) -> List[BaseNLM]:
        query_lower = query.lower()
        selected = set()

        for domain, keywords in self.DOMAIN_KEYWORDS.items():
            if any(kw in query_lower for kw in keywords):
                # Find NLMs with this domain
                for nlm in available_nlms.values():
                    if nlm.domain == domain:
                        selected.add(nlm)

        # If no keywords matched, select all
        return list(selected) if selected else list(available_nlms.values())


class BroadcastRoutingStrategy(RoutingStrategy):
    """Broadcast to all NLMs"""

    async def select_nlms(self,
                         query: str,
                         available_nlms: Dict[str, BaseNLM],
                         filters: Dict = None) -> List[BaseNLM]:
        return list(available_nlms.values())


class Orchestrator:
    """
    Main orchestrator for the NLM mesh

    Responsibilities:
    - Route queries to appropriate NLMs
    - Aggregate results
    - Manage SME context
    - Track engagement
    """

    def __init__(self, routing_strategy: Optional[RoutingStrategy] = None):
        self.nlms: Dict[str, BaseNLM] = {}
        self.simp = SIMPProtocol()

        # Routing
        self.routing_strategy = routing_strategy or SiloRoutingStrategy()
        self.sme_context_nlm: Optional[BaseNLM] = None

        # State
        self.status = "initializing"
        self.stats = {
            "total_queries": 0,
            "total_results_returned": 0,
            "average_latency_ms": 0,
            "nlm_count": 0
        }

        logger.info("Initialized Orchestrator")

    async def initialize(self):
        """Initialize the orchestrator"""
        self.status = "active"
        logger.info("Orchestrator ready")

    async def register_nlm(self, nlm: BaseNLM):
        """Register an NLM with the orchestrator"""
        self.nlms[nlm.nlm_id] = nlm
        self.stats["nlm_count"] = len(self.nlms)
        logger.info(f"[Orchestrator] Registered NLM: {nlm.nlm_id} ({nlm.domain})")

    async def register_sme_context(self, sme_nlm: BaseNLM):
        """Register SME context stream NLM"""
        self.sme_context_nlm = sme_nlm
        logger.info(f"[Orchestrator] Registered SME context: {sme_nlm.nlm_id}")

    # ========================================================================
    # QUERY ROUTING
    # ========================================================================

    async def query(self,
                   user_query: str,
                   max_results: int = 10,
                   filters: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Process a user query

        Args:
            user_query: The user's search query
            max_results: Maximum results to return
            filters: Optional filters (silos, domains, etc.)

        Returns:
            Aggregated results from all relevant NLMs
        """
        start_time = datetime.utcnow()
        filters = filters or {}

        logger.info(f"[Orchestrator] Query: {user_query}")

        # Get SME context if available
        sme_context = None
        if self.sme_context_nlm:
            sme_context = await self._get_sme_context(user_query, filters)

        # Select which NLMs to query
        target_nlms = await self.routing_strategy.select_nlms(
            user_query,
            self.nlms,
            filters
        )

        logger.info(f"[Orchestrator] Routing to {len(target_nlms)} NLMs: "
                   f"{[nlm.nlm_id for nlm in target_nlms]}")

        # Create SIMP messages for each NLM
        tasks = []
        for nlm in target_nlms:
            message = create_search_query(
                sender="orchestrator",
                query=user_query,
                max_results=max_results,
                filters=filters
            )
            message.receiver = nlm.nlm_id

            # Add SME context if available
            if sme_context:
                message.metadata["sme_context"] = sme_context

            tasks.append(nlm.process_message(message))

        # Query all NLMs concurrently
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Aggregate results
        aggregated = await self._aggregate_results(
            query=user_query,
            responses=responses,
            target_nlms=target_nlms,
            sme_context=sme_context
        )

        # Calculate latency
        end_time = datetime.utcnow()
        latency_ms = (end_time - start_time).total_seconds() * 1000

        # Update stats
        self.stats["total_queries"] += 1
        self.stats["total_results_returned"] += aggregated["total_results"]
        self.stats["average_latency_ms"] = (
            (self.stats["average_latency_ms"] * (self.stats["total_queries"] - 1) + latency_ms)
            / self.stats["total_queries"]
        )

        aggregated["processing_time_ms"] = latency_ms

        logger.info(f"[Orchestrator] Returned {aggregated['total_results']} results in {latency_ms:.2f}ms")

        return aggregated

    async def _get_sme_context(self, query: str, filters: Dict) -> Optional[str]:
        """Get SME context for query"""
        if not self.sme_context_nlm:
            return None

        try:
            message = SIMPMessage(
                msg_type=MessageType.QUERY,
                sender="orchestrator",
                receiver=self.sme_context_nlm.nlm_id,
                intent=Intent.ANALYZE,
                context={
                    "query": query,
                    "filters": filters
                }
            )

            response = await self.sme_context_nlm.process_message(message)

            if response.msg_type == MessageType.RESPONSE:
                return response.context.get("sme_insights", "")

        except Exception as e:
            logger.error(f"[Orchestrator] SME context error: {e}")

        return None

    async def _aggregate_results(self,
                                query: str,
                                responses: List[Any],
                                target_nlms: List[BaseNLM],
                                sme_context: Optional[str]) -> Dict[str, Any]:
        """Aggregate results from multiple NLMs"""

        all_grants = []
        nlms_queried = []
        errors = []

        for i, response in enumerate(responses):
            nlm = target_nlms[i]

            if isinstance(response, Exception):
                logger.error(f"[Orchestrator] Error from {nlm.nlm_id}: {response}")
                errors.append({
                    "nlm_id": nlm.nlm_id,
                    "error": str(response)
                })
                continue

            if isinstance(response, SIMPMessage):
                if response.msg_type == MessageType.RESPONSE:
                    grants = response.context.get("results", [])
                    all_grants.extend(grants)
                    nlms_queried.append(nlm.nlm_id)
                elif response.msg_type == MessageType.ERROR:
                    errors.append({
                        "nlm_id": nlm.nlm_id,
                        "error": response.context.get("error_message", "Unknown error")
                    })

        # Sort by relevance (if we had scores) or deadline
        all_grants.sort(key=lambda g: g.get("deadline", "9999-12-31"))

        result = {
            "query": query,
            "nlms_queried": nlms_queried,
            "total_results": len(all_grants),
            "grants": all_grants,
            "sme_context": sme_context,
            "errors": errors if errors else None
        }

        return result

    # ========================================================================
    # COMMAND ROUTING
    # ========================================================================

    async def trigger_scrape(self, url: str, domain: Optional[str] = None) -> Dict[str, Any]:
        """Trigger scraping on appropriate NLM"""

        # Find target NLM
        target_nlm = None
        if domain:
            for nlm in self.nlms.values():
                if nlm.domain == domain:
                    target_nlm = nlm
                    break
        else:
            # Auto-detect from URL
            for nlm in self.nlms.values():
                if nlm.config.can_scrape:
                    target_nlm = nlm
                    break

        if not target_nlm:
            return {
                "success": False,
                "error": "No suitable NLM found for scraping"
            }

        # Send scrape command
        message = SIMPMessage(
            msg_type=MessageType.COMMAND,
            sender="orchestrator",
            receiver=target_nlm.nlm_id,
            intent=Intent.SCRAPE,
            context={
                "url": url
            }
        )

        response = await target_nlm.process_message(message)

        return {
            "success": response.msg_type != MessageType.ERROR,
            "nlm_id": target_nlm.nlm_id,
            "response": response.context
        }

    async def get_status(self) -> Dict[str, Any]:
        """Get orchestrator and all NLM statuses"""

        # Get status from all NLMs
        nlm_statuses = []
        for nlm in self.nlms.values():
            message = SIMPMessage(
                msg_type=MessageType.QUERY,
                sender="orchestrator",
                receiver=nlm.nlm_id,
                intent=Intent.STATUS,
                context={}
            )

            response = await nlm.process_message(message)
            if response.msg_type == MessageType.RESPONSE:
                nlm_statuses.append(response.context)

        return {
            "orchestrator_status": self.status,
            "stats": self.stats,
            "nlms": nlm_statuses,
            "sme_context_available": self.sme_context_nlm is not None
        }

    # ========================================================================
    # ADVANCED ROUTING
    # ========================================================================

    def set_routing_strategy(self, strategy: RoutingStrategy):
        """Change routing strategy"""
        self.routing_strategy = strategy
        logger.info(f"[Orchestrator] Routing strategy set to: {strategy.__class__.__name__}")

    async def multi_step_query(self, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Execute multi-step workflow

        Example:
        [
            {"action": "search", "query": "AI grants", "filters": {"silo": "UK"}},
            {"action": "analyze", "query": "eligibility for startup"},
            {"action": "deadline_check", "days": 30}
        ]
        """
        results = []

        for step in steps:
            action = step.get("action")

            if action == "search":
                result = await self.query(
                    step.get("query"),
                    max_results=step.get("max_results", 10),
                    filters=step.get("filters")
                )
                results.append(result)

            elif action == "analyze":
                # Would call analysis NLM
                pass

            elif action == "deadline_check":
                # Would filter by deadline
                pass

        return results

    # ========================================================================
    # LIFECYCLE
    # ========================================================================

    async def shutdown(self):
        """Shutdown orchestrator and all NLMs"""
        logger.info("[Orchestrator] Shutting down...")

        # Shutdown all NLMs
        tasks = [nlm.shutdown() for nlm in self.nlms.values()]
        if self.sme_context_nlm:
            tasks.append(self.sme_context_nlm.shutdown())

        await asyncio.gather(*tasks)

        self.status = "offline"
        logger.info("[Orchestrator] Shutdown complete")


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    import asyncio
    from .base_nlm import NLMConfig, BaseNLM

    class TestNLM(BaseNLM):
        def __init__(self, nlm_id: str, domain: str, silo: str):
            config = NLMConfig(
                nlm_id=nlm_id,
                name=f"{domain} NLM",
                domain=domain,
                silo=silo
            )
            super().__init__(config)

    async def test():
        # Create orchestrator
        orch = Orchestrator()
        await orch.initialize()

        # Register NLMs
        iuk_nlm = TestNLM("iuk_nlm", "innovate_uk", "UK")
        nihr_nlm = TestNLM("nihr_nlm", "nihr", "UK")
        horizon_nlm = TestNLM("horizon_nlm", "horizon_europe", "EU")

        for nlm in [iuk_nlm, nihr_nlm, horizon_nlm]:
            await nlm.initialize()
            await orch.register_nlm(nlm)

        # Test query
        result = await orch.query(
            "AI grants for startups",
            filters={"silos": ["UK"]}
        )

        print(f"Query results: {result['total_results']} grants")
        print(f"NLMs queried: {result['nlms_queried']}")
        print(f"Latency: {result['processing_time_ms']:.2f}ms")

        # Get status
        status = await orch.get_status()
        print(f"\nOrchestrator stats: {status['stats']}")

        # Shutdown
        await orch.shutdown()

    asyncio.run(test())
