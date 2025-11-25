import django_agent_trust
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django_otp import devices_for_user
from django_otp import login as otp_login
from django_otp import user_has_device, verify_token
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken
from django_otp.plugins.otp_totp.models import TOTPDevice
from ninja import Form, NinjaAPI, Schema
from ninja.security import django_auth
from ninja.throttling import AnonRateThrottle, AuthRateThrottle
from sesame.utils import get_user

import sure.api
import tenants.api
import texts.api
from core.auth import auth_2fa, auth_2fa_or_trusted

api = NinjaAPI(
    auth=auth_2fa_or_trusted,
    throttle=[
        AnonRateThrottle("5/s"),
        AuthRateThrottle("50/s"),
    ],
)

api.add_router("/sure", sure.api.router)
api.add_router("/tenants", tenants.api.router)
api.add_router("/texts", texts.api.router)


class LoginResponse(Schema):
    success: bool
    error: str | None = None


AUTH_RESPONSE = {
    200: LoginResponse,
    401: LoginResponse,
}


@api.post("/auth/login", auth=None, response=AUTH_RESPONSE)
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


@api.post("/auth/logout", auth=django_auth)
@csrf_exempt
def logout_view(request, forget: Form[bool] = False):
    logout(request)
    if forget:
        django_agent_trust.revoke_agent(request)
    return {"success": True}


@api.post(
    "/auth/set-initial-password",
    auth=None,
    response={200: LoginResponse, 400: list[str], 401: LoginResponse},
)
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
    try:
        validate_password(new_password, user)
    except ValidationError as e:
        return api.create_response(
            request,
            data=[err.message for err in e.error_list],
            status=400,
        )
    with transaction.atomic():
        user.set_password(new_password)
        user.save()
    login(request, user)
    return {"success": True}


class OTPDeviceResponse(Schema):
    id: str
    name: str
    config_url: str | None = None


@api.post(
    "/auth/otp/create-device",
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


@api.post("/auth/otp/verify-device", response=AUTH_RESPONSE, auth=django_auth)
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
    with transaction.atomic():
        device.confirmed = True
        device.save()
    otp_login(request, device)
    return {"success": True}


@api.post("/auth/otp/remove-device", response=AUTH_RESPONSE, auth=auth_2fa)
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
    "/auth/otp/devices",
    response={200: list[OTPDeviceResponse], 400: LoginResponse},
    auth=django_auth,
)
def list_otp_devices_view(request):
    devices = devices_for_user(request.user, confirmed=True)
    return [{"id": device.persistent_id, "name": device.name} for device in devices]


@api.post(
    "/auth/otp/backup-codes",
    response={200: list[str], 400: LoginResponse},
    auth=auth_2fa,
)
def generate_otp_backup_codes_view(request):
    static_device, created = StaticDevice.objects.get_or_create(
        user=request.user, name="Backup Codes"
    )
    if not created:
        with transaction.atomic():
            static_device.delete()
            static_device = StaticDevice.objects.create(
                user=request.user, name="Backup Codes"
            )
    with transaction.atomic():
        for _i in range(10):
            static_device.token_set.create(token=StaticToken.random_token())
    return static_device.token_set.values_list("token", flat=True)


@api.post("/auth/otp/2fa-challenge", response=AUTH_RESPONSE, auth=django_auth)
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

    if remember:
        django_agent_trust.trust_agent(request, trust_days=30)
    else:
        django_agent_trust.trust_session(request)

    return {"success": True}


@api.post("/auth/set-password", response=AUTH_RESPONSE, auth=auth_2fa)
def change_password_view(request, old_password: Form[str], new_password: Form[str]):
    user = request.user
    if not user.check_password(old_password):
        return api.create_response(
            request,
            data=LoginResponse(success=False, error="Old password is incorrect"),
            status=401,
        )
    if old_password == new_password:
        return api.create_response(
            request,
            data=LoginResponse(
                success=False, error="New password must be different from old password"
            ),
            status=400,
        )
    try:
        validate_password(new_password, user)
    except ValidationError as e:
        return api.create_response(
            request,
            data=[err.message for err in e.error_list],
            status=400,
        )
    with transaction.atomic():
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
    full_name: str | None = None


@api.post("/auth/account", response=AccountResponse, auth=None)
def account(request):
    if request.user.is_authenticated:
        return {
            "username": request.user.username,
            "is_staff": request.user.is_staff,
            "is_superuser": request.user.is_superuser,
            "verified": request.user.is_verified() or request.agent.is_trusted,
            "otp": request.user.is_verified(),
            "is_trusted": request.agent.is_trusted,
            "full_name": request.user.get_full_name(),
        }
    return {"username": None, "is_staff": None, "is_superuser": None}
