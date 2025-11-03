#!/usr/bin/env python3
"""
Federated Node Architecture
Each funding body is a self-contained node with:
- Own database silo
- Specialized agent (SME for that data)
- Scraping scheduler
- SIMP communication
- Independent operation
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging
from pathlib import Path
import json

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import chromadb
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class FederatedNode:
    """
    Self-contained node for a funding body
    Houses everything needed to operate independently
    """

    def __init__(
        self,
        funding_body_code: str,
        funding_body_name: str,
        silo: str,
        base_urls: List[str] = None
    ):
        # Identity
        self.funding_body_code = funding_body_code
        self.funding_body_name = funding_body_name
        self.silo = silo

        # Node-specific directories
        self.node_dir = Path(f"data/nodes/{silo}_{funding_body_code}")
        self.db_dir = self.node_dir / "chroma_db"
        self.cache_dir = self.node_dir / "cache"
        self.logs_dir = self.node_dir / "logs"

        # Create directories
        for directory in [self.node_dir, self.db_dir, self.cache_dir, self.logs_dir]:
            directory.mkdir(parents=True, exist_ok=True)

        # Own database
        self.vector_db = None
        self.collection = None
        self.embedder = None

        # Own scraping scheduler
        self.scheduler = AsyncIOScheduler()
        self.scheduled_sources = []

        # Communication
        self.orchestrator_connection = None
        self.message_queue = []

        # State
        self.grant_count = 0
        self.last_update = None
        self.status = "initializing"

        # Scraping config
        self.base_urls = base_urls or []
        self.scrape_config = self._get_scrape_config()

        logger.info(f"🚀 Initialized Federated Node: {funding_body_code} ({funding_body_name})")

    async def initialize(self):
        """Initialize the node's components"""
        logger.info(f"Initializing {self.funding_body_code} node...")

        # Initialize vector database
        await self._initialize_vector_db()

        # Initialize embedder
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')

        # Start scheduler
        self.scheduler.start()

        self.status = "active"
        logger.info(f"✅ {self.funding_body_code} node initialized and active")

    async def _initialize_vector_db(self):
        """Initialize node's own vector database"""
        self.vector_db = chromadb.PersistentClient(
            path=str(self.db_dir)
        )

        # Create collection for this node
        collection_name = f"{self.silo}_{self.funding_body_code}"
        self.collection = self.vector_db.get_or_create_collection(
            name=collection_name,
            metadata={
                "funding_body": self.funding_body_code,
                "silo": self.silo,
                "created": datetime.utcnow().isoformat()
            }
        )

        logger.info(f"   Vector DB initialized: {collection_name}")

    def _get_scrape_config(self) -> Dict[str, Any]:
        """Get node-specific scraping configuration"""
        # Override in subclasses for funding body-specific logic
        return {
            "max_depth": 2,
            "follow_pdfs": True,
            "timeout": 30,
            "user_agent": f"FALM-{self.funding_body_code}-Bot"
        }

    # ========================================================================
    # DATA OPERATIONS
    # ========================================================================

    async def ingest_grant(self, grant_data: Dict[str, Any]) -> str:
        """Ingest a grant into this node's database"""
        try:
            grant_id = grant_data.get("grant_id", f"{self.funding_body_code}_{datetime.utcnow().timestamp()}")

            # Ensure funding body is set
            grant_data["funding_body"] = self.funding_body_code
            grant_data["silo"] = self.silo

            # Generate embeddings
            content = f"{grant_data.get('title', '')} {grant_data.get('description', '')}"
            embeddings = self.embedder.encode(content).tolist()

            # Add to vector DB
            self.collection.add(
                ids=[grant_id],
                embeddings=[embeddings],
                documents=[content],
                metadatas=[grant_data]
            )

            self.grant_count += 1
            self.last_update = datetime.utcnow()

            logger.info(f"   [{self.funding_body_code}] Ingested grant: {grant_id}")

            # Send notification to orchestrator
            await self._notify_orchestrator("grant_added", {"grant_id": grant_id})

            return grant_id

        except Exception as e:
            logger.error(f"   [{self.funding_body_code}] Ingestion error: {e}")
            raise

    async def search(self, query: str, n_results: int = 10, filters: Dict = None) -> List[Dict]:
        """Search within this node's data"""
        try:
            # Generate query embedding
            query_embedding = self.embedder.encode(query).tolist()

            # Search
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=filters
            )

            # Format results
            grants = []
            if results['metadatas'] and results['metadatas'][0]:
                for metadata in results['metadatas'][0]:
                    grants.append(metadata)

            logger.info(f"   [{self.funding_body_code}] Search '{query}': {len(grants)} results")

            return grants

        except Exception as e:
            logger.error(f"   [{self.funding_body_code}] Search error: {e}")
            return []

    async def get_all_grants(self, limit: int = 100) -> List[Dict]:
        """Get all grants from this node"""
        try:
            results = self.collection.get(limit=limit)
            return results.get('metadatas', [])
        except Exception as e:
            logger.error(f"   [{self.funding_body_code}] Get all grants error: {e}")
            return []

    # ========================================================================
    # SCRAPING & SCHEDULING
    # ========================================================================

    async def scrape_source(self, url: str) -> Dict[str, Any]:
        """
        Scrape a source URL using node-specific logic
        Override this in subclasses for custom extraction
        """
        logger.info(f"   [{self.funding_body_code}] Scraping: {url}")

        # This would call the scraping engine with node-specific config
        # For now, return basic structure
        return {
            "funding_body": self.funding_body_code,
            "silo": self.silo,
            "source_url": url,
            "scraped_at": datetime.utcnow().isoformat()
        }

    def schedule_scraping(self, url: str, cron_expression: str):
        """Schedule recurring scraping of a source"""
        job_id = f"{self.funding_body_code}_{len(self.scheduled_sources)}"

        trigger = CronTrigger.from_crontab(cron_expression)

        self.scheduler.add_job(
            self.scrape_source,
            trigger=trigger,
            args=[url],
            id=job_id,
            name=f"Scrape {url}",
            replace_existing=True
        )

        self.scheduled_sources.append({
            "url": url,
            "cron": cron_expression,
            "job_id": job_id
        })

        logger.info(f"   [{self.funding_body_code}] Scheduled: {url} ({cron_expression})")

    def schedule_daily_update(self, hour: int = 3, minute: int = 0):
        """Schedule daily updates of all base URLs"""
        for url in self.base_urls:
            # Daily at specified time
            cron_expr = f"{minute} {hour} * * *"
            self.schedule_scraping(url, cron_expr)

        logger.info(f"   [{self.funding_body_code}] Scheduled daily updates at {hour:02d}:{minute:02d}")

    # ========================================================================
    # SIMP COMMUNICATION
    # ========================================================================

    async def send_simp_message(self, msg_type: str, receiver: str, intent: str, context: Dict) -> Dict:
        """Send SIMP protocol message"""
        message = {
            "version": "1.0",
            "msg_type": msg_type,
            "sender": f"{self.silo}_{self.funding_body_code}",
            "receiver": receiver,
            "intent": intent,
            "context": context,
            "timestamp": datetime.utcnow().isoformat(),
            "correlation_id": f"{self.funding_body_code}_{datetime.utcnow().timestamp()}"
        }

        # Queue message for sending
        self.message_queue.append(message)

        logger.info(f"   [{self.funding_body_code}] SIMP → {receiver}: {intent}")

        return message

    async def receive_simp_message(self, message: Dict) -> Dict:
        """Receive and process SIMP protocol message"""
        msg_type = message.get("msg_type")
        intent = message.get("intent")
        context = message.get("context", {})

        logger.info(f"   [{self.funding_body_code}] SIMP ← {message.get('sender')}: {intent}")

        # Route based on intent
        if intent == "search":
            results = await self.search(
                query=context.get("query", ""),
                n_results=context.get("max_results", 10),
                filters=context.get("filters")
            )
            return await self.send_simp_message(
                msg_type="response",
                receiver=message.get("sender"),
                intent="search_results",
                context={"results": results, "count": len(results)}
            )

        elif intent == "status_check":
            return await self.send_simp_message(
                msg_type="response",
                receiver=message.get("sender"),
                intent="status",
                context=self.get_status()
            )

        elif intent == "trigger_scrape":
            url = context.get("url")
            if url:
                await self.scrape_source(url)
                return await self.send_simp_message(
                    msg_type="response",
                    receiver=message.get("sender"),
                    intent="scrape_complete",
                    context={"url": url}
                )

        return {}

    async def _notify_orchestrator(self, event: str, data: Dict):
        """Notify orchestrator of events"""
        await self.send_simp_message(
            msg_type="notification",
            receiver="orchestrator",
            intent=event,
            context=data
        )

    # ========================================================================
    # NODE STATUS & MANAGEMENT
    # ========================================================================

    def get_status(self) -> Dict[str, Any]:
        """Get node status"""
        return {
            "funding_body_code": self.funding_body_code,
            "funding_body_name": self.funding_body_name,
            "silo": self.silo,
            "status": self.status,
            "grant_count": self.grant_count,
            "last_update": self.last_update.isoformat() if self.last_update else None,
            "scheduled_sources": len(self.scheduled_sources),
            "base_urls": len(self.base_urls),
            "db_path": str(self.db_dir),
            "pending_messages": len(self.message_queue)
        }

    async def shutdown(self):
        """Gracefully shutdown the node"""
        logger.info(f"Shutting down {self.funding_body_code} node...")

        # Stop scheduler
        self.scheduler.shutdown(wait=True)

        self.status = "offline"
        logger.info(f"✅ {self.funding_body_code} node shutdown complete")

    def __repr__(self):
        return f"<FederatedNode {self.silo}/{self.funding_body_code}: {self.grant_count} grants>"


