
from datetime import datetime

from app.extensions import db


class Market(db.Model):
    __tablename__ = "markets"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    name = db.Column(
        db.String(150),
        nullable=False,
        unique=True,
        index=True,
    )

    nepali_name = db.Column(
        db.String(150),
        nullable=True,
    )

    province = db.Column(
        db.String(100),
        nullable=True,
        index=True,
    )

    district = db.Column(
        db.String(100),
        nullable=True,
        index=True,
    )

    municipality = db.Column(
        db.String(100),
        nullable=True,
    )

    location = db.Column(
        db.String(255),
        nullable=True,
    )

    market_type = db.Column(
        db.String(100),
        nullable=True,
        index=True,
    )

    # ---------------------------------------------------------
    # SOURCE IDENTITY
    # ---------------------------------------------------------

    source_id = db.Column(
        db.Integer,
        db.ForeignKey("sources.id"),
        nullable=True,
        index=True,
    )

    source_code = db.Column(
        db.String(100),
        nullable=True,
        index=True,
    )

    # ---------------------------------------------------------
    # EXTERNAL MARKET IDENTITY
    # ---------------------------------------------------------

    market_uuid = db.Column(
        db.String(100),
        nullable=True,
        index=True,
    )

    market_url = db.Column(
        db.String(500),
        nullable=True,
    )

    price_url = db.Column(
        db.String(500),
        nullable=True,
    )

    # ---------------------------------------------------------
    # STATUS
    # ---------------------------------------------------------

    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
        index=True,
    )

    # ---------------------------------------------------------
    # TIMESTAMPS
    # ---------------------------------------------------------

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # ---------------------------------------------------------
    # RELATIONSHIPS
    # ---------------------------------------------------------

    source = db.relationship(
        "Source",
        backref=db.backref(
            "markets",
            lazy=True,
        ),
    )

    # ---------------------------------------------------------
    # REPRESENTATION
    # ---------------------------------------------------------

    def __repr__(self):
        return f"<Market {self.name}>"

