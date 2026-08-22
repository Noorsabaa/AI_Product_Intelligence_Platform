# scripts/generate_recommendations.py
import os
import time
import sqlite3
import pandas as pd
from google import genai
from google.genai import errors as genai_errors
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
MODEL_NAME = "gemini-3.6-flash"

DB_PATH = "data/reviews.db"
SPIKES_CSV = "scratch/detected_spikes.csv"
OUTPUT_CSV = "scratch/recommendations.csv"
DELAY_BETWEEN_CALLS = 5  # seconds, stay well under daily/per-minute limits

PROMPT_TEMPLATE = """You are helping a Customer Success Manager at a B2B SaaS company understand a spike in customer complaints.

App: {app_name}
Complaint category: {category}
Time period: {period} ({granularity})
This period's complaint count: {count}
Normal baseline: {baseline}
Increase: {pct_change}% above baseline

Sample of actual customer reviews from this period:
{sample_reviews}

Write a short, plain-English brief for a Customer Success Manager with exactly two parts:
1. WHAT HAPPENED: 1-2 sentences summarizing the issue based on the actual review text, not generic language.
2. RECOMMENDED ACTION: 1-2 sentences on what the CSM or their team should do about it.

Be specific and grounded in the review content. Do not invent details not supported by the reviews."""


def get_sample_reviews(conn, app_name, category, period, granularity, n=8):
    date_filter = (
        "strftime('%Y-%W', r.review_date) = strftime('%Y-%W', ?)"
        if granularity == "weekly"
        else "strftime('%Y-%m', r.review_date) = strftime('%Y-%m', ?)"
    )
    app_filter = "a.app_name = ?" if app_name != "ALL APPS" else "1=1"
    query = f"""
        SELECT r.content FROM reviews_categorized_confident r
        JOIN apps a ON r.app_id = a.app_id
        WHERE {date_filter} AND r.category = ? AND {app_filter}
        ORDER BY RANDOM() LIMIT {n}
    """
    params = [period, category]
    if app_name != "ALL APPS":
        params.append(app_name)
    rows = conn.execute(query, params).fetchall()
    return [r[0] for r in rows]


def load_existing_results():
    if os.path.exists(OUTPUT_CSV):
        return pd.read_csv(OUTPUT_CSV)
    return pd.DataFrame()


def generate_recommendations():
    spikes = pd.read_csv(SPIKES_CSV)
    existing = load_existing_results()
    done_keys = set()
    if not existing.empty:
        done_keys = set(zip(existing["app_name"], existing["category"], existing["period"]))

    conn = sqlite3.connect(DB_PATH)
    results = existing.to_dict("records") if not existing.empty else []

    for _, row in spikes.iterrows():
        key = (row["app_name"], row["category"], row["period"])
        if key in done_keys:
            continue  # already have a good brief, skip

        reviews = get_sample_reviews(
            conn, row["app_name"], row["category"], row["period"], row["granularity"]
        )
        sample_text = "\n".join(f"- {r[:200]}" for r in reviews) if reviews else "(no sample text available)"

        prompt = PROMPT_TEMPLATE.format(
            app_name=row["app_name"], category=row["category"],
            period=row["period"], granularity=row["granularity"],
            count=row["count"], baseline=row["baseline"],
            pct_change=row["pct_change"], sample_reviews=sample_text,
        )

        try:
            response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
            brief = response.text.strip()
        except genai_errors.ClientError as e:
            if "RESOURCE_EXHAUSTED" in str(e):
                print("Daily/rate quota hit. Stopping here — rerun later to resume.")
                break
            brief = f"ERROR generating brief: {e}"
        except Exception as e:
            brief = f"ERROR generating brief: {e}"

        print(f"\n=== {row['app_name']} | {row['category']} | {row['period']} ===")
        print(brief)
        results.append({**row.to_dict(), "brief": brief})

        pd.DataFrame(results).to_csv(OUTPUT_CSV, index=False)  # save after every call
        time.sleep(DELAY_BETWEEN_CALLS)

    conn.close()
    print(f"\nSaved {len(results)} briefs total to {OUTPUT_CSV}")


if __name__ == "__main__":
    generate_recommendations()