# ============================================================================
# SPECIALIZED NODES
# ============================================================================

class InnovateUKNode(FederatedNode):
    """IUK-specific node with custom logic"""

    def __init__(self):
        super().__init__(
            funding_body_code="IUK",
            funding_body_name="Innovate UK",
            silo="UK",
            base_urls=[
                "https://apply-for-innovation-funding.service.gov.uk/competition/search"
            ]
        )

    def _get_scrape_config(self) -> Dict[str, Any]:
        """IUK-specific scraping config"""
        return {
            "max_depth": 3,  # IUK has deep link structures
            "follow_pdfs": True,
            "keywords": ["guidance", "scope", "eligibility", "assessment"],
            "timeout": 45
        }

    async def scrape_source(self, url: str) -> Dict[str, Any]:
        """IUK-specific scraping logic"""
        result = await super().scrape_source(url)

        # IUK-specific extraction
        result["competition_id"] = self._extract_competition_id(url)
        result["match_funding_required"] = True
        result["currency"] = "GBP"

        return result

    def _extract_competition_id(self, url: str) -> str:
        """Extract IUK competition ID"""
        import re
        match = re.search(r'/competition/(\d+)/', url)
        return match.group(1) if match else "unknown"


class NIHRNode(FederatedNode):
    """NIHR-specific node"""

    def __init__(self):
        super().__init__(
            funding_body_code="NIHR",
            funding_body_name="National Institute for Health Research",
            silo="UK",
            base_urls=[
                "https://www.nihr.ac.uk/explore-nihr/funding-programmes/"
            ]
        )

    def _get_scrape_config(self) -> Dict[str, Any]:
        """NIHR-specific scraping config"""
        return {
            "max_depth": 2,
            "follow_pdfs": True,
            "keywords": ["fellowship", "grant", "award", "eligibility"],
            "focus_areas": ["health", "clinical", "research"]
        }


