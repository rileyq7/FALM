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
import hashlib
import json
import numpy as np
from sentence_transformers import SentenceTransformer

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
        "innovate_uk": ["innovate uk", "iuk", "cr&d"],
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

        # Embedder for semantic scoring
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')

        # Query cache
        self.query_cache = {}  # query_hash -> (results, timestamp)
        self.cache_ttl = 3600  # 1 hour

        # Logging
        self.enable_query_logging = True
        self.orchestrator_version = "1.0"

        # State
        self.status = "initializing"
        self.stats = {
            "total_queries": 0,
            "total_results_returned": 0,
            "average_latency_ms": 0,
            "nlm_count": 0,
            "cache_hits": 0,
            "cache_misses": 0
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
        filters = filters or {}

        # Check cache first
        cache_key = hashlib.md5(
            f"{user_query}:{max_results}:{json.dumps(filters, sort_keys=True)}".encode()
        ).hexdigest()

        if cache_key in self.query_cache:
            cached_result, timestamp = self.query_cache[cache_key]
            age = (datetime.utcnow() - timestamp).total_seconds()

            if age < self.cache_ttl:
                logger.info(f"[Orchestrator] Cache hit: {user_query}")
                self.stats["cache_hits"] += 1
                cached_result['from_cache'] = True
                cached_result['cache_age_seconds'] = age
                return cached_result

        # Cache miss - check for complex query decomposition
        self.stats["cache_misses"] += 1

        if self._is_complex_query(user_query):
            sub_queries = await self._decompose_query(user_query, max_results, filters)
            logger.info(f"[Orchestrator] Decomposed into {len(sub_queries)} sub-queries")

            # Execute sub-queries in parallel
            sub_results = await asyncio.gather(*[
                self._execute_query(sq['query'], sq['max_results'], sq['filters'])
                for sq in sub_queries
            ])

            # Merge and deduplicate
            result = self._merge_results(sub_results, user_query)
        else:
            result = await self._execute_query(user_query, max_results, filters)

        # Store in cache
        self.query_cache[cache_key] = (result.copy(), datetime.utcnow())

        # Prune old cache entries
        if len(self.query_cache) > 1000:
            self._prune_cache()

        return result

    async def _execute_query(self,
                            user_query: str,
                            max_results: int,
                            filters: Dict) -> Dict[str, Any]:
        """Execute the actual query (called on cache miss)"""
        start_time = datetime.utcnow()

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

        # Create SIMP messages for each NLM with retry logic
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

            # Wrap in retry logic
            task = self._query_with_retry(nlm, message, max_retries=3)
            tasks.append(task)

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

        # Log query for analytics and RLHF training
        if self.enable_query_logging:
            await self._log_query(
                query=user_query,
                filters=filters,
                nlms_used=[nlm.nlm_id for nlm in target_nlms],
                result_count=aggregated['total_results'],
                latency_ms=latency_ms,
                timestamp=datetime.utcnow().isoformat()
            )

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
        """Aggregate results from multiple NLMs with semantic scoring"""

        all_grants = []
        nlms_queried = []
        errors = []

        # Get query embedding once
        query_embedding = self.embedder.encode(query)

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

                    # Add relevance scores and source info
                    for grant in grants:
                        grant_text = f"{grant.get('title', '')} {grant.get('description', '')}"
                        grant_embedding = self.embedder.encode(grant_text)

                        # Cosine similarity
                        similarity = np.dot(query_embedding, grant_embedding) / (
                            np.linalg.norm(query_embedding) * np.linalg.norm(grant_embedding)
                        )

                        grant['relevance_score'] = float(similarity)
                        grant['nlm_source'] = nlm.nlm_id

                    all_grants.extend(grants)
                    nlms_queried.append(nlm.nlm_id)
                elif response.msg_type == MessageType.ERROR:
                    errors.append({
                        "nlm_id": nlm.nlm_id,
                        "error": response.context.get("error_message", "Unknown error")
                    })

        # Sort by relevance score (descending), then deadline (ascending)
        all_grants.sort(key=lambda g: (-g.get('relevance_score', 0), g.get('deadline', '9999-12-31')))

        result = {
            "query": query,
            "nlms_queried": nlms_queried,
            "total_results": len(all_grants),
            "grants": all_grants,
            "sme_context": sme_context,
            "errors": errors if errors else None
        }

        return result

    async def _query_with_retry(self, nlm: BaseNLM, message: SIMPMessage, max_retries: int = 3) -> SIMPMessage:
        """Query NLM with exponential backoff"""
        for attempt in range(max_retries):
            try:
                response = await asyncio.wait_for(
                    nlm.process_message(message),
                    timeout=5.0  # 5 second timeout
                )
                return response

            except asyncio.TimeoutError:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # 1s, 2s, 4s
                    logger.warning(f"[Orchestrator] Timeout from {nlm.nlm_id}, "
                                 f"retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"[Orchestrator] {nlm.nlm_id} failed after {max_retries} attempts")
                    raise

            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"[Orchestrator] Error from {nlm.nlm_id}: {e}, retrying...")
                    await asyncio.sleep(1)
                else:
                    logger.error(f"[Orchestrator] {nlm.nlm_id} failed after {max_retries} attempts: {e}")
                    raise

    def _prune_cache(self):
        """Remove old entries from cache"""
        current_time = datetime.utcnow()
        keys_to_remove = []

        for key, (_, timestamp) in self.query_cache.items():
            age = (current_time - timestamp).total_seconds()
            if age > self.cache_ttl:
                keys_to_remove.append(key)

        for key in keys_to_remove:
            del self.query_cache[key]

        logger.info(f"[Orchestrator] Pruned {len(keys_to_remove)} cache entries")

    def _is_complex_query(self, query: str) -> bool:
        """Detect if query needs decomposition"""
        complexity_indicators = [
            ' and ', ' or ', ' with ', ' for ',
            'ai medical', 'uk startup', 'health tech',
            'multiple', 'different', 'various'
        ]
        return any(ind in query.lower() for ind in complexity_indicators)

    async def _decompose_query(self, query: str, max_results: int, filters: Dict) -> List[Dict]:
        """Break down complex query into sub-queries"""
        query_lower = query.lower()
        sub_queries = []

        # Geographic decomposition
        geographic_terms = {
            'uk': ['UK'],
            'eu': ['EU'],
            'europe': ['EU'],
            'us': ['US']
        }

        for term, silos in geographic_terms.items():
            if term in query_lower:
                sub_queries.append({
                    'query': query,
                    'filters': {**filters, 'silos': silos},
                    'max_results': max_results
                })

        # Domain decomposition
        domain_terms = {
            'medical': ['nihr'],
            'health': ['nihr'],
            'innovation': ['innovate_uk'],
            'research': ['ukri'],
            'horizon': ['horizon_europe']
        }

        for term, domains in domain_terms.items():
            if term in query_lower:
                sub_queries.append({
                    'query': query,
                    'filters': {**filters, 'domains': domains},
                    'max_results': max_results
                })

        # If no decomposition found, return original
        return sub_queries if sub_queries else [{
            'query': query,
            'filters': filters,
            'max_results': max_results
        }]

    def _merge_results(self, sub_results: List[Dict], original_query: str) -> Dict[str, Any]:
        """Merge and deduplicate results from sub-queries"""
        all_grants = []
        all_nlms_queried = set()
        all_errors = []
        total_processing_time = 0

        # Collect all results
        for result in sub_results:
            grants = result.get('grants', [])
            all_grants.extend(grants)
            all_nlms_queried.update(result.get('nlms_queried', []))
            if result.get('errors'):
                all_errors.extend(result['errors'])
            total_processing_time += result.get('processing_time_ms', 0)

        # Deduplicate by grant ID or title
        seen = set()
        unique_grants = []
        for grant in all_grants:
            identifier = grant.get('id') or grant.get('title', '')
            if identifier and identifier not in seen:
                seen.add(identifier)
                unique_grants.append(grant)

        # Re-sort by relevance score
        unique_grants.sort(key=lambda g: (-g.get('relevance_score', 0), g.get('deadline', '9999-12-31')))

        return {
            'query': original_query,
            'nlms_queried': list(all_nlms_queried),
            'total_results': len(unique_grants),
            'grants': unique_grants,
            'processing_time_ms': total_processing_time,
            'decomposed': True,
            'sub_query_count': len(sub_results),
            'errors': all_errors if all_errors else None
        }

    async def _log_query(self, **kwargs):
        """
        Log query for analytics and RLHF training

        This data is invaluable for:
        - Understanding user behavior
        - Training custom models
        - Improving routing strategies
        - Performance monitoring
        """
        from pathlib import Path

        log_entry = {
            **kwargs,
            'orchestrator_version': self.orchestrator_version,
            'routing_strategy': self.routing_strategy.__class__.__name__,
            'cache_hit_rate': self.stats['cache_hits'] / max(1, self.stats['cache_hits'] + self.stats['cache_misses'])
        }

        # Ensure logs directory exists
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)

        # Write to JSONL file for later analysis
        log_file = log_dir / 'query_log.jsonl'
        try:
            with open(log_file, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
        except Exception as e:
            logger.error(f"[Orchestrator] Failed to log query: {e}")

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
