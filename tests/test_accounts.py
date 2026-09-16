import hashlib
import sqlite3
import time
import pytest
from fastapi.testclient import TestClient
import db.connection as connection
from api.main import app
from services.accounts import accounts_db,COOKIE,workspace_path

@pytest.fixture
def isolated(tmp_path,monkeypatch):
    monkeypatch.setattr(connection,'DB_PATH',tmp_path/'sample.db')
    monkeypatch.delenv('ACCOUNTS_DB',raising=False)
    return tmp_path

def register(client,username='alice'):
    response=client.post('/api/auth/register',json={'username':username,'password':'A-long-account-password'})
    assert response.status_code==201,response.text
    client.headers['X-CSRF-Token']=response.json()['csrf']
    return response.json()['user']

def add_and_analyze(client,text='The billing export fails repeatedly when downloading invoices.'):
    response=client.post('/api/ingest/csv',files={'file':('input.csv',f'content,review_date,score\n{text},2026-09-01,1'.encode(),'text/csv')})
    assert response.status_code==200,response.text
    response=client.post('/api/pipeline/run?engine=lexical')
    assert response.status_code==202,response.text
    assert client.get('/api/pipeline/status').json()['status']=='completed'


def test_accounts_isolate_feedback_reports_exports_and_evidence(isolated):
    with TestClient(app) as alice,TestClient(app) as bob:
        register(alice,'alice')
        add_and_analyze(alice)
        report=alice.post('/api/reports',json={'days':90,'title':'Alice report'}).json()
        assert 'id' in report
        register(bob,'bob')
        assert bob.get('/api/dashboard/overview').json()['summary']['total']==0
        assert bob.get('/api/reports').json()=={'reports':[]}
        for suffix in ('','/reviews','/download'):
            assert bob.get('/api/reports/'+report['id']+suffix).status_code==404
        assert 'billing export' not in bob.get('/api/dashboard/export').text
        add_and_analyze(bob,'Our scheduling calendar refuses to save recurring appointments.')
        assert alice.get('/api/dashboard/reviews').json()['reviews'][0]['content'].startswith('The billing')
        assert bob.get('/api/dashboard/reviews').json()['reviews'][0]['content'].startswith('Our scheduling')
        assert alice.get('/api/reports').json()['reports'][0]['id']==report['id']


def test_password_storage_login_logout_and_expiry(isolated):
    with TestClient(app) as client:
        user=register(client,'MixedCase')
        token=client.cookies.get(COOKIE)
        with accounts_db() as conn:
            row=conn.execute('SELECT * FROM users').fetchone()
            assert row['username']=='mixedcase'
            assert row['password_hash'].startswith('scrypt$')
            assert 'A-long-account-password' not in row['password_hash']
            assert conn.execute('SELECT token_hash FROM sessions').fetchone()[0]!=token
        assert client.post('/api/auth/logout').status_code==200
        assert client.get('/api/dashboard/overview').status_code==401
        assert client.post('/api/auth/login',json={'username':'MIXEDCASE','password':'Incorrect-password'}).status_code==401
        response=client.post('/api/auth/login',json={'username':'MIXEDCASE','password':'A-long-account-password'})
        assert response.status_code==200
        assert 'HttpOnly' in response.headers['set-cookie'] and 'SameSite=lax' in response.headers['set-cookie']
        with accounts_db() as conn:
            conn.execute('UPDATE sessions SET expires_at=?',(time.time()-1,))
        assert client.get('/api/dashboard/overview').status_code==401


def test_unauthenticated_csrf_and_cross_origin_requests_are_rejected(isolated):
    with TestClient(app) as client:
        assert client.get('/api/reports').status_code==401
        assert client.get('/api/dashboard/export').status_code==401
        register(client)
        csrf=client.headers.pop('X-CSRF-Token')
        assert client.post('/api/reports',json={'days':90}).status_code==403
        client.headers['X-CSRF-Token']=csrf
        assert client.post('/api/auth/logout',headers={'Origin':'https://attacker.example'}).status_code==403
        assert client.get('/api/auth/session').json()['user']['username']=='alice'
        assert client.post('/api/auth/logout').status_code==200


def test_registration_validation_and_duplicate_username(isolated):
    with TestClient(app) as client:
        assert client.post('/api/auth/register',json={'username':'../outside','password':'A-long-account-password'}).status_code==422
        assert client.post('/api/auth/register',json={'username':'okay-name','password':'short'}).status_code==422
        register(client,'unique-name')
        assert client.post('/api/auth/register',json={'username':'UNIQUE-NAME','password':'A-long-account-password'}).status_code==409
        assert 'email' not in client.get('/api/auth/session').json()['user']


def test_salted_passwords_differ_and_attempts_are_limited(isolated):
    with TestClient(app) as client:
        register(client,'first-user')
        register(client,'second-user')
        with accounts_db() as conn:
            hashes=[r[0] for r in conn.execute('SELECT password_hash FROM users')]
            assert hashes[0]!=hashes[1]
            conn.executemany('INSERT INTO auth_attempts VALUES (?,?)',[('login-user:first-user',time.time())]*10)
        assert client.post('/api/auth/login',json={'username':'first-user','password':'A-long-account-password'}).status_code==429
