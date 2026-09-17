
"""add source identity and external URLs to markets

Revision ID: 20b05acced37
Revises: 2fd0fcde5bbb
Create Date: 2026-09-17 14:05:39.453797

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20b05acced37"
down_revision = "2fd0fcde5bbb"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table(
        "markets",
        schema=None,
    ) as batch_op:

        batch_op.add_column(
            sa.Column(
                "source_id",
                sa.Integer(),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "source_code",
                sa.String(length=100),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "market_uuid",
                sa.String(length=100),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "market_url",
                sa.String(length=500),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "price_url",
                sa.String(length=500),
                nullable=True,
            )
        )

        batch_op.create_index(
            "ix_markets_market_uuid",
            ["market_uuid"],
            unique=False,
        )

        batch_op.create_index(
            "ix_markets_source_code",
            ["source_code"],
            unique=False,
        )

        batch_op.create_index(
            "ix_markets_source_id",
            ["source_id"],
            unique=False,
        )

        batch_op.create_foreign_key(
            "fk_markets_source_id",
            "sources",
            ["source_id"],
            ["id"],
        )


def downgrade():
    with op.batch_alter_table(
        "markets",
        schema=None,
    ) as batch_op:

        batch_op.drop_constraint(
            "fk_markets_source_id",
            type_="foreignkey",
        )

        batch_op.drop_index(
            "ix_markets_source_id",
        )

        batch_op.drop_index(
            "ix_markets_source_code",
        )

        batch_op.drop_index(
            "ix_markets_market_uuid",
        )

        batch_op.drop_column(
            "price_url",
        )

        batch_op.drop_column(
            "market_url",
        )

        batch_op.drop_column(
            "market_uuid",
        )

        batch_op.drop_column(
            "source_code",
        )

        batch_op.drop_column(
            "source_id",
        )

