from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from api.routers import dashboard, ingest, pipeline, reports, auth
from api.account_middleware import AccountMiddleware
from services.accounts import initialize_accounts,recover_workspaces
from services.storage import initialize, recover_interrupted_runs

@asynccontextmanager
async def lifespan(app):
    initialize()
    recover_interrupted_runs()
    initialize_accounts()
    recover_workspaces()
    yield

app = FastAPI(title='Customer feedback analysis', version='3.0.0', lifespan=lifespan)
app.add_middleware(AccountMiddleware)
app.add_middleware(CORSMiddleware, allow_origins=['http://localhost:5173', 'http://127.0.0.1:5173'],
                   allow_methods=['GET', 'POST', 'PATCH'], allow_headers=['Content-Type','X-CSRF-Token'],allow_credentials=True)
app.include_router(auth.router,prefix='/api/auth',tags=['Accounts'])
app.include_router(dashboard.router, prefix='/api/dashboard', tags=['Intelligence'])
app.include_router(ingest.router, prefix='/api/ingest', tags=['Sources'])
app.include_router(pipeline.router, prefix='/api/pipeline', tags=['Analysis'])
app.include_router(reports.router, prefix='/api/reports', tags=['Reports'])

@app.get('/api/health')
@app.get('/health', include_in_schema=False)
def health():
    return {'status': 'ok', 'version': '3.0.0'}

dist = Path(__file__).resolve().parents[1] / 'frontend' / 'dist'
if dist.exists():
    app.mount('/', StaticFiles(directory=dist, html=True), name='frontend')
