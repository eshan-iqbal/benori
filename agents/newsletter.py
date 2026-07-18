
import json
import os
from openai import OpenAI
from dotenv import load_dotenv
from agents.extraction import load_deals, DATA_PROCESSED_DIR
from datetime import datetime

load_dotenv()
client = OpenAI(
    api_key=os.getenv("PERPLEXITY_API_KEY"),
    base_url="https://api.perplexity.ai"
)

def generate_newsletter(deals: list[dict], target_date: str = None) -> str:
    """
    Generate an executive FMCG newsletter based on extracted deals.
    If target_date is provided, it uses that date for the newsletter header.
    """
    date_str = target_date if target_date else datetime.now().strftime("%B %d, %Y")
    
    system_prompt = (
        "You are an experienced business intelligence analyst and newsletter writer. "
        "Your task is to produce a concise, executive-level FMCG (Fast-Moving Consumer Goods) industry intelligence newsletter "
        "from the structured deal data provided. "
        "Structure the newsletter in these sections:\n"
        "1. Header with date\n"
        "2. Top Deals (most significant M&A)\n"
        "3. Funding Activity\n"
        "4. Strategic Investments & Partnerships\n"
        "5. Market Trends\n"
        "6. Key Takeaways\n\n"
        "Use clear, professional language. The newsletter should be readable in under 5 minutes. "
        "Use markdown formatting (## for headings, - for bullets, **bold** for key figures)."
    )

    deals_text = json.dumps(deals, indent=2, default=str)

    user_text = (
        f"Today's date: {date_str}\n\n"
        f"Deal data ({len(deals)} deals):\n{deals_text}"
    )

    try:
        response = client.chat.completions.create(
            model="sonar-pro",      # sonar-pro: better for long-form creative/analytical writing
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_text},
            ],
            max_tokens=2048,
            temperature=0.5,        # slight creativity for readability
        )
        return response.choices[0].message.content or ""
    except Exception as e:
        print(f"Error generating newsletter: {e}")
        return ""

if __name__ == "__main__":
    deals = load_deals()
    newsletter = generate_newsletter(deals)
    print(newsletter)
