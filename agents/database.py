"""
database.py
MongoDB integration for the FMCG Intelligence Agent.

Collections:
  - raw_articles       : Articles fetched from RSS feeds
  - cleaned_articles   : HTML-cleaned, normalized articles
  - deduplicated_articles : After fuzzy + exact dedup
  - relevant_articles  : FMCG-deal filtered articles
  - credible_articles  : Credibility-scored articles (with score field)
  - deals              : Extracted structured deal data (with embeddings)
  - newsletters        : Generated newsletter text per run
  - pipeline_runs      : Metadata about each pipeline execution
"""

import os
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

try:
    from pymongo import MongoClient, ASCENDING, TEXT
    from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
    PYMONGO_AVAILABLE = True
except ImportError:
    PYMONGO_AVAILABLE = False
    print("⚠️  pymongo not installed. Run: pip install pymongo")

MONGO_URI        = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME    = os.getenv("MONGO_DB_NAME", "fmcg_intelligence")

_client = None
_db     = None


# ─── Connection ───────────────────────────────────────────────────────────────

def get_db():
    """Return a MongoDB database handle (singleton)."""
    global _client, _db
    if not PYMONGO_AVAILABLE:
        raise RuntimeError("pymongo is not installed. Run: pip install pymongo")
    if _db is None:
        try:
            import certifi
            ca = certifi.where()
        except ImportError:
            ca = None

        kwargs = {"serverSelectionTimeoutMS": 5000}
        if ca:
            kwargs["tlsCAFile"] = ca

        _client = MongoClient(MONGO_URI, **kwargs)
        # Trigger a real connection check
        _client.admin.command("ping")
        _db = _client[MONGO_DB_NAME]
        _ensure_indexes(_db)
        print(f"✅ Connected to MongoDB: {MONGO_URI[:40]}... / db={MONGO_DB_NAME}")
    return _db



def _ensure_indexes(db):
    """Create useful indexes on startup."""
    try:
        db.raw_articles.create_index([("url", ASCENDING)], unique=True, sparse=True)
        db.raw_articles.create_index([("date", ASCENDING)])

        db.deals.create_index([("target_company", TEXT), ("buyer", TEXT), ("summary", TEXT)])
        db.deals.create_index([("run_id", ASCENDING)])
        db.deals.create_index([("deal_type", ASCENDING)])

        db.newsletters.create_index([("run_id", ASCENDING)])
        db.pipeline_runs.create_index([("started_at", ASCENDING)])
    except Exception as e:
        print(f"Index creation warning: {e}")


def is_connected() -> bool:
    """Return True if MongoDB is reachable."""
    try:
        get_db()
        return True
    except Exception:
        return False


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _strip_id(doc: dict) -> dict:
    """Remove MongoDB _id for JSON serialisation."""
    doc.pop("_id", None)
    return doc


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ─── Pipeline Run ─────────────────────────────────────────────────────────────

def create_pipeline_run(meta: dict | None = None) -> str:
    """Insert a pipeline_run document and return its run_id."""
    db = get_db()
    doc = {
        "started_at": _now(),
        "status": "running",
        **(meta or {}),
    }
    result = db.pipeline_runs.insert_one(doc)
    return str(result.inserted_id)


def finish_pipeline_run(run_id: str, summary: dict):
    """Mark a pipeline run as finished with summary stats."""
    from bson import ObjectId
    db = get_db()
    db.pipeline_runs.update_one(
        {"_id": ObjectId(run_id)},
        {"$set": {"status": "done", "finished_at": _now(), **summary}}
    )


# ─── Articles ─────────────────────────────────────────────────────────────────

def _upsert_articles(collection_name: str, articles: list[dict], run_id: str) -> int:
    """
    Upsert a list of articles into the named collection.
    Deduplicates by URL (if present) otherwise inserts fresh.
    Returns the count of upserted/inserted docs.
    """
    if not articles:
        return 0
    db = get_db()
    col = db[collection_name]
    count = 0
    for art in articles:
        doc = {**art, "run_id": run_id, "saved_at": _now()}
        url = doc.get("url")
        if url:
            col.update_one({"url": url}, {"$set": doc}, upsert=True)
        else:
            col.insert_one(doc)
        count += 1
    return count


