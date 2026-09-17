from __future__ import annotations

import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app
from app.services.ingestors.ampis import AMPISIngestor
from app.services.sync.ampis_markets import AMPISMarketSynchronizer


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)


def main() -> None:
    app = create_app()

    with app.app_context():
        logger.info("Starting KrishiRate production initialization")

        logger.info("Synchronizing AMPIS markets")

        market_sync = AMPISMarketSynchronizer()

        try:
            market_result = market_sync.sync()
            logger.info(
                "AMPIS market sync completed: %s",
                market_result,
            )
        finally:
            market_sync.close()

        logger.info("Ingesting AMPIS prices")

        ingestor = AMPISIngestor()

        try:
            price_result = ingestor.ingest_all_markets()
            logger.info(
                "AMPIS price ingestion completed: %s",
                price_result,
            )
        finally:
            ingestor.close()

        logger.info("KrishiRate production initialization completed")


if __name__ == "__main__":
    main()