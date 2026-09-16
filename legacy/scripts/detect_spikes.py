# scripts/detect_spikes.py
import sqlite3
import os
from pathlib import Path

import pandas as pd

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "reviews.db"

# The conservative profile is the default. The demo profile is useful for
# small portfolio datasets where production-sized volume thresholds are too strict.
SPIKE_PROFILE = os.getenv("SPIKE_PROFILE", "conservative").lower()
if SPIKE_PROFILE == "demo":
    WEEKLY_FLOOR = 2
    MONTHLY_FLOOR = 2
    SPIKE_MULTIPLIER = 1.25
    MIN_ABSOLUTE_JUMP = 3
elif SPIKE_PROFILE == "conservative":
    WEEKLY_FLOOR = 10
    MONTHLY_FLOOR = 8
    SPIKE_MULTIPLIER = 1.75
    MIN_ABSOLUTE_JUMP = 15
else:
    raise ValueError("SPIKE_PROFILE must be 'conservative' or 'demo'")

BASELINE_WEEKS = 4         # trailing window used to compute "normal"


def calculate_priority(count, baseline, avg_score):
    pct_change = max(0.0, (count / baseline - 1) * 100) if baseline else 0.0
    growth_points = min(40.0, pct_change / 5)
    volume_points = min(30.0, count / 2)
    severity_points = min(30.0, max(0.0, (5 - avg_score) / 4 * 30))
    score = round(growth_points + volume_points + severity_points)
    priority = "High" if score >= 70 else "Medium" if score >= 40 else "Low"
    return score, priority

def complete_period_counts(counts, group_columns, period_column, frequency):
    completed = []
    for group_values, group in counts.groupby(group_columns):
        group = group.set_index(period_column).sort_index()
        periods = pd.date_range(
            group.index.min(), group.index.max(), freq=frequency
        )
        group = group.reindex(periods)
        group["count"] = group["count"].fillna(0).astype(int)
        for column, value in zip(group_columns, group_values):
            group[column] = value
        group.index.name = period_column
        completed.append(group.reset_index())
    return pd.concat(completed, ignore_index=True) if completed else counts

def load_data():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("""
        SELECT r.review_id, a.app_name, r.category, r.review_date, r.score
        FROM reviews_categorized_confident r
        JOIN apps a ON r.app_id = a.app_id
    """, conn)
    conn.close()
    df["review_date"] = pd.to_datetime(
    df["review_date"],
    format="mixed",
    errors="coerce"
)
    
    df["week"] = df["review_date"].dt.to_period("W").apply(lambda p: p.start_time)
    df["month"] = df["review_date"].dt.to_period("M").apply(lambda p: p.start_time)
    return df


def detect_weekly_spikes(df):
    """Per app + category, weekly granularity. Only for pairs with enough volume."""
    counts = df.groupby(["app_name", "category", "week"]).agg(
        count=("review_id", "size"), avg_score=("score", "mean")
    ).reset_index()
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
            if len(baseline_window) < BASELINE_WEEKS:
                continue  # not enough history yet

            baseline_avg = baseline_window["count"].mean()

            if baseline_avg < WEEKLY_FLOOR:
                continue  # too sparse for weekly detection, handled by monthly fallback

            is_spike = (
                current_count >= baseline_avg * SPIKE_MULTIPLIER and
                (current_count - baseline_avg) >= MIN_ABSOLUTE_JUMP
            )
            if is_spike:
                priority_score, priority = calculate_priority(
                    current_count, baseline_avg, group.loc[i, "avg_score"]
                )
                results.append({
                    "app_name": app, "category": cat, "period": current_week,
                    "granularity": "weekly", "count": current_count,
                    "baseline": round(baseline_avg, 1),
                    "pct_change": round((current_count / baseline_avg - 1) * 100, 1),
                    "avg_score": round(group.loc[i, "avg_score"], 2),
                    "priority_score": priority_score,
                    "priority": priority,
                })

    return pd.DataFrame(results)


def detect_monthly_spikes(df):
    """Categories too sparse for weekly detection, evaluated per app."""
    counts = df.groupby(["app_name", "category", "month"]).agg(
        count=("review_id", "size"), avg_score=("score", "mean")
    ).reset_index()
    counts = complete_period_counts(
        counts, ["app_name", "category"], "month", "MS"
    )
    results = []

    for (app, cat), group in counts.groupby(["app_name", "category"]):
        group = group.sort_values("month").reset_index(drop=True)
        for i in range(len(group)):
            current_month = group.loc[i, "month"]
            current_count = group.loc[i, "count"]

            baseline_window = group[group["month"] < current_month].tail(3)
            if len(baseline_window) < 3:
                continue

            baseline_avg = baseline_window["count"].mean()
            if baseline_avg < MONTHLY_FLOOR:
                continue  # even monthly is too sparse, skip entirely for v1

            is_spike = (
                current_count >= baseline_avg * SPIKE_MULTIPLIER and
                (current_count - baseline_avg) >= MIN_ABSOLUTE_JUMP / 2  # lower bar, monthly buckets are naturally bigger jumps
            )
            if is_spike:
                priority_score, priority = calculate_priority(
                    current_count, baseline_avg, group.loc[i, "avg_score"]
                )
                results.append({
                    "app_name": app, "category": cat, "period": current_month,
                    "granularity": "monthly", "count": current_count,
                    "baseline": round(baseline_avg, 1),
                    "pct_change": round((current_count / baseline_avg - 1) * 100, 1),
                    "avg_score": round(group.loc[i, "avg_score"], 2),
                    "priority_score": priority_score,
                    "priority": priority,
                })

    return pd.DataFrame(results)


if __name__ == "__main__":
    df = load_data()
    print(f"Loaded {len(df)} rows")

    weekly = detect_weekly_spikes(df)
    monthly = detect_monthly_spikes(df)

    print("\n=== WEEKLY SPIKES (per app+category) ===")
    print(weekly.to_string(index=False) if not weekly.empty else "None found")

    print("\n=== MONTHLY SPIKES (per app, low-volume categories) ===")
    print(monthly.to_string(index=False) if not monthly.empty else "None found")

    all_spikes = pd.concat([weekly, monthly], ignore_index=True)
    all_spikes.to_csv("scratch/detected_spikes.csv", index=False)
    print(f"\nSaved {len(all_spikes)} total spikes to scratch/detected_spikes.csv")