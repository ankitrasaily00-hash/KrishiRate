from __future__ import annotations

from datetime import datetime

from app.extensions import db
from app.models import Market, Source
from app.services.collectors.ampis_markets import (
    AMPISMarket,
    AMPISMarketCollector,
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


class AMPISMarketSynchronizer:
    """
    Synchronize markets discovered from AMPIS
    into the KrishiRate database.
    """

    def __init__(
        self,
        collector: AMPISMarketCollector | None = None,
    ):
        self.collector = (
            collector
            or AMPISMarketCollector()
        )

    # ==========================================================
    # SOURCE
    # ==========================================================

    def get_or_create_source(self) -> Source:
        """Find or create the AMPIS source record."""

        source = Source.query.filter_by(
            name=AMPIS_SOURCE_NAME,
        ).first()

        organization = (
            "Agriculture Market Price Information System"
        )

        if source:
            changed = False

            if source.organization != organization:
                source.organization = organization
                changed = True

            if source.url != AMPIS_SOURCE_URL:
                source.url = AMPIS_SOURCE_URL
                changed = True

            if source.source_type != AMPIS_SOURCE_TYPE:
                source.source_type = AMPIS_SOURCE_TYPE
                changed = True

            if source.description != AMPIS_SOURCE_DESCRIPTION:
                source.description = AMPIS_SOURCE_DESCRIPTION
                changed = True

            if changed:
                source.updated_at = datetime.utcnow()
                db.session.flush()

            return source

        source = Source(
            name=AMPIS_SOURCE_NAME,
            organization=organization,
            url=AMPIS_SOURCE_URL,
            source_type=AMPIS_SOURCE_TYPE,
            description=AMPIS_SOURCE_DESCRIPTION,
            is_active=True,
        )

        db.session.add(source)
        db.session.flush()

        return source

    # ==========================================================
    # MARKET LOOKUP
    # ==========================================================

    def find_existing_market(
        self,
        market: AMPISMarket,
        source: Source,
    ) -> Market | None:
        """
        Find an existing market using stable AMPIS identity.

        Lookup order:

        1. AMPIS source + market UUID
        2. Existing market name
        """

        if market.market_uuid:
            existing = Market.query.filter_by(
                source_id=source.id,
                market_uuid=market.market_uuid,
            ).first()

            if existing:
                return existing

        existing = Market.query.filter_by(
            name=market.name,
        ).first()

        return existing

    # ==========================================================
    # MARKET
    # ==========================================================

    def get_or_create_market(
        self,
        market: AMPISMarket,
        source: Source,
    ) -> tuple[Market, bool]:
        """
        Find an existing market or create a new one.

        Returns:
            (market_record, created)
        """

        existing = self.find_existing_market(
            market=market,
            source=source,
        )

        if existing:
            changed = False

            # --------------------------------------------------
            # BASIC IDENTITY
            # --------------------------------------------------

            if market.name and existing.name != market.name:
                existing.name = market.name
                changed = True

            if (
                market.province
                and existing.province != market.province
            ):
                existing.province = market.province
                changed = True

            if (
                market.district
                and existing.district != market.district
            ):
                existing.district = market.district
                changed = True

            if (
                market.location
                and existing.location != market.location
            ):
                existing.location = market.location
                changed = True

            # --------------------------------------------------
            # SOURCE IDENTITY
            # --------------------------------------------------

            if existing.source_id != source.id:
                existing.source_id = source.id
                changed = True

            if existing.source_code != AMPIS_SOURCE_CODE:
                existing.source_code = AMPIS_SOURCE_CODE
                changed = True

            # --------------------------------------------------
            # AMPIS EXTERNAL IDENTITY
            # --------------------------------------------------

            if (
                market.market_uuid
                and existing.market_uuid != market.market_uuid
            ):
                existing.market_uuid = market.market_uuid
                changed = True

            if (
                market.market_url
                and existing.market_url != market.market_url
            ):
                existing.market_url = market.market_url
                changed = True

            if (
                market.price_url
                and existing.price_url != market.price_url
            ):
                existing.price_url = market.price_url
                changed = True

            # --------------------------------------------------
            # STATUS
            # --------------------------------------------------

            if not existing.market_type:
                existing.market_type = "Agricultural Market"
                changed = True

            if not existing.is_active:
                existing.is_active = True
                changed = True

            # --------------------------------------------------
            # SAVE
            # --------------------------------------------------

            if changed:
                existing.updated_at = datetime.utcnow()
                db.session.flush()

            return existing, False

        # ------------------------------------------------------
        # CREATE NEW MARKET
        # ------------------------------------------------------

        record = Market(
            name=market.name,
            province=market.province,
            district=market.district,
            location=market.location,
            market_type="Agricultural Market",
            source_id=source.id,
            source_code=AMPIS_SOURCE_CODE,
            market_uuid=market.market_uuid,
            market_url=market.market_url,
            price_url=market.price_url,
            is_active=True,
        )

        db.session.add(record)
        db.session.flush()

        return record, True

    # ==========================================================
    # SYNC
    # ==========================================================

    def sync(self) -> dict:
        """
        Discover AMPIS markets and synchronize them
        into the database.
        """

        source = self.get_or_create_source()

        discovered = self.collector.fetch_markets()

        created = 0
        existing = 0
        updated = 0

        for market in discovered:

            existing_before = self.find_existing_market(
                market=market,
                source=source,
            )

            previous_values = None

            if existing_before:
                previous_values = (
                    existing_before.source_id,
                    existing_before.source_code,
                    existing_before.market_uuid,
                    existing_before.market_url,
                    existing_before.price_url,
                    existing_before.province,
                    existing_before.district,
                    existing_before.location,
                )

            record, was_created = (
                self.get_or_create_market(
                    market=market,
                    source=source,
                )
            )

            if was_created:
                created += 1
                continue

            existing += 1

            if previous_values is not None:
                current_values = (
                    record.source_id,
                    record.source_code,
                    record.market_uuid,
                    record.market_url,
                    record.price_url,
                    record.province,
                    record.district,
                    record.location,
                )

                if previous_values != current_values:
                    updated += 1

        # ------------------------------------------------------
        # SOURCE HEALTH
        # ------------------------------------------------------

        now = datetime.utcnow()

        source.last_checked_at = now
        source.last_success_at = now

        db.session.commit()

        return {
            "discovered": len(discovered),
            "created": created,
            "existing": existing,
            "updated": updated,
            "source_id": source.id,
        }

    # ==========================================================
    # CLEANUP
    # ==========================================================

    def close(self) -> None:
        """Close the AMPIS market collector."""

        self.collector.close()

    def __enter__(
        self,
    ) -> "AMPISMarketSynchronizer":
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ) -> None:
        self.close()