
from datetime import datetime

from app.extensions import db


class Price(db.Model):
    __tablename__ = "prices"

    __table_args__ = (
        db.UniqueConstraint(
            "product_id",
            "market_id",
            "source_id",
            "price_date",
            name="uq_prices_product_market_source_date",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)

    product_id = db.Column(
        db.Integer,
        db.ForeignKey("products.id"),
        nullable=False,
        index=True,
    )

    market_id = db.Column(
        db.Integer,
        db.ForeignKey("markets.id"),
        nullable=True,
        index=True,
    )

    source_id = db.Column(
        db.Integer,
        db.ForeignKey("sources.id"),
        nullable=False,
        index=True,
    )

    min_price = db.Column(
        db.Numeric(12, 2),
        nullable=True,
    )

    max_price = db.Column(
        db.Numeric(12, 2),
        nullable=True,
    )

    average_price = db.Column(
        db.Numeric(12, 2),
        nullable=True,
    )

    unit = db.Column(
        db.String(50),
        nullable=False,
    )

    price_date = db.Column(
        db.Date,
        nullable=False,
        index=True,
    )

    collected_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )

    source_reference = db.Column(
        db.String(500),
        nullable=True,
    )

    freshness = db.Column(
        db.String(50),
        nullable=False,
        default="RECENT",
        index=True,
    )

    notes = db.Column(
        db.Text,
        nullable=True,
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    product = db.relationship(
        "Product",
        backref=db.backref("prices", lazy=True),
    )

    market = db.relationship(
        "Market",
        backref=db.backref("prices", lazy=True),
    )

    source = db.relationship(
        "Source",
        backref=db.backref("prices", lazy=True),
    )

    def __repr__(self):
        return (
            f"<Price product={self.product_id} "
            f"market={self.market_id} "
            f"date={self.price_date}>"
        )
