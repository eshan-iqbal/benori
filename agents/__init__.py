
from .ingestion import fetch_multi_source_news, save_articles, load_articles
from .cleaning import clean_articles, save_cleaned_articles, load_cleaned_articles
from .deduplication import deduplicate_articles, save_processed_articles, load_deduplicated_articles
from .relevance import filter_relevant_articles, save_relevant_articles, load_relevant_articles
from .credibility import filter_by_credibility, save_credible_articles, load_credible_articles
from .extraction import extract_all_deals, save_deals, load_deals
from .newsletter import generate_newsletter
from .exporter import export_to_csv, export_to_json, export_to_excel, export_to_word, export_to_powerpoint
from .embedding import embed_articles, embed_deals, get_embedding
from .database import (
    get_db, is_connected, get_pipeline_stats,
    create_pipeline_run, finish_pipeline_run,
    save_raw_articles, save_cleaned_articles as db_save_cleaned,
    save_deduplicated_articles, save_relevant_articles as db_save_relevant,
    save_credible_articles as db_save_credible,
    save_deals as db_save_deals, load_deals as db_load_deals,
    save_newsletter, load_latest_newsletter, load_newsletters,
    search_deals_by_text,
)

