from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from labor.models import (
    FTPConnection,
    Laboratory,
    LabOrder,
    LabOrderCounter,
    TestProfile,
    LocationToLab,
)

from simple_history.admin import SimpleHistoryAdmin

from .forms import FTPConnectionForm


class FTPConnectionInline(TabularInline):
    model = FTPConnection
    extra = 0

    form = FTPConnectionForm


@admin.register(Laboratory)
class LaboratoryAdmin(ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)

    inlines = [FTPConnectionInline]


@admin.register(LabOrderCounter)
class LabOrderCounterAdmin(ModelAdmin):
    list_display = ("base_number", "last_index")
    search_fields = ("base_number",)

    list_filter = ("nr_kreis",)


@admin.register(TestProfile)
class TestProfileAdmin(ModelAdmin):
    list_display = ("profile_name", "test_kind", "laboratory", "profile_code")
    search_fields = ("profile_name", "profile_code", "test_kind__name")
    list_filter = ("laboratory",)
    autocomplete_fields = ("test_kind", "laboratory")


@admin.register(LocationToLab)
class LocationToLabAdmin(ModelAdmin):
    list_display = ("location", "labor", "client_code")
    search_fields = ("location__name", "labor__name", "client_code")
    autocomplete_fields = ("location", "labor")

    list_filter = ("labor",)


@admin.register(LabOrder)
class LabOrderAdmin(SimpleHistoryAdmin, ModelAdmin):
    list_display = (
        "order_number",
        "visit",
        "created_at",
        "status",
        "visit__case__location",
    )
    search_fields = ("order_number", "visit__case__id")
    list_filter = ("status", "created_at", "visit__case__location")

    def has_change_permission(self, *args, **kwargs) -> bool:
        return False

    def has_add_permission(self, *args, **kwargs) -> bool:
        return False

    def has_delete_permission(self, *args, **kwargs) -> bool:
        return False
