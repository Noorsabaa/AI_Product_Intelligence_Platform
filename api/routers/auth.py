import os
from fastapi import APIRouter,Request,Response
from pydantic import BaseModel,Field
from services.accounts import COOKIE,SESSION_SECONDS,create_account,authenticate,new_session,session_user,revoke_session,rate_limit,public_user

router=APIRouter()

class Credentials(BaseModel):
    username:str=Field(min_length=3,max_length=40)
    password:str=Field(min_length=12,max_length=128)

class Registration(Credentials):
    sample:bool=False

def signed_in(user,response):
    token,csrf=new_session(user['id'])
    response.set_cookie(COOKIE,token,max_age=SESSION_SECONDS,httponly=True,
                        secure=os.getenv('COOKIE_SECURE')=='1',samesite='lax',path='/')
    response.headers['Cache-Control']='no-store'
    return {'user':public_user(user),'csrf':csrf}

@router.post('/register',status_code=201)
def register(body:Registration,request:Request,response:Response):
    rate_limit('register:'+request.client.host,5,3600)
    return signed_in(create_account(body.username,body.password,body.sample),response)

@router.post('/login')
def login(body:Credentials,request:Request,response:Response):
    rate_limit('login-ip:'+request.client.host,30,900)
    rate_limit('login-user:'+body.username.strip().casefold(),10,900)
    return signed_in(authenticate(body.username,body.password),response)

@router.get('/session')
def session(request:Request,response:Response):
    response.headers['Cache-Control']='no-store'
    user=session_user(request.cookies.get(COOKIE))
    return {'user':public_user(user) if user else None,'csrf':user['csrf'] if user else None}

@router.post('/logout')
def logout(request:Request,response:Response):
    revoke_session(request.cookies.get(COOKIE,''))
    response.delete_cookie(COOKIE,path='/')
    return {'ok':True}
