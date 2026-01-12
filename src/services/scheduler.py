import logging
import asyncio
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from src.config import settings

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def run_async(coro):
    """Helper to run async functions in sync context."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def sync_osha_inspections():
    """Scheduled job to sync OSHA inspections."""
    from src.services.sync_service import sync_service

    logger.info("Running scheduled OSHA inspection sync...")
    try:
        stats = run_async(sync_service.sync_inspections(days_back=7))
        logger.info(
            f"Scheduled sync completed: {stats['created']} created, "
            f"{stats['updated']} updated"
        )
    except Exception as e:
        logger.error(f"Scheduled sync failed: {e}")


def sync_violations():
    """Scheduled job to sync violations for existing inspections."""
    from src.services.violation_sync_service import violation_sync_service

    logger.info("Running scheduled violation sync...")
    try:
        stats = run_async(violation_sync_service.sync_violations_smart(
            max_inspections_to_check=100
        ))
        logger.info(
            f"Violation sync completed: checked {stats['inspections_checked']} inspections, "
            f"found {stats['new_violations_found']} new violations across "
            f"{stats['inspections_with_new_violations']} inspections"
        )
    except Exception as e:
        logger.error(f"Violation sync failed: {e}")


def start_scheduler():
    """Start the background scheduler with configured jobs."""
    if scheduler.running:
        logger.warning("Scheduler already running")
        return

    # Sync OSHA inspections based on configured interval
    # Default: every hour, but also run daily at midnight for full sync
    scheduler.add_job(
        sync_osha_inspections,
        trigger=IntervalTrigger(hours=settings.FETCH_INTERVAL_HOURS),
        id="osha_sync_interval",
        name="OSHA Inspection Sync (Interval)",
        replace_existing=True,
    )

    # Daily full sync at 2 AM
    scheduler.add_job(
        sync_osha_inspections,
        trigger=CronTrigger(hour=2, minute=0),
        id="osha_sync_daily",
        name="OSHA Inspection Sync (Daily)",
        replace_existing=True,
    )

    # Sync violations every 6 hours (to catch new citations)
    # This is the key for lead generation - catching new violations
    # Reduced frequency to be more conservative with API rate limits
    scheduler.add_job(
        sync_violations,
        trigger=IntervalTrigger(hours=6),
        id="violation_sync_interval",
        name="Violation Sync (Every 6 Hours)",
        replace_existing=True,
    )

    # Also run violation sync daily at 3 AM (after inspection sync)
    scheduler.add_job(
        sync_violations,
        trigger=CronTrigger(hour=3, minute=0),
        id="violation_sync_daily",
        name="Violation Sync (Daily)",
        replace_existing=True,
    )

    scheduler.start()
    logger.info(
        f"Scheduler started: "
        f"Inspections every {settings.FETCH_INTERVAL_HOURS}h + daily at 2 AM, "
        f"Violations every 6h + daily at 3 AM"
    )


def stop_scheduler():
    """Stop the background scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")


def get_scheduled_jobs():
    """Get list of scheduled jobs."""
    return [
        {
            "id": job.id,
            "name": job.name,
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
        }
        for job in scheduler.get_jobs()
    ]
