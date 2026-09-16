import csv
import io
import json
from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context
from datetime import date, timedelta

import numpy as np
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient as BaseTestClient
from contextlib import contextmanager
from services.accounts import initialize_accounts,create_account,workspace_path
import db.connection as connection
from api.main import app
from services import analysis, discovery
from services.imports import parse_csv, import_rows
from services.intelligence import dashboard, priority_categories, load_scope
from services.reports import create_report, get_report
from services.storage import database, initialize, recover_interrupted_runs


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    monkeypatch.setattr(connection, 'DB_PATH', tmp_path / 'workspace.db')
    initialize()
    initialize_accounts()
    user=create_account('test-owner','A-long-test-password')
    token=connection.WORKSPACE_PATH.set(workspace_path(user['id']))
    monkeypatch.setattr(analysis, 'detect_language', lambda text: 'en')
    yield tmp_path
    connection.WORKSPACE_PATH.reset(token)


@contextmanager
def TestClient(app):
    with BaseTestClient(app) as client:
        session=client.post('/api/auth/login',json={'username':'test-owner','password':'A-long-test-password'})
        assert session.status_code==200
        client.headers['X-CSRF-Token']=session.json()['csrf']
        yield client


def sample_csv(content='Opening a project crashes the application repeatedly.', score=1, day=None, customer_id='', source=''):
    stream = io.StringIO()
    writer = csv.writer(stream)
    writer.writerow(['content', 'review_date', 'score', 'customer_id', 'source'])
    writer.writerow([content, day or date.today().isoformat(), score, customer_id, source])
    return stream.getvalue().encode()


def seed(**kwargs):
    return import_rows(parse_csv(sample_csv(**kwargs)), 'sample.csv')


def run(engine='lexical'):
    run_id = analysis.reserve_run(engine)
    analysis.run_pipeline(run_id)
    assert analysis.latest_run()['status'] == 'completed', analysis.latest_run()['error']
    return run_id


def test_import_needs_no_apps_or_ratings_and_deduplicates(workspace):
    rows = parse_csv(b'content,review_date\nA very unusual piece of customer feedback,2026-01-01')
    assert import_rows(rows, 'minimal.csv')['inserted'] == 1
    assert import_rows(rows, 'minimal.csv')['duplicates'] == 1
    run()
    d = dashboard(0)
    assert d['summary']['total'] == 1
    assert d['summary']['analyzed'] == d['summary']['neutral'] == 0
    assert load_scope(0)[0][0]['score'] is None
    assert load_scope(0)[0][0]['sentiment_method'] == 'unavailable'


def test_same_feedback_from_distinct_customers_is_not_lost(workspace):
    assert seed(customer_id='account-a')['inserted'] == 1
    assert seed(customer_id='account-b')['inserted'] == 1
    assert seed(customer_id='account-b')['duplicates'] == 1
    assert dashboard()['summary']['known_customers'] == 2


@pytest.mark.parametrize('raw', [
    b'content,review_date,score\nbad,not-a-date,1',
    b'content,review_date,score\nbad,2026-01-01,6',
    b'content,review_date,score\n,2026-01-01,1',
    b'content,review_date,score\nbad',
    b'content,review_date,score\nbad,2999-01-01,1',
    b'content,review_date,score\n\x00,2026-01-01,1',
    b'content,review_date,score,score\nbad,2026-01-01,1,2',
    b'content,score\nhello,1',
])
def test_invalid_upload_never_replaces_data(workspace, raw):
    seed()
    with TestClient(app) as client:
        response = client.post('/api/ingest/csv?mode=replace', files={'file': ('bad.csv', raw, 'text/csv')})
        assert response.status_code == 422
    assert dashboard()['summary']['total'] == 1


def test_mixed_valid_invalid_file_rejected_whole(workspace):
    seed()
    with pytest.raises(HTTPException):
        parse_csv(sample_csv() + b'Invalid score,2026-01-01,zero,,\n')
    assert dashboard()['summary']['total'] == 1


def test_equivalent_iso_dates_deduplicate(workspace):
    seed(day='2026-01-01T10:00:00+05:00')
    assert seed(day='2026-01-01')['duplicates'] == 1


def test_pipeline_publishes_and_preserves_raw(workspace):
    seed()
    assert dashboard()['summary']['analyzed'] == 0
    published = run()
    d = dashboard()
    assert d['summary']['total'] == d['summary']['analyzed'] == 1
    assert not d['scope']['needs_analysis']
    assert d['scope']['published_run']['id'] == published
    assert d['summary']['negative'] == 1
    assert d['summary']['ungrouped_negative'] == 1
    with database() as conn:
        assert conn.execute('SELECT sentiment FROM reviews').fetchone()[0] is None


