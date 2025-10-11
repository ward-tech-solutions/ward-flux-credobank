#!/usr/bin/env python3
"""
Simple SQL migration runner for the Ward OPS project.

Applies SQL files from migrations/postgres in ascending order and records
which migrations have run in the database.

Usage:
    env DATABASE_URL=postgresql://user:pass@host:port/db scripts/run_sql_migrations.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, text

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations" / "postgres"
BASELINE_SKIP = {"001_core_schema.sql"}  # schema created via bootstrap/migration script


def split_statements(sql: str) -> list[str]:
    statements: list[str] = []
    buffer: list[str] = []
    for line in sql.splitlines():
        stripped = line.strip()
        buffer.append(line)
        if stripped.endswith(";"):
            statements.append("".join(buffer).strip())
            buffer.clear()
    if buffer:
        statements.append("".join(buffer).strip())
    return [stmt for stmt in statements if stmt]


def main() -> None:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("[migrate] DATABASE_URL is not set", file=sys.stderr)
        sys.exit(1)

    engine = create_engine(database_url, isolation_level="AUTOCOMMIT")

    with engine.connect() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    id SERIAL PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
        )

    migration_files = sorted(f for f in MIGRATIONS_DIR.glob("*.sql"))
    if not migration_files:
        print("[migrate] No migration files found.")
        return

    with engine.connect() as conn:
        for migration in migration_files:
            name = migration.name

            # mark baseline migrations as applied without executing them
            if name in BASELINE_SKIP:
                conn.execute(
                    text(
                        "INSERT INTO schema_migrations (name) VALUES (:name) "
                        "ON CONFLICT (name) DO NOTHING"
                    ),
                    {"name": name},
                )
                continue

            applied = conn.execute(
                text("SELECT 1 FROM schema_migrations WHERE name = :name"),
                {"name": name},
            ).fetchone()

            if applied:
                print(f"[migrate] {name} already applied, skipping.")
                continue

            sql = migration.read_text()
            statements = split_statements(sql)
            if not statements:
                print(f"[migrate] {name} contains no statements, skipping.")
                continue

            print(f"[migrate] Applying {name}...")
            try:
                for statement in statements:
                    conn.execute(text(statement))
                conn.execute(
                    text("INSERT INTO schema_migrations (name) VALUES (:name)"),
                    {"name": name},
                )
                print(f"[migrate] {name} applied.")
            except Exception as exc:
                print(f"[migrate] Failed to apply {name}: {exc}", file=sys.stderr)
                sys.exit(1)


if __name__ == "__main__":
    main()
