from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from app.models import Market, Price, Product, Source


class PriceEngine:
    """
    Read-only price intelligence service.

    Handles:
        - Product search
        - Latest prices
        - Market comparison
        - Market price listings
        - Current price statistics
        - Price history
        - Source attribution
        - Freshness calculation
        - API serialization
    """

    # ==============================================================
    # PRODUCT
    # ==============================================================

    @staticmethod
    def get_product(
        product_id: int,
    ) -> Optional[Product]:
        """Return an active product by ID."""

        return Product.query.filter(
            Product.id == product_id,
            Product.is_active.is_(True),
        ).first()

    @staticmethod
    def search_products(
        query: str,
        limit: int = 20,
    ) -> list[Product]:
        """Search products by common product fields."""

        query = (query or "").strip()

        if not query:
            return []

        pattern = f"%{query}%"

        return (
            Product.query
            .filter(
                Product.is_active.is_(True),
                (
                    Product.name.ilike(pattern)
                    | Product.nepali_name.ilike(pattern)
                    | Product.english_name.ilike(pattern)
                    | Product.source_code.ilike(pattern)
                    | Product.aliases.ilike(pattern)
                ),
            )
            .order_by(Product.name.asc())
            .limit(limit)
            .all()
        )

    # ==============================================================
    # LATEST PRICE
    # ==============================================================

    @staticmethod
    def get_latest_price(
        product_id: int,
        market_id: Optional[int] = None,
        source_id: Optional[int] = None,
    ) -> Optional[Price]:
        """
        Return the latest available price record.

        Ordering:
            1. price_date
            2. collected_at
            3. record ID
        """

        query = Price.query.filter(
            Price.product_id == product_id,
        )

        if market_id is not None:
            query = query.filter(
                Price.market_id == market_id,
            )

        if source_id is not None:
            query = query.filter(
                Price.source_id == source_id,
            )

        return (
            query
            .order_by(
                Price.price_date.desc(),
                Price.collected_at.desc(),
                Price.id.desc(),
            )
            .first()
        )

    @staticmethod
    def get_latest_prices(
        product_id: int,
        source_id: Optional[int] = None,
    ) -> list[Price]:
        """
        Return the latest price for each market
        for a product.
        """

        query = Price.query.filter(
            Price.product_id == product_id,
        )

        if source_id is not None:
            query = query.filter(
                Price.source_id == source_id,
            )

        prices = (
            query
            .order_by(
                Price.market_id.asc(),
                Price.price_date.desc(),
                Price.collected_at.desc(),
                Price.id.desc(),
            )
            .all()
        )

        latest_by_market: dict[Optional[int], Price] = {}

        for price in prices:
            if price.market_id not in latest_by_market:
                latest_by_market[price.market_id] = price

        return list(latest_by_market.values())

    @staticmethod
    def get_market_latest_prices(
        market_id: int,
        source_id: Optional[int] = None,
    ) -> list[Price]:
        """
        Return the latest price for each product
        available at a market.
        """

        query = Price.query.filter(
            Price.market_id == market_id,
        )

        if source_id is not None:
            query = query.filter(
                Price.source_id == source_id,
            )

        prices = (
            query
            .order_by(
                Price.product_id.asc(),
                Price.price_date.desc(),
                Price.collected_at.desc(),
                Price.id.desc(),
            )
            .all()
        )

        latest_by_product: dict[int, Price] = {}

        for price in prices:
            if price.product_id not in latest_by_product:
                latest_by_product[price.product_id] = price

        return list(latest_by_product.values())

    # ==============================================================
    # MARKET COMPARISON
    # ==============================================================

    @classmethod
    def compare_markets(
        cls,
        product_id: int,
        source_id: Optional[int] = None,
    ) -> list[dict]:
        """Compare the latest product price across markets."""

        prices = cls.get_latest_prices(
            product_id=product_id,
            source_id=source_id,
        )

        return [
            cls.price_to_dict(price)
            for price in prices
        ]

    # ==============================================================
    # CURRENT STATISTICS
    # ==============================================================

    @classmethod
    def get_current_statistics(
        cls,
        product_id: int,
        source_id: Optional[int] = None,
    ) -> dict:
        """
        Calculate current statistics using the latest
        available price from each market.
        """

        prices = cls.get_latest_prices(
            product_id=product_id,
            source_id=source_id,
        )

        if not prices:
            return {
                "minimum_price": None,
                "maximum_price": None,
                "average_price": None,
                "market_count": 0,
                "unit": None,
            }

        minimums = [
            price.min_price
            for price in prices
            if price.min_price is not None
        ]

        maximums = [
            price.max_price
            for price in prices
            if price.max_price is not None
        ]

        averages = [
            price.average_price
            for price in prices
            if price.average_price is not None
        ]

        units = [
            price.unit
            for price in prices
            if price.unit
        ]

        overall_average = None

        if averages:
            overall_average = (
                sum(averages, Decimal("0"))
                / Decimal(len(averages))
            )

        return {
            "minimum_price": (
                min(minimums)
                if minimums
                else None
            ),
            "maximum_price": (
                max(maximums)
                if maximums
                else None
            ),
            "average_price": overall_average,
            "market_count": len(prices),
            "unit": units[0] if units else None,
        }

    # ==============================================================
    # PRICE HISTORY
    # ==============================================================

    @staticmethod
    def get_price_history(
        product_id: int,
        market_id: Optional[int] = None,
        days: int = 30,
        source_id: Optional[int] = None,
    ) -> list[Price]:
        """
        Return historical price records.

        Examples:
            7 days
            30 days
            90 days
            365 days
        """

        if days <= 0:
            raise ValueError(
                "days must be greater than zero."
            )

        today = date.today()

        start_date = today - timedelta(
            days=days - 1
        )

        query = Price.query.filter(
            Price.product_id == product_id,
            Price.price_date >= start_date,
            Price.price_date <= today,
        )

        if market_id is not None:
            query = query.filter(
                Price.market_id == market_id,
            )

        if source_id is not None:
            query = query.filter(
                Price.source_id == source_id,
            )

        return (
            query
            .order_by(
                Price.price_date.asc(),
                Price.market_id.asc(),
                Price.collected_at.asc(),
            )
            .all()
        )

    @classmethod
    def get_7_day_history(
        cls,
        product_id: int,
        market_id: Optional[int] = None,
        source_id: Optional[int] = None,
    ) -> list[Price]:
        """Return the last 7 days of price history."""

        return cls.get_price_history(
            product_id=product_id,
            market_id=market_id,
            days=7,
            source_id=source_id,
        )

    @classmethod
    def get_30_day_history(
        cls,
        product_id: int,
        market_id: Optional[int] = None,
        source_id: Optional[int] = None,
    ) -> list[Price]:
        """Return the last 30 days of price history."""

        return cls.get_price_history(
            product_id=product_id,
            market_id=market_id,
            days=30,
            source_id=source_id,
        )

    @classmethod
    def get_3_month_history(
        cls,
        product_id: int,
        market_id: Optional[int] = None,
        source_id: Optional[int] = None,
    ) -> list[Price]:
        """Return approximately 3 months of history."""

        return cls.get_price_history(
            product_id=product_id,
            market_id=market_id,
            days=90,
            source_id=source_id,
        )

    @classmethod
    def get_1_year_history(
        cls,
        product_id: int,
        market_id: Optional[int] = None,
        source_id: Optional[int] = None,
    ) -> list[Price]:
        """Return approximately 1 year of history."""

        return cls.get_price_history(
            product_id=product_id,
            market_id=market_id,
            days=365,
            source_id=source_id,
        )

    # ==============================================================
    # PRODUCT SUMMARY
    # ==============================================================

    @classmethod
    def get_product_summary(
        cls,
        product_id: int,
        source_id: Optional[int] = None,
    ) -> Optional[dict]:
        """
        Return product information, statistics,
        and latest market prices.
        """

        product = cls.get_product(product_id)

        if not product:
            return None

        prices = cls.get_latest_prices(
            product_id=product_id,
            source_id=source_id,
        )

        statistics = cls.get_current_statistics(
            product_id=product_id,
            source_id=source_id,
        )

        return {
            "product": {
                "id": product.id,
                "name": product.name,
                "nepali_name": product.nepali_name,
                "english_name": product.english_name,
                "category": product.category,
                "subcategory": product.subcategory,
                "variety": product.variety,
                "unit": product.unit,
                "source_code": product.source_code,
            },
            "statistics": statistics,
            "markets": [
                cls.price_to_dict(price)
                for price in prices
            ],
        }

    # ==============================================================
    # FRESHNESS
    # ==============================================================

    @staticmethod
    def get_freshness(
        price_date: Optional[date],
    ) -> str:
        """
        Calculate freshness from the actual price date.

        LIVE:
            Price is from today.

        RECENT:
            Price is 1-3 days old.

        STALE:
            Price is 4-30 days old.

        HISTORICAL:
            Price is more than 30 days old.
        """

        if price_date is None:
            return "UNKNOWN"

        age = (
            date.today() - price_date
        ).days

        if age <= 0:
            return "LIVE"

        if age <= 3:
            return "RECENT"

        if age <= 30:
            return "STALE"

        return "HISTORICAL"

    # ==============================================================
    # SOURCE
    # ==============================================================

    @staticmethod
    def get_source(
        source_id: int,
    ) -> Optional[Source]:
        """Return a source by ID."""

        return Source.query.filter(
            Source.id == source_id,
        ).first()

    @staticmethod
    def get_market(
        market_id: int,
    ) -> Optional[Market]:
        """Return a market by ID."""

        return Market.query.filter(
            Market.id == market_id,
        ).first()

    # ==============================================================
    # SERIALIZATION
    # ==============================================================

    @classmethod
    def price_to_dict(
        cls,
        price: Price,
    ) -> dict:
        """
        Convert a Price model into a complete dictionary
        suitable for APIs and frontend usage.
        """

        product = price.product
        market = price.market
        source = price.source

        return {
            # ------------------------------------------------------
            # PRICE
            # ------------------------------------------------------

            "price_id": price.id,

            "minimum": price.min_price,
            "maximum": price.max_price,
            "average": price.average_price,
            "unit": price.unit,

            "price_date": (
                price.price_date.isoformat()
                if price.price_date
                else None
            ),

            "collected_at": (
                price.collected_at.isoformat()
                if price.collected_at
                else None
            ),

            "freshness": cls.get_freshness(
                price.price_date
            ),

            # ------------------------------------------------------
            # PRODUCT
            # ------------------------------------------------------

            "product_id": price.product_id,

            "product": (
                product.name
                if product
                else None
            ),

            "nepali_name": (
                product.nepali_name
                if product
                else None
            ),

            "english_name": (
                product.english_name
                if product
                else None
            ),

            "category": (
                product.category
                if product
                else None
            ),

            "subcategory": (
                product.subcategory
                if product
                else None
            ),

            "variety": (
                product.variety
                if product
                else None
            ),

            "product_source_code": (
                product.source_code
                if product
                else None
            ),

            # ------------------------------------------------------
            # MARKET
            # ------------------------------------------------------

            "market_id": price.market_id,

            "market": (
                market.name
                if market
                else None
            ),

            "district": (
                market.district
                if market
                else None
            ),

            "province": (
                market.province
                if market
                else None
            ),

            # ------------------------------------------------------
            # SOURCE
            # ------------------------------------------------------

            "source": (
                source.name
                if source
                else None
            ),

            "source_url": (
                source.url
                if source
                else None
            ),

            "source_reference": (
                price.source_reference
            ),
        }