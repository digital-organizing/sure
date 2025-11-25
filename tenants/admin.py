"""Admin configuration for the tenants app."""

from django.contrib import admin
from django.db.models.query import QuerySet
from django.http.request import HttpRequest
from django.urls import URLPattern, path
from django_otp import devices_for_user
from unfold.admin import ModelAdmin, TabularInline

from tenants.account import send_2fa_reset_mail, send_reset_mail
from tenants.models import Consultant, InformationBanner, Location, Tag, Tenant
from tenants.views import ConsultantInviteView


class LocationInline(TabularInline):
    """Inline admin for locations."""

    model = Location
    extra = 0


@admin.register(
    Location,
)
class LocationAdmin(ModelAdmin):
    """Admin for locations."""

    list_display = ("name", "tenant")
    search_fields = ("name", "tenant__name")

    autocomplete_fields = ("tenant",)
    filter_horizontal = ("excluded_questions",)

    def get_queryset(self, request: HttpRequest) -> QuerySet[Location]:
        if request.user.is_superuser:
            return super().get_queryset(request)
        return super().get_queryset(request).filter(tenant__admins=request.user)


@admin.register(
    Consultant,
)
class ConsultantAdmin(ModelAdmin):
    """Admin for consultants."""

    list_display = ("user", "tenant")
    search_fields = ("user__username", "user__email", "tenant__name")

    autocomplete_fields = ("user", "locations")

    readonly_fields = ("tenant", "user")

    actions = ["reset_password", "reset_2fa"]

    def get_queryset(self, request: HttpRequest) -> QuerySet[Consultant]:
        if request.user.is_superuser:
            return super().get_queryset(request)
        return super().get_queryset(request).filter(tenant__admins=request.user)

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
            if path.pattern.name != "tenants_consultant_add"
        ]


class ConsultantInline(TabularInline):
    """Inline admin for consultants."""

    model = Consultant
    extra = 0
    autocomplete_fields = ("locations",)
    readonly_fields = ("user",)


@admin.register(
    Tenant,
)
class TenantAdmin(ModelAdmin):
    """Admin for tenants.

    Only superusers can see all tenants.
    Regular users can only see tenants where they are admins."""

    list_display = ("name", "owner")
    search_fields = ("name", "owner__username", "owner__email")
    inlines = [LocationInline, ConsultantInline]
    autocomplete_fields = ("owner", "admins")

    def get_queryset(self, request):
        """Limit queryset based on user permissions."""
        if request.user.is_superuser:
            return super().get_queryset(request)
        return super().get_queryset(request).filter(admins=request.user)


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
        if request.user.is_superuser:
            return super().get_queryset(request)
        return super().get_queryset(request).filter(owner=request.user)


@admin.register(InformationBanner)
class InformationBannerAdmin(ModelAdmin):
    """Admin for information banners."""

    list_display = ("name", "created_at", "published_at", "expires_at", "tenant")
    search_fields = ("content", "tenant__name")

    autocomplete_fields = ("tenant", "locations")

    def get_queryset(self, request):
        """Limit queryset based on user permissions."""
        if request.user.is_superuser:
            return super().get_queryset(request)
        return super().get_queryset(request).filter(tenant__admins=request.user)
