"""Pure ASGI middleware keeps workspace context through response background jobs."""
import hmac
from urllib.parse import urlsplit
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from db.connection import WORKSPACE_PATH
from services.accounts import COOKIE,session_user,workspace_path


class AccountMiddleware:
    def __init__(self,app):
        self.app=app

    async def __call__(self,scope,receive,send):
        if scope['type']!='http' or not scope['path'].startswith('/api/'):
            return await self.app(scope,receive,send)
        request=Request(scope,receive)
        mutating=request.method in ('POST','PUT','PATCH','DELETE')
        if mutating and request.headers.get('origin'):
            origin=urlsplit(request.headers['origin'])
            if origin.netloc!=request.headers.get('host'):
                return await JSONResponse({'detail':'Request origin is not allowed.'},status_code=403)(scope,receive,send)
        if scope['path'] in ('/api/health','/api/auth/register','/api/auth/login','/api/auth/session'):
            return await self.app(scope,receive,send)
        user=await run_in_threadpool(session_user,request.cookies.get(COOKIE))
        if not user:
            return await JSONResponse({'detail':'Sign in to access your workspace.'},status_code=401)(scope,receive,send)
        if mutating and not hmac.compare_digest(request.headers.get('x-csrf-token',''),user['csrf']):
            return await JSONResponse({'detail':'Session security token is missing. Refresh and try again.'},status_code=403)(scope,receive,send)
        scope.setdefault('state',{})['user']=user
        token=WORKSPACE_PATH.set(workspace_path(user['id']))
        try:
            async def private_send(message):
                if message['type']=='http.response.start':
                    message['headers']=list(message.get('headers',[]))+[(b'cache-control',b'no-store')]
                await send(message)
            await self.app(scope,receive,private_send)
        finally:
            WORKSPACE_PATH.reset(token)
