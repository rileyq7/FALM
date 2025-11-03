"""
Database Utilities (MongoDB)
"""

from typing import Dict, List, Optional
import logging
from motor.motor_asyncio import AsyncIOMotorClient

from .config import settings

logger = logging.getLogger(__name__)


class Database:
    """MongoDB database client"""

    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.db = None

    async def connect(self):
        """Connect to MongoDB"""
        try:
            self.client = AsyncIOMotorClient(settings.MONGODB_URL)
            self.db = self.client[settings.MONGODB_DB]
            logger.info(f"[Database] Connected to MongoDB: {settings.MONGODB_DB}")
        except Exception as e:
            logger.error(f"[Database] Connection failed: {e}")

    async def disconnect(self):
        """Disconnect from MongoDB"""
        if self.client:
            self.client.close()
            logger.info("[Database] Disconnected")

    async def save_grant(self, grant: Dict) -> str:
        """Save grant to database"""
        collection = self.db.grants
        result = await collection.insert_one(grant)
        return str(result.inserted_id)

    async def get_grant(self, grant_id: str) -> Optional[Dict]:
        """Get grant by ID"""
        collection = self.db.grants
        return await collection.find_one({"grant_id": grant_id})

    async def search_grants(self, query: Dict, limit: int = 100) -> List[Dict]:
        """Search grants"""
        collection = self.db.grants
        cursor = collection.find(query).limit(limit)
        return await cursor.to_list(length=limit)


db = Database()
