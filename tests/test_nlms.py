"""
Tests for NLMs
"""

import pytest

from src.nlms import InnovateUKNLM, HorizonEuropeNLM


@pytest.mark.asyncio
async def test_innovate_uk_nlm():
    """Test Innovate UK NLM"""
    nlm = InnovateUKNLM()
    await nlm.initialize()

    assert nlm.nlm_id == "innovate_uk"
    assert nlm.silo == "UK"
    assert nlm.status == "active"

    await nlm.shutdown()


@pytest.mark.asyncio
async def test_index_and_search():
    """Test indexing and searching"""
    nlm = InnovateUKNLM()
    await nlm.initialize()

    # Index grant
    grant_id = await nlm.index_grant({
        "title": "AI Innovation Grant",
        "description": "Funding for AI projects",
        "amount_max": 500000
    })

    assert grant_id is not None

    # Search
    results = await nlm.search("AI innovation")
    assert len(results) > 0

    await nlm.shutdown()


@pytest.mark.asyncio
async def test_horizon_europe_nlm():
    """Test Horizon Europe NLM"""
    nlm = HorizonEuropeNLM()
    await nlm.initialize()

    assert nlm.nlm_id == "horizon_europe"
    assert nlm.silo == "EU"

    await nlm.shutdown()
