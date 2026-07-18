
import json
import os
from agents.relevance import load_relevant_articles, DATA_PROCESSED_DIR

SOURCE_SCORES = {
    "Reuters": 10,
    "Bloomberg": 10,
    "CNBC": 9,
    "Economic Times": 8,
    "Mint": 8,
    "Business Standard": 7,
    "Google News": 5
}

def calculate_credibility_score(article):
    score = 0
    source = article.get("source", "")
    for s in SOURCE_SCORES:
        if s.lower() in source.lower():
            score += SOURCE_SCORES[s]
            break
    
    url = article.get("url", "")
    if url.startswith("https://"):
        score += 1
    
    if article.get("content", "") and len(article["content"]) > 100:
        score +=1
    
    return score

def filter_by_credibility(articles, min_score=1):
    scored = []
    for article in articles:
        score = calculate_credibility_score(article)
        article["credibility_score"] = score
        # Lowered min_score to 1 because anti-bot paywalls often block content fetching,
        # leaving articles with just an HTTPS url (score = 1) and a title/summary.
        if score >= min_score:
            scored.append(article)
    scored.sort(key=lambda x: x["credibility_score"], reverse=True)
    return scored

def save_credible_articles(articles, filename="credible_articles.json"):
    filepath = os.path.join(DATA_PROCESSED_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)
    return filepath

def load_credible_articles(filename="credible_articles.json"):
    filepath = os.path.join(DATA_PROCESSED_DIR, filename)
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

if __name__ == "__main__":
    relevant = load_relevant_articles()
    credible = filter_by_credibility(relevant)
    save_credible_articles(credible)
    print(f"Filtered to {len(credible)} credible articles")

