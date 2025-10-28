from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from ninja import Form, NinjaAPI, Schema
from ninja.security import django_auth

import sure.api

api = NinjaAPI(auth=django_auth)

api.add_router("/sure", sure.api.router)


class CsrfTokenResponse(Schema):
    csrfToken: str


@ensure_csrf_cookie
@api.post("/csrf", auth=None, response=CsrfTokenResponse)
def get_csrf_token(request) -> CsrfTokenResponse:
    return CsrfTokenResponse(csrfToken=get_token(request))


@api.post("/login", auth=None)
def login_view(request, username: Form[str], password: Form[str]):
    if (
        user := authenticate(request, username=username, password=password)
    ) is not None:
        login(request, user)
        return {"success": True}
    return {"success": False}


@api.post("/logout")
def logout_view(request):
    logout(request)
    return {"success": True}


@api.post("/account")
def account(request):
    if request.user.is_authenticated:
        return {"username": request.user.username}
    return {"username": None}
