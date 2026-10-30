from pathlib import Path

import mongomock
import pytest
from fastapi.testclient import TestClient

from app.database import get_reports_collection
from app.main import app

SAMPLES = Path(__file__).resolve().parent.parent / "sample_data"


@pytest.fixture()
def client():
    collection = mongomock.MongoClient().db.reports
    app.dependency_overrides[get_reports_collection] = lambda: collection
    yield TestClient(app)
    app.dependency_overrides.clear()


def post(client, internal: bytes, bank: bytes):
    return client.post(
        "/reconcile",
        files={"internal_file": ("internal.csv", internal), "bank_file": ("bank.csv", bank)},
    )


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_reconcile_sample_data_and_fetch_it_back(client):
    resp = post(client, (SAMPLES / "internal.csv").read_bytes(), (SAMPLES / "bank.csv").read_bytes())
    assert resp.status_code == 200, resp.text
    report = resp.json()
    assert report["summary"]["perfect_matches"] == 3
    assert report["summary"]["amount_mismatch"] == 1
    assert report["summary"]["missing_in_bank"] == 1
    assert report["summary"]["missing_in_internal"] == 1
    assert "_id" not in report

    fetched = client.get(f"/reports/{report['reconciliation_id']}")
    assert fetched.status_code == 200
    assert fetched.json()["summary"] == report["summary"]

    listing = client.get("/reports").json()
    assert len(listing) == 1 and "details" not in listing[0]


def test_bad_csv_is_a_400_not_a_500(client):
    good = b"transaction_id,amount\nT1,1\n"
    resp = post(client, b"id,amt\n1,2\n", good)
    assert resp.status_code == 400
    assert "internal_file" in resp.json()["detail"]


def test_unknown_report_is_404(client):
    assert client.get("/reports/does-not-exist").status_code == 404
