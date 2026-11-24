"""Durable state adapter for the small standalone Shopnoltd API.

The larger Kubernetes services have their own database contracts. This adapter is
intentionally scoped to the root API so Render can persist its currently supported
wallet, transaction, user, payment, audit, and exchange state without changing the
public route shapes.
"""

from __future__ import annotations

import json
import os
from typing import Any

import psycopg2
from psycopg2.extras import Json, RealDictCursor


class PostgresStateStore:
    def __init__(self) -> None:
        self.database_url = os.getenv("DATABASE_URL", "").strip()
        self.enabled = bool(self.database_url)

    def _connect(self):
        return psycopg2.connect(self.database_url, connect_timeout=8)

    def initialize(self) -> None:
        if not self.enabled:
            return
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS shopnoltd_api_state (
                    state_key TEXT PRIMARY KEY,
                    state_value JSONB NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )

    def load(self, keys: list[str]) -> dict[str, Any]:
        if not self.enabled:
            return {}
        with self._connect() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT state_key, state_value FROM shopnoltd_api_state WHERE state_key = ANY(%s)",
                (keys,),
            )
            return {row["state_key"]: row["state_value"] for row in cur.fetchall()}

    def save(self, state: dict[str, Any]) -> None:
        if not self.enabled:
            return
        with self._connect() as conn, conn.cursor() as cur:
            for key, value in state.items():
                cur.execute(
                    """
                    INSERT INTO shopnoltd_api_state (state_key, state_value, updated_at)
                    VALUES (%s, %s, NOW())
                    ON CONFLICT (state_key) DO UPDATE SET
                        state_value = EXCLUDED.state_value,
                        updated_at = NOW()
                    """,
                    (key, Json(value)),
                )

    def health(self) -> str:
        return "postgres" if self.enabled else "memory"


STATE_KEYS = [
    "wallets",
    "transactions",
    "users",
    "payment_methods",
    "audit_log",
    "exchange_orders",
]


def serialize_state(state: dict[str, Any]) -> dict[str, Any]:
    """Validate that state can be encoded before a request commits it."""
    return json.loads(json.dumps(state, ensure_ascii=False))
