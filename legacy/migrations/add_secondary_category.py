import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).resolve().parents[1] / "data" / "reviews.db"


def add_secondary_category():
    conn = sqlite3.connect(DB_PATH)
    try:
        columns = (
            ("secondary_category", "TEXT"),
            ("secondary_category_confidence", "REAL"),
        )
        for column_name, column_type in columns:
            try:
                conn.execute(f"ALTER TABLE reviews ADD COLUMN {column_name} {column_type}")
            except sqlite3.OperationalError as error:
                if "duplicate column name" not in str(error):
                    raise
        conn.commit()
    finally:
        conn.close()
    print("Secondary category columns enabled.")


if __name__ == "__main__":
    add_secondary_category()