def test_failed_model_keeps_previous_snapshot(workspace, monkeypatch):
    seed()
    published = run()
    def fail():
        raise RuntimeError('Model unavailable')
    monkeypatch.setattr(analysis, 'load_transformer', fail)
    analysis.run_pipeline(analysis.reserve_run('semantic'))
    assert analysis.latest_run()['status'] == 'failed'
    assert dashboard()['scope']['published_run']['id'] == published
    assert dashboard()['summary']['analyzed'] == 1


def test_new_import_is_pending_and_blocks_report(workspace):
    seed()
    run()
    seed(content='This is different customer feedback requiring analysis.')
    d = dashboard()
    assert d['summary']['total'] == 2 and d['summary']['analyzed'] == 1
    assert d['scope']['needs_analysis']
    with pytest.raises(HTTPException) as exc:
        create_report()
    assert exc.value.status_code == 409


def test_queue_blocks_imports_and_other_runs(workspace):
    seed()
    analysis.reserve_run()
    for operation in (seed, analysis.reserve_run):
        with pytest.raises(HTTPException) as exc:
            operation()
        assert exc.value.status_code == 409


def test_simultaneous_run_claim_has_one_winner(workspace):
    seed()
    def claim(_):
        try:
            return analysis.reserve_run()
        except HTTPException:
            return None
    contexts = [copy_context() for _ in range(4)]
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda context: context.run(claim, None), contexts))
    assert sum(r is not None for r in results) == 1


def test_restart_recovers_interruption(workspace):
    seed()
    analysis.reserve_run()
    recover_interrupted_runs()
    assert analysis.latest_run()['status'] == 'interrupted'
    run()


def corpus():
    groups = [
        ['Invoice tax calculations are incorrect for overseas customers', 'Invoice tax amounts are wrong on monthly statements', 'Invoice tax totals fail when exporting international purchases', 'Invoice tax charges repeat across several customer accounts', 'Invoice tax errors affect overseas purchase summaries', 'Invoice tax calculation breaks for foreign currency payments'],
        ['Warehouse barcode scanning fails with damaged product labels', 'Warehouse barcode scanner cannot read printed inventory labels', 'Warehouse barcode scanners lose connection during stock counts', 'Warehouse barcode scanning freezes while counting new inventory', 'Warehouse barcode recognition fails for incoming inventory stock', 'Warehouse barcode reader keeps rejecting printed product tags'],
        ['Video captions translation is inaccurate during Spanish meetings', 'Video captions translation omits spoken sentences in recordings', 'Video captions translation produces incorrect foreign language subtitles', 'Video captions translation cannot recognize French meeting conversations', 'Video captions translation delays subtitles in live meetings', 'Video captions translation misses words in recorded conversations'],
    ]
    return [text for group in groups for text in group]


def seeded_categories():
    for index, text in enumerate(corpus()):
        seed(content=text, score=1 if index % 3 else 3, day=(date.today()-timedelta(days=index*2)).isoformat())
    run()
    assert len(dashboard()['categories']) >= 2


def test_unseen_domains_are_discovered_without_taxonomy(workspace):
    seeded_categories()
    d = dashboard()
    names = ' '.join(c['label'] for c in d['categories']).lower()
    assert 'barcode' in names and ('caption' in names or 'translation' in names)
    assert sum(c['negative'] for c in d['categories']) + d['summary']['ungrouped_negative'] == d['summary']['negative']
    assert sum(t['total'] for t in d['trends']) == d['summary']['analyzed']
    topic = d['categories'][0]
    filtered = dashboard(90, topic['id'])
    assert filtered['summary'] == d['summary']
    assert sum(t['negative'] for t in filtered['trends']) == topic['negative']
    assert len(load_scope(90, topic['id'], 'negative')[0]) == topic['negative']
    assert 'app_name' not in load_scope()[0][0]


def test_repeated_wording_cannot_manufacture_density_and_languages_abstain(workspace):
    rows = [{'review_id':str(i),'content':'Warehouse barcode scanning fails repeatedly for inventory labels','language':'en'} for i in range(100)]
    rows += [{'review_id':'other','content':'Estas funciones de inventario no funcionan correctamente','language':'es'}]
    topics, assignments, stats = discovery.discover_topics(rows, 'lexical', [])
    assert not topics and stats['distinct_texts'] == 1
    assert assignments['other']['reason'] == 'unsupported_language'
    assert all(a['topic_id'] is None for a in assignments.values())


