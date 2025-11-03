"""
FastAPI Application

Main API server for FALM system
"""

import logging
from contextlib import asynccontextmanager
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from ..core.orchestrator import Orchestrator
from ..nlms import InnovateUKNLM, HorizonEuropeNLM, NIHRNLM, UKRINLM
from ..nlms.enhanced_sme_nlm import EnhancedSMEContextNLM
from ..tracking.engagement import EngagementTracker
from ..tracking.dashboard import DashboardManager
from ..utils.database import db
from ..utils.config import settings

logger = logging.getLogger(__name__)

# Global instances
orchestrator: Optional[Orchestrator] = None
engagement_tracker: Optional[EngagementTracker] = None
dashboard_manager: Optional[DashboardManager] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager"""
    global orchestrator, engagement_tracker, dashboard_manager

    # Startup
    logger.info("Starting FALM system...")

    # Initialize orchestrator
    orchestrator = Orchestrator()
    await orchestrator.initialize()

    # Register NLMs
    nlms = [
        InnovateUKNLM(),
        HorizonEuropeNLM(),
        NIHRNLM(),
        UKRINLM()
    ]

    for nlm in nlms:
        await nlm.initialize()
        await orchestrator.register_nlm(nlm)

    # Register Enhanced SME context (rule-based expert system)
    sme_nlm = EnhancedSMEContextNLM()
    await sme_nlm.initialize()
    await orchestrator.register_sme_context(sme_nlm)

    # Initialize tracking
    engagement_tracker = EngagementTracker()
    dashboard_manager = DashboardManager()

    # Connect to database (optional)
    try:
        await db.connect()
    except Exception as e:
        logger.warning(f"Database connection failed: {e}")

    logger.info("FALM system ready")

    yield

    # Shutdown
    logger.info("Shutting down FALM system...")
    await orchestrator.shutdown()
    await db.disconnect()


# Create FastAPI app
app = FastAPI(
    title="FALM - Federated Agentic Language Model",
    description="Grant discovery and analysis system using specialized NLMs",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class QueryRequest(BaseModel):
    query: str
    max_results: int = 10
    silos: Optional[List[str]] = None
    domains: Optional[List[str]] = None
    user_id: Optional[str] = "anonymous"


class QueryResponse(BaseModel):
    query: str
    nlms_queried: List[str]
    total_results: int
    grants: List[Dict]
    sme_context: Optional[str] = None
    processing_time_ms: float


class GrantIndexRequest(BaseModel):
    domain: str
    grant_data: Dict


class DashboardAddRequest(BaseModel):
    user_id: str
    grant_id: str


# ============================================================================
# API ROUTES
# ============================================================================

@app.get("/")
async def root():
    """Health check"""
    return {
        "status": "online",
        "system": "FALM",
        "version": "1.0.0"
    }


@app.post("/api/query", response_model=QueryResponse)
async def query_grants(request: QueryRequest):
    """
    Search for grants across all NLMs

    This is the main entry point for grant searches
    """
    filters = {}
    if request.silos:
        filters["silos"] = request.silos
    if request.domains:
        filters["domains"] = request.domains

    # Query orchestrator
    result = await orchestrator.query(
        user_query=request.query,
        max_results=request.max_results,
        filters=filters
    )

    # Track engagement
    await engagement_tracker.track_query(
        user_id=request.user_id,
        query=request.query,
        results_count=result["total_results"]
    )

    return QueryResponse(**result)


@app.post("/api/grants/index")
async def index_grant(request: GrantIndexRequest):
    """Index a new grant in the appropriate NLM"""
    domain = request.domain

    # Find appropriate NLM
    nlm = orchestrator.nlms.get(domain)
    if not nlm:
        raise HTTPException(status_code=404, detail=f"NLM not found: {domain}")

    # Index grant
    grant_id = await nlm.index_grant(request.grant_data)

    return {
        "success": True,
        "grant_id": grant_id,
        "nlm_id": nlm.nlm_id
    }


@app.post("/api/dashboard/add")
async def add_to_dashboard(request: DashboardAddRequest):
    """Add grant to user dashboard"""
    # Get grant details (simplified - would query from NLMs)
    grant = {"grant_id": request.grant_id}

    await dashboard_manager.add_grant(request.user_id, grant)

    # Track engagement
    await engagement_tracker.track_dashboard_add(
        user_id=request.user_id,
        grant_id=request.grant_id
    )

    return {"success": True}


@app.get("/api/dashboard/{user_id}")
async def get_dashboard(user_id: str):
    """Get user's dashboard"""
    grants = await dashboard_manager.get_dashboard(user_id)
    return {
        "user_id": user_id,
        "grants": grants,
        "total": len(grants)
    }


@app.get("/api/dashboard/{user_id}/urgent")
async def get_urgent_deadlines(user_id: str, days: int = 30):
    """Get grants with urgent deadlines"""
    urgent = await dashboard_manager.get_urgent_deadlines(user_id, days)
    return {
        "user_id": user_id,
        "urgent_grants": urgent,
        "total": len(urgent)
    }


@app.get("/api/engagement/hot-leads")
async def get_hot_leads():
    """Get list of hot leads"""
    leads = await engagement_tracker.get_hot_leads()
    return {
        "hot_leads": leads,
        "total": len(leads)
    }


@app.get("/api/status")
async def get_status():
    """Get system status"""
    status = await orchestrator.get_status()
    return status


@app.get("/api/stats")
async def get_stats():
    """Get system statistics"""
    return {
        "orchestrator": orchestrator.stats,
        "engagement": {
            "total_sessions": len(engagement_tracker.sessions),
            "hot_leads": len(engagement_tracker.hot_leads)
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=settings.API_HOST,
        port=settings.API_PORT,
        log_level="info"
    )
