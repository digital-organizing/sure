"""Admin configuration for the tenants app."""

from typing import Any
from django.contrib import admin
from django.db.models.query import QuerySet
from django.http.request import HttpRequest
from django.shortcuts import redirect
from django.contrib.auth.models import Group
from django.urls import URLPattern, path
from django.utils.translation import gettext_lazy as _
from django_otp import devices_for_user
from modeltranslation.admin import TabbedTranslationAdmin
from simple_history.admin import SimpleHistoryAdmin
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import action

from tenants.account import send_2fa_reset_mail, send_reset_mail
from tenants.models import (
    APIToken,
    Consultant,
    InformationBanner,
    Location,
    Tag,
    Tenant,
)
from tenants.views import ConsultantInviteView


class LocationInline(TabularInline):
    """Inline admin for locations."""

    model = Location
    extra = 0


@admin.register(
    Location,
)
class LocationAdmin(SimpleHistoryAdmin, ModelAdmin):
    """Admin for locations."""

    list_display = ("name", "tenant")
    search_fields = ("name", "tenant__name")

    autocomplete_fields = ("tenant",)
    filter_horizontal = ("excluded_questions", "included_questions")

    # Section for excluded and included questions with title ('visible questions')
    fieldsets = (
        (
            None,
            {
                "fields": ("name", "tenant", "opening_hours", "phone_number"),
            },
        ),
        (
            _("Visible questions"),
            {
                "fields": ("excluded_questions", "included_questions"),
                "classes": ("tab",),
            },
        ),
    )

    def get_queryset(self, request: HttpRequest) -> QuerySet[Location]:
        if getattr(request.user, "is_superuser", False):
            return super().get_queryset(request)
        return super().get_queryset(request).filter(tenant__admins=request.user)


@admin.register(
    Consultant,
)
class ConsultantAdmin(SimpleHistoryAdmin, ModelAdmin):
    """Admin for consultants."""

    list_display = (
        "user",
        "tenant",
        "user__first_name",
        "user__last_name",
        "display_locations",
    )
    search_fields = ("user__username", "user__email", "tenant__name")

    autocomplete_fields = ("user", "locations")

    readonly_fields = ("tenant", "user")

    actions = ["reset_password", "reset_2fa"]

    actions_detail = ["reset_password_detail", "reset_2fa_detail"]

    def get_queryset(self, request: HttpRequest) -> QuerySet[Consultant]:
        if getattr(request.user, "is_superuser", False):
            return super().get_queryset(request)
        return super().get_queryset(request).filter(tenant__admins=request.user)

    @action(description="Reset password")
    def reset_password_detail(self, request: HttpRequest, object_id: int):
        """Admin action to reset password for a single consultant."""
        consultant = self.get_queryset(request).get(pk=object_id)
        user = consultant.user
        user.set_unusable_password()
        user.save()
        send_reset_mail(request, consultant)
        return redirect("admin:tenants_consultant_change", object_id)

    @action(description="Reset 2FA")
    def reset_2fa_detail(self, request: HttpRequest, object_id: int):
        """Admin action to reset 2FA for a single consultant."""
        consultant = self.get_queryset(request).get(pk=object_id)
        user = consultant.user
        for device in devices_for_user(user):
            device.delete()
        send_2fa_reset_mail(request, user)
        return redirect("admin:tenants_consultant_change", object_id)

    @admin.action(description="Reset passwords for selected consultants")
    def reset_password(
        self, request: HttpRequest, queryset: QuerySet[Consultant]
    ) -> None:
        """Admin action to reset passwords for selected consultants."""
        for consultant in queryset:
            user = consultant.user
            user.set_unusable_password()
            user.save()
            send_reset_mail(request, consultant)

    @admin.action(description="Reset 2FA for selected consultants")
    def reset_2fa(self, request: HttpRequest, queryset: QuerySet[Consultant]) -> None:
        """Admin action to reset 2FA for selected consultants."""
        for consultant in queryset:
            user = consultant.user
            for device in devices_for_user(user):
                device.delete()
            send_2fa_reset_mail(request, user)

    def get_urls(self) -> list[URLPattern]:
        invite_view = self.admin_site.admin_view(
            ConsultantInviteView.as_view(model_admin=self)
        )
        return [
            path("add/", invite_view, name="tenants_consultant_add"),
        ] + [
            path
            for path in super().get_urls()
            if getattr(path.pattern, "name", None) != "tenants_consultant_add"
        ]

    def display_locations(self, obj: Consultant) -> str:
        """Display locations as a comma-separated list."""
        return ", ".join(location.name for location in obj.locations.all())

    display_locations.short_description = "Locations"  # type: ignore[unresolved-attribute]


