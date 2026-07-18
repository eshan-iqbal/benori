
import json
import os
from openai import OpenAI
from dotenv import load_dotenv
from agents.deduplication import load_deduplicated_articles, DATA_PROCESSED_DIR

load_dotenv()
client = OpenAI(
    api_key=os.getenv("PERPLEXITY_API_KEY"),
    base_url="https://api.perplexity.ai"
)

SYSTEM_PROMPT = (
    "You are a precise financial news classifier specializing in FMCG (Fast-Moving Consumer Goods) industry intelligence. "
    "Your sole task is to determine whether a given article is directly about an FMCG deal event such as a merger, acquisition, "
    "investment round, funding, strategic partnership, or joint venture involving an FMCG company. "
    "Respond with exactly one word: YES or NO."
)

def is_fmcg_deal_article(article):
    title   = article.get("title", "").strip()
    summary = article.get("summary", "").strip()
    content = article.get("content", "").strip()

    # Compose a concise user message — truncate content to keep tokens low
    user_text = (
        f"Title: {title}\n"
        f"Summary: {summary}\n"
        f"Content (excerpt): {content[:800]}"
    )

    try:
        response = client.chat.completions.create(
            model="sonar",          # Sonar: fast reasoning model, no live web search needed
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_text},
            ],
            max_tokens=16,  # Perplexity minimum is 16
            temperature=0,
        )
        answer = response.choices[0].message.content.strip().upper()
        return answer.startswith("YES")
    except Exception as e:
        print(f"Error checking relevance for '{title}': {e}")
        return False

def filter_relevant_articles(articles):
    relevant = []
    for article in articles:
        if is_fmcg_deal_article(article):
            relevant.append(article)
    return relevant

def save_relevant_articles(articles, filename="relevant_articles.json"):
    filepath = os.path.join(DATA_PROCESSED_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)
    return filepath

def load_relevant_articles(filename="relevant_articles.json"):
    filepath = os.path.join(DATA_PROCESSED_DIR, filename)
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

if __name__ == "__main__":
    deduplicated = load_deduplicated_articles()
    relevant = filter_relevant_articles(deduplicated)
    save_relevant_articles(relevant)
    print(f"Filtered to {len(relevant)} relevant FMCG deal articles")
