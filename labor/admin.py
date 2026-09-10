from django.contrib import admin
from django.db.models.query import QuerySet
from django.http import HttpResponse
from django.http.request import HttpRequest
from django.shortcuts import redirect
from django.urls import reverse
from simple_history.admin import SimpleHistoryAdmin
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import action

from labor.models import (
    FTPConnection,
    HL7Result,
    Laboratory,
    LabOrder,
    LabOrderCounter,
    LocationToLab,
    OrderStatus,
    ResultMapping,
    TestProfile,
)
from labor.tasks import (
    MAX_PROCESSING_ATTEMPTS,
    process_single_result,
    retrieve_results_task,
    upload_single_order,
)
from sure.models import TestResultOption

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

    actions_detail = ["fetch_results"]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs

        return qs.filter(managers=request.user)

    @action(description="Fetch results", icon="refresh")  # ty:ignore[call-non-callable]
    def fetch_results(self, request, object_id):
        laboratory = self.get_object(request, object_id)
        if not laboratory:
            self.message_user(request, "Laboratory not found.", level="error")
            return redirect(reverse("admin:labor_laboratory_change", args=[object_id]))

        retrieve_results_task.delay(laboratory.id)
        self.message_user(request, "Result retrieval initiated.", level="success")
        return redirect(reverse("admin:labor_laboratory_change", args=[object_id]))


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
                    test_kind_id = (
                        TestProfile.objects.filter(pk=object_id)
                        .values_list("test_kind_id", flat=True)
                        .get()
                    )
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

    actions_detail = ["download_hl7", "upload_hl7"]

    @action(description="Download HL7 content", icon="download")  # ty:ignore[call-non-callable]
    def download_hl7(self, request, object_id):
        order = self.get_object(request, object_id)
        if not order:
            self.message_user(request, "Lab order not found.", level="error")

            return redirect(reverse("admin:labor_laborder_change", args=[object_id]))

        msg = order.content
        return HttpResponse(
            msg,
            content_type="text/plain",
            headers={
                "Content-Disposition": f'attachment; filename="lab_order_{order.order_number}.hl7"'
            },
        )

    @action(description="Upload", icon="upload")  # ty:ignore[call-non-callable]
    def upload_hl7(self, request, object_id):
        obj = self.get_object(request, object_id)
        if not obj:
            self.message_user(request, "Lab order not found.", level="error")
            return redirect(reverse("admin:labor_laborder_change", args=[object_id]))

        if obj.status != OrderStatus.GENERATED:
            self.message_user(
                request,
                "Only orders with status 'Generated' can be uploaded.",
                level="error",
            )
            return redirect(reverse("admin:labor_laborder_change", args=[object_id]))
        upload_single_order.delay(obj.pk)
        self.message_user(request, "Lab order upload started.", level="success")
        return redirect(reverse("admin:labor_laborder_change", args=[object_id]))

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


@admin.register(HL7Result)
class HL7ResultAdmin(ModelAdmin):
    """Visibility into what the lab sent and why processing failed.

    Without this the scheduled task wrote errors into a field nobody could
    read, and a message that failed for a fixable reason had no way back in.
    """

    list_display = (
        "__str__",
        "laboratory",
        "created_at",
        "processed_at",
        "attempts",
        "processing_state",
    )
    list_filter = ("laboratory", "processed_at", "created_at")
    search_fields = ("content", "logs")
    readonly_fields = ("created_at", "processed_at", "attempts", "content", "logs")
    date_hierarchy = "created_at"

    actions_detail = ["reprocess"]

    @admin.display(description="State")
    def processing_state(self, obj: HL7Result) -> str:
        if obj.processed_at:
            return "Processed"
        if obj.attempts >= MAX_PROCESSING_ATTEMPTS:
            return f"Given up after {obj.attempts} attempts"
        if obj.attempts:
            return f"Failed {obj.attempts}x, will retry"
        return "Pending"

    def has_add_permission(self, *args, **kwargs) -> bool:
        return False

    def has_change_permission(self, *args, **kwargs) -> bool:
        return False

    @action(description="Process again", icon="refresh")  # ty:ignore[call-non-callable]
    def reprocess(self, request, object_id):
        result = self.get_object(request, object_id)
        if not result:
            self.message_user(request, "HL7 result not found.", level="error")
            return redirect(reverse("admin:labor_hl7result_changelist"))

        # Clear the attempt count so a message abandoned earlier gets a fresh
        # run once the underlying cause (a missing profile, say) is fixed.
        result.attempts = 0
        result.save(update_fields=["attempts"])
        process_single_result.delay(result.pk)

        self.message_user(request, "Processing started.", level="success")
        return redirect(reverse("admin:labor_hl7result_change", args=[object_id]))
