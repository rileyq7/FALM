"""
Base NLM (Narrow Language Model) Class

NLMs are specialized agents with domain expertise.
They communicate via SIMP protocol for efficiency.
"""

from typing import Dict, List, Optional, Any, Callable
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
import logging
import asyncio
from dataclasses import dataclass

from sentence_transformers import SentenceTransformer
import chromadb

from .simp import SIMPMessage, SIMPProtocol, MessageType, Intent

logger = logging.getLogger(__name__)


@dataclass
class NLMConfig:
    """Configuration for an NLM"""
    nlm_id: str
    name: str
    domain: str  # e.g., "innovate_uk", "horizon_europe"
    silo: str  # e.g., "UK", "EU", "US"

    # Storage
    data_dir: Path = None
    db_dir: Path = None
    cache_dir: Path = None

    # Capabilities
    can_search: bool = True
    can_scrape: bool = False
    can_analyze: bool = True

    # LLM config (optional - for SME context)
    llm_provider: Optional[str] = None  # "anthropic", "openai", etc.
    llm_model: Optional[str] = None
    llm_api_key: Optional[str] = None

    # Embeddings
    embedding_model: str = "all-MiniLM-L6-v2"

    def __post_init__(self):
        """Set up directories"""
        if not self.data_dir:
            self.data_dir = Path(f"data/nlms/{self.nlm_id}")
        if not self.db_dir:
            self.db_dir = self.data_dir / "chroma_db"
        if not self.cache_dir:
            self.cache_dir = self.data_dir / "cache"

        # Create directories
        for directory in [self.data_dir, self.db_dir, self.cache_dir]:
            directory.mkdir(parents=True, exist_ok=True)


