"""
Run the OSHA Tracker application.

Usage:
    python run.py              # Run the web server
    python run.py --sync       # Run a manual sync then exit
    python run.py --init-db    # Initialize database tables then exit
    python run.py --no-reload  # Run without auto-reload (more stable)
"""
import sys
import os
import asyncio
import argparse
import shutil
import time
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def clear_pycache():
    """Clear all __pycache__ directories to prevent stale bytecode issues."""
    logger.info("Clearing Python cache directories...")
    project_root = Path(__file__).parent
    cache_dirs = list(project_root.rglob("__pycache__"))

    cleared = 0
    failed = 0
    for cache_dir in cache_dirs:
        try:
            shutil.rmtree(cache_dir)
            cleared += 1
            logger.debug(f"  Cleared: {cache_dir.relative_to(project_root)}")
        except Exception as e:
            failed += 1
            logger.debug(f"  Skipped (in use): {cache_dir.relative_to(project_root)}")

    if cleared > 0:
        logger.info(f"Cache cleared: {cleared} directories removed")
    if failed > 0:
        logger.debug(f"  {failed} directories skipped (files in use)")


def main():
    parser = argparse.ArgumentParser(description="OSHA Tracker Application")
    parser.add_argument("--sync", action="store_true", help="Run a manual sync")
    parser.add_argument("--init-db", action="store_true", help="Initialize database")
    parser.add_argument("--days", type=int, default=30, help="Days to look back for sync")
    parser.add_argument("--no-reload", action="store_true", help="Disable auto-reload (more stable)")
    parser.add_argument("--clear-cache", action="store_true", help="Clear Python cache before starting")
    args = parser.parse_args()

    # Clear cache if requested or if running server
    if args.clear_cache or (not args.sync and not args.init_db):
        clear_pycache()

    if args.init_db:
        from src.database.connection import init_db
        logger.info("Initializing database...")
        init_db()
        logger.info("Database initialized successfully!")
        return

    if args.sync:
        from src.services.sync_service import sync_service
        logger.info(f"Running manual sync (days_back={args.days})...")
        stats = asyncio.run(sync_service.sync_inspections(days_back=args.days))
        logger.info("Sync complete!")
        logger.info(f"  Fetched: {stats['fetched']}")
        logger.info(f"  Created: {stats['created']}")
        logger.info(f"  Updated: {stats['updated']}")
        logger.info(f"  Errors:  {stats['errors']}")
        return

    # Run the web server with error handling
    import uvicorn
    from src.config import settings

    logger.info("=" * 60)
    logger.info("Starting OSHA Tracker...")
    logger.info(f"Dashboard: http://{settings.API_HOST}:{settings.API_PORT}")
    logger.info(f"API Docs:  http://{settings.API_HOST}:{settings.API_PORT}/docs")
    logger.info(f"Auto-reload: {'disabled' if args.no_reload else 'enabled'}")
    logger.info("=" * 60)

    try:
        uvicorn.run(
            "src.main:app",
            host=settings.API_HOST,
            port=settings.API_PORT,
            reload=not args.no_reload,
            log_level="info",
            access_log=True,
            # Timeout configurations to prevent hanging
            timeout_keep_alive=75,
            timeout_graceful_shutdown=30,
        )
    except KeyboardInterrupt:
        logger.info("\nShutting down gracefully...")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
