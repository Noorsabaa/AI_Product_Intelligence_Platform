import argparse

from db.connection import get_connection
from ingestion.scraper import scrape_and_store_reviews, upsert_app
from scripts.init_db import init_db
from api.routers.pipeline import run_full_pipeline


def ingest_app(app_name, package_name, days_back, lang, country, count):
    init_db()
    conn = get_connection()
    try:
        app_id = upsert_app(conn, app_name, package_name)
        inserted = scrape_and_store_reviews(
            conn,
            app_id,
            package_name,
            count=count,
            days_back=days_back,
            lang=lang,
            country=country,
        )
    finally:
        conn.close()

    print(f"Inserted {inserted} new reviews for {app_name}.")
    print("Starting analysis pipeline...")
    run_full_pipeline()


def main():
    parser = argparse.ArgumentParser(
        description="Scrape one Google Play app and run the full analysis pipeline."
    )
    parser.add_argument("--name", required=True, help="Display name for the app")
    parser.add_argument(
        "--package", required=True, help="Google Play package ID, e.g. com.trello"
    )
    parser.add_argument(
        "--days", type=int, default=180, help="Review window in days (default: 180)"
    )
    parser.add_argument(
        "--lang", default="en", help="Google Play language code (default: en)"
    )
    parser.add_argument(
        "--country", default="us", help="Google Play country code (default: us)"
    )
    parser.add_argument(
        "--count", type=int, default=200, help="Reviews requested per page (default: 200)"
    )
    args = parser.parse_args()

    if args.days < 1:
        parser.error("--days must be at least 1")
    if not 1 <= args.count <= 200:
        parser.error("--count must be between 1 and 200")

    ingest_app(
        args.name.strip(),
        args.package.strip(),
        args.days,
        args.lang.strip(),
        args.country.strip(),
        args.count,
    )


if __name__ == "__main__":
    main()
