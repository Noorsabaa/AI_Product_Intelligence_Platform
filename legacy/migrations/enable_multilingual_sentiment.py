import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).resolve().parents[1] / "data" / "reviews.db"


def enable_multilingual_sentiment():
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("DROP VIEW IF EXISTS reviews_categorized_confident")
        conn.execute("DROP VIEW IF EXISTS reviews_trend_window")
        conn.execute("""
            CREATE VIEW reviews_trend_window AS
            SELECT r.*
            FROM reviews r
            WHERE r.is_analyzable = 1
              AND r.review_date >= date('now', '-180 days')
        """)
        conn.execute("""
            CREATE VIEW reviews_categorized_confident AS
            SELECT *
            FROM reviews_trend_window
            WHERE category IS NOT NULL
                            AND category_confidence >= 0.7
        """)
        conn.commit()
    finally:
        conn.close()
    print("Multilingual sentiment views enabled.")


if __name__ == "__main__":
    enable_multilingual_sentiment()