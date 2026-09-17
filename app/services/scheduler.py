
from __future__ import annotations

import logging
import os

from apscheduler.schedulers.background import BackgroundScheduler

from app.services.ingestors.ampis import AMPISIngestor
from app.services.sync.ampis_markets import AMPISMarketSynchronizer


logger = logging.getLogger(__name__)

_scheduler = None
_app = None


MARKET_SYNC_INTERVAL_HOURS = int(
    os.getenv("AMPIS_MARKET_SYNC_HOURS", "24")
)

PRICE_SYNC_INTERVAL_HOURS = int(
    os.getenv("AMPIS_PRICE_SYNC_HOURS", "3")
)


def run_market_sync():
    """Synchronize AMPIS market definitions."""

    if _app is None:
        logger.error(
            "Cannot run AMPIS market sync: Flask app is unavailable."
        )
        return

    synchronizer = None

    with _app.app_context():
        try:
            synchronizer = AMPISMarketSynchronizer()

            result = synchronizer.sync()

            logger.info(
                "AMPIS market sync completed: %s",
                result,
            )

        except Exception:
            logger.exception(
                "AMPIS market synchronization failed."
            )

        finally:
            if synchronizer is not None:
                synchronizer.close()


def run_price_sync():
    """
    Synchronize the latest AMPIS prices.

    The scheduler controls when synchronization happens.
    AMPIS itself determines the authoritative price date
    from each market's published price page.
    """

    if _app is None:
        logger.error(
            "Cannot run AMPIS price sync: Flask app is unavailable."
        )
        return

    ingestor = None

    with _app.app_context():
        try:
            ingestor = AMPISIngestor()

            # Do not pass date.today().
            #
            # AMPIS publishes the authoritative price date
            # on each market page. The collector extracts that
            # date and the ingestor stores it in Price.price_date.
            result = ingestor.ingest_all_markets()

            logger.info(
                "AMPIS price sync completed: %s",
                result,
            )

        except Exception:
            logger.exception(
                "AMPIS price synchronization failed."
            )

        finally:
            if ingestor is not None:
                close_method = getattr(
                    ingestor,
                    "close",
                    None,
                )

                if callable(close_method):
                    close_method()


def start_scheduler(app):
    """Start the KrishiRate background scheduler."""

    global _scheduler
    global _app

    if _scheduler is not None:
        return _scheduler

    if (
        app.debug
        and os.getenv("WERKZEUG_RUN_MAIN") != "true"
    ):
        logger.info(
            "Skipping scheduler in Flask reloader parent process."
        )

        return None

    _app = app

    scheduler = BackgroundScheduler(
        timezone="Asia/Kathmandu",
    )

    scheduler.add_job(
        run_market_sync,
        trigger="interval",
        hours=MARKET_SYNC_INTERVAL_HOURS,
        id="ampis_market_sync",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    scheduler.add_job(
        run_price_sync,
        trigger="interval",
        hours=PRICE_SYNC_INTERVAL_HOURS,
        id="ampis_price_sync",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    scheduler.start()

    _scheduler = scheduler

    logger.warning(
        "KrishiRate scheduler started."
    )

    logger.warning(
        "AMPIS market sync interval: %s hour(s)",
        MARKET_SYNC_INTERVAL_HOURS,
    )

    logger.warning(
        "AMPIS price sync interval: %s hour(s)",
        PRICE_SYNC_INTERVAL_HOURS,
    )

    return scheduler


def stop_scheduler():
    """Stop the scheduler if it is running."""

    global _scheduler
    global _app

    if _scheduler is None:
        return

    try:
        _scheduler.shutdown(
            wait=False,
        )

        logger.warning(
            "KrishiRate scheduler stopped."
        )

    except Exception:
        logger.exception(
            "Error while stopping KrishiRate scheduler."
        )

    finally:
        _scheduler = None
        _app = None

