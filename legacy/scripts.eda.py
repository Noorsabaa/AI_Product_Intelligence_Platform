import sqlite3
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

DB_PATH = Path("data/reviews.db")
OUTPUT_DIR = Path("eda_outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

conn = sqlite3.connect(DB_PATH)

df = pd.read_sql_query("""
SELECT r.review_id, r.app_id, a.app_name, r.content, r.score,
       r.review_date, r.language, r.detected_lang,
       r.language_confidence, r.is_analyzable
FROM reviews r
JOIN apps a ON r.app_id = a.app_id
""", conn)
conn.close()

df["review_date"] = pd.to_datetime(df["review_date"], errors="coerce")
df["month"] = df["review_date"].dt.to_period("M").astype(str)

eligible = df[(df["is_analyzable"] == 1) & (df["language"] != "other")].copy()

print("\n=== DATASET OVERVIEW ===")
print(f"Total reviews: {len(df):,}")
print(f"Eligible reviews: {len(eligible):,}")
print(f"Excluded reviews: {len(df)-len(eligible):,}")
print(f"Apps: {df['app_name'].nunique()}")
print(f"Date range: {df['review_date'].min()} -> {df['review_date'].max()}")

def save_bar(series, title, xlabel, ylabel, filename, rotation=35):
    ax = series.plot(kind="bar", figsize=(10, 6))
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    plt.xticks(rotation=rotation, ha="right")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / filename, dpi=150)
    plt.close()

reviews_per_app = eligible.groupby("app_name").size().sort_values(ascending=False)
print("\n=== REVIEWS PER APP ===\n", reviews_per_app)
save_bar(reviews_per_app, "Eligible Reviews per App", "App",
         "Number of Reviews", "reviews_per_app.png")

score_counts = eligible["score"].value_counts().sort_index()
print("\n=== SCORE DISTRIBUTION ===\n", score_counts)
save_bar(score_counts, "Review Score Distribution", "Score",
         "Number of Reviews", "score_distribution.png", 0)

avg_score = eligible.groupby("app_name")["score"].agg(["mean", "count"]).sort_values("mean")
print("\n=== AVERAGE SCORE PER APP ===\n", avg_score.round(2))
save_bar(avg_score["mean"], "Average Review Score per App", "App",
         "Average Score", "average_score_per_app.png")
plt.close()

monthly = eligible.groupby("month").size()
print("\n=== REVIEWS PER MONTH ===\n", monthly)
ax = monthly.plot(kind="line", marker="o", figsize=(12, 6))
ax.set_title("Eligible Reviews per Month")
ax.set_xlabel("Month")
ax.set_ylabel("Number of Reviews")
plt.xticks(rotation=45, ha="right")
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "reviews_per_month.png", dpi=150)
plt.close()

monthly_app = eligible.groupby(["month", "app_name"]).size().unstack(fill_value=0)
ax = monthly_app.plot(figsize=(13, 7))
ax.set_title("Monthly Review Volume by App")
ax.set_xlabel("Month")
ax.set_ylabel("Number of Reviews")
plt.xticks(rotation=45, ha="right")
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "monthly_reviews_by_app.png", dpi=150)
plt.close()

language_counts = df["language"].fillna("unknown").value_counts()
print("\n=== LANGUAGE DISTRIBUTION ===\n", language_counts)
save_bar(language_counts, "Review Language Classification", "Language",
         "Number of Reviews", "language_distribution.png", 0)

eligible["content_length"] = eligible["content"].fillna("").str.len()
print("\n=== REVIEW LENGTH ===\n", eligible["content_length"].describe())

ax = eligible["content_length"].clip(upper=500).plot(kind="hist", bins=50, figsize=(10, 6))
ax.set_title("Review Length Distribution (capped at 500 characters)")
ax.set_xlabel("Characters")
ax.set_ylabel("Number of Reviews")
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "review_length_distribution.png", dpi=150)
plt.close()

short_counts = pd.Series({
    "<10 chars": (eligible["content_length"] < 10).sum(),
    "10–49 chars": ((eligible["content_length"] >= 10) & (eligible["content_length"] < 50)).sum(),
    "50–99 chars": ((eligible["content_length"] >= 50) & (eligible["content_length"] < 100)).sum(),
    "100+ chars": (eligible["content_length"] >= 100).sum(),
})
print("\n=== REVIEW LENGTH BUCKETS ===\n", short_counts)
save_bar(short_counts, "Review Length Buckets", "Length",
         "Number of Reviews", "review_length_buckets.png", 0)

repeated = eligible.groupby("content").size().sort_values(ascending=False).head(15)
print("\n=== TOP 15 REPEATED REVIEW TEXTS ===\n", repeated)

reviews_per_app.rename("review_count").to_csv(OUTPUT_DIR / "reviews_per_app.csv")
score_counts.rename("review_count").to_csv(OUTPUT_DIR / "score_distribution.csv")
avg_score.round(2).to_csv(OUTPUT_DIR / "average_score_per_app.csv")
monthly.rename("review_count").to_csv(OUTPUT_DIR / "reviews_per_month.csv")
language_counts.rename("review_count").to_csv(OUTPUT_DIR / "language_distribution.csv")

print(f"\nEDA complete. Charts and tables saved to: {OUTPUT_DIR.resolve()}")