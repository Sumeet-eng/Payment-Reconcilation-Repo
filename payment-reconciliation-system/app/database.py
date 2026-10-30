from pymongo import MongoClient
from pymongo.collection import Collection

from app.config import COLLECTION_NAME, DB_NAME, MONGO_URI

_client = None


def get_client() -> MongoClient:
    """Create the Mongo client lazily so importing the app never needs a live DB."""
    global _client
    if _client is None:
        _client = MongoClient(MONGO_URI, tz_aware=True, serverSelectionTimeoutMS=3000)
    return _client


def get_reports_collection() -> Collection:
    """FastAPI dependency. Tests override this with an in-memory collection."""
    return get_client()[DB_NAME][COLLECTION_NAME]
