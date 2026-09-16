import argparse
import csv
import json
import sqlite3
from collections import defaultdict
from pathlib import Path

CATEGORY_CONFIDENCE_THRESHOLD = 0.7


def score_labels(expected, predicted):
    labels = sorted(set(expected) | set(predicted))
    total = len(expected)
    result = {
        "rows": total,
        "accuracy": sum(a == b for a, b in zip(expected, predicted)) / total if total else 0.0,
        "macro_f1": 0.0,
        "per_label": {},
    }
    for label in labels:
        true_positive = sum(a == label and b == label for a, b in zip(expected, predicted))
        false_positive = sum(a != label and b == label for a, b in zip(expected, predicted))
        false_negative = sum(a == label and b != label for a, b in zip(expected, predicted))
        precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
        recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        result["per_label"][label] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "support": true_positive + false_negative,
        }
        result["macro_f1"] += f1
    if labels:
        result["macro_f1"] /= len(labels)
    result["accuracy"] = round(result["accuracy"], 4)
    result["macro_f1"] = round(result["macro_f1"], 4)
    return result


def review_length_bucket(content):
    length = len(content.strip())
    if length < 10:
        return "short (<10)"
    if length < 50:
        return "medium (10-49)"
    if length < 100:
        return "long (50-99)"
    return "very long (100+)"


def grouped_metrics(rows, group_key, task):
    groups = defaultdict(lambda: {"gold_rows": 0, "expected": [], "predicted": []})
    for row in rows:
        group = row[group_key]
        groups[group]["gold_rows"] += 1
        if task == "sentiment":
            expected = row["true_sentiment"]
            predicted = row["sentiment"]
        else:
            if row["true_sentiment"] not in ("negative", "neutral"):
                continue
            expected = row["true_category"]
            predicted = row["category"]

        if predicted:
            groups[group]["expected"].append(expected)
            groups[group]["predicted"].append(predicted)

    result = {}
    for group, values in sorted(groups.items()):
        expected = values["expected"]
        predicted = values["predicted"]
        result[group] = {
            "gold_rows": values["gold_rows"],
            "covered_rows": len(predicted),
            "coverage": round(len(predicted) / values["gold_rows"], 4)
            if values["gold_rows"] else 0.0,
            **score_labels(expected, predicted),
        }
    return result


def evaluate(database, labels_file):
    with labels_file.open(encoding="utf-8-sig", newline="") as stream:
        gold = list(csv.DictReader(stream))

    conn = sqlite3.connect(database)
    app_names = dict(conn.execute("SELECT app_id, app_name FROM apps"))
    rows = conn.execute(
        """
        SELECT app_id, content, review_date, sentiment,
               category, category_confidence, language
        FROM reviews
        """
    ).fetchall()
    conn.close()
    predictions = {
        (app_names[app_id], content, review_date): (
            sentiment,
            category if (category_confidence or 0.0) >= CATEGORY_CONFIDENCE_THRESHOLD else None,
            language or "unknown",
        )
        for app_id, content, review_date, sentiment, category, category_confidence, language in rows
    }

    sentiment_expected = []
    sentiment_predicted = []
    category_expected = []
    category_predicted = []
    evaluation_rows = []
    missing = 0
    complaint_rows = 0
    for row in gold:
        prediction = predictions.get((row["app_name"], row["content"], row["review_date"]))
        if prediction is None:
            missing += 1
            continue
        sentiment, category, language = prediction
        evaluation_rows.append({
            "app": row["app_name"],
            "language": language,
            "length": review_length_bucket(row["content"]),
            "true_sentiment": row["true_sentiment"],
            "sentiment": sentiment,
            "true_category": row["true_category"],
            "category": category,
        })
        if sentiment:
            sentiment_expected.append(row["true_sentiment"])
            sentiment_predicted.append(sentiment)
        if row["true_sentiment"] in ("negative", "neutral"):
            complaint_rows += 1
            if category:
                category_expected.append(row["true_category"])
                category_predicted.append(category)

    return {
        "gold_rows": len(gold),
        "unique_predictions": len(predictions),
        "join_missing": missing,
        "sentiment_coverage": round(len(sentiment_predicted) / len(gold), 4) if gold else 0.0,
        "category_complaint_coverage": round(
            len(category_predicted) / complaint_rows, 4
        ) if complaint_rows else 0.0,
        "category_confidence_threshold": CATEGORY_CONFIDENCE_THRESHOLD,
        "sentiment": score_labels(sentiment_expected, sentiment_predicted),
        "category": score_labels(category_expected, category_predicted),
        "breakdowns": {
            "sentiment_by_language": grouped_metrics(
                evaluation_rows, "language", "sentiment"
            ),
            "sentiment_by_review_length": grouped_metrics(
                evaluation_rows, "length", "sentiment"
            ),
            "sentiment_by_app": grouped_metrics(
                evaluation_rows, "app", "sentiment"
            ),
            "category_by_language": grouped_metrics(
                evaluation_rows, "language", "category"
            ),
            "category_by_review_length": grouped_metrics(
                evaluation_rows, "length", "category"
            ),
            "category_by_app": grouped_metrics(
                evaluation_rows, "app", "category"
            ),
            "category_by_true_category": grouped_metrics(
                evaluation_rows, "true_category", "category"
            ),
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Evaluate stored predictions against labelled reviews.")
    parser.add_argument("--database", type=Path, default=Path("data/reviews.db"))
    parser.add_argument("--labels", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(evaluate(args.database, args.labels), indent=2))


if __name__ == "__main__":
    main()