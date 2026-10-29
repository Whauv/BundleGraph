"""Small deployment CLI for schema migration and trusted catalog activation."""
from __future__ import annotations

import argparse
import os
from datetime import UTC, datetime
from pathlib import Path

from bundlegraph.models import AvailabilityStatus, FixtureCatalog, FreshnessStatus, Money
from bundlegraph.catalog import OFFLINE_FIXTURE_CATALOG

from .postgres import PostgresCatalogRepository


def _database_url() -> str:
    value = os.environ.get("DATABASE_URL")
    if not value:
        raise SystemExit("DATABASE_URL is required")
    return value


def _migration_directory(environ: dict[str, str] | None = None) -> Path:
    values = environ or os.environ
    configured = values.get("BUNDLEGRAPH_MIGRATIONS_DIR", "").strip()
    directory = Path(configured) if configured else Path(__file__).resolve().parents[2] / "migrations"
    if not directory.is_dir() or not any(directory.glob("*.sql")):
        raise SystemExit(f"no SQL migrations found in {directory}")
    return directory


def migrate(database_url: str) -> None:
    try:
        import psycopg
    except ImportError as exc:
        raise SystemExit("Install the postgres dependency group before migrating") from exc
    migration_directory = _migration_directory()
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute("CREATE TABLE IF NOT EXISTS bundlegraph_schema_migrations (name TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())")
            for path in sorted(migration_directory.glob("*.sql")):
                cursor.execute("SELECT 1 FROM bundlegraph_schema_migrations WHERE name = %s", (path.name,))
                if cursor.fetchone():
                    continue
                cursor.execute(path.read_text(encoding="utf-8"))
                cursor.execute("INSERT INTO bundlegraph_schema_migrations (name) VALUES (%s)", (path.name,))


def activate_catalog(database_url: str, catalog_id: str, path: Path) -> None:
    catalog = FixtureCatalog.model_validate_json(path.read_text(encoding="utf-8"))
    PostgresCatalogRepository(database_url).put_active(catalog_id, catalog)


def local_demo_catalog() -> FixtureCatalog:
    """Return an explicitly synthetic, currently observed catalog for local E2E use."""
    now = datetime.now(UTC)
    offers = tuple(offer.model_copy(update={"availability_status": AvailabilityStatus.AVAILABLE, "shipping": Money(amount_minor=0, currency=offer.unit_price.currency), "tax": Money(amount_minor=0, currency=offer.unit_price.currency), "observed_at": now}) for offer in OFFLINE_FIXTURE_CATALOG.offers)
    availability_ids = {offer.availability_evidence_id for offer in offers}
    evidence = tuple(record.model_copy(update={"observed_at": now, "observed_value": "available", "freshness_status": FreshnessStatus.FRESH}) if record.evidence_id in availability_ids else record for record in OFFLINE_FIXTURE_CATALOG.evidence)
    return OFFLINE_FIXTURE_CATALOG.model_copy(update={"offers": offers, "evidence": evidence}).validate_references()


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m bundlegraph_app.manage")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("migrate")
    catalog_parser = subparsers.add_parser("activate-catalog")
    catalog_parser.add_argument("catalog_id")
    catalog_parser.add_argument("path", type=Path)
    subparsers.add_parser("activate-offline-fixture-catalog")
    subparsers.add_parser("activate-local-demo-catalog")
    arguments = parser.parse_args()
    database_url = _database_url()
    if arguments.command == "migrate":
        migrate(database_url)
    elif arguments.command == "activate-catalog":
        activate_catalog(database_url, arguments.catalog_id, arguments.path)
    elif arguments.command == "activate-offline-fixture-catalog":
        PostgresCatalogRepository(database_url).put_active("offline-fixture-v1", OFFLINE_FIXTURE_CATALOG)
    else:
        PostgresCatalogRepository(database_url).put_active("synthetic-local-demo-v1", local_demo_catalog())


if __name__ == "__main__":
    main()
