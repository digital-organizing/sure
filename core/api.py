from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from ninja import Form, NinjaAPI, Schema
from ninja.security import django_auth

import sure.api
import tenants.api

api = NinjaAPI(auth=django_auth)

api.add_router("/sure", sure.api.router)
api.add_router("/tenants", tenants.api.router)


class CsrfTokenResponse(Schema):
    csrfToken: str


@ensure_csrf_cookie
@api.post("/csrf", auth=None, response=CsrfTokenResponse)
def get_csrf_token(request) -> CsrfTokenResponse:
    return CsrfTokenResponse(csrfToken=get_token(request))


class LoginResponse(Schema):
    success: bool
    error: str | None = None


@api.post("/login", auth=None)
def login_view(request, username: Form[str], password: Form[str]):
    if (
        user := authenticate(request, username=username, password=password)
    ) is not None:
        login(request, user)
        return {"success": True}
    return api.create_response(
        request,
        {"message": "Invalid username or password."},
        status=401,
    )


@api.post("/logout")
def logout_view(request):
    logout(request)
    return {"success": True}


class AccountResponse(Schema):
    username: str | None
    is_staff: bool | None = None
    is_superuser: bool | None = None


@api.post("/account", response=AccountResponse, auth=None)
def account(request):
    if request.user.is_authenticated:
        return {
            "username": request.user.username,
            "is_staff": request.user.is_staff,
            "is_superuser": request.user.is_superuser,
        }
    return {"username": None, "is_staff": None, "is_superuser": None}
