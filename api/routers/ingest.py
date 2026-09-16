import io
import csv
from datetime import datetime, timezone
from fastapi import APIRouter, UploadFile, File, Query, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from services.imports import parse_csv, import_rows, MAX_BYTES
from services.storage import database

router = APIRouter()

@router.post('/csv')
async def ingest_csv(file: UploadFile = File(...), mode: str = Query('append'), date_order: str = Query('auto')):
    if not (file.filename or '').lower().endswith('.csv'):
        raise HTTPException(422, 'Choose a .csv file.')
    raw = await file.read(MAX_BYTES + 1)
    return import_rows(parse_csv(raw, date_order), (file.filename or 'reviews.csv')[:255], mode)

@router.get('/template')
def template():
    today = datetime.now(timezone.utc).date().isoformat()
    return Response(f'content,review_date,score,service,segment\n"The export does not include my saved columns.",{today},2,Reporting,Enterprise\n',
                    media_type='text/csv', headers={'Content-Disposition': 'attachment; filename=review-template.csv'})

@router.get('/history')
def history():
    with database() as conn:
        return {'imports': [dict(r) for r in conn.execute('SELECT * FROM imports ORDER BY id DESC LIMIT 20')]}

class PlayImport(BaseModel):
    app_name: str = Field(min_length=1, max_length=120)
    package: str = Field(pattern=r'^[A-Za-z][\w]*(\.[\w]+)+$', max_length=200)
    count: int = Field(default=200, ge=1, le=1000)

@router.post('/google-play')
def google_play(body: PlayImport):
    try:
        from google_play_scraper import reviews, Sort
    except ImportError as exc:
        raise HTTPException(503, 'Install requirements-connectors.txt to enable Google Play imports.') from exc
    try:
        result, _ = reviews(body.package, lang='en', country='us', sort=Sort.NEWEST, count=body.count)
    except Exception as exc:
        raise HTTPException(502, 'Google Play could not be reached. Check the package ID or try a CSV import.') from exc
    if not result:
        raise HTTPException(422, 'No reviews returned for this app.')
    stream = io.StringIO()
    writer = csv.writer(stream)
    writer.writerow(['app_name', 'content', 'review_date', 'score'])
    for row in result:
        writer.writerow([body.app_name, row['content'], row['at'].date().isoformat(), row['score']])
    return import_rows(parse_csv(stream.getvalue().encode()), f'Google Play: {body.package}')
