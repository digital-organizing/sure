from django.contrib import admin
from django.db.models.query import QuerySet
from django.http import HttpResponse
from django.http.request import HttpRequest

from django.shortcuts import redirect
from django.urls import reverse
from unfold.decorators import action
from unfold.admin import ModelAdmin, TabularInline
from labor.models import (
    FTPConnection,
    Laboratory,
    LabOrder,
    LabOrderCounter,
    ResultMapping,
    TestProfile,
    LocationToLab,
)
from sure.models import TestResultOption

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


class ResultMappingInline(TabularInline):
    model = ResultMapping
    extra = 0

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "result_option":
            object_id = None
            if request.resolver_match:
                object_id = request.resolver_match.kwargs.get("object_id")

            if object_id:
                try:
                    test_kind_id = TestProfile.objects.filter(pk=object_id).values_list(
                        "test_kind_id", flat=True
                    ).get()
                    kwargs["queryset"] = TestResultOption.objects.filter(
                        test_kind_id=test_kind_id
                    ).order_by("label")
                except TestProfile.DoesNotExist:
                    kwargs["queryset"] = TestResultOption.objects.none()
            else:
                kwargs["queryset"] = TestResultOption.objects.none()

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

@admin.register(TestProfile)
class TestProfileAdmin(ModelAdmin):
    list_display = ("profile_name", "test_kind", "laboratory", "profile_code")
    search_fields = ("profile_name", "profile_code", "test_kind__name")
    list_filter = ("laboratory",)
    autocomplete_fields = ("test_kind", "laboratory")
    inlines = [ResultMappingInline]

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
    

    actions_detail = ["download_hl7"]
    
    
    @action(description="Download HL7 content", icon="download")
    def download_hl7(self, request, object_id):
        order = self.get_object(request, object_id)
        if not order:
            self.message_user(request, "Lab order not found.", level="error")

            return redirect(reverse("admin:labor_laborder_change", args=[object_id]))
        
        msg = order.content
        return HttpResponse(msg, content_type="text/plain", headers={"Content-Disposition": f'attachment; filename="lab_order_{order.order_number}.hl7"'})

    def has_change_permission(self, *args, **kwargs) -> bool:
        return False

    def has_add_permission(self, *args, **kwargs) -> bool:
        return False

    def has_delete_permission(self, *args, **kwargs) -> bool:
        return False

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        qs = super().get_queryset(request)
        if getattr(request.user, "is_superuser", False):
            return qs

        consultant = getattr(request.user, "consultant", None)
        if not consultant:
            return qs.none()
        return qs.filter(visit__case__location__tenant=consultant.tenant)
