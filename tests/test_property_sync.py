"""
Tests for property_sync.py

These are exactly the kind of checks a GitHub Actions workflow would run
on every push/PR -- catching broken logic before it reaches the nightly
scheduled sync.
"""

import json
from pathlib import Path

import pytest

from src.property_sync import validate_row, sync_properties, SyncError


# --- validate_row tests -------------------------------------------------

def test_validate_row_accepts_good_record():
    row = {
        "property_id": "P9001",
        "address": "1 Main St",
        "city": "Deerfield Beach",
        "state": "FL",
        "zip": "33441",
        "unit_count": "10",
        "status": "active",
        "last_updated": "2026-06-19",
    }
    record = validate_row(row)
    assert record.property_id == "P9001"
    assert record.unit_count == 10
    assert record.status == "active"


def test_validate_row_rejects_missing_address():
    row = {"property_id": "P9002", "address": "", "zip": "33441",
           "unit_count": "5", "status": "active"}
    with pytest.raises(SyncError, match="missing address"):
        validate_row(row)


def test_validate_row_rejects_missing_zip():
    row = {"property_id": "P9003", "address": "1 Main St", "zip": "",
           "unit_count": "5", "status": "active"}
    with pytest.raises(SyncError, match="missing zip"):
        validate_row(row)


def test_validate_row_rejects_bad_unit_count():
    row = {"property_id": "P9004", "address": "1 Main St", "zip": "33441",
           "unit_count": "not-a-number", "status": "active"}
    with pytest.raises(SyncError, match="invalid unit_count"):
        validate_row(row)


def test_validate_row_rejects_unknown_status():
    row = {"property_id": "P9005", "address": "1 Main St", "zip": "33441",
           "unit_count": "5", "status": "pending"}
    with pytest.raises(SyncError, match="unrecognized status"):
        validate_row(row)


# --- end-to-end sync test -----------------------------------------------

def test_sync_properties_end_to_end(tmp_path: Path):
    """Runs the full sync against a small in-memory CSV, including some
    bad rows, and checks the summary + output file are correct."""

    source = tmp_path / "source.csv"
    dest = tmp_path / "dest.json"

    source.write_text(
        "property_id,address,city,state,zip,unit_count,status,last_updated\n"
        "P1,123 A St,Town,FL,33000,5,active,2026-06-01\n"
        "P2,,Town,FL,33000,5,active,2026-06-01\n"  # missing address
        "P3,456 B St,Town,FL,33000,5,active,2026-06-01\n"
    )

    summary = sync_properties(source, dest)

    assert summary["total_rows"] == 3
    assert summary["synced"] == 2
    assert summary["skipped"] == 1
    assert "P2" in summary["errors"][0]

    output = json.loads(dest.read_text())
    assert len(output) == 2
    assert output[0]["property_id"] == "P1"
