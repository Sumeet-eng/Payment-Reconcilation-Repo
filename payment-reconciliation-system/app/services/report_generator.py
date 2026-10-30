import uuid
from datetime import datetime, timezone


def generate_report(result: dict, internal_filename: str, bank_filename: str) -> dict:
    return {
        "reconciliation_id": str(uuid.uuid4()),
        "created_at": datetime.now(timezone.utc),
        "files": {"internal": internal_filename, "bank": bank_filename},
        "summary": result["summary"],
        "details": result["details"],
    }
