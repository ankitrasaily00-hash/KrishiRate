from __future__ import annotations

from datetime import date, datetime

from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Market, Price, Product, Source
from app.services.collectors.ampis import (
    AMPISCollector,
    AMPISCommodity,
    AMPISPrice,
)


AMPIS_SOURCE_NAME = (
    "Agriculture Market Price Information System (AMPIS)"
)

AMPIS_SOURCE_URL = "https://ampis.gov.np/"

AMPIS_SOURCE_TYPE = "government_price"

AMPIS_SOURCE_CODE = "AMPIS"

AMPIS_SOURCE_DESCRIPTION = (
    "Nepal agricultural market price data from the "
    "Agriculture Market Price Information System."
)


class AMPISIngestor:
    """
    Ingest AMPIS commodity and market-price data
    into the KrishiRate database.

    AMPIS publishes the authoritative price date on
    each market page. The collector extracts that date
    and every Price record uses the source-published date
    rather than the machine's current date.

    Markets that return an empty AMPIS page without a
    published date or price table are reported as EMPTY,
    not FAILED.
    """

    def __init__(
        self,
        collector: AMPISCollector | None = None,
    ):
        self.collector = collector or AMPISCollector()

    # =========================================================
    # SOURCE
    # =========================================================

    def get_or_create_source(self) -> Source:
        """Get the AMPIS source or create it if necessary."""

        source = Source.query.filter_by(
            name=AMPIS_SOURCE_NAME,
        ).first()

        if source:
            return source

        source = Source(
            name=AMPIS_SOURCE_NAME,
            organization=(
                "Agriculture Market Price Information System"
            ),
            url=AMPIS_SOURCE_URL,
            source_type=AMPIS_SOURCE_TYPE,
            description=AMPIS_SOURCE_DESCRIPTION,
            is_active=True,
        )

        db.session.add(source)
        db.session.flush()

        return source

    # =========================================================
    # PRODUCT
    # =========================================================

    def get_or_create_product(
        self,
        commodity: AMPISCommodity,
        source: Source,
    ) -> tuple[Product, bool]:
        """
        Find or create an AMPIS product.

        AMPIS commodity code is treated as the stable
        external identity of the product.
        """

        product = Product.query.filter_by(
            source_id=source.id,
            source_code=commodity.code,
        ).first()

        if product:
            changed = False

            if product.name != commodity.name:
                product.name = commodity.name
                changed = True

            if product.nepali_name != commodity.name:
                product.nepali_name = commodity.name
                changed = True

            if changed:
                product.updated_at = datetime.utcnow()
                db.session.flush()

            return product, False

        product = Product(
            name=commodity.name,
            nepali_name=commodity.name,
            source_code=commodity.code,
            source_id=source.id,
            category="Agricultural Commodity",
            is_active=True,
        )

        db.session.add(product)
        db.session.flush()

        return product, True

    # =========================================================
    # MARKET
    # =========================================================

    def get_market(
        self,
        market_id: int,
        source: Source,
    ) -> Market | None:
        """Get an existing AMPIS market by database ID."""

        return Market.query.filter_by(
            id=market_id,
            source_id=source.id,
            source_code=AMPIS_SOURCE_CODE,
        ).first()

    # =========================================================
    # PRICE
    # =========================================================

    def price_exists(
        self,
        product: Product,
        market: Market,
        source: Source,
        price_date: date,
    ) -> bool:
        """Check whether the same price record already exists."""

        existing = Price.query.filter_by(
            product_id=product.id,
            market_id=market.id,
            source_id=source.id,
            price_date=price_date,
        ).first()

        return existing is not None

    def create_price(
        self,
        price: AMPISPrice,
        product: Product,
        market: Market,
        source: Source,
        source_reference: str,
    ) -> Price | None:
        """Insert a price record unless it already exists."""

        if self.price_exists(
            product=product,
            market=market,
            source=source,
            price_date=price.price_date,
        ):
            return None

        record = Price(
            product_id=product.id,
            market_id=market.id,
            source_id=source.id,
            min_price=price.minimum,
            max_price=price.maximum,
            average_price=price.average,
            unit=price.unit,
            price_date=price.price_date,
            collected_at=datetime.utcnow(),
            source_reference=source_reference,
            freshness="RECENT",
        )

        try:
            with db.session.begin_nested():
                db.session.add(record)
                db.session.flush()

        except IntegrityError:
            return None

        return record

    # =========================================================
    # SINGLE MARKET INGESTION
    # =========================================================

    def ingest_market(
        self,
        market: Market,
        price_date: date | None = None,
        source: Source | None = None,
        commodities: list[AMPISCommodity] | None = None,
    ) -> dict:
        """
        Ingest prices for one synchronized AMPIS market.

        The supplied price_date remains for backwards
        compatibility. The AMPIS page date is authoritative.
        """

        source = source or self.get_or_create_source()

        if market.source_id != source.id:
            raise ValueError(
                f"Market '{market.name}' does not belong "
                "to the AMPIS source."
            )

        if not market.price_url:
            return {
                "market": market.name,
                "market_id": market.id,
                "status": "NO_PRICE_URL",
                "source_date": None,
                "commodities": 0,
                "prices": 0,
                "products_created": 0,
                "prices_created": 0,
                "prices_skipped": 0,
                "unmatched_prices": 0,
            }

        if commodities is None:
            commodities = self.collector.fetch_commodities()

        commodity_map = {
            commodity.code: commodity
            for commodity in commodities
        }

        html = self.collector.fetch(
            market.price_url
        )

        # -----------------------------------------------------
        # AMPIS SOURCE DATE + PRICE DATA
        # -----------------------------------------------------

        try:
            prices = self.collector.parse_price_page(
                html,
                price_date=price_date,
                commodities=commodities,
            )

        except ValueError as exc:
            message = str(exc)

            if message == "AMPIS source date is empty":
                return {
                    "market": market.name,
                    "market_id": market.id,
                    "status": "EMPTY",
                    "source_date": None,
                    "commodities": len(commodities),
                    "prices": 0,
                    "products_created": 0,
                    "prices_created": 0,
                    "prices_skipped": 0,
                    "unmatched_prices": 0,
                    "reason": (
                        "AMPIS returned no published "
                        "price date or price data."
                    ),
                }

            raise

        # -----------------------------------------------------
        # NO PRICES
        # -----------------------------------------------------

        if not prices:
            return {
                "market": market.name,
                "market_id": market.id,
                "status": "EMPTY",
                "source_date": None,
                "commodities": len(commodities),
                "prices": 0,
                "products_created": 0,
                "prices_created": 0,
                "prices_skipped": 0,
                "unmatched_prices": 0,
                "reason": (
                    "AMPIS returned no price records."
                ),
            }

        source_date = prices[0].price_date

        products_created = 0
        prices_created = 0
        prices_skipped = 0
        unmatched_prices = 0

        # -----------------------------------------------------
        # INGEST PRICES
        # -----------------------------------------------------

        for price in prices:

            if not price.commodity_code:
                unmatched_prices += 1
                continue

            commodity = commodity_map.get(
                price.commodity_code
            )

            if not commodity:
                unmatched_prices += 1
                continue

            product, was_created = (
                self.get_or_create_product(
                    commodity=commodity,
                    source=source,
                )
            )

            if was_created:
                products_created += 1

            record = self.create_price(
                price=price,
                product=product,
                market=market,
                source=source,
                source_reference=market.price_url,
            )

            if record:
                prices_created += 1
            else:
                prices_skipped += 1

        return {
            "market": market.name,
            "market_id": market.id,
            "status": "SUCCESS",
            "source_date": source_date.isoformat(),
            "commodities": len(commodities),
            "prices": len(prices),
            "products_created": products_created,
            "prices_created": prices_created,
            "prices_skipped": prices_skipped,
            "unmatched_prices": unmatched_prices,
        }

    # =========================================================
    # LEGACY SINGLE-PAGE INGESTION
    # =========================================================

    def ingest_market_prices(
        self,
        market_name: str,
        price_url: str,
        price_date: date | None = None,
    ) -> dict:
        """
        Backward-compatible single-market ingestion method.

        The supplied price_date remains for compatibility,
        but the AMPIS page's published date is authoritative.
        """

        source = self.get_or_create_source()

        market = Market.query.filter_by(
            name=market_name,
            source_id=source.id,
        ).first()

        if not market:
            market = Market(
                name=market_name,
                market_type="Agricultural Market",
                source_id=source.id,
                source_code=AMPIS_SOURCE_CODE,
                price_url=price_url,
                is_active=True,
            )

            db.session.add(market)
            db.session.flush()

        elif not market.price_url:
            market.price_url = price_url
            db.session.flush()

        commodities = self.collector.fetch_commodities()

        commodity_map = {
            commodity.code: commodity
            for commodity in commodities
        }

        html = self.collector.fetch(
            price_url
        )

        try:
            prices = self.collector.parse_price_page(
                html,
                price_date=price_date,
                commodities=commodities,
            )

        except ValueError as exc:
            if str(exc) == "AMPIS source date is empty":
                db.session.commit()

                return {
                    "status": "EMPTY",
                    "source_date": None,
                    "commodities": len(commodities),
                    "prices": 0,
                    "products_created": 0,
                    "prices_created": 0,
                    "prices_skipped": 0,
                    "unmatched_prices": 0,
                    "reason": (
                        "AMPIS returned no published "
                        "price date or price data."
                    ),
                }

            raise

        products_created = 0
        prices_created = 0
        prices_skipped = 0
        unmatched_prices = 0

        source_date = None

        if prices:
            source_date = prices[0].price_date

        for price in prices:

            if not price.commodity_code:
                unmatched_prices += 1
                continue

            commodity = commodity_map.get(
                price.commodity_code
            )

            if not commodity:
                unmatched_prices += 1
                continue

            product, was_created = (
                self.get_or_create_product(
                    commodity=commodity,
                    source=source,
                )
            )

            if was_created:
                products_created += 1

            record = self.create_price(
                price=price,
                product=product,
                market=market,
                source=source,
                source_reference=price_url,
            )

            if record:
                prices_created += 1
            else:
                prices_skipped += 1

        db.session.commit()

        now = datetime.utcnow()

        source.last_checked_at = now
        source.last_success_at = now

        db.session.commit()

        return {
            "status": "SUCCESS",
            "source_date": (
                source_date.isoformat()
                if source_date
                else None
            ),
            "commodities": len(commodities),
            "prices": len(prices),
            "products_created": products_created,
            "prices_created": prices_created,
            "prices_skipped": prices_skipped,
            "unmatched_prices": unmatched_prices,
        }

    # =========================================================
    # ALL MARKETS
    # =========================================================

    def ingest_all_markets(
        self,
        price_date: date | None = None,
    ) -> dict:
        """
        Ingest prices from every synchronized AMPIS market.

        Each market's AMPIS page supplies its own authoritative
        price date.

        Empty AMPIS feeds are tracked separately from failures.
        """

        source = self.get_or_create_source()

        markets = (
            Market.query
            .filter_by(
                source_id=source.id,
                source_code=AMPIS_SOURCE_CODE,
                is_active=True,
            )
            .order_by(Market.name)
            .all()
        )

        if not markets:
            raise RuntimeError(
                "No AMPIS markets found. "
                "Run AMPIS market synchronization first."
            )

        # -----------------------------------------------------
        # FETCH COMMODITY CATALOG ONCE
        # -----------------------------------------------------

        commodities = self.collector.fetch_commodities()

        results = []

        total_prices = 0
        total_created = 0
        total_skipped = 0
        total_products_created = 0
        total_unmatched = 0

        successful_markets = 0
        empty_markets = 0
        failed_markets = 0

        source_dates: set[date] = set()

        # -----------------------------------------------------
        # PROCESS EACH MARKET
        # -----------------------------------------------------

        for market in markets:

            try:
                result = self.ingest_market(
                    market=market,
                    price_date=price_date,
                    source=source,
                    commodities=commodities,
                )

                results.append(result)

                if result["status"] == "SUCCESS":
                    successful_markets += 1

                elif result["status"] == "EMPTY":
                    empty_markets += 1

                elif result["status"] in {
                    "NO_PRICE_URL",
                }:
                    empty_markets += 1

                if result.get("source_date"):
                    source_dates.add(
                        date.fromisoformat(
                            result["source_date"]
                        )
                    )

                total_prices += result["prices"]
                total_created += result["prices_created"]
                total_skipped += result["prices_skipped"]

                total_products_created += (
                    result["products_created"]
                )

                total_unmatched += (
                    result["unmatched_prices"]
                )

                db.session.commit()

            except Exception as exc:
                db.session.rollback()

                failed_markets += 1

                results.append(
                    {
                        "market": market.name,
                        "market_id": market.id,
                        "status": "FAILED",
                        "source_date": None,
                        "error": str(exc),
                    }
                )

        # -----------------------------------------------------
        # SOURCE HEALTH
        # -----------------------------------------------------

        source.last_checked_at = datetime.utcnow()

        if failed_markets == 0:
            source.last_success_at = datetime.utcnow()

        db.session.commit()

        # -----------------------------------------------------
        # SOURCE DATE SUMMARY
        # -----------------------------------------------------

        if len(source_dates) == 1:
            reported_price_date = (
                next(iter(source_dates)).isoformat()
            )

        elif len(source_dates) > 1:
            reported_price_date = "multiple"

        else:
            reported_price_date = (
                price_date.isoformat()
                if price_date
                else None
            )

        return {
            "price_date": reported_price_date,
            "source_dates": sorted(
                source_date.isoformat()
                for source_date in source_dates
            ),
            "markets": len(markets),
            "successful_markets": successful_markets,
            "empty_markets": empty_markets,
            "failed_markets": failed_markets,
            "commodities": len(commodities),
            "prices_found": total_prices,
            "prices_created": total_created,
            "prices_skipped": total_skipped,
            "products_created": total_products_created,
            "unmatched_prices": total_unmatched,
            "results": results,
        }

    # =========================================================
    # CLEANUP
    # =========================================================

    def close(self) -> None:
        """Close the collector session."""

        self.collector.close()

    def __enter__(
        self,
    ) -> "AMPISIngestor":

        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ) -> None:

        self.close()
