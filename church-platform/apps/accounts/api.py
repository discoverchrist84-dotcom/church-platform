from django.contrib.auth import authenticate, login, logout
from django.db import IntegrityError
from ninja import Router, Schema
from ninja.errors import HttpError
from ninja.security import django_auth

from .models import User

router = Router()


class UserOut(Schema):
    id: int
    username: str
    email: str
    first_name: str
    last_name: str


class SignUpIn(Schema):
    username: str
    email: str
    password: str
    first_name: str = ""
    last_name: str = ""


class LoginIn(Schema):
    username: str
    password: str


@router.post("/signup", response={201: UserOut})
def signup(request, payload: SignUpIn):
    if len(payload.password) < 8:
        raise HttpError(400, "Password must be at least 8 characters.")
    if User.objects.filter(email__iexact=payload.email).exists():
        raise HttpError(400, "That email is already registered.")
    try:
        user = User.objects.create_user(
            username=payload.username,
            email=payload.email,
            password=payload.password,
            first_name=payload.first_name,
            last_name=payload.last_name,
        )
    except IntegrityError:
        raise HttpError(400, "That username is taken.")
    login(request, user)
    return 201, user


@router.post("/login", response=UserOut)
def api_login(request, payload: LoginIn):
    user = authenticate(request, username=payload.username, password=payload.password)
    if user is None:
        raise HttpError(401, "Invalid credentials.")
    login(request, user)
    return user


@router.post("/logout", auth=django_auth)
def api_logout(request):
    logout(request)
    return {"ok": True}


@router.get("/me", response=UserOut, auth=django_auth)
def me(request):
    return request.user
