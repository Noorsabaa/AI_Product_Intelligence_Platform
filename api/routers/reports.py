from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field
from services.reports import create_report, get_report, render_html, csv_feedback
from services.storage import database

router = APIRouter()

class ReportRequest(BaseModel):
    days: int = Field(default=90, ge=0, le=730)
    title: str = Field(default='', max_length=150)

@router.post('', status_code=201)
def generate(body: ReportRequest):
    return create_report(body.days, body.title)

@router.get('')
def history():
    with database() as conn:
        return {'reports': [dict(r) for r in conn.execute('SELECT id,title,created_at,period_start,period_end,run_id FROM reports ORDER BY created_at DESC')]}

@router.get('/{report_id}')
def detail(report_id: str):
    report = get_report(report_id)
    report.pop('evidence', None)
    return report

@router.get('/{report_id}/reviews')
def evidence(report_id: str, topic_id: str = '', sentiment: str = '', search: str = '', page: int = Query(1, ge=1), limit: int = Query(20,ge=1,le=100)):
    report = get_report(report_id)
    rows = [r for r in report['evidence'] if (not topic_id or r['topic_id']==topic_id or topic_id=='ungrouped' and not r['topic_id'])
            and (not sentiment or r['sentiment']==sentiment) and (not search or search.casefold() in r['content'].casefold())]
    return {'reviews': rows[(page-1)*limit:page*limit], 'total': len(rows), 'page': page, 'limit': limit}

@router.get('/{report_id}/download')
def download(report_id: str, format: str = 'html'):
    report = get_report(report_id)
    if format == 'csv':
        return Response(csv_feedback(report['evidence']), media_type='text/csv', headers={'Content-Disposition': f'attachment; filename=report-{report_id[:8]}-evidence.csv'})
    if format != 'html':
        raise HTTPException(422, 'Choose html or csv.')
    return Response(render_html(report), media_type='text/html', headers={'Content-Disposition': f'attachment; filename=performance-report-{report_id[:8]}.html'})