def test_small_semantic_corpus_does_not_fail_spectral_initialization(workspace, monkeypatch):
    rows = [{'review_id':str(i),'content':text,'language':'en'} for i,text in enumerate(corpus()[:6])]
    vectors = np.random.default_rng(42).normal(size=(6,16)).astype(np.float32)
    vectors /= np.linalg.norm(vectors,axis=1,keepdims=True)
    monkeypatch.setattr(discovery, 'cached_embeddings', lambda *_: (vectors,6))
    topics, assignments, stats = discovery.discover_topics(rows, 'semantic', [])
    assert len(assignments) == 6 and stats['distinct_texts'] == 6


def test_saved_report_preserves_names_evidence_and_metadata_after_replacement(workspace):
    seeded_categories()
    with TestClient(app) as client:
        d = client.get('/api/dashboard/overview').json()
        topic = d['categories'][0]
        result = client.post('/api/reports', json={'days':90,'title':'Quarter <script>alert(1)</script>'})
        assert result.status_code == 201
        rid = result.json()['id']
        frozen = get_report(rid)
        assert client.patch('/api/dashboard/categories/'+topic['id'],json={'label':'Operations review'}).status_code == 200
        run()
        assert any(c['label']=='Operations review' for c in dashboard()['categories'])
        assert get_report(rid) == frozen
        import_rows(parse_csv(sample_csv(content='New service feedback for a different reporting period.')), 'replace.csv', 'replace')
        assert get_report(rid) == frozen
        assert client.get('/api/reports').json()['reports'][0]['id'] == rid
        evidence = client.get(f'/api/reports/{rid}/reviews',params={'topic_id':topic['id'],'sentiment':'negative','limit':1}).json()
        assert evidence['total'] == topic['negative'] and len(evidence['reviews']) == 1
        assert 'customer_id' not in evidence['reviews'][0]
        exported = client.get(f'/api/reports/{rid}/download').text
        assert '<script>alert(1)</script>' not in exported and '&lt;script&gt;' in exported
        assert 'rating' in client.get(f'/api/reports/{rid}/download?format=csv').text


def test_priority_requires_history_and_neutral_is_not_complaint():
    end=date.today()
    topics=[{'id':'a','label':'New issue','custom_label':None,'keywords':'[]','coherence':.8}]
    def row(i,ago,sentiment='negative',topic='a'):
        return {'review_id':str(i),'review_date':(end-timedelta(days=ago)).isoformat(),'sentiment':sentiment,'topic_id':topic,'content':str(i)}
    rows=[row(i,i%7) for i in range(10)] + [row(20,0,'neutral')]
    result=priority_categories(rows,topics,{'start':end.isoformat(),'end':end.isoformat()})[0]
    assert result['negative']==10 and result['neutral']==1
    assert result['score_parts']['growth']==0 and result['change_pp'] is None
    rows += [row(i,7+i%28,'positive',None) for i in range(21,61)]
    result=priority_categories(rows,topics,{'start':(end-timedelta(days=90)).isoformat(),'end':end.isoformat()})[0]
    assert result['has_baseline'] and result['is_rising']
    assert 0 <= result['priority_score'] <= 100 and result['score_parts']['growth']==25


def test_api_filters_csv_and_stale_evidence(workspace):
    seed(content='=HYPERLINK("bad")')
    run()
    with TestClient(app) as client:
        assert client.get('/api/health').json()['version']=='3.0.0'
        assert client.get('/api/dashboard/reviews?page=0').status_code==422
        assert client.get('/api/dashboard/reviews?run_id=stale').status_code==409
        assert client.get('/api/dashboard/reviews?sentiment=positive').json()['total']==0
        result=client.get('/api/dashboard/export')
        rows=list(csv.DictReader(io.StringIO(result.text.lstrip('\ufeff'))))
        assert rows[0]['content'].startswith("'=") and 'app_name' not in rows[0]


def test_real_language_detector_is_repeatable():
    assert analysis.detect_language('This application crashes every time I open the project.') == 'en'
    assert analysis.detect_language('Esta aplicación no funciona y es muy lenta.') == 'es'


def test_ambiguous_import_can_retry_without_changing_file(workspace):
    seed()
    raw = b'Reviews,Date,Rating\nBilling export failed,8/3/2026,2.0'
    with TestClient(app) as client:
        rejected = client.post('/api/ingest/csv?mode=replace', files={'file': ('export.csv', raw, 'text/csv')})
        assert rejected.status_code == 422
        assert rejected.json()['detail']['code'] == 'ambiguous_date_order'
        assert dashboard()['summary']['total'] == 1
        accepted = client.post('/api/ingest/csv?mode=replace&date_order=mdy', files={'file': ('export.csv', raw, 'text/csv')})
        assert accepted.status_code == 200
        assert accepted.json()['inserted'] == 1
        with database() as conn:
            assert conn.execute('SELECT review_date FROM reviews').fetchone()[0] == '2026-08-03'
