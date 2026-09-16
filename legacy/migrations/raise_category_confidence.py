import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).resolve().parents[1] / "data" / "reviews.db"


def raise_category_confidence():
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("DROP VIEW IF EXISTS reviews_categorized_confident")
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
    print("Category confidence threshold set to 0.7.")


if __name__ == "__main__":
    raise_category_confidence()