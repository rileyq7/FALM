"""
Configuration Management
"""

import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""

    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    # LLM APIs
    ANTHROPIC_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None

    # Database
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB: str = "falm"

    # ChromaDB
    CHROMADB_MODE: str = "local"  # "local" or "cloud"
    CHROMADB_CLOUD_URL: Optional[str] = None
    CHROMADB_API_KEY: Optional[str] = None
    CHROMADB_TENANT: Optional[str] = None
    CHROMADB_DATABASE: Optional[str] = None

    # AWS
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    S3_BUCKET: Optional[str] = None

    # Paths
    DATA_DIR: Path = Path("data")
    GRANTS_DIR: Path = Path("data/grants")

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
