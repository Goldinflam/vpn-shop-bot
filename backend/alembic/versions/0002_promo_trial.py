"""promo codes, promo usages, trial flag, subscription_url

Revision ID: 0002_promo_trial
Revises: 0001_initial
Create Date: 2026-04-23 00:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002_promo_trial"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "trial_used",
            sa.Boolean(),
            server_default="0",
            nullable=False,
        ),
    )
    op.add_column(
        "subscriptions",
        sa.Column("subscription_url", sa.Text(), nullable=True),
    )
    op.create_table(
        "promo_codes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("is_trial", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("trial_days", sa.Integer(), nullable=True),
        sa.Column("trial_traffic_gb", sa.Integer(), nullable=True),
        sa.Column("discount_percent", sa.Integer(), nullable=True),
        sa.Column("usage_limit", sa.Integer(), nullable=True),
        sa.Column("used_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("per_user_limit", sa.Integer(), server_default="1", nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="1", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_promo_codes_code"),
    )
    op.create_table(
        "promo_usages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("promo_code_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("subscription_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["promo_code_id"], ["promo_codes.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["subscription_id"], ["subscriptions.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "promo_code_id", "user_id", name="uq_promo_usages_promo_user"
        ),
    )
    op.create_index(
        op.f("ix_promo_usages_promo_code_id"),
        "promo_usages",
        ["promo_code_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_promo_usages_user_id"),
        "promo_usages",
        ["user_id"],
        unique=False,
    )

    # Seed the two required trial promo codes.
    op.bulk_insert(
        sa.table(
            "promo_codes",
            sa.column("code", sa.String),
            sa.column("is_trial", sa.Boolean),
            sa.column("trial_days", sa.Integer),
            sa.column("trial_traffic_gb", sa.Integer),
            sa.column("discount_percent", sa.Integer),
            sa.column("usage_limit", sa.Integer),
            sa.column("used_count", sa.Integer),
            sa.column("per_user_limit", sa.Integer),
            sa.column("is_active", sa.Boolean),
        ),
        [
            {
                "code": "FREE1",
                "is_trial": True,
                "trial_days": 1,
                "trial_traffic_gb": 2,
                "discount_percent": None,
                "usage_limit": None,
                "used_count": 0,
                "per_user_limit": 1,
                "is_active": True,
            },
            {
                "code": "FREE7",
                "is_trial": True,
                "trial_days": 7,
                "trial_traffic_gb": 10,
                "discount_percent": None,
                "usage_limit": None,
                "used_count": 0,
                "per_user_limit": 1,
                "is_active": True,
            },
        ],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_promo_usages_user_id"), table_name="promo_usages")
    op.drop_index(op.f("ix_promo_usages_promo_code_id"), table_name="promo_usages")
    op.drop_table("promo_usages")
    op.drop_table("promo_codes")
    op.drop_column("subscriptions", "subscription_url")
    op.drop_column("users", "trial_used")
