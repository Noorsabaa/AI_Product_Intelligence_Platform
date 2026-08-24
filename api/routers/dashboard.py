import sqlite3
from fastapi import APIRouter

router = APIRouter()

DB_PATH = "data/reviews.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@router.get("/summary")
def summary():
    conn = get_conn()

    total_reviews = conn.execute("""
        SELECT COUNT(*) AS c
        FROM reviews_trend_window
    """).fetchone()["c"]

    sentiment_counts = dict(conn.execute("""
        SELECT sentiment, COUNT(*) AS c
        FROM reviews_trend_window
        WHERE sentiment IS NOT NULL
        GROUP BY sentiment
    """).fetchall())

    per_app = [
        dict(row)
        for row in conn.execute("""
            SELECT
                a.app_name,
                COUNT(*) AS review_count,
                ROUND(AVG(r.score), 2) AS avg_score
            FROM reviews_trend_window r
            JOIN apps a ON r.app_id = a.app_id
            GROUP BY a.app_name
            ORDER BY review_count DESC
        """).fetchall()
    ]

    conn.close()

    return {
        "total_reviews_last_180_days": total_reviews,
        "sentiment_breakdown": sentiment_counts,
        "per_app": per_app,
    }


@router.get("/categories")
def categories():
    conn = get_conn()

    rows = [
        dict(row)
        for row in conn.execute("""
            SELECT
                category,
                COUNT(*) AS count
            FROM reviews_categorized_confident
            GROUP BY category
            ORDER BY count DESC
        """).fetchall()
    ]

    conn.close()

    return {
        "categories": rows
    }

@router.get("/spikes")
def spikes():
    try:
        import pandas as pd

        df = pd.read_csv("scratch/detected_spikes.csv")

    except FileNotFoundError:
        return {"spikes": []}

    return {
        "spikes": df.to_dict("records")
    }

@router.get("/recommendations")
def recommendations():
    try:
        import pandas as pd

        df = pd.read_csv("scratch/recommendations.csv")

    except FileNotFoundError:
        return {"recommendations": []}

    return {
        "recommendations": df.to_dict("records")
    }