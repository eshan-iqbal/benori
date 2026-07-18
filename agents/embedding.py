"""
embedding.py
Generates vector embeddings for articles using Perplexity's embedding model.
Embeddings are used for semantic deduplication and similarity search in MongoDB.
"""

import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.getenv("PERPLEXITY_API_KEY"),
    base_url="https://api.perplexity.ai"
)

EMBEDDING_MODEL = "llama-3.1-sonar-small-128k-online"  # Perplexity embedding-compatible model


def get_embedding(text: str) -> list[float]:
    """
    Generate a vector embedding for a given text string.
    Note: Perplexity API currently does not support an /embeddings endpoint.
    Returning an empty list to allow the pipeline to proceed without 404 errors.
    If you add an OpenAI key later, you can swap this back to OpenAI's text-embedding-ada-002.
    """
    return []


def embed_article(article: dict) -> dict:
    """
    Attach an embedding vector to an article dict.
    The embedding is generated from title + summary + content excerpt.
    """
    text = " ".join([
        article.get("title", ""),
        article.get("summary", ""),
        article.get("content", "")[:500]
    ]).strip()

    embedding = get_embedding(text)
    return {**article, "embedding": embedding}


def embed_articles(articles: list[dict]) -> list[dict]:
    """Generate embeddings for a list of articles."""
    embedded = []
    for i, article in enumerate(articles):
        print(f"  Embedding article {i+1}/{len(articles)}: {article.get('title', '')[:60]}")
        embedded.append(embed_article(article))
    return embedded


def embed_deal(deal: dict) -> dict:
    """
    Attach an embedding vector to a deal dict.
    Embedding generated from deal summary + company names + deal type.
    """
    text = " ".join(filter(None, [
        deal.get("target_company", ""),
        deal.get("buyer", ""),
        deal.get("deal_type", ""),
        deal.get("industry", ""),
        deal.get("summary", ""),
    ])).strip()

    embedding = get_embedding(text)
    return {**deal, "embedding": embedding}


def embed_deals(deals: list[dict]) -> list[dict]:
    """Generate embeddings for a list of extracted deals."""
    embedded = []
    for i, deal in enumerate(deals):
        print(f"  Embedding deal {i+1}/{len(deals)}: {deal.get('target_company', 'Unknown')}")
        embedded.append(embed_deal(deal))
    return embedded


if __name__ == "__main__":
    # Quick smoke test
    test_text = "Hindustan Unilever acquires Minimalist skincare brand for Rs 2955 crore"
    vec = get_embedding(test_text)
    if vec:
        print(f"✅ Embedding generated: {len(vec)} dimensions")
        print(f"   First 5 values: {vec[:5]}")
    else:
        print("❌ Embedding failed")
