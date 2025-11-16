import django_agent_trust
from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from django_otp import devices_for_user
from django_otp import login as otp_login
from django_otp import user_has_device, verify_token
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken
from django_otp.plugins.otp_totp.models import TOTPDevice
from ninja import Form, NinjaAPI, Schema
from ninja.security import django_auth
from sesame.utils import get_user

import sure.api
import tenants.api
from core.auth import auth_2fa, auth_2fa_or_trusted

api = NinjaAPI(auth=auth_2fa_or_trusted)

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


AUTH_RESPONSE = {
    200: LoginResponse,
    401: LoginResponse,
}


@api.post("/login", auth=None, response=AUTH_RESPONSE)
def login_view(request, username: Form[str], password: Form[str]):
    if (
        user := authenticate(request, username=username, password=password)
    ) is not None:
        login(request, user)
        return {"success": True}
    return api.create_response(
        request,
        data=LoginResponse(success=False, error="Invalid credentials"),
        status=401,
    )


@api.post("/logout", auth=django_auth)
def logout_view(request, forget: Form[bool] = False):
    logout(request)
    print("Forget device:", forget)
    if forget:
        print("Revoking trusted agent")
        django_agent_trust.revoke_agent(request)
    return {"success": True}


@api.post("/set-initial-password", auth=None, response=AUTH_RESPONSE)
def set_initial_password(
    request, sesame: Form[str], email: Form[str], new_password: Form[str]
):
    user = get_user(sesame, scope=f"setup_account:{email}")
    if user is None:
        return api.create_response(
            request,
            data=LoginResponse(success=False, error="Invalid or expired token"),
            status=401,
        )
    if user.has_usable_password():
        return api.create_response(
            request,
            data=LoginResponse(success=False, error="Password has already been set"),
            status=400,
        )
    user.set_password(new_password)
    user.save()
    return {"success": True}


class OTPDeviceResponse(Schema):
    id: str
    name: str
    config_url: str | None = None


@api.post(
    "/otp/create-device",
    response={200: OTPDeviceResponse, 400: LoginResponse},
    auth=django_auth,
)
def setup_otp_view(request, name: Form[str]):
    if user_has_device(request.user, True) and not request.user.is_verified():
        return api.create_response(
            request,
            data=LoginResponse(
                success=False, error="Device already exists and user not verified"
            ),
            status=400,
        )

    device = TOTPDevice.objects.create(user=request.user, name=name, confirmed=False)
    return {
        "id": device.persistent_id,
        "name": device.name,
        "config_url": device.config_url,
    }


@api.post("/otp/verify-device", response=AUTH_RESPONSE, auth=django_auth)
def verify_otp_view(request, device_id: Form[str], token: Form[str]):
    if user_has_device(request.user, True) and not auth_2fa_or_trusted(request):
        return api.create_response(
            request,
            data=LoginResponse(
                success=False, error="Log in with 2fa before verifying a new device"
            ),
            status=400,
        )
    device = verify_token(request.user, device_id, token)
    if device is None:
        return api.create_response(
            request,
            data=LoginResponse(success=False, error="Invalid token"),
            status=401,
        )
    device.confirmed = True
    device.save()
    otp_login(request, device)
    return {"success": True}


@api.post("/otp/remove-device", response=AUTH_RESPONSE, auth=auth_2fa)
def remove_otp_view(request, device_id: Form[str]):
    devices = devices_for_user(request.user, confirmed=True)
    for device in devices:
        if device.persistent_id == device_id:
            device.delete()
            return {"success": True}
    return api.create_response(
        request,
        data=LoginResponse(success=False, error="Device not found"),
        status=404,
    )


@api.get(
    "/otp/devices",
    response={200: list[OTPDeviceResponse], 400: LoginResponse},
    auth=django_auth,
)
def list_otp_devices_view(request):
    devices = devices_for_user(request.user, confirmed=True)
    return [{"id": device.persistent_id, "name": device.name} for device in devices]


@api.post("/otp/backup-codes", response=list[str], auth=auth_2fa)
def generate_otp_backup_codes_view(request):
    static_device, created = StaticDevice.objects.get_or_create(
        user=request.user, name="Backup Codes"
    )
    if not created:
        static_device.delete()
        static_device = StaticDevice.objects.create(
            user=request.user, name="Backup Codes"
        )
    for _i in range(10):
        static_device.token_set.create(token=StaticToken.random_token())
    return static_device.token_set.values_list("token", flat=True)


@api.post("/otp/2fa-challenge", response=AUTH_RESPONSE, auth=django_auth)
def otp_2fa_challenge_view(
    request, device_id: Form[str], token: Form[str], remember: Form[bool] = False
):
    device = verify_token(request.user, device_id, token)
    if device is None:
        return api.create_response(
            request,
            data=LoginResponse(success=False, error="Invalid token"),
            status=401,
        )
    otp_login(request, device)
    print("Remember device:", remember)

    if remember:
        django_agent_trust.trust_agent(request, trust_days=30)
    else:
        django_agent_trust.trust_session(request)

    return {"success": True}


@api.post("/set-password", response=AUTH_RESPONSE, auth=auth_2fa)
def change_password_view(request, old_password: Form[str], new_password: Form[str]):
    user = request.user
    if not user.check_password(old_password):
        return api.create_response(
            request,
            data=LoginResponse(success=False, error="Old password is incorrect"),
            status=401,
        )
    user.set_password(new_password)
    user.save()
    return {"success": True}


class AccountResponse(Schema):
    username: str | None
    is_staff: bool | None = None
    is_superuser: bool | None = None
    verified: bool | None = None
    otp: bool | None = None
    is_trusted: bool | None = None


@api.post("/account", response=AccountResponse, auth=None)
def account(request):
    if request.user.is_authenticated:
        return {
            "username": request.user.username,
            "is_staff": request.user.is_staff,
            "is_superuser": request.user.is_superuser,
            "verified": request.user.is_verified() or request.agent.is_trusted,
            "otp": request.user.is_verified(),
            "is_trusted": request.agent.is_trusted,
        }
    return {"username": None, "is_staff": None, "is_superuser": None}
