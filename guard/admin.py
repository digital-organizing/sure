from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.db.models import Q
from django.utils import timezone
from unfold.admin import ModelAdmin

from .models import ProtectedEndpoint, BlockedIdentifier, BlockedEndpointHit



@admin.register(ProtectedEndpoint)
class ProtectedEndpointAdmin(ModelAdmin):
    list_display = ("path_matcher", "description", "status_code", "max_errors", "window", "block_duration")

class EnabledFilter(admin.SimpleListFilter):
    title = "Enabled Status"
    parameter_name = "enabled"

    def lookups(self, request, model_admin):
        return (
            ("enabled", "Enabled"),
            ("disabled", "Disabled"),
        )

    def queryset(self, request, queryset):
        if self.value() == "enabled":
            return queryset.filter(Q(disabled_at__isnull=True) | Q(disabled_at__gt=timezone.now()))
        if self.value() == "disabled":
            return queryset.filter(Q(disabled_at__isnull=False) & Q(disabled_at__lte=timezone.now()))
        return queryset


@admin.register(BlockedIdentifier)
class BlockedIdentifierAdmin(ModelAdmin):
    list_display = ("identifier", "reason", "blocked_at", "disabled_at", "disabled_by")
    list_filter = ("reason", "disabled_by", EnabledFilter)
    
    
    @admin.action(description="Clear selected blocks")
    def clear_blocks(self, request, queryset):
        queryset.update(disabled_at=timezone.now(), disabled_by=request.user)
        