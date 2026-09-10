from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.functional import cached_property
from .models import ReportFormFile, Test, VisitExport, VisitExportDownload
from django.core.exceptions import PermissionDenied
from core.auth import require_2fa_or_trusted

import io
import polars as pl
from typing import Any
from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from django.views.generic.edit import FormView
from unfold.views import UnfoldModelAdminViewMixin

from sure.client_service import create_case, create_visit, get_case_link
from sure.forms import (
    GenerateCaseBatchForm,
    ReportCopyMappingForm,
    ReportTestFillForm,
)
from sure.report_forms import copy_mapping, fill_report


@require_2fa_or_trusted
def download_visit_export(request, pk):
    visit_export = VisitExport.objects.get(pk=pk)

    if not request.user.is_superuser:
        export_tenant = visit_export.user.consultant.tenant_id
        user_tenant = request.user.consultant.tenant_id

        if export_tenant != user_tenant:
            raise PermissionDenied(
                "You do not have permission to download this export."
            )

    redirect_url = visit_export.file.url
    VisitExportDownload.objects.create(
        visit_export=visit_export,
        user=request.user,
    )
    # Logic to handle the download process would go here
    return redirect(redirect_url)


class GenerateCaseBatchView(UnfoldModelAdminViewMixin, FormView):
    """Admin view for generating batches of cases."""

    title = "Generate Case Batch"
    permission_required = ("sure.add_visit",)
    form_class = GenerateCaseBatchForm
    template_name = "admin/sure/generate_batch.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def form_valid(self, form: Any) -> HttpResponse:
        location = form.cleaned_data["location"]
        questionnaire = form.cleaned_data["questionnaire"]
        tag = form.cleaned_data["tag"]
        quantity = form.cleaned_data["quantity"]
        selected_tests = form.cleaned_data.get("tests", [])

        records = []
        with transaction.atomic():
            for _ in range(quantity):
                case = create_case(
                    location_id=location.pk,
                    user=self.request.user,
                    external_id="",
                    language="en",
                )
                visit = create_visit(case, questionnaire)
                visit.tags = [tag]
                visit.save(update_fields=["tags"])

                # Create selected tests for this visit
                if selected_tests:
                    tests_to_create = [
                        Test(visit=visit, test_kind=test_kind, user=self.request.user)
                        for test_kind in selected_tests
                    ]
                    Test.objects.bulk_create(tests_to_create)

                visit.logs.create(
                    action="Case created (batch)",
                    user=self.request.user,
                )

                link = get_case_link(case)
                records.append(
                    {
                        "Case ID": case.human_id,
                        "Access Link": link,
                        "Location": location.name,
                        "Questionnaire": questionnaire.name,
                        "Tag": tag,
                        "Created At": timezone.localtime(visit.created_at).strftime(
                            "%Y-%m-%d %H:%M:%S"
                        ),
                    }
                )

        df = pl.DataFrame(records)
        output = io.BytesIO()
        df.write_excel(output)
        output.seek(0)

        filename = (
            f"case_batch_{location.name.replace(' ', '_')}_{tag.replace(' ', '_')}.xlsx"
        )
        response = HttpResponse(
            output.read(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f"attachment; filename={filename}"
        return response


class ReportFormFileActionView(UnfoldModelAdminViewMixin, FormView):
    """Base of the admin views that act on one report form file."""

    permission_required = ("sure.change_reportformfile",)
    template_name = "admin/sure/report_form_file_action.html"
    description = ""

    @cached_property
    def file(self) -> ReportFormFile:
        return get_object_or_404(
            ReportFormFile.objects.select_related("form"), pk=self.kwargs["object_id"]
        )

    def get_change_url(self) -> str:
        return reverse("admin:sure_reportformfile_change", args=[self.file.pk])

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "title": f"{self.title}: {self.file}",
                "description": self.description,
                "file": self.file,
                "change_url": self.get_change_url(),
            }
        )
        return context


class ReportTestFillView(ReportFormFileActionView):
    """Download a report form filled with the data of any case to check its mapping."""

    title = "Test fill"
    description = (
        "Download the form filled with the data of a case to check the mapping."
    )
    form_class = ReportTestFillForm

    def form_valid(self, form: Any) -> HttpResponse:
        visit = form.cleaned_data["case_id"]
        pdf = fill_report(self.file, visit, self.request.user)
        visit.logs.create(
            action=f"Report form test fill: {self.file}", user=self.request.user
        )
        filename = f"test-{self.file.pk}-{visit.case.human_id}.pdf"
        return HttpResponse(
            pdf,
            content_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )


class ReportCopyMappingView(ReportFormFileActionView):
    """Copy the mapping of another report form file, e.g. another language version."""

    title = "Copy mapping"
    description = (
        "Fields with the same name get the source, question code and value of the "
        "chosen file. The other fields stay as they are."
    )
    form_class = ReportCopyMappingForm

    def get_form_kwargs(self) -> dict[str, Any]:
        kwargs = super().get_form_kwargs()
        kwargs["target"] = self.file
        return kwargs

    def form_valid(self, form: Any) -> HttpResponse:
        copied = copy_mapping(form.cleaned_data["source"], self.file)
        messages.success(self.request, f"Copied the mapping of {copied} fields.")
        return redirect(self.get_change_url())
