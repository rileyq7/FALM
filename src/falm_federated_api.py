#!/usr/bin/env python3
"""
FALM Federated API Server
Complete federated node architecture where each funding body is a self-contained node
"""

import os
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn
from dotenv import load_dotenv

# Import federated components
from federated_nodes import (
    FederatedMesh,
    InnovateUKNode,
    NIHRNode,
    WellcomeNode,
    FederatedNode
)
from funding_body_detector import FundingBodyDetector

# Load environment
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/falm_federated_api.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Create logs directory
Path("logs").mkdir(exist_ok=True)

# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class QueryRequest(BaseModel):
    """User query request"""
    query: str
    funding_bodies: Optional[List[str]] = None
    silos: Optional[List[str]] = None
    max_results: int = 10

class QueryResponse(BaseModel):
    """Query response"""
    query: str
    nodes_queried: List[str]
    total_results: int
    grants: List[Dict[str, Any]]
    processing_time_ms: float

class IngestURLRequest(BaseModel):
    """URL ingestion request"""
    source_url: str
    funding_body: Optional[str] = None  # Auto-detect if not provided
    silo: Optional[str] = None
    max_depth: int = 2

class GrantData(BaseModel):
    """Grant data model"""
    grant_id: Optional[str] = None
    title: str
    provider: str
    silo: str
    funding_body: Optional[str] = None
    amount_min: Optional[float] = None
    amount_max: Optional[float] = None
    currency: str = "GBP"
    deadline: Optional[str] = None
    sectors: List[str] = Field(default_factory=list)
    eligibility: Dict[str, Any] = Field(default_factory=dict)
    description: str = ""
    application_url: Optional[str] = None
    supplementary_urls: List[str] = Field(default_factory=list)
    pdf_documents: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ScheduleRequest(BaseModel):
    """Schedule scraping request"""
    url: str
    funding_body: Optional[str] = None
    cron_expression: str = "0 3 * * *"  # Default: daily at 3am

class NodeStatusResponse(BaseModel):
    """Node status response"""
    funding_body_code: str
    funding_body_name: str
    silo: str
    status: str
    grant_count: int
    last_update: Optional[str]
    scheduled_sources: int

# ============================================================================
# FASTAPI APP
# ============================================================================

