from db.connection import get_connection
from pathlib import Path


def init_db():
    schema_path = Path(__file__).resolve().parent.parent / "db" / "schema.sql"
    schema_sql = schema_path.read_text()

    conn = get_connection()
    conn.executescript(schema_sql)
    conn.commit()
    conn.close()

    print("Database initialized successfully.")


if __name__ == "__main__":
    init_db()