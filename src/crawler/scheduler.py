"""
Crawler Scheduler

Manages automatic crawling on a schedule
"""

from typing import Dict, List, Callable
from datetime import datetime
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)


class CrawlerScheduler:
    """Scheduler for automatic grant crawling"""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.jobs: Dict[str, Dict] = {}

    async def initialize(self):
        """Start scheduler"""
        self.scheduler.start()
        logger.info("[Scheduler] Started")

    def schedule_crawl(self,
                      job_id: str,
                      crawler_func: Callable,
                      cron_expression: str = "0 3 * * *"):
        """
        Schedule a crawl job

        Args:
            job_id: Unique job ID
            crawler_func: Async function to call
            cron_expression: Cron schedule (default: daily at 3am)
        """
        trigger = CronTrigger.from_crontab(cron_expression)

        self.scheduler.add_job(
            crawler_func,
            trigger=trigger,
            id=job_id,
            name=f"Crawl {job_id}",
            replace_existing=True
        )

        self.jobs[job_id] = {
            "cron": cron_expression,
            "added": datetime.utcnow().isoformat()
        }

        logger.info(f"[Scheduler] Scheduled {job_id}: {cron_expression}")

    async def shutdown(self):
        """Shutdown scheduler"""
        self.scheduler.shutdown(wait=True)
        logger.info("[Scheduler] Shutdown")
