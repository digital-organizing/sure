# myapp/admin.py or a separate file like admin_site.py
# from django.contrib.admin import AdminSite
from functools import wraps

from django.shortcuts import redirect
from django_otp import devices_for_user
from unfold.sites import UnfoldAdminSite

from .auth import auth_2fa_or_trusted


def enforce_2fa(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("/login")

        if auth_2fa_or_trusted(request):
            return view_func(request, *args, **kwargs)

        devices = list(devices_for_user(request.user, confirmed=True))

        if not devices:
            return redirect("/setup-2fa")

        return redirect("/login")

    return wrapper


class MyAdminSite(UnfoldAdminSite):
    def admin_view(self, view, cacheable=False):
        inner = super().admin_view(view, cacheable)
        return enforce_2fa(inner)


admin_site = MyAdminSite(name="myadmin")
