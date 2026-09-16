# scripts/ingest_all_apps.py
from db.connection import get_connection
from ingestion.scraper import upsert_app, scrape_and_store_reviews


APPS = [
    ("Zoom", "us.zoom.videomeetings"),
    ("Slack", "com.Slack"),
    ("Microsoft Teams", "com.microsoft.teams"),
    ("Asana", "com.asana.app"),
    ("ClickUp", "co.mangotechnologies.clickup"),
    ("Notion", "notion.id"),
]


def ingest_all_apps(days_back=180):
    conn = get_connection()
    try:
        for app_name, package_name in APPS:
            print("\n" + "=" * 60)
            print(f"Processing: {app_name}")
            print(f"Package ID: {package_name}")
            print("=" * 60)

            app_id = upsert_app(conn, app_name, package_name)
            print(f"App ID: {app_id}")

            inserted = scrape_and_store_reviews(
                conn, app_id, package_name,
                count=200, days_back=days_back,
                max_pages=100, max_reviews=20000,
            )
            print(f"Reviews inserted: {inserted}")
    finally:
        conn.close()


if __name__ == "__main__":
    ingest_all_apps(days_back=180)