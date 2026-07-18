
import json
import os
from openai import OpenAI
from dotenv import load_dotenv
from agents.credibility import load_credible_articles, DATA_PROCESSED_DIR

load_dotenv()
client = OpenAI(
    api_key=os.getenv("PERPLEXITY_API_KEY"),
    base_url="https://api.perplexity.ai"
)

SYSTEM_PROMPT = (
    "You are a structured data extraction specialist for M&A and investment news in the FMCG industry. "
    "Given an article, extract deal information and return ONLY a valid JSON object with these exact keys: "
    "buyer, seller, target_company, deal_type, value, country, industry, summary. "
    "Use null for any field you cannot determine. Do not include any explanation, markdown, or text outside the JSON object."
)

def extract_deal_info(article):
    title   = article.get("title", "").strip()
    summary = article.get("summary", "").strip()
    content = article.get("content", "").strip()

    user_text = (
        f"Title: {title}\n"
        f"Summary: {summary}\n"
        f"Content (excerpt): {content[:1200]}"
    )

    try:
        response = client.chat.completions.create(
            model="sonar",          # sonar: fast + no web search needed; we supply the text
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_text},
            ],
            max_tokens=512,
            temperature=0,
        )
        raw = response.choices[0].message.content or ""

        # Robustly extract the first {...} block
        start = raw.find("{")
        end   = raw.rfind("}")
        if start != -1 and end != -1:
            return json.loads(raw[start:end + 1])
        return {}
    except json.JSONDecodeError as e:
        print(f"JSON parse error for '{title}': {e}")
        return {}
    except Exception as e:
        print(f"Error extracting info for '{title}': {e}")
        return {}

def extract_all_deals(articles):
    deals = []
    for article in articles:
        deal = extract_deal_info(article)
        if deal:
            deal["article"] = article
            deals.append(deal)
    return deals

def save_deals(deals, filename="deals.json"):
    filepath = os.path.join(DATA_PROCESSED_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(deals, f, ensure_ascii=False, indent=2)
    return filepath

def load_deals(filename="deals.json"):
    filepath = os.path.join(DATA_PROCESSED_DIR, filename)
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

if __name__ == "__main__":
    credible = load_credible_articles()
    deals = extract_all_deals(credible)
    save_deals(deals)
    print(f"Extracted {len(deals)} deals")
