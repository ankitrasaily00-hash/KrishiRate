
from datetime import datetime

from app.extensions import db


class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    name = db.Column(
        db.String(150),
        nullable=False,
        index=True,
    )

    nepali_name = db.Column(
        db.String(150),
        nullable=True,
        index=True,
    )

    english_name = db.Column(
        db.String(150),
        nullable=True,
        index=True,
    )

    source_code = db.Column(
        db.String(100),
        nullable=True,
        index=True,
    )

    source_id = db.Column(
        db.Integer,
        db.ForeignKey("sources.id"),
        nullable=True,
        index=True,
    )

    category = db.Column(
        db.String(100),
        nullable=False,
        index=True,
    )

    subcategory = db.Column(
        db.String(100),
        nullable=True,
        index=True,
    )

    variety = db.Column(
        db.String(150),
        nullable=True,
    )

    unit = db.Column(
        db.String(50),
        nullable=True,
    )

    aliases = db.Column(
        db.Text,
        nullable=True,
    )

    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
        index=True,
    )

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

    source = db.relationship(
        "Source",
        backref=db.backref("products", lazy=True),
    )

    def __repr__(self):
        return f"<Product {self.name}>"


