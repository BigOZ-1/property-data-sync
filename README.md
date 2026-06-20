# Property Data Sync

A small CI/CD-backed data sync pipeline, modeled on the kind of automation
work common in DevOps / data operations roles: pulling property records
from a source system, validating and cleaning them, and loading the
results into a destination system -- with errors logged and skipped
instead of crashing the whole job.

## What it does

`src/property_sync.py` reads `data/source_properties.csv` (standing in for
an export from a property management platform), validates each row, and
writes the clean records to `data/synced_properties.json` (standing in for
a database write or API call to a destination system).

Bad rows (missing address, missing zip, invalid unit count, unrecognized
status) are logged and skipped rather than failing the whole sync -- this
is the difference between a brittle script and a reliable one.

## Running it locally

```bash
pip install -r requirements.txt

# run the sync
python -m src.property_sync

# run the tests
pytest -v
```

## CI/CD pipeline

`.github/workflows/sync.yml` defines two jobs:

- **test** -- runs on every push/PR to `main`. Runs the full pytest suite
  so broken logic is caught before merge.
- **sync** -- runs nightly on a schedule (`cron`), or on demand via the
  "Run workflow" button in the GitHub Actions tab. Runs the actual sync
  and uploads the output as a build artifact.

This mirrors a common real-world pattern: validate on every code change,
run the real job on a schedule, and keep both definitions in one
version-controlled file instead of configuring them separately in a CI
tool's UI.

## Project structure

```
property-data-sync/
├── .github/workflows/sync.yml   # CI/CD pipeline definition
├── data/
│   └── source_properties.csv    # mock input data (some rows intentionally bad)
├── src/
│   └── property_sync.py         # sync logic
├── tests/
│   └── test_property_sync.py    # pytest suite
└── requirements.txt
```
