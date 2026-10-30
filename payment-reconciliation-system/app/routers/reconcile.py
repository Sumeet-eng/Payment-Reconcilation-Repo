from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pymongo.errors import PyMongoError

from app.config import MAX_UPLOAD_MB
from app.database import get_reports_collection
from app.services.file_parser import ParseError, parse_csv
from app.services.matching_engine import reconcile_data
from app.services.report_generator import generate_report

router = APIRouter()


def _load(upload: UploadFile, label: str):
    if upload.size is not None and upload.size > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(413, f"{label}: file exceeds {MAX_UPLOAD_MB} MB limit")
    try:
        return parse_csv(upload, label)
    except ParseError as exc:
        raise HTTPException(400, str(exc))


# Plain `def` (not `async def`): pandas and pymongo are blocking, so FastAPI
# runs these in a worker thread instead of stalling the event loop.
@router.post("/reconcile")
def reconcile(
    internal_file: UploadFile = File(..., description="CSV with transaction_id, amount"),
    bank_file: UploadFile = File(..., description="CSV with transaction_id, amount"),
    collection=Depends(get_reports_collection),
):
    internal_df = _load(internal_file, "internal_file")
    bank_df = _load(bank_file, "bank_file")

    report = generate_report(
        reconcile_data(internal_df, bank_df),
        internal_file.filename,
        bank_file.filename,
    )

    try:
        # Insert a copy: insert_one() adds a non-serialisable `_id` to the dict it is given.
        collection.insert_one(dict(report))
    except PyMongoError:
        raise HTTPException(503, "Database unavailable; report was not saved")
    return report


@router.get("/reports")
def list_reports(
    limit: int = Query(20, ge=1, le=100),
    skip: int = Query(0, ge=0),
    collection=Depends(get_reports_collection),
):
    """Newest first, summaries only (no per-transaction details)."""
    try:
        cursor = (
            collection.find({}, {"_id": 0, "details": 0})
            .sort("created_at", -1)
            .skip(skip)
            .limit(limit)
        )
        return list(cursor)
    except PyMongoError:
        raise HTTPException(503, "Database unavailable")


@router.get("/reports/{reconciliation_id}")
def get_report(reconciliation_id: str, collection=Depends(get_reports_collection)):
    try:
        report = collection.find_one({"reconciliation_id": reconciliation_id}, {"_id": 0})
    except PyMongoError:
        raise HTTPException(503, "Database unavailable")
    if report is None:
        raise HTTPException(404, "Report not found")
    return report
