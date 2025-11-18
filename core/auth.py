from functools import wraps

from django.core.exceptions import PermissionDenied as Unauthorized


def auth_2fa_or_trusted(request) -> bool:
    return request.user.is_authenticated and (
        request.user.is_verified() or request.agent.is_trusted
    )


def auth_2fa(request) -> bool:
    return request.user.is_authenticated and request.user.is_verified()


def require_2fa(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not auth_2fa(request):
            raise Unauthorized("2FA required")
        return view_func(request, *args, **kwargs)

    return _wrapped_view
