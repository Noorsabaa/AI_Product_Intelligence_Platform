from fastapi import APIRouter, BackgroundTasks, Query
from services.analysis import reserve_run, run_pipeline, latest_run
from services.storage import database

router = APIRouter()

@router.post('/run', status_code=202)
def trigger_pipeline(background_tasks: BackgroundTasks, engine: str = Query('semantic')):
    run_id = reserve_run(engine)
    background_tasks.add_task(run_pipeline, run_id)
    return {'id': run_id, 'status': 'queued'}

@router.get('/status')
def pipeline_status():
    return latest_run()

@router.get('/history')
def history():
    with database() as conn:
        return {'runs': [dict(r) for r in conn.execute('SELECT * FROM pipeline_runs ORDER BY started_at DESC LIMIT 20')]}
