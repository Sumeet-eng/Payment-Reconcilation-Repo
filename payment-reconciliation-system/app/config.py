import os

from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "reconciliation_db")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "reports")

# Amounts within this many currency units are treated as a match (0 = exact).
AMOUNT_TOLERANCE = float(os.getenv("AMOUNT_TOLERANCE", "0"))

# Reject uploads larger than this.
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "20"))

# Each detail list stored in a report is capped so a report never nears
# MongoDB's 16 MB document limit. Summary counts are always exact.
MAX_DETAIL_ROWS = int(os.getenv("MAX_DETAIL_ROWS", "1000"))
