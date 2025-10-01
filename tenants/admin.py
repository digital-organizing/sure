"""Admin configuration for the tenants app."""

from django.contrib import admin

from tenants.models import Counselor, Location, Tenant


class LocationInline(admin.TabularInline):
    """Inline admin for locations."""

    model = Location
    extra = 0


class CounselorInline(admin.TabularInline):
    """Inline admin for counselors."""

    model = Counselor
    extra = 0


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    """Admin for tenants.

    Only superusers can see all tenants.
    Regular users can only see tenants where they are admins."""

    list_display = ("name", "owner")
    search_fields = ("name", "owner__username", "owner__email")
    inlines = [LocationInline, CounselorInline]
    filter_horizontal = ("admins",)

    def get_queryset(self, request):
        """Limit queryset based on user permissions."""
        if request.user.is_superuser:
            return super().get_queryset(request)
        return super().get_queryset(request).filter(admins=request.user)
