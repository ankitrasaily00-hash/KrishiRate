from flask import Blueprint, jsonify, request
from sqlalchemy import func

from app.extensions import db
from app.models import Market, Price, Product
from app.services.price_engine import PriceEngine


api_bp = Blueprint(
    "api",
    __name__,
    url_prefix="/api",
)


# ==============================================================
# DASHBOARD
# ==============================================================

@api_bp.get("/dashboard")
def get_dashboard():
    active_markets = (
        Market.query
        .filter_by(is_active=True)
        .count()
    )

    active_products = (
        Product.query
        .filter_by(is_active=True)
        .count()
    )

    total_price_records = Price.query.count()

    latest_price_date = (
        db.session.query(
            func.max(Price.price_date)
        )
        .scalar()
    )

    latest_prices = (
        Price.query
        .order_by(
            Price.price_date.desc(),
            Price.collected_at.desc(),
            Price.id.desc(),
        )
        .limit(8)
        .all()
    )

    latest_source = None

    if latest_prices:
        source = latest_prices[0].source

        if source:
            latest_source = {
                "id": source.id,
                "name": source.name,
                "organization": source.organization,
                "url": source.url,
            }

    return jsonify({
        "success": True,
        "statistics": {
            "active_markets": active_markets,
            "active_products": active_products,
            "total_price_records": total_price_records,
            "latest_price_date": (
                latest_price_date.isoformat()
                if latest_price_date
                else None
            ),
        },
        "latest_source": latest_source,
        "latest_prices": [
            PriceEngine.price_to_dict(price)
            for price in latest_prices
        ],
    })


# ==============================================================
# LATEST PRICES
# ==============================================================

@api_bp.get("/prices/latest")
def get_latest_prices():
    """
    Return the latest available price for each
    product + market + source combination.

    This endpoint is designed for the Prices page so
    the frontend does not need one API request per product.
    """

    prices = (
        Price.query
        .join(
            Product,
            Price.product_id == Product.id,
        )
        .join(
            Market,
            Price.market_id == Market.id,
        )
        .filter(
            Product.is_active.is_(True),
            Market.is_active.is_(True),
        )
        .order_by(
            Price.product_id.asc(),
            Price.market_id.asc(),
            Price.source_id.asc(),
            Price.price_date.desc(),
            Price.collected_at.desc(),
            Price.id.desc(),
        )
        .all()
    )

    latest_prices = {}
    
    for price in prices:
        key = (
            price.product_id,
            price.market_id,
            price.source_id,
        )

        if key not in latest_prices:
            latest_prices[key] = price

    result = [
        PriceEngine.price_to_dict(price)
        for price in latest_prices.values()
    ]

    result.sort(
        key=lambda item: (
            item.get("product") or "",
            item.get("market") or "",
        )
    )

    return jsonify({
        "success": True,
        "count": len(result),
        "prices": result,
    })


# ==============================================================
# PRODUCT SEARCH / CATALOG
# ==============================================================

@api_bp.get("/products/search")
def search_products():
    query = request.args.get("q", "").strip()

    if query:
        products = PriceEngine.search_products(query)
    else:
        products = (
            Product.query
            .filter_by(is_active=True)
            .order_by(Product.name.asc())
            .limit(200)
            .all()
        )

    return jsonify({
        "success": True,
        "query": query or None,
        "count": len(products),
        "products": [
            {
                "id": product.id,
                "name": product.name,
                "nepali_name": product.nepali_name,
                "english_name": product.english_name,
                "source_code": product.source_code,
                "category": product.category,
                "subcategory": product.subcategory,
                "variety": product.variety,
                "unit": product.unit,
            }
            for product in products
        ],
    })


# ==============================================================
# PRODUCT DETAILS
# ==============================================================

@api_bp.get("/products/<int:product_id>")
def get_product(product_id):
    summary = PriceEngine.get_product_summary(
        product_id
    )

    if summary is None:
        return jsonify({
            "success": False,
            "error": "Product not found.",
        }), 404

    return jsonify({
        "success": True,
        "product": summary["product"],
        "statistics": summary["statistics"],
        "markets": summary["markets"],
    })


# ==============================================================
# PRODUCT PRICE HISTORY
# ==============================================================

@api_bp.get("/products/<int:product_id>/history")
def get_product_history(product_id):
    days = request.args.get(
        "days",
        default=30,
        type=int,
    )

    if days <= 0:
        return jsonify({
            "success": False,
            "error": "Days must be greater than 0.",
        }), 400

    if days > 365:
        return jsonify({
            "success": False,
            "error": "Maximum history period is 365 days.",
        }), 400

    product = PriceEngine.get_product(
        product_id
    )

    if product is None:
        return jsonify({
            "success": False,
            "error": "Product not found.",
        }), 404

    history = PriceEngine.get_price_history(
        product_id=product_id,
        days=days,
    )

    return jsonify({
        "success": True,
        "product": {
            "id": product.id,
            "name": product.name,
            "nepali_name": product.nepali_name,
            "english_name": product.english_name,
            "source_code": product.source_code,
        },
        "period": {
            "days": days,
            "records": len(history),
        },
        "history": [
            PriceEngine.price_to_dict(price)
            for price in history
        ],
    })


# ==============================================================
# MARKETS
# ==============================================================

@api_bp.get("/markets")
def get_markets():
    markets = (
        Market.query
        .filter_by(is_active=True)
        .order_by(Market.name.asc())
        .all()
    )

    return jsonify({
        "success": True,
        "count": len(markets),
        "markets": [
            {
                "id": market.id,
                "name": market.name,
                "nepali_name": market.nepali_name,
                "province": market.province,
                "district": market.district,
                "municipality": market.municipality,
                "location": market.location,
                "market_type": market.market_type,
                "source_id": market.source_id,
                "source_code": market.source_code,
                "market_uuid": market.market_uuid,
                "market_url": market.market_url,
                "price_url": market.price_url,
                "is_active": market.is_active,
            }
            for market in markets
        ],
    })


# ==============================================================
# MARKET LATEST PRICES
# ==============================================================

@api_bp.get("/markets/<int:market_id>/prices")
def get_market_prices(market_id):
    market = (
        Market.query
        .filter_by(
            id=market_id,
            is_active=True,
        )
        .first()
    )

    if market is None:
        return jsonify({
            "success": False,
            "error": "Market not found.",
        }), 404

    prices = PriceEngine.get_market_latest_prices(
        market_id=market_id,
    )

    return jsonify({
        "success": True,
        "market": {
            "id": market.id,
            "name": market.name,
            "nepali_name": market.nepali_name,
            "province": market.province,
            "district": market.district,
            "municipality": market.municipality,
            "location": market.location,
            "market_type": market.market_type,
            "source_id": market.source_id,
            "source_code": market.source_code,
            "market_uuid": market.market_uuid,
            "market_url": market.market_url,
            "price_url": market.price_url,
        },
        "count": len(prices),
        "prices": [
            PriceEngine.price_to_dict(price)
            for price in prices
        ],
    })