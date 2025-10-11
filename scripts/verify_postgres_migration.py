#!/usr/bin/env python3
"""Compare row counts between SQLite and PostgreSQL copies of Ward OPS data."""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from typing import Iterable, List, Sequence

from sqlalchemy import MetaData, create_engine, text
from sqlalchemy.engine import Engine


DEFAULT_SQLITE = "data/ward_ops.db"


@dataclass
class TableDiff:
    name: str
    sqlite_count: int | None
    postgres_count: int | None
    exists_in_postgres: bool

    @property
    def delta(self) -> int | None:
        if self.sqlite_count is None or self.postgres_count is None:
            return None
        return self.postgres_count - self.sqlite_count


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare table row counts between SQLite and PostgreSQL",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--sqlite", default=DEFAULT_SQLITE, help="Path to SQLite file")
    parser.add_argument("--postgres", default=os.getenv("DATABASE_URL"), help="PostgreSQL connection URL")
    parser.add_argument(
        "--tables",
        nargs="*",
        help="Explicit list of tables to check (defaults to all tables found in SQLite)",
    )
    parser.add_argument(
        "--fail-on-mismatch",
        action="store_true",
        help="Exit with status 1 if any table has a different row count or is missing",
    )
    return parser.parse_args()


def require(condition: bool, message: str) -> None:
    if not condition:
        print(f"❌ {message}", file=sys.stderr)
        sys.exit(1)


def reflect_sqlite_tables(engine: Engine) -> Sequence[str]:
    metadata = MetaData()
    metadata.reflect(bind=engine)
    return list(metadata.tables.keys())


def postgres_table_exists(engine: Engine, table: str) -> bool:
    query = text("SELECT to_regclass(:name)")
    # Default schema is public – include schema qualification
    qualified = f"public.{table}"
    with engine.connect() as conn:
        return conn.execute(query, {"name": qualified}).scalar() is not None


def count_rows(engine: Engine, table: str) -> int:
    query = text(f'SELECT COUNT(*) FROM "{table}"')
    with engine.connect() as conn:
        return conn.execute(query).scalar_one()


def build_diffs(sqlite_engine: Engine, postgres_engine: Engine, tables: Iterable[str]) -> List[TableDiff]:
    diffs: List[TableDiff] = []
    for name in tables:
        try:
            sqlite_count = count_rows(sqlite_engine, name)
        except Exception as exc:  # pragma: no cover - diagnostic output
            print(f"⚠️  Skipping {name} on SQLite: {exc}")
            sqlite_count = None

        exists_pg = postgres_table_exists(postgres_engine, name)
        if exists_pg:
            try:
                postgres_count = count_rows(postgres_engine, name)
            except Exception as exc:
                print(f"⚠️  Unable to count {name} on PostgreSQL: {exc}")
                postgres_count = None
        else:
            postgres_count = None

        diffs.append(TableDiff(name=name, sqlite_count=sqlite_count, postgres_count=postgres_count, exists_in_postgres=exists_pg))

    return diffs


def print_summary(diffs: Sequence[TableDiff]) -> None:
    header = f"{'Table':30} {'SQLite':>12} {'Postgres':>12} {'Δ':>8}"
    print(header)
    print("-" * len(header))
    for diff in diffs:
        sqlite_display = str(diff.sqlite_count) if diff.sqlite_count is not None else "-"
        if diff.exists_in_postgres:
            postgres_display = str(diff.postgres_count) if diff.postgres_count is not None else "-"
        else:
            postgres_display = "missing"

        delta_display = str(diff.delta) if diff.delta is not None else "-"
        print(f"{diff.name:30} {sqlite_display:>12} {postgres_display:>12} {delta_display:>8}")


def main() -> None:
    args = parse_args()

    require(args.postgres, "PostgreSQL URL must be provided via --postgres or DATABASE_URL")

    sqlite_url = f"sqlite:///{args.sqlite}"
    require(os.path.exists(args.sqlite), f"SQLite database not found at {args.sqlite}")

    sqlite_engine = create_engine(sqlite_url)
    postgres_engine = create_engine(args.postgres)

    if args.tables:
        tables = args.tables
    else:
        tables = reflect_sqlite_tables(sqlite_engine)

    diffs = build_diffs(sqlite_engine, postgres_engine, tables)
    print_summary(diffs)

    if args.fail_on_mismatch:
        mismatches = [d for d in diffs if (d.sqlite_count != d.postgres_count) or not d.exists_in_postgres]
        if mismatches:
            print("\n❌ Differences detected.")
            for diff in mismatches:
                print(f" - {diff.name}: sqlite={diff.sqlite_count}, postgres={diff.postgres_count}, exists_pg={diff.exists_in_postgres}")
            sys.exit(1)


if __name__ == "__main__":
    main()