class BaseNLM(ABC):
    """
    Base class for all Narrow Language Models

    An NLM is a specialized agent that:
    1. Has domain expertise (via embeddings + optional SME context)
    2. Communicates efficiently via SIMP
    3. Manages its own data silo
    4. Can be queried independently or via orchestrator
    """

    # Shared embedder pool (class-level) for memory efficiency
    _embedder_pool: Dict[str, SentenceTransformer] = {}
    _embedder_lock = asyncio.Lock()

    def __init__(self, config: NLMConfig):
        self.config = config
        self.nlm_id = config.nlm_id
        self.name = config.name
        self.domain = config.domain
        self.silo = config.silo

        # SIMP protocol
        self.simp = SIMPProtocol()
        self.message_queue: List[SIMPMessage] = []

        # Vector database
        self.vector_db: Optional[chromadb.Client] = None
        self.collection: Optional[chromadb.Collection] = None
        self.embedder: Optional[SentenceTransformer] = None

        # State
        self.status = "initializing"
        self.stats = {
            "queries_handled": 0,
            "grants_indexed": 0,
            "last_updated": None,
            "errors": 0
        }

        # Message handlers
        self.handlers: Dict[Intent, Callable] = {}
        self._register_default_handlers()

        logger.info(f"Initialized NLM: {self.nlm_id} ({self.name})")

    async def initialize(self):
        """Initialize the NLM with shared embedder pool"""
        logger.info(f"[{self.nlm_id}] Initializing...")

        # Initialize vector database
        await self._initialize_vector_db()

        # Get or create shared embedder (memory efficient!)
        model_name = self.config.embedding_model

        async with BaseNLM._embedder_lock:
            if model_name not in BaseNLM._embedder_pool:
                logger.info(f"[{self.nlm_id}] Loading embedding model: {model_name}")
                BaseNLM._embedder_pool[model_name] = SentenceTransformer(model_name)
            else:
                logger.info(f"[{self.nlm_id}] Using cached embedder: {model_name}")

        self.embedder = BaseNLM._embedder_pool[model_name]

        # Custom initialization
        await self.on_initialize()

        self.status = "active"
        logger.info(f"[{self.nlm_id}] Initialization complete")

    async def _initialize_vector_db(self):
        """Initialize vector database"""
        import os

        # Check if using ChromaDB Cloud
        chroma_mode = os.getenv("CHROMADB_MODE", "local")

        if chroma_mode == "cloud":
            # ChromaDB Cloud configuration
            cloud_url = os.getenv("CHROMADB_CLOUD_URL", "api.trychroma.com")
            api_key = os.getenv("CHROMADB_API_KEY")
            tenant = os.getenv("CHROMADB_TENANT")
            database = os.getenv("CHROMADB_DATABASE")

            if not api_key or not tenant or not database:
                logger.warning(f"[{self.nlm_id}] ChromaDB Cloud credentials missing, falling back to local")
                chroma_mode = "local"
            else:
                logger.info(f"[{self.nlm_id}] Connecting to ChromaDB Cloud...")
                logger.info(f"[{self.nlm_id}] Tenant: {tenant}, Database: {database}")

                # Use CloudClient for ChromaDB 1.3.0+
                self.vector_db = chromadb.CloudClient(
                    api_key=api_key,
                    tenant=tenant,
                    database=database
                )
                logger.info(f"[{self.nlm_id}] ChromaDB Cloud connected: {cloud_url}")

        if chroma_mode == "local":
            # Local ChromaDB (development)
            logger.info(f"[{self.nlm_id}] Using local ChromaDB: {self.config.db_dir}")
            self.vector_db = chromadb.PersistentClient(
                path=str(self.config.db_dir)
            )

        # Create/get collection (works for both local and cloud)
        collection_name = f"{self.silo}_{self.domain}"
        self.collection = self.vector_db.get_or_create_collection(
            name=collection_name,
            metadata={
                "nlm_id": self.nlm_id,
                "domain": self.domain,
                "silo": self.silo,
                "created": datetime.utcnow().isoformat()
            }
        )

        logger.info(f"[{self.nlm_id}] Vector DB ready: {collection_name}")

    def _register_default_handlers(self):
        """Register default message handlers"""
        self.register_handler(Intent.SEARCH, self.handle_search)
        self.register_handler(Intent.STATUS, self.handle_status)
        self.register_handler(Intent.FETCH, self.handle_fetch)

    def register_handler(self, intent: Intent, handler: Callable):
        """Register a handler for a specific intent"""
        self.handlers[intent] = handler

    # ========================================================================
    # MESSAGE PROCESSING (SIMP Protocol)
    # ========================================================================

    async def process_message(self, message: SIMPMessage) -> SIMPMessage:
        """
        Process incoming SIMP message

        This is the main entry point for all communication
        """
        # Validate message
        is_valid, error = self.simp.validate_message(message)
        if not is_valid:
            logger.error(f"[{self.nlm_id}] Invalid message: {error}")
            return message.create_error(error, "INVALID_MESSAGE")

        # Log incoming message
        logger.info(f"[{self.nlm_id}] ← {message.sender}: {message.intent.value}")
        self.simp.add_to_history(message)

        try:
            # Route to appropriate handler
            if message.intent in self.handlers:
                handler = self.handlers[message.intent]
                response = await handler(message)
            else:
                # No handler registered
                response = message.create_error(
                    f"No handler for intent: {message.intent.value}",
                    "NO_HANDLER"
                )

            # Log outgoing response
            logger.info(f"[{self.nlm_id}] → {message.sender}: response")
            self.simp.add_to_history(response)

            # Update stats
            self.stats["queries_handled"] += 1

            return response

        except Exception as e:
            logger.error(f"[{self.nlm_id}] Error processing message: {e}")
            self.stats["errors"] += 1
            return message.create_error(str(e), "PROCESSING_ERROR")

    async def send_message(self, message: SIMPMessage) -> SIMPMessage:
        """Send a message and await response"""
        # In a real system, this would send to orchestrator/other NLMs
        # For now, just queue it
        self.message_queue.append(message)
        logger.info(f"[{self.nlm_id}] → {message.receiver}: {message.intent.value}")
        return message

    # ========================================================================
    # DEFAULT MESSAGE HANDLERS
    # ========================================================================

    async def handle_search(self, message: SIMPMessage) -> SIMPMessage:
        """Handle search queries"""
        context = message.context
        query = context.get("query", "")
        max_results = context.get("max_results", 10)
        filters = context.get("filters", {})

        # Perform search
        results = await self.search(query, max_results, filters)

        return message.create_response(
            context={
                "results": results,
                "total": len(results),
                "nlm_id": self.nlm_id,
                "domain": self.domain
            },
            intent=Intent.SEARCH
        )

    async def handle_status(self, message: SIMPMessage) -> SIMPMessage:
        """Handle status requests"""
        status_info = {
            "nlm_id": self.nlm_id,
            "name": self.name,
            "domain": self.domain,
            "silo": self.silo,
            "status": self.status,
            "stats": self.stats,
            "capabilities": {
                "can_search": self.config.can_search,
                "can_scrape": self.config.can_scrape,
                "can_analyze": self.config.can_analyze
            }
        }

        return message.create_response(
            context=status_info,
            intent=Intent.STATUS
        )

    async def handle_fetch(self, message: SIMPMessage) -> SIMPMessage:
        """Handle data fetch requests"""
        context = message.context
        limit = context.get("limit", 100)

        grants = await self.get_all_grants(limit)

        return message.create_response(
            context={
                "grants": grants,
                "total": len(grants),
                "nlm_id": self.nlm_id
            },
            intent=Intent.FETCH
        )

    # ========================================================================
    # DATA OPERATIONS
    # ========================================================================

    def _prepare_metadata(self, grant_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare metadata for ChromaDB (only accepts simple types)

        Args:
            grant_data: Grant information

        Returns:
            Metadata dictionary with simple types
        """
        import json

        metadata = {}
        for key, value in grant_data.items():
            if value is None:
                continue
            elif isinstance(value, (str, int, float, bool)):
                metadata[key] = value
            elif isinstance(value, (list, dict)):
                metadata[key] = json.dumps(value)
            else:
                metadata[key] = str(value)

        return metadata

    async def index_grant(self, grant_data: Dict[str, Any]) -> str:
        """
        Index a grant in this NLM's database

        Args:
            grant_data: Grant information

        Returns:
            grant_id
        """
        grant_id = grant_data.get("grant_id", f"{self.nlm_id}_{datetime.utcnow().timestamp()}")

        # Ensure domain/silo metadata
        grant_data["nlm_id"] = self.nlm_id
        grant_data["domain"] = self.domain
        grant_data["silo"] = self.silo
        grant_data["indexed_at"] = datetime.utcnow().isoformat()

        # Generate embeddings
        content = await self.generate_search_content(grant_data)
        embeddings = self.embedder.encode(content).tolist()

        # Prepare metadata
        metadata = self._prepare_metadata(grant_data)

        # Add to vector DB
        self.collection.add(
            ids=[grant_id],
            embeddings=[embeddings],
            documents=[content],
            metadatas=[metadata]
        )

        self.stats["grants_indexed"] += 1
        self.stats["last_updated"] = datetime.utcnow().isoformat()

        logger.info(f"[{self.nlm_id}] Indexed grant: {grant_id}")

        return grant_id

    async def index_grants_batch(self, grants: List[Dict[str, Any]], batch_size: int = 32) -> List[str]:
        """
        Bulk index grants - much faster than indexing one-by-one

        Args:
            grants: List of grant data dictionaries
            batch_size: Batch size for encoding (default: 32)

        Returns:
            List of grant IDs
        """
        if not grants:
            return []

        logger.info(f"[{self.nlm_id}] Starting batch indexing of {len(grants)} grants...")

        # Ensure domain/silo metadata for all grants
        indexed_at = datetime.utcnow().isoformat()
        for grant in grants:
            grant["nlm_id"] = self.nlm_id
            grant["domain"] = self.domain
            grant["silo"] = self.silo
            grant["indexed_at"] = indexed_at

        # Generate all content
        contents = [await self.generate_search_content(g) for g in grants]

        # Batch encode (much faster than one-by-one)
        embeddings = self.embedder.encode(contents, batch_size=batch_size, show_progress_bar=True)

        # Prepare IDs and metadata
        ids = [g.get("grant_id", f"{self.nlm_id}_{i}_{datetime.utcnow().timestamp()}")
               for i, g in enumerate(grants)]
        metadatas = [self._prepare_metadata(g) for g in grants]

        # Single ChromaDB call for all grants
        self.collection.add(
            ids=ids,
            embeddings=embeddings.tolist(),
            documents=contents,
            metadatas=metadatas
        )

        # Update stats
        self.stats["grants_indexed"] += len(grants)
        self.stats["last_updated"] = indexed_at

        logger.info(f"[{self.nlm_id}] Bulk indexed {len(grants)} grants successfully")

        return ids

    async def search(self, query: str, max_results: int = 10, filters: Dict = None) -> List[Dict]:
        """
        Hybrid search: semantic + keyword matching

        Combines:
        - Semantic similarity (70% weight)
        - Keyword overlap (30% weight)

        Args:
            query: Search query
            max_results: Maximum results to return
            filters: Optional filters

        Returns:
            List of matching grants with hybrid relevance scores
        """
        import json

        # Generate query embedding
        query_embedding = self.embedder.encode(query).tolist()
        query_terms = set(query.lower().split())

        # Get more results for re-ranking
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=max_results * 3,  # Get 3x for re-ranking
            where=filters
        )

        # Parse and score results
        grants = []
        if results['metadatas'] and results['metadatas'][0]:
            for i, metadata in enumerate(results['metadatas'][0]):
                grant = {}
                for key, value in metadata.items():
                    # Deserialize JSON strings
                    if isinstance(value, str) and (value.startswith('[') or value.startswith('{')):
                        try:
                            grant[key] = json.loads(value)
                        except json.JSONDecodeError:
                            grant[key] = value
                    else:
                        grant[key] = value

                # Calculate keyword overlap score
                grant_text = f"{grant.get('title', '')} {grant.get('description', '')}".lower()
                grant_terms = set(grant_text.split())
                keyword_overlap = len(query_terms.intersection(grant_terms))
                keyword_score = keyword_overlap / max(len(query_terms), 1)

                # Semantic distance from ChromaDB (lower = better)
                semantic_distance = results['distances'][0][i]
                semantic_score = 1 - semantic_distance  # Convert to similarity

                # Combined score (weighted)
                combined_score = (
                    0.7 * semantic_score +
                    0.3 * keyword_score
                )

                grant['relevance_score'] = float(combined_score)
                grant['semantic_score'] = float(semantic_score)
                grant['keyword_score'] = float(keyword_score)

                grants.append(grant)

        # Sort by combined score
        grants.sort(key=lambda g: g['relevance_score'], reverse=True)

        # Return top N
        top_grants = grants[:max_results]

        if top_grants:
            avg_semantic = sum(g['semantic_score'] for g in top_grants) / len(top_grants)
            avg_keyword = sum(g['keyword_score'] for g in top_grants) / len(top_grants)
            logger.info(f"[{self.nlm_id}] Hybrid search '{query}': {len(top_grants)} results "
                       f"(avg semantic: {avg_semantic:.3f}, avg keyword: {avg_keyword:.3f})")
        else:
            logger.info(f"[{self.nlm_id}] Hybrid search '{query}': 0 results")

        return top_grants

    async def get_all_grants(self, limit: int = 100) -> List[Dict]:
        """Get all grants from this NLM's database"""
        import json

        results = self.collection.get(limit=limit)
        metadatas = results.get('metadatas', [])

        grants = []
        for metadata in metadatas:
            grant = {}
            for key, value in metadata.items():
                if isinstance(value, str) and (value.startswith('[') or value.startswith('{')):
                    try:
                        grant[key] = json.loads(value)
                    except json.JSONDecodeError:
                        grant[key] = value
                else:
                    grant[key] = value
            grants.append(grant)

        return grants

    # ========================================================================
    # ABSTRACT METHODS (Override in subclasses)
    # ========================================================================

    async def generate_search_content(self, grant_data: Dict[str, Any]) -> str:
        """
        Generate searchable content from grant data

        Override this to customize how grants are embedded
        """
        return f"{grant_data.get('title', '')} {grant_data.get('description', '')}"

    async def on_initialize(self):
        """Called after initialization - override for custom setup"""
        pass

    async def on_shutdown(self):
        """Called before shutdown - override for custom cleanup"""
        pass

    # ========================================================================
    # LIFECYCLE
    # ========================================================================

    async def shutdown(self):
        """Shutdown the NLM"""
        logger.info(f"[{self.nlm_id}] Shutting down...")

        await self.on_shutdown()

        self.status = "offline"
        logger.info(f"[{self.nlm_id}] Shutdown complete")

    def __repr__(self):
        return f"<NLM {self.nlm_id}: {self.domain} ({self.silo})>"


# ============================================================================
# EXAMPLE NLM
# ============================================================================

class ExampleNLM(BaseNLM):
    """Example NLM implementation"""

    def __init__(self):
        config = NLMConfig(
            nlm_id="example_nlm",
            name="Example NLM",
            domain="example",
            silo="TEST"
        )
        super().__init__(config)

    async def generate_search_content(self, grant_data: Dict[str, Any]) -> str:
        """Custom search content generation"""
        parts = [
            grant_data.get('title', ''),
            grant_data.get('description', ''),
            ' '.join(grant_data.get('sectors', []))
        ]
        return ' '.join(parts)


if __name__ == "__main__":
    import asyncio

    async def test():
        # Create and initialize NLM
        nlm = ExampleNLM()
        await nlm.initialize()

        # Index a grant
        grant_id = await nlm.index_grant({
            "title": "AI Innovation Grant",
            "description": "Funding for AI startups",
            "amount_max": 500000,
            "sectors": ["AI", "Technology"]
        })
        print(f"Indexed: {grant_id}")

        # Search
        results = await nlm.search("AI startups")
        print(f"Search results: {len(results)}")

        # Process SIMP message
        from .simp import create_search_query
        msg = create_search_query("orchestrator", "AI grants")
        msg.receiver = "example_nlm"

        response = await nlm.process_message(msg)
        print(f"Response: {response.context.get('total')} results")

        await nlm.shutdown()

    asyncio.run(test())
