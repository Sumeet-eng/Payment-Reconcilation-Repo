# Payment Reconciliation System

A small REST service that reconciles an **internal transaction ledger** against a **bank statement**. Upload two CSV files and it tells you which transactions match, which have a different amount, and which exist on only one side. Every run is saved to MongoDB so reports can be fetched later.

**Stack:** FastAPI · Pandas · MongoDB · Docker

## Why this exists

Finance and payments teams reconcile ledgers against bank settlements constantly, and it's usually done by eye in spreadsheets. This automates the first pass and hands people a short exceptions list instead of two long files.

## Quick start

```bash
git clone https://github.com/Sumeet-eng/Payment-Reconcilation-system.git
cd Payment-Reconcilation-system/payment-reconciliation-system
docker compose up --build
```

Open **http://localhost:8000/docs** for the interactive API, or try it from the terminal with the bundled sample files:

```bash
curl -X POST http://localhost:8000/reconcile \
  -F "internal_file=@sample_data/internal.csv" \
  -F "bank_file=@sample_data/bank.csv"
```

## Input format

Both files are CSVs with two required columns. Header case and surrounding spaces don't matter, extra columns are ignored, and amounts may contain thousands separators (`1,234.50`).

| transaction_id | amount |
|----------------|--------|
| TXN001         | 1500.00 |
| TXN002         | 250.50 |

Bad input is rejected with a `400` that says which file and which line is wrong (missing column, blank ID, non-numeric amount, empty file).

## How matching works

Records are joined on `transaction_id`, then each one lands in exactly one bucket:

| Bucket | Meaning |
|---|---|
| `perfect_matches` | ID on both sides, amounts agree (within `AMOUNT_TOLERANCE`) |
| `amount_mismatch` | ID on both sides, amounts differ |
| `missing_in_bank` | In the ledger, not on the bank statement (e.g. payment not settled yet) |
| `missing_in_internal` | On the bank statement, not in the ledger (e.g. unrecorded fee or payment) |
| `duplicates_internal` / `duplicates_bank` | An ID that appears more than once on either side. These are **set aside for manual review** rather than guessed at |

Design choices worth knowing:

- **Money is compared as integers.** Amounts are converted to minor units (paise/cents) on load, so there is no floating-point noise like `0.1 + 0.2 != 0.3`.
- **Duplicates are excluded, not merged.** A plain join multiplies rows when an ID repeats, which silently inflates every count. Here they're reported separately.
- **IDs are strings.** `001` stays `001`.

## API

| Method | Path | Description |
|---|---|---|
| `POST` | `/reconcile` | Upload `internal_file` and `bank_file`; returns the full report |
| `GET` | `/reports` | List past reports, newest first (`limit`, `skip`); summaries only |
| `GET` | `/reports/{reconciliation_id}` | Fetch one full report |
| `GET` | `/health` | Liveness check |

Example response for the sample files (trimmed):

```json
{
  "reconciliation_id": "3f0c9a52-…",
  "created_at": "2026-10-30T09:15:00Z",
  "files": { "internal": "internal.csv", "bank": "bank.csv" },
  "summary": {
    "total_internal": 5,
    "total_bank": 5,
    "perfect_matches": 3,
    "amount_mismatch": 1,
    "missing_in_bank": 1,
    "missing_in_internal": 1,
    "match_rate_percent": 50.0,
    "total_internal_amount": 3125.49,
    "total_bank_amount": 2244.99,
    "net_difference": 880.5
  },
  "details": {
    "amount_mismatch": [
      { "transaction_id": "TXN002", "internal_amount": 250.5, "bank_amount": 250.0, "difference": 0.5 }
    ],
    "missing_in_bank": [ { "transaction_id": "TXN004", "internal_amount": 1200.0 } ],
    "missing_in_internal": [ { "transaction_id": "TXN006", "bank_amount": 320.0 } ]
  }
}
```

If MongoDB is unreachable, the API returns `503` instead of crashing.

## Configuration

Set via environment variables (or a `.env` file; see `.env.example`).

| Variable | Default | Purpose |
|---|---|---|
| `MONGO_URI` | `mongodb://localhost:27017` | MongoDB connection string (set automatically in Docker Compose) |
| `DB_NAME` | `reconciliation_db` | Database name |
| `COLLECTION_NAME` | `reports` | Collection for saved reports |
| `AMOUNT_TOLERANCE` | `0` | Amounts within this many currency units count as a match |
| `MAX_UPLOAD_MB` | `20` | Reject larger uploads |
| `MAX_DETAIL_ROWS` | `1000` | Cap per detail list in a report. Summary counts are always exact; `details_truncated` tells you if a cap was hit |

## Run locally without Docker

```bash
cd payment-reconciliation-system
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
# needs a MongoDB on localhost:27017, e.g.: docker run -d -p 27017:27017 mongo:6
uvicorn app.main:app --reload
```

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

Tests cover the matching rules (including tolerance and duplicates), CSV validation, and the API end to end against an in-memory MongoDB, so no database is needed. GitHub Actions runs them and builds the Docker image on every push and pull request.

## Project layout

```
payment-reconciliation-system/
├── app/
│   ├── main.py                    # FastAPI app + /health
│   ├── config.py                  # env-driven settings
│   ├── database.py                # lazy MongoDB client
│   ├── routers/reconcile.py       # /reconcile and /reports endpoints
│   └── services/
│       ├── file_parser.py         # CSV validation + normalisation
│       ├── matching_engine.py     # the reconciliation logic
│       └── report_generator.py    # report document
├── tests/
├── sample_data/
├── Dockerfile
└── docker-compose.yml
```

## Limitations and ideas

- Matching is by `transaction_id` only. Real bank statements often lack your internal ID, so fuzzy matching on date + amount + reference would be the natural next step.
- Single currency, no authentication, and uploads are processed in memory.
- Possible additions: CSV/Excel export of the exceptions list, a one-to-many matcher (one bank settlement covering several ledger entries), and async processing for very large files.
