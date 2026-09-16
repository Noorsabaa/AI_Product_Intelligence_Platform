from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field
from services.intelligence import dashboard, load_scope
from services.reports import csv_feedback
from services.storage import database, active_run

router = APIRouter()

@router.get('/overview')
def overview(days: int = Query(90, ge=0, le=730), topic_id: str = ''):
    return dashboard(days, topic_id)

@router.get('/reviews')
def reviews(days: int = Query(90,ge=0,le=730), topic_id: str = '', sentiment: str = '',
            search: str = Query('',max_length=200), page: int = Query(1,ge=1), limit: int = Query(20,ge=1,le=100), run_id: str = ''):
    rows, scope, _ = load_scope(days,topic_id,sentiment,search)
    if run_id and (scope['published_run'] or {}).get('id') != run_id:
        raise HTTPException(409, 'Analysis has changed. Close this panel and refresh the dashboard.')
    return {'reviews':rows[(page-1)*limit:page*limit], 'total':len(rows), 'page':page, 'limit':limit}

@router.get('/export')
def export(days: int = Query(90,ge=0,le=730), topic_id: str = '', sentiment: str = '', search: str = ''):
    rows,_,_ = load_scope(days,topic_id,sentiment,search)
    return Response(csv_feedback(rows), media_type='text/csv', headers={'Content-Disposition':'attachment; filename=customer-feedback.csv'})

class TopicName(BaseModel):
    label: str = Field(min_length=1,max_length=100)

@router.patch('/categories/{topic_id}')
def rename(topic_id: str, body: TopicName):
    if not body.label.strip():
        raise HTTPException(422,'Category name cannot be blank.')
    with database() as conn:
        conn.execute('BEGIN IMMEDIATE')
        if active_run(conn):
            raise HTTPException(409,'Wait for analysis to finish before renaming a category.')
        result=conn.execute('UPDATE discovered_topics SET custom_label=? WHERE id=?',(body.label.strip(),topic_id))
        if not result.rowcount:
            raise HTTPException(404,'Category not found.')
    return {'id':topic_id,'label':body.label.strip()}
