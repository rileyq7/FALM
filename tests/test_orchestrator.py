"""
Tests for Orchestrator
"""

import pytest
import asyncio

from src.core.orchestrator import Orchestrator
from src.nlms import InnovateUKNLM


@pytest.mark.asyncio
async def test_orchestrator_init():
    """Test orchestrator initialization"""
    orch = Orchestrator()
    await orch.initialize()

    assert orch.status == "active"
    assert len(orch.nlms) == 0

    await orch.shutdown()


@pytest.mark.asyncio
async def test_register_nlm():
    """Test NLM registration"""
    orch = Orchestrator()
    await orch.initialize()

    nlm = InnovateUKNLM()
    await nlm.initialize()
    await orch.register_nlm(nlm)

    assert "innovate_uk" in orch.nlms
    assert orch.stats["nlm_count"] == 1

    await orch.shutdown()


@pytest.mark.asyncio
async def test_query():
    """Test query routing"""
    orch = Orchestrator()
    await orch.initialize()

    nlm = InnovateUKNLM()
    await nlm.initialize()
    await orch.register_nlm(nlm)

    # Index a test grant
    await nlm.index_grant({
        "title": "Test AI Grant",
        "description": "AI innovation funding"
    })

    # Query
    result = await orch.query("AI grants")

    assert result["total_results"] >= 0
    assert "innovate_uk" in result["nlms_queried"]

    await orch.shutdown()
