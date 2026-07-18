
import feedparser
import requests
from newspaper import Article
from datetime import datetime, timedelta
import json
import os

DATA_RAW_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "raw")

def fetch_multi_source_news(query="top FMCG deals in India merger acquisition investment funding partnership", max_results=30, target_date=None):
    articles = []
    
    if target_date:
        try:
            dt = datetime.strptime(target_date, "%Y-%m-%d")
            after = (dt - timedelta(days=1)).strftime("%Y-%m-%d")
            before = (dt + timedelta(days=2)).strftime("%Y-%m-%d") # +2 to include the day itself fully
            query += f" after:{after} before:{before}"
            print(f"Applying date filter to query: {query}")
        except Exception as e:
            print(f"Invalid date format {target_date}: {e}")

    # Define our 3 sources
    rss_feeds = [
        # 1. Google News Search (Broad Coverage)
        f"https://news.google.com/rss/search?q={query.replace(' ', '+')}&hl=en-IN&gl=IN&ceid=IN:en",
        
        # 2. Economic Times FMCG Specific Feed
        "https://economictimes.indiatimes.com/industry/cons-products/fmcg/rssfeeds/27521798.cms",
        
        # 3. Mint Companies Feed (Good for Indian M&A)
        "https://www.livemint.com/rss/companies"
    ]
    
    for rss_url in rss_feeds:
        print(f"Fetching from source: {rss_url[:60]}...")
        try:
            response = requests.get(rss_url, timeout=30)
            response.raise_for_status()
            feed = feedparser.parse(response.content)
            
            # Take top N from each source to balance them
            for entry in feed.entries[:15]: 
                try:
                    article = {
                        "title": entry.get("title", ""),
                        "url": entry.get("link", ""),
                        "source": entry.get("source", {}).get("title", "") or "News Publisher",
                        "date": entry.get("published", datetime.now().isoformat()),
                        "summary": entry.get("summary", ""),
                        "content": ""
                    }
                    
                    try:
                        news_article = Article(article["url"])
                        news_article.download()
                        news_article.parse()
                        article["content"] = news_article.text
                    except Exception:
                        pass # Skip content fetch failures quietly to speed up
                        
                    articles.append(article)
                except Exception as e:
                    pass
        except Exception as e:
            print(f"Failed to fetch RSS feed {rss_url}: {e}")
            
    # Limit total to max_results to keep LLM fast, but we now have diverse sources
    return articles[:max_results]

def save_articles(articles, filename="raw_articles.json"):
    if not os.path.exists(DATA_RAW_DIR):
        os.makedirs(DATA_RAW_DIR)
    filepath = os.path.join(DATA_RAW_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)
    return filepath

def load_articles(filename="raw_articles.json"):
    filepath = os.path.join(DATA_RAW_DIR, filename)
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

if __name__ == "__main__":
    articles = fetch_google_news_rss()
    print(f"Fetched {len(articles)} articles")
    save_articles(articles)

