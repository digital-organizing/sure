# myapp/admin.py or a separate file like admin_site.py
# from django.contrib.admin import AdminSite
from functools import wraps

from django.db.models import Q
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


class ScopedChoicesMixin:
    """Limits relation fields to what the user may see in the related admin.

    The autocomplete search is already scoped by the related admin's
    get_queryset, but the form validates a submitted id against every row, so
    an id of another tenant would be accepted. Values the edited object already
    has stay valid, otherwise saving would silently drop or reject them.
    """

    def get_form(self, request, obj=None, **kwargs):
        request._scoped_choices_obj = obj
        return super().get_form(request, obj, **kwargs)

    def _scoped_queryset(self, db_field, request):
        if getattr(request.user, "is_superuser", False):
            return None
        related_model = db_field.remote_field.model
        related_admin = self.admin_site._registry.get(related_model)
        if related_admin is None:
            return None

        allowed = Q(pk__in=related_admin.get_queryset(request).values("pk"))
        obj = getattr(request, "_scoped_choices_obj", None)
        if obj is not None and obj.pk and isinstance(obj, db_field.model):
            if db_field.many_to_many:
                current = getattr(obj, db_field.name).values("pk")
                allowed |= Q(pk__in=current)
            else:
                allowed |= Q(pk=getattr(obj, db_field.attname))
        return related_model._default_manager.filter(allowed)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if "queryset" not in kwargs:
            queryset = self._scoped_queryset(db_field, request)
            if queryset is not None:
                kwargs["queryset"] = queryset
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if "queryset" not in kwargs:
            queryset = self._scoped_queryset(db_field, request)
            if queryset is not None:
                kwargs["queryset"] = queryset
        return super().formfield_for_manytomany(db_field, request, **kwargs)


class MyAdminSite(UnfoldAdminSite):
    def admin_view(self, view, cacheable=False):
        inner = super().admin_view(view, cacheable)
        return enforce_2fa(inner)


admin_site = MyAdminSite(name="myadmin")