class ConsultantInline(TabularInline):
    """Inline admin for consultants."""

    model = Consultant
    extra = 0
    autocomplete_fields = ("locations",)
    readonly_fields = ("user",)


@admin.register(
    Tenant,
)
class TenantAdmin(SimpleHistoryAdmin, ModelAdmin):
    """Admin for tenants.

    Only superusers can see all tenants.
    Regular users can only see tenants where they are admins."""

    list_display = ("name", "owner")
    search_fields = ("name", "owner__username", "owner__email")
    inlines = [LocationInline, ConsultantInline]
    autocomplete_fields = ("owner", "admins")

    def get_queryset(self, request):
        """Limit queryset based on user permissions."""
        if getattr(request.user, "is_superuser", False):
            return super().get_queryset(request)
        return super().get_queryset(request).filter(admins=request.user)

    def save_related(
        self, request: HttpRequest, form: Any, formsets: Any, change: Any
    ) -> None:
        ret = super().save_related(request, form, formsets, change)
        for user in form.instance.admins.all():
            user.is_staff = True
            user.groups.add(Group.objects.get_or_create(name="Tenant Admins")[0])
            user.save()
        return ret


@admin.register(
    Tag,
)
class TagAdmin(ModelAdmin):
    """Admin for tags."""

    list_display = ("name", "owner")
    search_fields = ("name", "owner__username", "owner__email")

    autocomplete_fields = ("owner", "available_in")

    def get_queryset(self, request):
        """Limit queryset based on user permissions."""
        if getattr(request.user, "is_superuser", False):
            return super().get_queryset(request)
        return (
            super()
            .get_queryset(request)
            .filter(owner__consultant__tenant__admins=request.user)
        )


@admin.register(InformationBanner)
class InformationBannerAdmin(SimpleHistoryAdmin, ModelAdmin, TabbedTranslationAdmin):
    """Admin for information banners."""

    list_display = ("name", "created_at", "published_at", "expires_at", "tenant")
    search_fields = ("content", "tenant__name")

    autocomplete_fields = ("tenant", "locations")

    def get_queryset(self, request):
        """Limit queryset based on user permissions."""
        if getattr(request.user, "is_superuser", False):
            return super().get_queryset(request)
        return super().get_queryset(request).filter(tenant__admins=request.user)


@admin.register(APIToken)
class APITokenAdmin(ModelAdmin):
    """Admin for API tokens."""

    list_display = ("name", "tenant", "owner", "revoked", "created_at")
    search_fields = ("name", "tenant__name", "owner__username", "owner__email")

    autocomplete_fields = ("tenant", "owner")
    exclude = ("token",)

    readonly_fields = ("created_at", "header")

    def header(self, obj: APIToken) -> str:
        """Display the full API token header."""
        return f"{obj.name}:{obj.token}"

    header.short_description = "X-Tenant-Token"  # type: ignore[unresolved-attribute]

    def get_queryset(self, request):
        """Limit queryset based on user permissions."""
        if getattr(request.user, "is_superuser", False):
            return super().get_queryset(request)
        return super().get_queryset(request).filter(tenant__admins=request.user)
