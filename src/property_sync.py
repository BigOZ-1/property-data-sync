"""
property_sync.py

Simulates syncing property records from a source system (e.g. a property
management platform export) into a destination system (e.g. an internal
database or reporting tool).

Real-world equivalent: pulling data from an API or CSV export, validating
it, transforming it, and loading it into another system -- while logging
and skipping bad records instead of letting the whole job crash.
"""

import csv
import json
import logging
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

# --- Logging setup -----------------------------------------------------
# In production this might go to a file, Slack webhook, or monitoring
# system instead of just stdout.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("property_sync")


@dataclass
class PropertyRecord:
    property_id: str
    address: str
    city: str
    state: str
    zip: str
    unit_count: int
    status: str
    last_updated: str


class SyncError(Exception):
    """Raised when a single record fails validation -- caught per-row
    so one bad record doesn't kill the whole sync job."""
    pass


def validate_row(row: dict) -> PropertyRecord:
    """Validate and transform a single raw CSV row into a clean record.

    Raises SyncError with a clear reason if the row can't be used.
    """
    property_id = row.get("property_id", "").strip()
    if not property_id:
        raise SyncError("missing property_id")

    address = row.get("address", "").strip()
    if not address:
        raise SyncError(f"{property_id}: missing address")

    zip_code = row.get("zip", "").strip()
    if not zip_code:
        raise SyncError(f"{property_id}: missing zip code")

    try:
        unit_count = int(row.get("unit_count", "0"))
    except ValueError:
        raise SyncError(f"{property_id}: invalid unit_count")

    status = row.get("status", "").strip().lower()
    if status not in {"active", "inactive"}:
        raise SyncError(f"{property_id}: unrecognized status '{status}'")

    return PropertyRecord(
        property_id=property_id,
        address=address,
        city=row.get("city", "").strip(),
        state=row.get("state", "").strip(),
        zip=zip_code,
        unit_count=unit_count,
        status=status,
        last_updated=row.get("last_updated", "").strip(),
    )


def read_source(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def sync_properties(source_path: Path, dest_path: Path) -> dict:
    """Run the full sync. Returns a summary dict with counts -- this is
    what you'd log, alert on, or report in a CI job summary."""

    logger.info("Starting property sync from %s", source_path)
    raw_rows = read_source(source_path)

    synced: list[PropertyRecord] = []
    errors: list[str] = []

    for row in raw_rows:
        try:
            record = validate_row(row)
            synced.append(record)
        except SyncError as e:
            errors.append(str(e))
            logger.warning("Skipped row: %s", e)

    # Write the clean records to the "destination system" -- here just
    # a JSON file standing in for a database write or API call.
    dest_path.write_text(
        json.dumps([asdict(r) for r in synced], indent=2),
        encoding="utf-8",
    )

    summary = {
        "total_rows": len(raw_rows),
        "synced": len(synced),
        "skipped": len(errors),
        "errors": errors,
    }

    logger.info(
        "Sync complete: %d/%d records synced, %d skipped",
        summary["synced"], summary["total_rows"], summary["skipped"],
    )

    if errors:
        logger.warning("Skipped records:\n  - " + "\n  - ".join(errors))

    return summary


def main(argv: Optional[list[str]] = None) -> int:
    source = Path("data/source_properties.csv")
    dest = Path("data/synced_properties.json")

    summary = sync_properties(source, dest)

    # Non-zero exit if EVERY record failed -- that signals something is
    # fundamentally broken (bad file, wrong format) rather than just a
    # few messy rows, and should fail the CI job / alert on-call.
    if summary["synced"] == 0 and summary["total_rows"] > 0:
        logger.error("All records failed validation -- aborting")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
