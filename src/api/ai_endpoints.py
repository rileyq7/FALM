"""
AI-Enhanced API Endpoints

Provides intelligent grant analysis, summarization, and advisory
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
import logging

from ..agents.grant_analyst_agent import GrantAnalystAgent
from ..core.orchestrator import Orchestrator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai", tags=["AI Agent"])

# Initialize AI agent
ai_agent = GrantAnalystAgent()


class AIChatRequest(BaseModel):
    """AI chat request"""
    query: str = Field(..., description="Natural language query")
    conversation_history: Optional[List[Dict]] = Field(default=[], description="Previous conversation context")
    max_results: int = Field(default=5, description="Max grants to consider")


class AIAnalyzeRequest(BaseModel):
    """Grant analysis request"""
    grant_ids: List[str] = Field(..., description="Grant IDs to analyze")
    analysis_type: str = Field(default="summarize", description="Type of analysis: summarize, compare, eligibility")


class AIWriteRequest(BaseModel):
    """Proposal writing assistance request"""
    project_description: str = Field(..., description="Project description")
    grant_id: str = Field(..., description="Target grant ID")


class DocumentFetchRequest(BaseModel):
    """External document fetch request"""
    url: str = Field(..., description="URL to PDF or webpage")


@router.post("/chat")
async def ai_chat(request: AIChatRequest):
    """
    Intelligent chat with AI grant analyst

    Natural language understanding with context-aware responses.
    Can answer questions, provide advice, summarize, and more.
    """
    from .app import orchestrator

    try:
        # First, search for relevant grants
        search_results = await orchestrator.query(
            request.query,
            max_results=request.max_results
        )

        # Use AI agent to analyze and respond
        response = await ai_agent.analyze_query(
            query=request.query,
            grants=search_results.get("grants", []),
            context="\n".join([
                f"{msg['role']}: {msg['content']}"
                for msg in request.conversation_history[-3:]  # Last 3 messages
            ]) if request.conversation_history else None
        )

        return {
            "response": response,
            "grants": search_results.get("grants", []),
            "total_results": search_results.get("total_results", 0),
            "processing_time_ms": search_results.get("processing_time_ms", 0),
            "ai_powered": bool(ai_agent.anthropic_client or ai_agent.openai_client)
        }

    except Exception as e:
        logger.error(f"AI chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/summarize")
async def summarize_grant(grant_id: str):
    """
    Get AI-generated summary of a grant

    Returns comprehensive, actionable summary
    """
    from .app import orchestrator

    try:
        # Get grant details from orchestrator
        # (In production, you'd query the specific grant from the DB)
        search_results = await orchestrator.query(grant_id, max_results=1)

        if not search_results.get("grants"):
            raise HTTPException(status_code=404, detail="Grant not found")

        grant = search_results["grants"][0]
        summary = await ai_agent.summarize_grant(grant)

        return {
            "grant_id": grant_id,
            "summary": summary,
            "grant": grant
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Summarization error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/compare")
async def compare_grants(request: AIAnalyzeRequest):
    """
    Compare multiple grants with AI analysis

    Provides strategic recommendations
    """
    from .app import orchestrator

    try:
        # Fetch grants
        grants = []
        for grant_id in request.grant_ids:
            results = await orchestrator.query(grant_id, max_results=1)
            if results.get("grants"):
                grants.append(results["grants"][0])

        if len(grants) < 2:
            raise HTTPException(status_code=400, detail="Need at least 2 grants to compare")

        comparison = await ai_agent.compare_grants(grants)

        return {
            "comparison": comparison,
            "grants_compared": len(grants),
            "grants": grants
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Comparison error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/fetch-document")
async def fetch_and_analyze_document(request: DocumentFetchRequest):
    """
    Fetch external document (PDF/webpage) and analyze with AI

    Extracts and summarizes funding guidelines
    """

    try:
        analysis = await ai_agent.fetch_and_analyze_document(request.url)

        return {
            "url": request.url,
            "analysis": analysis,
            "success": True
        }

    except Exception as e:
        logger.error(f"Document fetch error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/write-proposal")
async def help_write_proposal(request: AIWriteRequest):
    """
    Get AI assistance writing grant proposal

    Generates compelling proposal sections aligned with funder priorities
    """
    from .app import orchestrator

    try:
        # Get grant details
        results = await orchestrator.query(request.grant_id, max_results=1)

        if not results.get("grants"):
            raise HTTPException(status_code=404, detail="Grant not found")

        grant = results["grants"][0]
        proposal_help = await ai_agent.help_write_proposal(
            request.project_description,
            grant
        )

        return {
            "grant_id": request.grant_id,
            "proposal_sections": proposal_help,
            "grant": grant
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Proposal writing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def ai_status():
    """Check AI capabilities status"""

    return {
        "ai_enabled": bool(ai_agent.anthropic_client or ai_agent.openai_client),
        "anthropic_available": bool(ai_agent.anthropic_client),
        "openai_available": bool(ai_agent.openai_client),
        "capabilities": {
            "natural_language_chat": bool(ai_agent.anthropic_client or ai_agent.openai_client),
            "grant_summarization": bool(ai_agent.anthropic_client or ai_agent.openai_client),
            "grant_comparison": bool(ai_agent.anthropic_client or ai_agent.openai_client),
            "document_fetching": True,  # Always available
            "proposal_writing": bool(ai_agent.anthropic_client or ai_agent.openai_client)
        },
        "message": "Add ANTHROPIC_API_KEY or OPENAI_API_KEY to .env for full AI capabilities" if not (ai_agent.anthropic_client or ai_agent.openai_client) else "AI agent fully operational"
    }
