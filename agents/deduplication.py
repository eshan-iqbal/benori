
import json
import os
from rapidfuzz import fuzz
from agents.cleaning import load_cleaned_articles, DATA_CLEANED_DIR

DATA_PROCESSED_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "processed")

def remove_exact_duplicates(articles):
    seen_urls = set()
    seen_titles = set()
    unique = []
    for article in articles:
        url = article.get("url", "")
        title = article.get("title", "")
        if url not in seen_urls and title not in seen_titles:
            seen_urls.add(url)
            seen_titles.add(title)
            unique.append(article)
    return unique

def remove_fuzzy_duplicates(articles, threshold=90):
    if len(articles) <= 1:
        return articles
    unique = [articles[0]]
    for article in articles[1:]:
        duplicate = False
        for u in unique:
            similarity = fuzz.token_set_ratio(article.get("title", ""), u.get("title", ""))
            if similarity > threshold:
                duplicate = True
                break
        if not duplicate:
            unique.append(article)
    return unique

def deduplicate_articles(articles):
    print(f"Starting with {len(articles)} articles")
    articles = remove_exact_duplicates(articles)
    print(f"After exact duplicates: {len(articles)}")
    articles = remove_fuzzy_duplicates(articles)
    print(f"After fuzzy duplicates: {len(articles)}")
    return articles

def save_processed_articles(articles, filename="deduplicated_articles.json"):
    if not os.path.exists(DATA_PROCESSED_DIR):
        os.makedirs(DATA_PROCESSED_DIR)
    filepath = os.path.join(DATA_PROCESSED_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)
    return filepath

def load_deduplicated_articles(filename="deduplicated_articles.json"):
    filepath = os.path.join(DATA_PROCESSED_DIR, filename)
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

if __name__ == "__main__":
    cleaned = load_cleaned_articles()
    deduplicated = deduplicate_articles(cleaned)
    save_processed_articles(deduplicated)
    print(f"Deduplicated to {len(deduplicated)} articles")

