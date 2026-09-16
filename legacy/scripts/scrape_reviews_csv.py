import argparse
import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path

from google_play_scraper import Sort, reviews

DEFAULT_APPS = {
    "slack": ("Slack", "com.Slack"),
    "zoom": ("Zoom", "us.zoom.videomeetings"),
    "notion": ("Notion", "notion.id"),
    "trello": ("Trello", "com.trello"),
    "asana": ("Asana", "com.asana.app"),
    "clickup": ("ClickUp", "co.mangotechnologies.clickup"),
    "teams": ("Microsoft Teams", "com.microsoft.teams"),
}
COLUMNS = ["app_name", "content", "review_date", "score"]


def scrape_app(app_name, package_name, cutoff, lang, country, count, max_reviews):
    rows = []
    continuation_token = None

    while len(rows) < max_reviews:
        batch, continuation_token = reviews(
            package_name,
            lang=lang,
            country=country,
            sort=Sort.NEWEST,
            count=min(count, max_reviews - len(rows)),
            continuation_token=continuation_token,
        )
        if not batch:
            break

        reached_cutoff = False
        for review in batch:
            if len(rows) >= max_reviews:
                break
            review_date = review["at"]
            if review_date < cutoff:
                reached_cutoff = True
                break
            if not review.get("content"):
                continue
            rows.append({
                "app_name": app_name,
                "content": review["content"].strip(),
                "review_date": review_date.isoformat(),
                "score": review["score"],
            })

        if reached_cutoff or continuation_token is None:
            break

    return rows


def main():
    parser = argparse.ArgumentParser(
        description="Scrape Google Play SaaS reviews into a pipeline-compatible CSV."
    )
    parser.add_argument(
        "--apps",
        default=",".join(DEFAULT_APPS),
        help="Comma-separated app keys: slack,zoom,notion,trello,asana,clickup,teams",
    )
    parser.add_argument("--days", type=int, default=180)
    parser.add_argument("--lang", default="en")
    parser.add_argument("--country", default="us")
    parser.add_argument("--count", type=int, default=200)
    parser.add_argument("--max-reviews", type=int, default=1000)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data") / "saas_reviews.csv",
    )
    args = parser.parse_args()

    if args.days < 1 or args.count < 1 or args.count > 200 or args.max_reviews < 1:
        parser.error("days, count, and max-reviews must be positive; count cannot exceed 200")

    requested = [key.strip().lower() for key in args.apps.split(",") if key.strip()]
    unknown = sorted(set(requested) - set(DEFAULT_APPS))
    if unknown:
        parser.error(f"Unknown app keys: {', '.join(unknown)}")

    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=args.days)
    rows = []
    for key in requested:
        app_name, package_name = DEFAULT_APPS[key]
        print(f"Scraping {app_name} ({package_name})...")
        app_rows = scrape_app(
            app_name, package_name, cutoff, args.lang, args.country,
            args.count, args.max_reviews,
        )
        rows.extend(app_rows)
        print(f"  collected {len(app_rows)} reviews")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Saved {len(rows)} reviews to {args.output.resolve()}")


if __name__ == "__main__":
    main()
