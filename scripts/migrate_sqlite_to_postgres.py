#!/usr/bin/env python3
import argparse
import json
import os
from datetime import date, datetime
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import MetaData, Table, create_engine, func, inspect, select, text
from sqlalchemy.engine import Connection, Engine, make_url


load_dotenv()


ALEMBIC_HEAD = "f8b2c6d41e73"
TABLES = [
    "users",
    "pricing_plans",
    "pricing_plan_versions",
    "ingredients",
    "nutrient_requirements",
    "devices",
    "formulation_series",
    "formulations",
    "otp_sessions",
    "device_licenses",
    "license_events",
    "license_payments",
    "referrals",
    "referral_credits",
]
SEEDED_TARGET_TABLES = {"pricing_plans", "pricing_plan_versions"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Copy an Alembic-head SQLite database into empty PostgreSQL tables."
    )
    parser.add_argument(
        "--source",
        default="sqlite:///./app_database.db",
        help="SQLite SQLAlchemy URL (default: sqlite:///./app_database.db)",
    )
    parser.add_argument(
        "--target",
        default=os.getenv("DATABASE_URL"),
        help="PostgreSQL SQLAlchemy URL (default: DATABASE_URL)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write data. Without this flag, only preflight checks run.",
    )
    return parser.parse_args()


def validate_urls(source_url: str, target_url: str | None) -> None:
    if not target_url:
        raise ValueError("A PostgreSQL target URL is required")
    if make_url(source_url).get_backend_name() != "sqlite":
        raise ValueError("The source URL must use SQLite")
    if make_url(target_url).get_backend_name() != "postgresql":
        raise ValueError("The target URL must use PostgreSQL")


def require_head(connection: Connection, label: str) -> None:
    if not inspect(connection).has_table("alembic_version"):
        raise RuntimeError(f"{label} has no Alembic schema")
    revision = connection.scalar(text("SELECT version_num FROM alembic_version"))
    if revision != ALEMBIC_HEAD:
        raise RuntimeError(
            f"{label} is at Alembic revision {revision!r}; expected {ALEMBIC_HEAD}"
        )


def reflect_tables(engine: Engine) -> dict[str, Table]:
    metadata = MetaData()
    return {
        name: Table(name, metadata, autoload_with=engine)
        for name in TABLES
    }


def read_rows(
    connection: Connection, tables: dict[str, Table]
) -> dict[str, list[dict]]:
    rows = {}
    for name in TABLES:
        table = tables[name]
        statement = select(table)
        if "id" in table.c:
            statement = statement.order_by(table.c.id)
        rows[name] = [dict(row._mapping) for row in connection.execute(statement)]
    return rows


def require_empty_target(
    connection: Connection, tables: dict[str, Table]
) -> None:
    populated = []
    for name in TABLES:
        count = connection.scalar(select(func.count()).select_from(tables[name]))
        if count and name not in SEEDED_TARGET_TABLES:
            populated.append(f"{name}={count}")
    if populated:
        raise RuntimeError(
            "PostgreSQL target must be empty; found " + ", ".join(populated)
        )


def reset_sequences(connection: Connection, tables: dict[str, Table]) -> None:
    for name, table in tables.items():
        if "id" not in table.c:
            continue
        sequence = connection.scalar(
            text("SELECT pg_get_serial_sequence(:table_name, 'id')"),
            {"table_name": name},
        )
        if not sequence:
            continue
        maximum_id = connection.scalar(select(func.max(table.c.id)))
        if maximum_id is None:
            connection.execute(
                text("SELECT setval(to_regclass(:sequence), 1, false)"),
                {"sequence": sequence},
            )
        else:
            connection.execute(
                text("SELECT setval(to_regclass(:sequence), :value, true)"),
                {"sequence": sequence, "value": maximum_id},
            )


def normalized(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: normalized(item) for key, item in sorted(value.items())}
    if isinstance(value, list):
        return [normalized(item) for item in value]
    return value


def fingerprint(rows: list[dict]) -> str:
    return json.dumps(normalized(rows), sort_keys=True, separators=(",", ":"))


def verify_copy(
    source_rows: dict[str, list[dict]],
    target_engine: Engine,
    target_tables: dict[str, Table],
) -> None:
    with target_engine.connect() as connection:
        target_rows = read_rows(connection, target_tables)
    mismatches = [
        name
        for name in TABLES
        if fingerprint(source_rows[name]) != fingerprint(target_rows[name])
    ]
    if mismatches:
        raise RuntimeError(
            "Post-migration content mismatch in: " + ", ".join(mismatches)
        )


def main() -> None:
    args = parse_args()
    validate_urls(args.source, args.target)

    source_path = Path(make_url(args.source).database or "")
    if not source_path.exists():
        raise FileNotFoundError(f"SQLite source does not exist: {source_path}")

    source_engine = create_engine(args.source)
    target_engine = create_engine(args.target)
    try:
        source_tables = reflect_tables(source_engine)
        target_tables = reflect_tables(target_engine)
        with source_engine.connect() as source_connection:
            require_head(source_connection, "SQLite source")
            source_rows = read_rows(source_connection, source_tables)
        with target_engine.connect() as target_connection:
            require_head(target_connection, "PostgreSQL target")
            require_empty_target(target_connection, target_tables)

        counts = ", ".join(
            f"{name}={len(source_rows[name])}" for name in TABLES
        )
        print(f"Preflight passed: {counts}")
        if not args.apply:
            print("Dry run only; pass --apply to copy data.")
            return

        with target_engine.begin() as target_connection:
            require_empty_target(target_connection, target_tables)
            target_connection.execute(target_tables["pricing_plan_versions"].delete())
            target_connection.execute(target_tables["pricing_plans"].delete())
            for name in TABLES:
                if source_rows[name]:
                    target_connection.execute(
                        target_tables[name].insert(), source_rows[name]
                    )
            reset_sequences(target_connection, target_tables)

        verify_copy(source_rows, target_engine, target_tables)
        print("Migration applied and every table verified successfully.")
    finally:
        source_engine.dispose()
        target_engine.dispose()


if __name__ == "__main__":
    main()
