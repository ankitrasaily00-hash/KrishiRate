from app import create_app
from app.services.price_engine import PriceEngine


app = create_app()

with app.app_context():

    print()
    print("=" * 70)
    print("KRISHIRATE PRICE ENGINE TEST")
    print("=" * 70)

    # ---------------------------------------------------------
    # PRODUCT SEARCH
    # ---------------------------------------------------------

    products = PriceEngine.search_products("गोलभेंडा")

    print()
    print("PRODUCT SEARCH")
    print("Found:", len(products))

    for product in products[:5]:
        print(
            product.id,
            "|",
            product.name,
            "| source_code:",
            product.source_code,
        )

    if not products:
        raise RuntimeError(
            "Product search returned no results."
        )

    product = products[0]

    print()
    print("SELECTED PRODUCT:")
    print(product.id, product.name)

    # ---------------------------------------------------------
    # LATEST PRICE
    # ---------------------------------------------------------

    latest = PriceEngine.get_latest_price(
        product_id=product.id,
    )

    print()
    print("LATEST PRICE")

    if latest:
        print(
            "Market:",
            latest.market.name if latest.market else None,
        )
        print("Minimum:", latest.min_price)
        print("Maximum:", latest.max_price)
        print("Average:", latest.average_price)
        print("Unit:", latest.unit)
        print("Date:", latest.price_date)
        print(
            "Freshness:",
            PriceEngine.get_freshness(
                latest.price_date
            ),
        )
    else:
        print("NO LATEST PRICE")

    # ---------------------------------------------------------
    # MARKET COMPARISON
    # ---------------------------------------------------------

    comparison = PriceEngine.compare_markets(
        product_id=product.id,
    )

    print()
    print("MARKET COMPARISON")
    print("Markets:", len(comparison))

    for item in comparison:
        print(
            item["market"],
            "|",
            item["minimum"],
            "-",
            item["maximum"],
            "| avg:",
            item["average"],
            "|",
            item["price_date"],
            "|",
            item["freshness"],
        )

    # ---------------------------------------------------------
    # CURRENT STATISTICS
    # ---------------------------------------------------------

    statistics = PriceEngine.get_current_statistics(
        product_id=product.id,
    )

    print()
    print("CURRENT STATISTICS")

    for key, value in statistics.items():
        print(
            f"{key}:",
            value,
        )

    # ---------------------------------------------------------
    # HISTORY
    # ---------------------------------------------------------

    history = PriceEngine.get_30_day_history(
        product_id=product.id,
    )

    print()
    print("30-DAY HISTORY")
    print("Records:", len(history))

    for price in history[:10]:
        print(
            price.price_date,
            "|",
            price.market.name if price.market else None,
            "|",
            price.average_price,
        )

    # ---------------------------------------------------------
    # SUMMARY
    # ---------------------------------------------------------

    summary = PriceEngine.get_product_summary(
        product_id=product.id,
    )

    print()
    print("PRODUCT SUMMARY")

    print(
        "Product:",
        summary["product"]["name"],
    )

    print(
        "Market count:",
        summary["statistics"]["market_count"],
    )

    print(
        "Average:",
        summary["statistics"]["average_price"],
    )

    print(
        "Market prices:",
        len(summary["markets"]),
    )

    # ---------------------------------------------------------
    # SERIALIZATION
    # ---------------------------------------------------------

    if latest:
        serialized = PriceEngine.price_to_dict(
            latest
        )

        print()
        print("SERIALIZED PRICE")

        for key, value in serialized.items():
            print(
                f"{key}:",
                value,
            )

    print()
    print("=" * 70)
    print("PRICE ENGINE TEST COMPLETE")
    print("=" * 70)
