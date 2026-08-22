# scripts/detect_spikes.py
import sqlite3
import pandas as pd

DB_PATH = "data/reviews.db"

# Tuned from your actual category volumes (Performance ~100/wk down to Billing ~4/wk)
WEEKLY_FLOOR = 10          # min trailing baseline needed to attempt weekly detection
MONTHLY_FLOOR = 8          # min trailing baseline for the monthly fallback
SPIKE_MULTIPLIER = 1.75    # current period must be at least this many times the baseline
MIN_ABSOLUTE_JUMP = 15     # AND at least this many more reviews than baseline
BASELINE_WEEKS = 4         # trailing window used to compute "normal"


def load_data():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("""
        SELECT r.review_id, a.app_name, r.category, r.review_date, r.score
        FROM reviews_categorized_confident r
        JOIN apps a ON r.app_id = a.app_id
    """, conn)
    conn.close()
    df["review_date"] = pd.to_datetime(df["review_date"])
    df["week"] = df["review_date"].dt.to_period("W").apply(lambda p: p.start_time)
    df["month"] = df["review_date"].dt.to_period("M").apply(lambda p: p.start_time)
    return df


def detect_weekly_spikes(df):
    """Per app + category, weekly granularity. Only for pairs with enough volume."""
    counts = df.groupby(["app_name", "category", "week"]).size().reset_index(name="count")
    results = []

    for (app, cat), group in counts.groupby(["app_name", "category"]):
        group = group.sort_values("week").reset_index(drop=True)
        for i in range(len(group)):
            current_week = group.loc[i, "week"]
            current_count = group.loc[i, "count"]

            baseline_window = group[
                (group["week"] < current_week) &
                (group["week"] >= current_week - pd.Timedelta(weeks=BASELINE_WEEKS))
            ]
            if len(baseline_window) == 0:
                continue  # not enough history yet

            baseline_avg = baseline_window["count"].mean()

            if baseline_avg < WEEKLY_FLOOR:
                continue  # too sparse for weekly detection, handled by monthly fallback

            is_spike = (
                current_count >= baseline_avg * SPIKE_MULTIPLIER and
                (current_count - baseline_avg) >= MIN_ABSOLUTE_JUMP
            )
            if is_spike:
                results.append({
                    "app_name": app, "category": cat, "period": current_week,
                    "granularity": "weekly", "count": current_count,
                    "baseline": round(baseline_avg, 1),
                    "pct_change": round((current_count / baseline_avg - 1) * 100, 1),
                })

    return pd.DataFrame(results)


def detect_monthly_spikes(df):
    """Categories too sparse for weekly detection, aggregated across ALL apps."""
    counts = df.groupby(["category", "month"]).size().reset_index(name="count")
    results = []

    for cat, group in counts.groupby("category"):
        group = group.sort_values("month").reset_index(drop=True)
        for i in range(len(group)):
            current_month = group.loc[i, "month"]
            current_count = group.loc[i, "count"]

            baseline_window = group[group["month"] < current_month].tail(3)
            if len(baseline_window) == 0:
                continue

            baseline_avg = baseline_window["count"].mean()
            if baseline_avg < MONTHLY_FLOOR:
                continue  # even monthly is too sparse, skip entirely for v1

            is_spike = (
                current_count >= baseline_avg * SPIKE_MULTIPLIER and
                (current_count - baseline_avg) >= MIN_ABSOLUTE_JUMP / 2  # lower bar, monthly buckets are naturally bigger jumps
            )
            if is_spike:
                results.append({
                    "app_name": "ALL APPS", "category": cat, "period": current_month,
                    "granularity": "monthly", "count": current_count,
                    "baseline": round(baseline_avg, 1),
                    "pct_change": round((current_count / baseline_avg - 1) * 100, 1),
                })

    return pd.DataFrame(results)


if __name__ == "__main__":
    df = load_data()
    print(f"Loaded {len(df)} rows")

    weekly = detect_weekly_spikes(df)
    monthly = detect_monthly_spikes(df)

    print("\n=== WEEKLY SPIKES (per app+category) ===")
    print(weekly.to_string(index=False) if not weekly.empty else "None found")

    print("\n=== MONTHLY SPIKES (aggregated across apps, low-volume categories) ===")
    print(monthly.to_string(index=False) if not monthly.empty else "None found")

    all_spikes = pd.concat([weekly, monthly], ignore_index=True)
    all_spikes.to_csv("scratch/detected_spikes.csv", index=False)
    print(f"\nSaved {len(all_spikes)} total spikes to scratch/detected_spikes.csv")