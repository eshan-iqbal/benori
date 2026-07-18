
import re
import json
import os
from agents.ingestion import load_articles, DATA_RAW_DIR

DATA_CLEANED_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "cleaned")

def clean_text(text):
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    text = text.encode('ascii', 'ignore').decode('ascii')
    return text

def clean_articles(articles):
    cleaned = []
    for article in articles:
        cleaned_article = {
            **article,
            "title": clean_text(article.get("title", "")),
            "summary": clean_text(article.get("summary", "")),
            "content": clean_text(article.get("content", ""))
        }
        cleaned.append(cleaned_article)
    return cleaned

def save_cleaned_articles(articles, filename="cleaned_articles.json"):
    if not os.path.exists(DATA_CLEANED_DIR):
        os.makedirs(DATA_CLEANED_DIR)
    filepath = os.path.join(DATA_CLEANED_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)
    return filepath

def load_cleaned_articles(filename="cleaned_articles.json"):
    filepath = os.path.join(DATA_CLEANED_DIR, filename)
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

if __name__ == "__main__":
    raw_articles = load_articles()
    cleaned_articles = clean_articles(raw_articles)
    save_cleaned_articles(cleaned_articles)
    print(f"Cleaned {len(cleaned_articles)} articles")

