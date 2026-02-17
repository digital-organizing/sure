from django.contrib import admin
from django.db.models.query import QuerySet
from django.http.request import HttpRequest
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
    
    autocomplete_fields = ("managers",)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(managers=request.user)
    
    
    


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
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(laboratory__managers=request.user)


@admin.register(LocationToLab)
class LocationToLabAdmin(ModelAdmin):
    list_display = ("location", "labor", "client_code")
    search_fields = ("location__name", "labor__name", "client_code")
    autocomplete_fields = ("location", "labor")

    list_filter = ("labor",)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(labor__managers=request.user)


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

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs

        consultant = getattr(request.user, "consultant", None)
        if not consultant:
            return qs.none()
        return qs.filter(visit__case__location__tenant=consultant.tenant)