def save_raw_articles(articles: list[dict], run_id: str) -> int:
    return _upsert_articles("raw_articles", articles, run_id)


def save_cleaned_articles(articles: list[dict], run_id: str) -> int:
    return _upsert_articles("cleaned_articles", articles, run_id)


def save_deduplicated_articles(articles: list[dict], run_id: str) -> int:
    return _upsert_articles("deduplicated_articles", articles, run_id)


def save_relevant_articles(articles: list[dict], run_id: str) -> int:
    return _upsert_articles("relevant_articles", articles, run_id)


def save_credible_articles(articles: list[dict], run_id: str) -> int:
    return _upsert_articles("credible_articles", articles, run_id)


# ─── Deals (with embeddings) ──────────────────────────────────────────────────

def save_deals(deals: list[dict], run_id: str) -> int:
    """
    Save extracted deals to MongoDB.
    Each deal may contain an 'embedding' field (list of floats).
    """
    if not deals:
        return 0
    db = get_db()
    count = 0
    for deal in deals:
        doc = {**deal, "run_id": run_id, "saved_at": _now()}
        # Store embedding as-is (list of floats)
        db.deals.insert_one(doc)
        count += 1
    return count


def load_deals(run_id: str | None = None) -> list[dict]:
    """Load deals from MongoDB. Optionally filter by run_id."""
    db = get_db()
    query = {"run_id": run_id} if run_id else {}
    docs  = list(db.deals.find(query).sort("saved_at", -1).limit(200))
    return [_strip_id(d) for d in docs]


def search_deals_by_text(query: str, limit: int = 20) -> list[dict]:
    """Full-text search across deals using MongoDB text index."""
    db   = get_db()
    docs = list(db.deals.find({"$text": {"$search": query}}).limit(limit))
    return [_strip_id(d) for d in docs]


# ─── Newsletter ───────────────────────────────────────────────────────────────

def save_newsletter(text: str, run_id: str) -> str:
    """Save a generated newsletter to MongoDB. Returns inserted doc id."""
    db = get_db()
    result = db.newsletters.insert_one({
        "text":       text,
        "run_id":     run_id,
        "created_at": _now(),
        "char_count": len(text),
    })
    return str(result.inserted_id)


def load_latest_newsletter() -> str:
    """Return the most recently generated newsletter text."""
    db  = get_db()
    doc = db.newsletters.find_one(sort=[("created_at", -1)])
    return doc["text"] if doc else ""


def load_newsletters(limit: int = 10) -> list[dict]:
    """Return the N most recent newsletters."""
    db   = get_db()
    docs = list(db.newsletters.find().sort("created_at", -1).limit(limit))
    return [_strip_id(d) for d in docs]


# ─── Stats ────────────────────────────────────────────────────────────────────

def get_pipeline_stats() -> dict:
    """Return collection counts as a summary dict."""
    db = get_db()
    return {
        "raw_articles":            db.raw_articles.count_documents({}),
        "cleaned_articles":        db.cleaned_articles.count_documents({}),
        "deduplicated_articles":   db.deduplicated_articles.count_documents({}),
        "relevant_articles":       db.relevant_articles.count_documents({}),
        "credible_articles":       db.credible_articles.count_documents({}),
        "deals":                   db.deals.count_documents({}),
        "newsletters":             db.newsletters.count_documents({}),
        "pipeline_runs":           db.pipeline_runs.count_documents({}),
    }


if __name__ == "__main__":
    if is_connected():
        print("✅ MongoDB connected")
        print("Stats:", get_pipeline_stats())
    else:
        print("❌ Could not connect to MongoDB. Check MONGO_URI in .env")