app = FastAPI(
    title="FALM Federated API",
    description="Federated Agentic LLM Mesh with autonomous nodes per funding body",
    version="2.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global mesh instance
mesh: Optional[FederatedMesh] = None

# ============================================================================
# STARTUP/SHUTDOWN
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize the federated mesh"""
    global mesh

    logger.info("=" * 60)
    logger.info("FALM FEDERATED API STARTUP")
    logger.info("=" * 60)

    # Create mesh
    mesh = FederatedMesh()

    # Initialize standard UK nodes
    logger.info("\n🇬🇧 Initializing UK Nodes...")
    await mesh.add_node(InnovateUKNode())
    await mesh.add_node(NIHRNode())
    await mesh.add_node(WellcomeNode())

    # TODO: Initialize EU and US nodes as they're created
    # await mesh.add_node(EICNode())
    # await mesh.add_node(NSFNode())

    logger.info("\n" + "=" * 60)
    logger.info(f"✅ FALM Federated Mesh Active")
    logger.info(f"   Total Nodes: {len(mesh.nodes)}")
    logger.info(f"   Status: {mesh.status}")
    logger.info("=" * 60 + "\n")

@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown the mesh"""
    global mesh

    if mesh:
        logger.info("Shutting down federated mesh...")
        await mesh.shutdown()
        logger.info("✅ Mesh shutdown complete")

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    """API root"""
    return {
        "service": "FALM Federated API",
        "version": "2.0.0",
        "architecture": "Federated Agentic LLM Mesh",
        "status": "operational",
        "nodes": len(mesh.nodes) if mesh else 0,
        "documentation": "/docs"
    }

@app.get("/health")
async def health_check():
    """Health check"""
    if not mesh:
        raise HTTPException(status_code=503, detail="Mesh not initialized")

    mesh_status = mesh.get_mesh_status()

    return {
        "status": "healthy",
        "mesh_status": mesh_status['status'],
        "total_nodes": mesh_status['total_nodes'],
        "total_grants": mesh_status['total_grants'],
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/api/query", response_model=QueryResponse)
async def query_grants(request: QueryRequest):
    """
    Query grants across the federated mesh
    Routes query to appropriate nodes and aggregates results
    """
    if not mesh:
        raise HTTPException(status_code=503, detail="Mesh not initialized")

    start_time = datetime.utcnow()

    try:
        # Route query through mesh
        result = await mesh.route_query(
            query=request.query,
            funding_bodies=request.funding_bodies,
            silos=request.silos
        )

        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000

        return QueryResponse(
            query=result['query'],
            nodes_queried=result['nodes_queried'],
            total_results=result['total_results'],
            grants=result['grants'],
            processing_time_ms=processing_time
        )

    except Exception as e:
        logger.error(f"Query error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ingest/url")
async def ingest_url(request: IngestURLRequest):
    """
    Ingest grant from URL
    Auto-detects funding body and routes to appropriate node
    """
    if not mesh:
        raise HTTPException(status_code=503, detail="Mesh not initialized")

    try:
        # Auto-detect funding body if not provided
        if not request.funding_body or not request.silo:
            silo, fb_code, fb_name = FundingBodyDetector.detect_from_url(request.source_url)
            request.funding_body = request.funding_body or fb_code
            request.silo = request.silo or silo

        logger.info(f"Ingesting URL: {request.source_url}")
        logger.info(f"  Detected: {request.silo}/{request.funding_body}")

        # Get the appropriate node
        node = mesh.nodes.get(request.funding_body)
        if not node:
            raise HTTPException(
                status_code=404,
                detail=f"Node for funding body '{request.funding_body}' not found"
            )

        # Scrape via the node
        grant_data = await node.scrape_source(request.source_url)

        # Ingest into node
        grant_id = await node.ingest_grant(grant_data)

        return {
            "status": "success",
            "grant_id": grant_id,
            "funding_body": request.funding_body,
            "silo": request.silo,
            "node": f"{request.silo}_{request.funding_body}",
            "message": f"Grant ingested into {request.funding_body} node"
        }

    except Exception as e:
        logger.error(f"URL ingestion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/grants")
async def add_grant(grant: GrantData):
    """
    Add grant manually to appropriate node
    """
    if not mesh:
        raise HTTPException(status_code=503, detail="Mesh not initialized")

    try:
        # Determine which node should handle this
        funding_body = grant.funding_body or "IUK"  # Default to IUK
        node = mesh.nodes.get(funding_body)

        if not node:
            raise HTTPException(
                status_code=404,
                detail=f"Node for funding body '{funding_body}' not found"
            )

        # Ingest into node
        grant_data = grant.dict()
        grant_id = await node.ingest_grant(grant_data)

        return {
            "status": "success",
            "grant_id": grant_id,
            "node": f"{node.silo}_{node.funding_body_code}",
            "message": f"Grant added to {funding_body} node"
        }

    except Exception as e:
        logger.error(f"Grant addition error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/schedule")
async def schedule_scraping(request: ScheduleRequest):
    """
    Schedule recurring scraping for a source
    """
    if not mesh:
        raise HTTPException(status_code=503, detail="Mesh not initialized")

    try:
        # Auto-detect funding body if not provided
        if not request.funding_body:
            silo, fb_code, fb_name = FundingBodyDetector.detect_from_url(request.url)
            request.funding_body = fb_code

        # Get node
        node = mesh.nodes.get(request.funding_body)
        if not node:
            raise HTTPException(
                status_code=404,
                detail=f"Node for funding body '{request.funding_body}' not found"
            )

        # Schedule on the node
        node.schedule_scraping(request.url, request.cron_expression)

        return {
            "status": "success",
            "funding_body": request.funding_body,
            "url": request.url,
            "cron": request.cron_expression,
            "message": f"Scheduled scraping on {request.funding_body} node"
        }

    except Exception as e:
        logger.error(f"Scheduling error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/nodes")
async def list_nodes():
    """
    List all active nodes in the mesh
    """
    if not mesh:
        raise HTTPException(status_code=503, detail="Mesh not initialized")

    mesh_status = mesh.get_mesh_status()

    return {
        "total_nodes": mesh_status['total_nodes'],
        "mesh_status": mesh_status['status'],
        "nodes": mesh_status['nodes']
    }

@app.get("/api/nodes/{funding_body}")
async def get_node_status(funding_body: str):
    """
    Get status of a specific node
    """
    if not mesh:
        raise HTTPException(status_code=503, detail="Mesh not initialized")

    node = mesh.nodes.get(funding_body)
    if not node:
        raise HTTPException(status_code=404, detail=f"Node '{funding_body}' not found")

    return node.get_status()

@app.get("/api/nodes/{funding_body}/grants")
async def get_node_grants(funding_body: str, limit: int = 50):
    """
    Get all grants from a specific node
    """
    if not mesh:
        raise HTTPException(status_code=503, detail="Mesh not initialized")

    node = mesh.nodes.get(funding_body)
    if not node:
        raise HTTPException(status_code=404, detail=f"Node '{funding_body}' not found")

    grants = await node.get_all_grants(limit=limit)

    return {
        "funding_body": funding_body,
        "node": f"{node.silo}_{node.funding_body_code}",
        "total_grants": len(grants),
        "grants": grants
    }

@app.get("/api/stats")
async def get_stats():
    """
    Get system-wide statistics
    """
    if not mesh:
        raise HTTPException(status_code=503, detail="Mesh not initialized")

    mesh_status = mesh.get_mesh_status()

    # Aggregate stats by silo
    stats_by_silo = {}
    for node_status in mesh_status['nodes']:
        silo = node_status['silo']
        if silo not in stats_by_silo:
            stats_by_silo[silo] = {
                "total_grants": 0,
                "funding_bodies": []
            }
        stats_by_silo[silo]['total_grants'] += node_status['grant_count']
        stats_by_silo[silo]['funding_bodies'].append(node_status['funding_body_code'])

    return {
        "total_nodes": mesh_status['total_nodes'],
        "total_grants": mesh_status['total_grants'],
        "mesh_status": mesh_status['status'],
        "by_silo": stats_by_silo,
        "nodes": mesh_status['nodes']
    }

@app.get("/api/funding-bodies")
async def list_funding_bodies():
    """
    List all known funding bodies (available and unavailable nodes)
    """
    all_bodies = FundingBodyDetector.get_all_bodies()

    # Mark which are active
    active_nodes = set(mesh.nodes.keys()) if mesh else set()

    result = {}
    for silo, bodies in all_bodies.items():
        result[silo] = []
        for code, info in bodies.items():
            result[silo].append({
                "code": code,
                "name": info["name"],
                "active": code in active_nodes,
                "domains": info["domains"]
            })

    return result

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    uvicorn.run(
        "falm_federated_api:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", 8000)),
        reload=False,
        log_level="info"
    )