class WellcomeNode(FederatedNode):
    """Wellcome Trust-specific node"""

    def __init__(self):
        super().__init__(
            funding_body_code="Wellcome",
            funding_body_name="Wellcome Trust",
            silo="UK",
            base_urls=[
                "https://wellcome.org/grant-funding/"
            ]
        )

    def _get_scrape_config(self) -> Dict[str, Any]:
        """Wellcome-specific scraping config"""
        return {
            "max_depth": 2,
            "follow_pdfs": True,
            "international": True,  # Wellcome funds internationally
            "focus_areas": ["biomedical", "health", "life sciences"]
        }


# ============================================================================
# FEDERATED MESH
# ============================================================================

class FederatedMesh:
    """
    The mesh that connects all federated nodes
    Handles routing, coordination, and aggregation
    """

    def __init__(self):
        self.nodes: Dict[str, FederatedNode] = {}
        self.status = "initializing"

        logger.info("🌐 Initializing Federated Mesh...")

    async def add_node(self, node: FederatedNode):
        """Add a node to the mesh"""
        await node.initialize()
        self.nodes[node.funding_body_code] = node
        logger.info(f"   ✅ Added node: {node.funding_body_code}")

    async def initialize_standard_nodes(self):
        """Initialize standard UK nodes"""
        # UK Nodes
        await self.add_node(InnovateUKNode())
        await self.add_node(NIHRNode())
        await self.add_node(WellcomeNode())

        # TODO: Add EU and US nodes

        self.status = "active"
        logger.info(f"🌐 Federated Mesh active with {len(self.nodes)} nodes")

    async def route_query(self, query: str, funding_bodies: List[str] = None,
                         silos: List[str] = None) -> Dict[str, Any]:
        """Route query across the mesh"""
        target_nodes = []

        if funding_bodies:
            # Query specific funding bodies
            for fb in funding_bodies:
                if fb in self.nodes:
                    target_nodes.append(self.nodes[fb])
        elif silos:
            # Query by silo
            for node in self.nodes.values():
                if node.silo in silos:
                    target_nodes.append(node)
        else:
            # Query all nodes
            target_nodes = list(self.nodes.values())

        logger.info(f"🔍 Routing query to {len(target_nodes)} nodes: {query}")

        # Query nodes concurrently via SIMP
        tasks = []
        for node in target_nodes:
            message = {
                "msg_type": "query",
                "sender": "orchestrator",
                "receiver": f"{node.silo}_{node.funding_body_code}",
                "intent": "search",
                "context": {"query": query, "max_results": 10}
            }
            tasks.append(node.receive_simp_message(message))

        # Aggregate results
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        all_grants = []
        for response in responses:
            if isinstance(response, dict) and response.get("context"):
                grants = response["context"].get("results", [])
                all_grants.extend(grants)

        logger.info(f"   📊 Aggregated {len(all_grants)} grants from {len(target_nodes)} nodes")

        return {
            "query": query,
            "nodes_queried": [n.funding_body_code for n in target_nodes],
            "total_results": len(all_grants),
            "grants": all_grants
        }

    def get_mesh_status(self) -> Dict[str, Any]:
        """Get status of entire mesh"""
        return {
            "status": self.status,
            "total_nodes": len(self.nodes),
            "nodes": [node.get_status() for node in self.nodes.values()],
            "total_grants": sum(node.grant_count for node in self.nodes.values())
        }

    async def shutdown(self):
        """Shutdown entire mesh"""
        logger.info("🌐 Shutting down Federated Mesh...")

        tasks = [node.shutdown() for node in self.nodes.values()]
        await asyncio.gather(*tasks)

        self.status = "offline"
        logger.info("✅ Federated Mesh shutdown complete")


# ============================================================================
# MAIN
# ============================================================================

async def main():
    """Test the federated mesh"""
    print("\n" + "=" * 60)
    print("FALM FEDERATED MESH - Node Architecture")
    print("=" * 60 + "\n")

    # Create mesh
    mesh = FederatedMesh()

    # Initialize nodes
    await mesh.initialize_standard_nodes()

    # Show status
    status = mesh.get_mesh_status()
    print(f"\nMesh Status: {status['status']}")
    print(f"Total Nodes: {status['total_nodes']}")
    print("\nNodes:")
    for node_status in status['nodes']:
        print(f"  - {node_status['funding_body_code']:12} ({node_status['silo']}): {node_status['status']}")

    # Test query routing
    print("\n\nTesting query routing...")
    result = await mesh.route_query("AI grants", silos=["UK"])
    print(f"Query routed to: {', '.join(result['nodes_queried'])}")
    print(f"Results: {result['total_results']} grants")

    # Shutdown
    await mesh.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
