
"""add source identity to products

Revision ID: 2fd0fcde5bbb
Revises: e37ad10b197d
Create Date: 2026-09-17 13:32:58.825098
"""

from alembic import op
import sqlalchemy as sa


revision = "2fd0fcde5bbb"
down_revision = "e37ad10b197d"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("products", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "source_code",
                sa.String(length=100),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "source_id",
                sa.Integer(),
                nullable=True,
            )
        )

        batch_op.create_index(
            "ix_products_source_code",
            ["source_code"],
            unique=False,
        )

        batch_op.create_index(
            "ix_products_source_id",
            ["source_id"],
            unique=False,
        )

        batch_op.create_foreign_key(
            "fk_products_source_id",
            "sources",
            ["source_id"],
            ["id"],
        )


def downgrade():
    with op.batch_alter_table("products", schema=None) as batch_op:
        batch_op.drop_constraint(
            "fk_products_source_id",
            type_="foreignkey",
        )

        batch_op.drop_index(
            "ix_products_source_id",
        )

        batch_op.drop_index(
            "ix_products_source_code",
        )

        batch_op.drop_column("source_id")
        batch_op.drop_column("source_code")

