import asyncio
import logging
from app.core.database import async_session
from app.services.cache_service import CacheService

logger = logging.getLogger(__name__)

async def start_cache_cleanup_loop():
    """
    Background service loop that runs cache cleanup periodically.
    Runs immediately on startup, and then every 24 hours.
    """
    logger.info("Cache cleanup background service active.")
    while True:
        try:
            logger.info("Executing daily cache database cleanup...")
            async with async_session() as db:
                await CacheService.run_cache_cleanup(db)
            logger.info("Daily cache database cleanup complete.")
        except asyncio.CancelledError:
            logger.info("Cache cleanup background task cancelled.")
            raise
        except Exception as e:
            logger.error(f"Error in cache cleanup loop: {e}")
        
        # Sleep for 24 hours (86400 seconds)
        await asyncio.sleep(86400)
