"""
Dashboard Manager

Manages user dashboards with saved grants
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class DashboardManager:
    """Manages user dashboards"""

    def __init__(self):
        self.dashboards: Dict[str, List[Dict]] = {}

    async def add_grant(self, user_id: str, grant: Dict):
        """Add grant to user's dashboard"""
        if user_id not in self.dashboards:
            self.dashboards[user_id] = []

        dashboard_item = {
            **grant,
            "added_at": datetime.utcnow().isoformat(),
            "notes": ""
        }

        self.dashboards[user_id].append(dashboard_item)
        logger.info(f"[Dashboard] {user_id} added {grant.get('grant_id')}")

    async def get_dashboard(self, user_id: str) -> List[Dict]:
        """Get user's dashboard"""
        grants = self.dashboards.get(user_id, [])

        # Sort by deadline
        grants.sort(key=lambda g: g.get("deadline", "9999-12-31"))

        return grants

    async def get_urgent_deadlines(self, user_id: str, days: int = 30) -> List[Dict]:
        """Get grants with deadlines in next N days"""
        grants = self.dashboards.get(user_id, [])
        cutoff = (datetime.utcnow() + timedelta(days=days)).isoformat()

        urgent = [
            g for g in grants
            if g.get("deadline", "") and g.get("deadline") < cutoff
        ]

        return urgent
