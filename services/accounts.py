"""Password accounts, opaque sessions and isolated per-user SQLite workspaces."""
import hashlib
import hmac
import os
import re
import secrets
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from fastapi import HTTPException
import db.connection as connection

COOKIE = 'feedback_session'
SESSION_SECONDS = 7 * 86400


def auth_path():
    return Path(os.getenv('ACCOUNTS_DB', Path(connection.DB_PATH).parent / 'accounts.db'))


@contextmanager
def accounts_db():
    path = auth_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON')
    conn.execute('PRAGMA journal_mode=WAL')
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def initialize_accounts():
    with accounts_db() as conn:
        conn.executescript('''
          CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY,username TEXT UNIQUE NOT NULL,
             password_hash TEXT NOT NULL,created_at REAL NOT NULL);
          CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY,user_id TEXT NOT NULL
             REFERENCES users(id) ON DELETE CASCADE,csrf TEXT NOT NULL,expires_at REAL NOT NULL);
          CREATE TABLE IF NOT EXISTS auth_attempts(key TEXT NOT NULL,created_at REAL NOT NULL);
          CREATE INDEX IF NOT EXISTS attempts_key ON auth_attempts(key,created_at);
        ''')
        conn.execute('DELETE FROM sessions WHERE expires_at<?', (time.time(),))
        conn.execute('DELETE FROM auth_attempts WHERE created_at<?', (time.time()-86400,))


def workspace_path(user_id):
    if not re.fullmatch(r'[a-f0-9]{32}', user_id):
        raise ValueError('Invalid account identifier')
    return auth_path().parent / 'workspaces' / user_id / 'reviews.db'


def rate_limit(key, limit=10, seconds=900):
    with accounts_db() as conn:
        conn.execute('BEGIN IMMEDIATE')
        recent = conn.execute('SELECT COUNT(*) FROM auth_attempts WHERE key=? AND created_at>?',
                              (key,time.time()-seconds)).fetchone()[0]
        if recent >= limit:
            raise HTTPException(429,'Too many attempts. Please try again later.')
        conn.execute('INSERT INTO auth_attempts VALUES (?,?)',(key,time.time()))


def password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.scrypt(password.encode('utf-8'),salt=bytes.fromhex(salt),n=131072,r=8,p=1,
                            maxmem=256*1024*1024,dklen=32).hex()
    return f'scrypt${salt}${digest}'


def valid_password(password, stored):
    try:
        return hmac.compare_digest(password_hash(password,stored.split('$')[1]),stored)
    except (ValueError,IndexError):
        return False


def public_user(user):
    return {key:user[key] for key in ('id','username','created_at')}


def create_account(username, password, sample=False):
    from services.storage import initialize
    username = username.strip().casefold()
    if not re.fullmatch(r'[a-z0-9][a-z0-9._-]{2,39}',username):
        raise HTTPException(422,'Use 3–40 letters, numbers, dots, underscores or hyphens for your username.')
    user={'id':uuid.uuid4().hex,'username':username,'created_at':time.time()}
    hashed=password_hash(password)
    with accounts_db() as conn:
        conn.execute('BEGIN IMMEDIATE')
        if conn.execute('SELECT 1 FROM users WHERE username=?',(username,)).fetchone():
            raise HTTPException(409,'That username is already taken. Choose another or sign in.')
        path=workspace_path(user['id'])
        path.parent.mkdir(parents=True,exist_ok=True)
        if sample:
            source=sqlite3.connect(connection.DB_PATH)
            target=sqlite3.connect(path)
            try:
                source.backup(target)
                # Shared sample source is never another user's workspace or report archive.
                for table in ('reports','imports','insight_actions'):
                    if target.execute('SELECT 1 FROM sqlite_master WHERE type=\'table\' AND name=?',(table,)).fetchone():
                        target.execute(f'DELETE FROM {table}')
                target.commit()
            finally:
                source.close()
                target.close()
        token=connection.WORKSPACE_PATH.set(path)
        try:
            initialize()
        finally:
            connection.WORKSPACE_PATH.reset(token)
        conn.execute('INSERT INTO users VALUES (?,?,?,?)',
                     (user['id'],username,hashed,user['created_at']))
    return user


def authenticate(username,password):
    with accounts_db() as conn:
        user=conn.execute('SELECT * FROM users WHERE username=?',(username.strip().casefold(),)).fetchone()
    # Equal-cost derivation for absent users avoids a fast password-check path.
    stored=user['password_hash'] if user else 'scrypt$'+'00'*16+'$'+'00'*32
    if not valid_password(password,stored) or not user:
        raise HTTPException(401,'Username or password is incorrect.')
    return public_user(user)


def new_session(user_id):
    token,csrf=secrets.token_urlsafe(32),secrets.token_urlsafe(32)
    with accounts_db() as conn:
        conn.execute('INSERT INTO sessions VALUES (?,?,?,?)',
                     (hashlib.sha256(token.encode()).hexdigest(),user_id,csrf,time.time()+SESSION_SECONDS))
    return token,csrf


def session_user(token):
    if not token or len(token)>128:
        return None
    with accounts_db() as conn:
        row=conn.execute('''SELECT u.id,u.username,u.created_at,s.csrf FROM sessions s
          JOIN users u ON u.id=s.user_id WHERE s.token_hash=? AND s.expires_at>?''',
          (hashlib.sha256(token.encode()).hexdigest(),time.time())).fetchone()
    return dict(row) if row else None


def revoke_session(token):
    with accounts_db() as conn:
        conn.execute('DELETE FROM sessions WHERE token_hash=?',(hashlib.sha256(token.encode()).hexdigest(),))


def recover_workspaces():
    from services.storage import initialize,recover_interrupted_runs
    with accounts_db() as conn:
        ids=[r[0] for r in conn.execute('SELECT id FROM users')]
    for user_id in ids:
        token=connection.WORKSPACE_PATH.set(workspace_path(user_id))
        try:
            initialize()
            recover_interrupted_runs()
        finally:
            connection.WORKSPACE_PATH.reset(token)
