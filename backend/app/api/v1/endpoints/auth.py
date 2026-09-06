from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import User
from app.services.auth_service import create_token, get_current_user, hash_password, require_roles, verify_password


router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=8, max_length=200)
    role: Literal['viewer', 'engineer', 'admin']


def public_user(user):
    return {'id': str(user.id), 'username': user.username, 'role': user.role, 'is_active': user.is_active}


@router.post('/login')
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    username = payload.username.strip().lower()
    user = db.query(User).filter(User.username == username, User.is_active.is_(True)).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, 'Incorrect username or password')
    return {'access_token': create_token(user), 'token_type': 'bearer', 'user': public_user(user)}


@router.get('/me')
def me(user: User = Depends(get_current_user)):
    return public_user(user)


@router.get('/users')
def list_users(_: User = Depends(require_roles('admin')), db: Session = Depends(get_db)):
    return [public_user(user) for user in db.query(User).order_by(User.username).all()]


@router.post('/users', status_code=201)
def create_user(payload: UserCreate, _: User = Depends(require_roles('admin')), db: Session = Depends(get_db)):
    username = payload.username.strip().lower()
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(409, 'Username already exists')
    user = User(username=username, password_hash=hash_password(payload.password), role=payload.role)
    db.add(user); db.commit(); db.refresh(user)
    return public_user(user)
