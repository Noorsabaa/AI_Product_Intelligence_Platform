import sqlite3

DB_PATH = "data/reviews.db"


def create_trend_window():
    conn = sqlite3.connect(DB_PATH)

    conn.execute("""
        CREATE VIEW IF NOT EXISTS reviews_trend_window AS
        SELECT r.*
        FROM reviews r
        WHERE r.is_analyzable = 1
          AND r.language != 'other'
          AND r.review_date >= date('now', '-180 days');
    """)

    conn.commit()
    conn.close()

    print("reviews_trend_window created successfully.")


if __name__ == "__main__":
    create_trend_window()