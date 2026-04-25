"""servers + subscription_clients + subscriptions.sub_token + plan seeds (RUB)

Revision ID: 0003_servers
Revises: 0002_promo_trial
Create Date: 2026-04-23 21:00:00.000000

Backfill rules:
- ``servers``: insert one row from the legacy XUI_* env vars so single-server
  installs keep working without admin action.
- ``subscriptions.sub_token``: pre-existing rows get a fresh hex token so
  the public ``/sub/{sub_token}`` endpoint can serve them.
- ``subscription_clients``: for each existing subscription, link it to the
  backfilled server using the existing ``xui_*`` columns so the merged
  VLESS list contains the original link.
- Plans: seed Russian-rouble tariffs (50/100/500 GB / Unlimited × 30 d) only
  if no non-trial plans exist, so dev DBs aren't disturbed.
"""

from __future__ import annotations

import os
import secrets
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0003_servers"
down_revision: str | None = "0002_promo_trial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _ensure_token() -> str:
    return secrets.token_hex(16)


def upgrade() -> None:
    op.create_table(
        "servers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column(
            "country_code", sa.String(length=8), nullable=False, server_default="XX"
        ),
        sa.Column("host", sa.String(length=255), nullable=False),
        sa.Column("username", sa.String(length=128), nullable=False),
        sa.Column("password", sa.String(length=255), nullable=False),
        sa.Column("inbound_id", sa.Integer(), nullable=False),
        sa.Column("public_host", sa.String(length=255), nullable=True),
        sa.Column("subscription_base_url", sa.Text(), nullable=True),
        sa.Column(
            "tls_verify", sa.Boolean(), nullable=False, server_default="1"
        ),
        sa.Column(
            "enabled", sa.Boolean(), nullable=False, server_default="1"
        ),
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
        sa.UniqueConstraint("name", name="uq_servers_name"),
    )

    op.create_table(
        "subscription_clients",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("subscription_id", sa.Integer(), nullable=False),
        sa.Column("server_id", sa.Integer(), nullable=False),
        sa.Column("xui_inbound_id", sa.Integer(), nullable=False),
        sa.Column("xui_client_uuid", sa.String(length=64), nullable=False),
        sa.Column("xui_email", sa.String(length=128), nullable=False),
        sa.Column("vless_link", sa.Text(), nullable=False),
        sa.Column(
            "enabled", sa.Boolean(), nullable=False, server_default="1"
        ),
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
        sa.ForeignKeyConstraint(
            ["subscription_id"], ["subscriptions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["server_id"], ["servers.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "subscription_id", "server_id", name="uq_sub_clients_sub_server"
        ),
    )
    op.create_index(
        op.f("ix_subscription_clients_subscription_id"),
        "subscription_clients",
        ["subscription_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_subscription_clients_server_id"),
        "subscription_clients",
        ["server_id"],
        unique=False,
    )

    # subscriptions.sub_token (nullable initially → backfill → NOT NULL)
    op.add_column(
        "subscriptions",
        sa.Column("sub_token", sa.String(length=64), nullable=True),
    )

    bind = op.get_bind()
    subs = bind.execute(sa.text("SELECT id FROM subscriptions")).fetchall()
    for (sub_id,) in subs:
        bind.execute(
            sa.text("UPDATE subscriptions SET sub_token = :token WHERE id = :id"),
            {"token": _ensure_token(), "id": sub_id},
        )

    with op.batch_alter_table("subscriptions") as batch:
        batch.alter_column("sub_token", existing_type=sa.String(length=64), nullable=False)
        batch.create_index(
            "ix_subscriptions_sub_token", ["sub_token"], unique=True
        )

    # Backfill ``servers`` from legacy env vars.
    legacy_host = os.environ.get("XUI_HOST", "").strip()
    legacy_user = os.environ.get("XUI_USERNAME", "admin")
    legacy_pass = os.environ.get("XUI_PASSWORD", "admin")
    legacy_inbound = int(os.environ.get("XUI_INBOUND_ID", "1") or "1")
    legacy_sub = os.environ.get("XUI_SUB_BASE_URL", "").strip() or None
    legacy_tls = os.environ.get("XUI_USE_TLS_VERIFY", "true").strip().lower() != "false"
    if legacy_host:
        bind.execute(
            sa.text(
                "INSERT INTO servers (name, country_code, host, username, password, "
                "inbound_id, public_host, subscription_base_url, tls_verify, enabled) "
                "VALUES (:name, :cc, :host, :u, :p, :inb, NULL, :sub, :tls, 1)"
            ),
            {
                "name": "default",
                "cc": "XX",
                "host": legacy_host,
                "u": legacy_user,
                "p": legacy_pass,
                "inb": legacy_inbound,
                "sub": legacy_sub,
                "tls": 1 if legacy_tls else 0,
            },
        )
        # Backfill subscription_clients for existing subs against the new server.
        new_server_id_row = bind.execute(
            sa.text("SELECT id FROM servers WHERE name = 'default'")
        ).fetchone()
        if new_server_id_row is not None:
            new_server_id = new_server_id_row[0]
            existing = bind.execute(
                sa.text(
                    "SELECT id, xui_inbound_id, xui_client_uuid, xui_email, vless_link "
                    "FROM subscriptions"
                )
            ).fetchall()
            for sub_id, inbound_id, client_uuid, email, vless in existing:
                bind.execute(
                    sa.text(
                        "INSERT INTO subscription_clients "
                        "(subscription_id, server_id, xui_inbound_id, "
                        "xui_client_uuid, xui_email, vless_link, enabled) "
                        "VALUES (:s, :sv, :i, :u, :e, :v, 1)"
                    ),
                    {
                        "s": sub_id,
                        "sv": new_server_id,
                        "i": inbound_id,
                        "u": client_uuid,
                        "e": email,
                        "v": vless,
                    },
                )

    # Seed RUB plans only when no non-trial plan exists yet.
    has_real_plan = bind.execute(
        sa.text("SELECT COUNT(*) FROM plans WHERE name <> '__trial__'")
    ).scalar()
    if not has_real_plan:
        op.bulk_insert(
            sa.table(
                "plans",
                sa.column("name", sa.String),
                sa.column("description", sa.Text),
                sa.column("duration_days", sa.Integer),
                sa.column("traffic_gb", sa.Integer),
                sa.column("price", sa.Numeric(12, 2)),
                sa.column("currency", sa.String),
                sa.column("is_active", sa.Boolean),
                sa.column("sort_order", sa.Integer),
            ),
            [
                {
                    "name": "50 GB / 30 дней",
                    "description": "50 ГБ трафика на 30 дней",
                    "duration_days": 30,
                    "traffic_gb": 50,
                    "price": 149,
                    "currency": "RUB",
                    "is_active": True,
                    "sort_order": 10,
                },
                {
                    "name": "100 GB / 30 дней",
                    "description": "100 ГБ трафика на 30 дней",
                    "duration_days": 30,
                    "traffic_gb": 100,
                    "price": 219,
                    "currency": "RUB",
                    "is_active": True,
                    "sort_order": 20,
                },
                {
                    "name": "500 GB / 30 дней",
                    "description": "500 ГБ трафика на 30 дней",
                    "duration_days": 30,
                    "traffic_gb": 500,
                    "price": 350,
                    "currency": "RUB",
                    "is_active": True,
                    "sort_order": 30,
                },
                {
                    "name": "Unlimited / 30 дней",
                    "description": "Безлимитный трафик на 30 дней",
                    "duration_days": 30,
                    "traffic_gb": 0,  # 0 = unlimited
                    "price": 500,
                    "currency": "RUB",
                    "is_active": True,
                    "sort_order": 40,
                },
            ],
        )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_subscription_clients_server_id"), table_name="subscription_clients"
    )
    op.drop_index(
        op.f("ix_subscription_clients_subscription_id"), table_name="subscription_clients"
    )
    op.drop_table("subscription_clients")
    with op.batch_alter_table("subscriptions") as batch:
        batch.drop_index("ix_subscriptions_sub_token")
        batch.drop_column("sub_token")
    op.drop_table("servers")
