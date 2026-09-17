from datetime import datetime

from app.extensions import db


class Source(db.Model):
    __tablename__ = "sources"

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(
        db.String(200),
        nullable=False,
        unique=True,
        index=True,
    )

    organization = db.Column(
        db.String(200),
        nullable=True,
        index=True,
    )

    url = db.Column(
        db.String(500),
        nullable=False,
    )

    source_type = db.Column(
        db.String(100),
        nullable=False,
        index=True,
    )

    description = db.Column(
        db.Text,
        nullable=True,
    )

    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
        index=True,
    )

    last_checked_at = db.Column(
        db.DateTime,
        nullable=True,
    )

    last_success_at = db.Column(
        db.DateTime,
        nullable=True,
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

    def __repr__(self):
        return f"<Source {self.name}>"