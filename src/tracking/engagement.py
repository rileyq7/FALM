"""
Engagement Tracking with SQLite persistence

Tracks user interactions to identify hot leads.
Now includes persistent storage that survives restarts!
"""

from typing import Dict, List, Optional
from datetime import datetime
import logging
from .persistent_tracking import PersistentEngagementTracker

logger = logging.getLogger(__name__)


# Use persistent storage as default
class EngagementTracker(PersistentEngagementTracker):
    """
    Engagement tracker with SQLite persistence

    Inherits from PersistentEngagementTracker to provide:
    - Persistent event storage
    - Hot lead detection across restarts
    - SQL-based analytics
    - Event history tracking
    """

    def __init__(self, db_path: str = "data/falm_engagement.db"):
        super().__init__(db_path)
        logger.info(f"[Engagement] Initialized with persistent storage: {db_path}")


# Legacy in-memory version (for testing/fallback)
class InMemoryEngagementTracker:
    """In-memory engagement tracker (loses data on restart)"""

    def __init__(self):
        self.sessions: Dict[str, List[Dict]] = {}
        self.hot_leads: List[Dict] = []
        logger.warning("[Engagement] Using in-memory storage - data will be lost on restart!")

    async def track_query(self, user_id: str, query: str, results_count: int):
        """Track a search query"""
        if user_id not in self.sessions:
            self.sessions[user_id] = []

        event = {
            "type": "query",
            "query": query,
            "results_count": results_count,
            "timestamp": datetime.utcnow().isoformat()
        }

        self.sessions[user_id].append(event)
        await self._check_hot_lead(user_id)

    async def track_view(self, user_id: str, grant_id: str):
        """Track grant view"""
        if user_id not in self.sessions:
            self.sessions[user_id] = []

        event = {
            "type": "view",
            "grant_id": grant_id,
            "timestamp": datetime.utcnow().isoformat()
        }

        self.sessions[user_id].append(event)
        await self._check_hot_lead(user_id)

    async def track_dashboard_add(self, user_id: str, grant_id: str):
        """Track adding grant to dashboard"""
        event = {
            "type": "dashboard_add",
            "grant_id": grant_id,
            "timestamp": datetime.utcnow().isoformat()
        }

        if user_id not in self.sessions:
            self.sessions[user_id] = []

        self.sessions[user_id].append(event)

        # Dashboard add = strong signal
        await self._mark_hot_lead(user_id, "Added grant to dashboard")

    async def _check_hot_lead(self, user_id: str):
        """Check if user is a hot lead"""
        events = self.sessions.get(user_id, [])

        # Hot lead criteria
        if len(events) >= 5:  # 5+ interactions
            await self._mark_hot_lead(user_id, "High engagement")

    async def _mark_hot_lead(self, user_id: str, reason: str):
        """Mark user as hot lead"""
        self.hot_leads.append({
            "user_id": user_id,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat(),
            "event_count": len(self.sessions.get(user_id, []))
        })

        logger.info(f"[Engagement] Hot lead: {user_id} - {reason}")

    async def get_hot_leads(self) -> List[Dict]:
        """Get list of hot leads"""
        return self.hot_leads
