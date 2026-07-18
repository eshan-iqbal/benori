
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sys
import os
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents import (
    # Pipeline stages
    fetch_multi_source_news, save_articles, load_articles,
    clean_articles, save_cleaned_articles, load_cleaned_articles,
    deduplicate_articles, save_processed_articles, load_deduplicated_articles,
    filter_relevant_articles, save_relevant_articles, load_relevant_articles,
    filter_by_credibility, save_credible_articles, load_credible_articles,
    extract_all_deals, save_deals, load_deals,
    generate_newsletter,
    export_to_csv, export_to_json, export_to_excel, export_to_word, export_to_powerpoint,
    # Embeddings
    embed_articles, embed_deals,
    # MongoDB
    is_connected, get_pipeline_stats,
    create_pipeline_run, finish_pipeline_run,
    save_raw_articles, db_save_cleaned, save_deduplicated_articles,
    db_save_relevant, db_save_credible,
    db_save_deals, db_load_deals,
    save_newsletter, load_latest_newsletter, load_newsletters,
    search_deals_by_text,
)

load_dotenv()

app = FastAPI(title="FMCG Intelligence Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:3002"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Health ───────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    mongo_ok = is_connected()
    return {
        "message": "FMCG Intelligence Agent API",
        "mongodb": "connected" if mongo_ok else "disconnected",
    }

@app.get("/db/stats")
async def db_stats():
    """Return MongoDB collection counts."""
    if not is_connected():
        raise HTTPException(status_code=503, detail="MongoDB not connected")
    return get_pipeline_stats()

# ─── Pipeline ─────────────────────────────────────────────────────────────────

@app.post("/fetch-news")
async def fetch_news():
    articles = fetch_multi_source_news()
    save_articles(articles)
    return {"count": len(articles), "articles": articles}


from pydantic import BaseModel
from typing import Optional

class PipelineRequest(BaseModel):
    target_date: Optional[str] = None

@app.post("/run-pipeline")
async def run_pipeline(req: PipelineRequest = PipelineRequest()):
    """Execute the full autonomous pipeline."""
    run_id = None
    mongo_ok = is_connected()
    if mongo_ok:
        run_id = create_pipeline_run({"source": "api", "max_results": 20, "target_date": req.target_date})

    # ── Stage 1: Fetch ────────────────────────────────────────────────────────
    articles = fetch_multi_source_news(max_results=20, target_date=req.target_date)
    save_articles(articles)
    if mongo_ok:
        save_raw_articles(articles, run_id)

    # ── Stage 2: Clean ────────────────────────────────────────────────────────
    cleaned = clean_articles(articles)
    save_cleaned_articles(cleaned)
    if mongo_ok:
        db_save_cleaned(cleaned, run_id)

    # ── Stage 3: Deduplicate ──────────────────────────────────────────────────
    deduplicated = deduplicate_articles(cleaned)
    save_processed_articles(deduplicated)
    if mongo_ok:
        save_deduplicated_articles(deduplicated, run_id)

    # ── Stage 4: Relevance (AI) ───────────────────────────────────────────────
    relevant = filter_relevant_articles(deduplicated)
    save_relevant_articles(relevant)
    if mongo_ok:
        # Embed relevant articles before saving
        print("Generating embeddings for relevant articles...")
        relevant_embedded = embed_articles(relevant)
        db_save_relevant(relevant_embedded, run_id)
    else:
        relevant_embedded = relevant

    # ── Stage 5: Credibility ──────────────────────────────────────────────────
    credible = filter_by_credibility(relevant)
    save_credible_articles(credible)
    if mongo_ok:
        db_save_credible(credible, run_id)

    # ── Stage 6: Extraction (AI) ──────────────────────────────────────────────
    deals = extract_all_deals(credible)
    if mongo_ok:
        # Embed deals before saving to MongoDB
        print("Generating embeddings for deals...")
        deals_embedded = embed_deals(deals)
        db_save_deals(deals_embedded, run_id)
    save_deals(deals)

    # ── Stage 7: Newsletter (AI) ──────────────────────────────────────────────
    newsletter = generate_newsletter(deals, target_date=req.target_date)
    if mongo_ok:
        save_newsletter(newsletter, run_id)

    # ── Stage 8: Exports ──────────────────────────────────────────────────────
    export_to_csv(deals)
    export_to_json(deals)
    export_to_excel(deals)
    export_to_word(newsletter, deals)
    export_to_powerpoint(newsletter, deals)

    # ── Finish run record ─────────────────────────────────────────────────────
    if mongo_ok:
        finish_pipeline_run(run_id, {
            "raw_count":        len(articles),
            "cleaned_count":    len(cleaned),
            "dedup_count":      len(deduplicated),
            "relevant_count":   len(relevant),
            "credible_count":   len(credible),
            "deals_count":      len(deals),
            "newsletter_chars": len(newsletter),
        })

    return {
        "run_id":       run_id,
        "mongodb":      "saved" if mongo_ok else "skipped (not connected)",
        "deals_count":  len(deals),
        "deals":        deals,
        "newsletter":   newsletter,
    }

# ─── Deals ────────────────────────────────────────────────────────────────────

@app.get("/deals")
async def get_deals(source: str = "file"):
    """
    Get deals.
    source=file  → load from local JSON (default)
    source=mongo → load from MongoDB
    """
    if source == "mongo":
        if not is_connected():
            raise HTTPException(status_code=503, detail="MongoDB not connected")
        return {"deals": db_load_deals()}
    return {"deals": load_deals()}


@app.get("/deals/search")
async def search_deals(q: str):
    """Full-text search across deals stored in MongoDB."""
    if not is_connected():
        raise HTTPException(status_code=503, detail="MongoDB not connected")
    results = search_deals_by_text(q)
    return {"results": results, "count": len(results)}

# ─── Newsletter ───────────────────────────────────────────────────────────────

@app.get("/newsletter")
async def get_newsletter(source: str = "file"):
    """
    Get newsletter.
    source=file  → regenerate from local deals JSON
    source=mongo → return latest saved newsletter from MongoDB
    """
    if source == "mongo":
        if not is_connected():
            raise HTTPException(status_code=503, detail="MongoDB not connected")
        text = load_latest_newsletter()
        return {"newsletter": text}
    deals = load_deals()
    newsletter = generate_newsletter(deals)
    return {"newsletter": newsletter}

@app.get("/newsletters")
async def list_newsletters(limit: int = 10):
    """List recent newsletters from MongoDB."""
    if not is_connected():
        raise HTTPException(status_code=503, detail="MongoDB not connected")
    return {"newsletters": load_newsletters(limit)}

# ─── Downloads ────────────────────────────────────────────────────────────────

@app.get("/exports/{file_format}")
async def download_export(file_format: str):
    exports_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "exports")
    filename    = f"newsletter.{file_format}"
    filepath    = os.path.join(exports_dir, filename)
    if os.path.exists(filepath):
        return FileResponse(filepath, filename=filename)
    raise HTTPException(status_code=404, detail="Export not found. Run the pipeline first.")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
