#!/usr/bin/env python3
"""
Seed sample grant data for testing
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.core.orchestrator import Orchestrator
from src.nlms import InnovateUKNLM, HorizonEuropeNLM, NIHRNLM, UKRINLM


SAMPLE_GRANTS = {
    "innovate_uk": [
        {
            "grant_id": "IUK_SMART_2025_001",
            "title": "Smart Grants: Spring 2025",
            "description": "Support for game-changing and disruptive R&D innovation",
            "grant_type": "Smart Grant",
            "amount_min": 25000,
            "amount_max": 2000000,
            "currency": "GBP",
            "sectors": ["AI & Data", "Clean Energy", "Digital"],
            "deadline": "2025-03-31",
            "application_url": "https://apply-for-innovation-funding.service.gov.uk"
        },
        {
            "grant_id": "IUK_CRD_2025_001",
            "title": "Collaborative R&D Grant",
            "description": "Funding for collaborative innovation projects",
            "grant_type": "CR&D",
            "amount_min": 100000,
            "amount_max": 1000000,
            "currency": "GBP",
            "sectors": ["Advanced Manufacturing", "Health"],
            "deadline": "2025-06-30",
        }
    ],
    "horizon_europe": [
        {
            "grant_id": "HORIZON_EIC_2025_001",
            "title": "EIC Accelerator 2025",
            "description": "Support for high-risk, high-impact innovations",
            "program": "EIC Accelerator",
            "amount_min": 500000,
            "amount_max": 2500000,
            "currency": "EUR",
            "topics": ["AI", "Quantum", "Biotech"],
            "trl_min": 5,
            "trl_max": 8,
            "deadline": "2025-06-30"
        }
    ],
    "nihr": [
        {
            "grant_id": "NIHR_RfPB_2025_001",
            "title": "Research for Patient Benefit",
            "description": "Patient-centered health and care research",
            "funding_stream": "Research for Patient Benefit",
            "amount_min": 50000,
            "amount_max": 500000,
            "currency": "GBP",
            "research_area": "Clinical research",
            "deadline": "2025-05-31"
        }
    ],
    "ukri": [
        {
            "grant_id": "UKRI_EPSRC_2025_001",
            "title": "EPSRC Responsive Mode",
            "description": "Investigator-led research in engineering and physical sciences",
            "council": "EPSRC",
            "amount_min": 100000,
            "amount_max": 1000000,
            "currency": "GBP",
            "deadline": "2025-12-31"
        }
    ]
}


async def seed_data():
    """Seed sample grants"""
    print("=" * 60)
    print("FALM Data Seeding")
    print("=" * 60)
    print()

    # Initialize orchestrator and NLMs
    orchestrator = Orchestrator()
    await orchestrator.initialize()

    nlms = {
        "innovate_uk": InnovateUKNLM(),
        "horizon_europe": HorizonEuropeNLM(),
        "nihr": NIHRNLM(),
        "ukri": UKRINLM()
    }

    for nlm in nlms.values():
        await nlm.initialize()
        await orchestrator.register_nlm(nlm)

    # Seed grants
    total_seeded = 0
    for domain, grants in SAMPLE_GRANTS.items():
        nlm = nlms[domain]
        print(f"Seeding {len(grants)} grants for {domain}...")

        for grant in grants:
            grant_id = await nlm.index_grant(grant)
            print(f"  ✓ {grant_id}")
            total_seeded += 1

    print()
    print(f"Total grants seeded: {total_seeded}")
    print()

    # Test search
    print("Testing search...")
    result = await orchestrator.query("AI grants")
    print(f"Found {result['total_results']} AI grants")

    # Shutdown
    await orchestrator.shutdown()

    print()
    print("=" * 60)
    print("Seeding complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(seed_data())
