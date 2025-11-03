"""
Add this to BaseNLM to share embedders across NLMs
Saves memory and startup time
"""

# Add this as a class variable at the top of BaseNLM
class BaseNLM(ABC):
    """Base class for all Narrow Language Models"""
    
    # Shared embedder pool (class-level)
    _embedder_pool: Dict[str, SentenceTransformer] = {}
    _embedder_lock = asyncio.Lock()
    
    # ... rest of existing code ...
    
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


# Benefits:
# - 4 NLMs using same model = 1x memory instead of 4x
# - Faster startup (only load model once)
# - Thread-safe with async lock

# Example memory savings:
# Before: 4 NLMs × 120MB model = 480MB
# After:  1 model shared        = 120MB
# Savings: 360MB (75% reduction!)
