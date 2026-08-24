from datetime import datetime, timezone
from threading import Lock

from fastapi import APIRouter, BackgroundTasks
import pandas as pd
import sqlite3

from scripts.detect_language import run_language_detection
from scripts.run_sentiment import run_sentiment
from scripts.run_categorization import run_categorization
from scripts.detect_spikes import (
    load_data,
    detect_weekly_spikes,
    detect_monthly_spikes,
)

router = APIRouter()

DB_PATH = "data/reviews.db"
_state_lock = Lock()
PIPELINE_STATE = {
    "status": "idle",
    "stage": None,
    "started_at": None,
    "finished_at": None,
    "last_error": None,
    "pending_before": None,
    "pending_after": None,
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _count_pending_work() -> dict:
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        return {
            "language": cur.execute(
                "SELECT COUNT(*) FROM reviews WHERE language IS NULL"
            ).fetchone()[0],
            "sentiment": cur.execute(
                "SELECT COUNT(*) FROM reviews WHERE sentiment IS NULL"
            ).fetchone()[0],
            "category": cur.execute(
                "SELECT COUNT(*) FROM reviews WHERE category IS NULL"
            ).fetchone()[0],
        }
    finally:
        conn.close()


def _update_state(**kwargs):
    with _state_lock:
        PIPELINE_STATE.update(kwargs)


def run_full_pipeline():
    _update_state(status="running", stage="starting")

    try:
        _update_state(stage="language_detection")
        print("Pipeline: language detection...", flush=True)
        run_language_detection()

        _update_state(stage="sentiment")
        print("Pipeline: sentiment...", flush=True)
        run_sentiment()

        _update_state(stage="categorization")
        print("Pipeline: categorization...", flush=True)
        run_categorization()

        _update_state(stage="spike_detection")
        print("Pipeline: spike detection...", flush=True)
        df = load_data()

        weekly = detect_weekly_spikes(df)
        monthly = detect_monthly_spikes(df)

        all_spikes = pd.concat(
            [weekly, monthly],
            ignore_index=True
        )

        all_spikes.to_csv(
            "scratch/detected_spikes.csv",
            index=False
        )

        _update_state(
            status="completed",
            stage="done",
            finished_at=_utc_now_iso(),
            pending_after=_count_pending_work(),
        )

        print("Pipeline: done.", flush=True)
        print(
            "Note: recommendations must be regenerated separately "
            "(LLM calls are rate-limited).",
            flush=True,
        )
    except Exception as exc:
        _update_state(
            status="failed",
            stage="error",
            finished_at=_utc_now_iso(),
            last_error=str(exc),
            pending_after=_count_pending_work(),
        )
        print(f"Pipeline: failed: {exc}", flush=True)
        raise


@router.post("/run")
def trigger_pipeline(background_tasks: BackgroundTasks):
    with _state_lock:
        if PIPELINE_STATE["status"] == "running":
            return {
                "status": "already_running",
                "note": "A pipeline run is already in progress.",
                "state": PIPELINE_STATE.copy(),
            }

        PIPELINE_STATE.update(
            {
                "status": "running",
                "stage": "queued",
                "started_at": _utc_now_iso(),
                "finished_at": None,
                "last_error": None,
                "pending_before": _count_pending_work(),
                "pending_after": None,
            }
        )

    background_tasks.add_task(run_full_pipeline)

    return {
        "status": "started",
        "note": (
            "Pipeline is running in the background. "
            "New reviews will have sentiment/category populated shortly. "
            "Check /dashboard/summary to monitor progress."
        ),
    }


@router.get("/status")
def pipeline_status():
    with _state_lock:
        return PIPELINE_STATE.copy()