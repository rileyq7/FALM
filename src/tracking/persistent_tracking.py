"""
Enhanced Dashboard Manager with SQLite persistence
Replaces in-memory dict that loses data on restart
"""

import sqlite3
import json
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class PersistentDashboardManager:
    """Dashboard manager with SQLite persistence"""
    
    def __init__(self, db_path: str = "data/falm_dashboard.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dashboard_grants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                grant_id TEXT NOT NULL,
                grant_data TEXT NOT NULL,
                added_at TEXT NOT NULL,
                notes TEXT DEFAULT '',
                status TEXT DEFAULT 'saved',
                UNIQUE(user_id, grant_id)
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_id ON dashboard_grants(user_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_deadline ON dashboard_grants(
                json_extract(grant_data, '$.deadline')
            )
        """)
        
        conn.commit()
        conn.close()
        logger.info(f"[Dashboard] Database initialized: {self.db_path}")
    
    async def add_grant(self, user_id: str, grant: Dict):
        """Add grant to user's dashboard"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        grant_data = {
            **grant,
            "added_at": datetime.utcnow().isoformat()
        }
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO dashboard_grants 
                (user_id, grant_id, grant_data, added_at)
                VALUES (?, ?, ?, ?)
            """, (
                user_id,
                grant.get('grant_id', ''),
                json.dumps(grant_data),
                datetime.utcnow().isoformat()
            ))
            
            conn.commit()
            logger.info(f"[Dashboard] {user_id} added {grant.get('grant_id')}")
            
        except sqlite3.IntegrityError as e:
            logger.warning(f"[Dashboard] Duplicate grant for {user_id}: {e}")
        finally:
            conn.close()
    
    async def get_dashboard(self, user_id: str) -> List[Dict]:
        """Get user's dashboard"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT grant_data FROM dashboard_grants
            WHERE user_id = ?
            ORDER BY json_extract(grant_data, '$.deadline') ASC
        """, (user_id,))
        
        grants = [json.loads(row[0]) for row in cursor.fetchall()]
        conn.close()
        
        return grants
    
    async def get_urgent_deadlines(self, user_id: str, days: int = 30) -> List[Dict]:
        """Get grants with deadlines in next N days"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff = (datetime.utcnow() + timedelta(days=days)).isoformat()
        
        cursor.execute("""
            SELECT grant_data FROM dashboard_grants
            WHERE user_id = ?
            AND json_extract(grant_data, '$.deadline') IS NOT NULL
            AND json_extract(grant_data, '$.deadline') < ?
            ORDER BY json_extract(grant_data, '$.deadline') ASC
        """, (user_id, cutoff))
        
        urgent = [json.loads(row[0]) for row in cursor.fetchall()]
        conn.close()
        
        return urgent
    
    async def update_notes(self, user_id: str, grant_id: str, notes: str):
        """Update notes for a grant"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE dashboard_grants
            SET notes = ?
            WHERE user_id = ? AND grant_id = ?
        """, (notes, user_id, grant_id))
        
        conn.commit()
        conn.close()
    
    async def get_stats(self) -> Dict:
        """Get dashboard statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(DISTINCT user_id) FROM dashboard_grants")
        total_users = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM dashboard_grants")
        total_grants = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "total_users": total_users,
            "total_saved_grants": total_grants,
            "avg_grants_per_user": total_grants / max(total_users, 1)
        }


class PersistentEngagementTracker:
    """Engagement tracker with SQLite persistence"""
    
    def __init__(self, db_path: str = "data/falm_engagement.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS engagement_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                event_data TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_timestamp 
            ON engagement_events(user_id, timestamp)
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS hot_leads (
                user_id TEXT PRIMARY KEY,
                reason TEXT NOT NULL,
                event_count INTEGER NOT NULL,
                marked_at TEXT NOT NULL
            )
        """)
        
        conn.commit()
        conn.close()
        logger.info(f"[Engagement] Database initialized: {self.db_path}")
    
    async def track_query(self, user_id: str, query: str, results_count: int):
        """Track a search query"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        event_data = {
            "query": query,
            "results_count": results_count
        }
        
        cursor.execute("""
            INSERT INTO engagement_events (user_id, event_type, event_data, timestamp)
            VALUES (?, ?, ?, ?)
        """, (
            user_id,
            "query",
            json.dumps(event_data),
            datetime.utcnow().isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        await self._check_hot_lead(user_id)
    
    async def track_dashboard_add(self, user_id: str, grant_id: str):
        """Track adding grant to dashboard"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        event_data = {"grant_id": grant_id}
        
        cursor.execute("""
            INSERT INTO engagement_events (user_id, event_type, event_data, timestamp)
            VALUES (?, ?, ?, ?)
        """, (
            user_id,
            "dashboard_add",
            json.dumps(event_data),
            datetime.utcnow().isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        # Dashboard add = strong signal
        await self._mark_hot_lead(user_id, "Added grant to dashboard")
    
    async def _check_hot_lead(self, user_id: str):
        """Check if user is a hot lead"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COUNT(*) FROM engagement_events
            WHERE user_id = ?
        """, (user_id,))
        
        event_count = cursor.fetchone()[0]
        conn.close()
        
        if event_count >= 5:  # 5+ interactions
            await self._mark_hot_lead(user_id, "High engagement")
    
    async def _mark_hot_lead(self, user_id: str, reason: str):
        """Mark user as hot lead"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Count events
        cursor.execute("""
            SELECT COUNT(*) FROM engagement_events
            WHERE user_id = ?
        """, (user_id,))
        event_count = cursor.fetchone()[0]
        
        cursor.execute("""
            INSERT OR REPLACE INTO hot_leads (user_id, reason, event_count, marked_at)
            VALUES (?, ?, ?, ?)
        """, (
            user_id,
            reason,
            event_count,
            datetime.utcnow().isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"[Engagement] Hot lead: {user_id} - {reason}")
    
    async def get_hot_leads(self) -> List[Dict]:
        """Get list of hot leads"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT user_id, reason, event_count, marked_at
            FROM hot_leads
            ORDER BY marked_at DESC
        """)
        
        leads = [
            {
                "user_id": row[0],
                "reason": row[1],
                "event_count": row[2],
                "marked_at": row[3]
            }
            for row in cursor.fetchall()
        ]
        
        conn.close()
        return leads


# Usage in app.py:
# Replace:
#   dashboard_manager = DashboardManager()
#   engagement_tracker = EngagementTracker()
# With:
#   dashboard_manager = PersistentDashboardManager()
#   engagement_tracker = PersistentEngagementTracker()
