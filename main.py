#!/usr/bin/env python3
"""
FALM - Federated Agentic Language Model
Grant Analyst System

Main entry point
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import uvicorn
from src.utils.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/falm.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def main():
    """Main entry point"""
    logger.info("=" * 60)
    logger.info("FALM - Federated Agentic Language Model")
    logger.info("Grant Discovery and Analysis System")
    logger.info("=" * 60)

    # Create required directories
    Path("logs").mkdir(exist_ok=True)
    Path("data").mkdir(exist_ok=True)
    Path("data/grants").mkdir(exist_ok=True)
    Path("data/nlms").mkdir(exist_ok=True)

    # Start API server
    logger.info(f"Starting API server on {settings.API_HOST}:{settings.API_PORT}")

    uvicorn.run(
        "src.api.app:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=False,
        log_level="info"
    )


if __name__ == "__main__":
    main()
