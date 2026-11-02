import io
from typing import Any, cast

import segno
import xlsxwriter
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.text import slugify
from django.views.generic.edit import FormView
from unfold.views import UnfoldModelAdminViewMixin

from core.auth import require_2fa_or_trusted
from sure.client_service import create_case, create_visit, get_case_link
from sure.forms import (
    GenerateCaseBatchForm,
    ReportCopyMappingForm,
    ReportTestFillForm,
)
from sure.report_forms import copy_mapping, fill_report

from .models import (
    ReportFormFile,
    Test,
    VisitExport,
    VisitExportDownload,
    signed_download_url,
)


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

    redirect_url = signed_download_url(visit_export.file, visit_export.filename)
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
        tag_names = [tag.name for tag in form.cleaned_data["tags"]]
        language = form.cleaned_data["language"]
        quantity = form.cleaned_data["quantity"]
        selected_tests = form.cleaned_data.get("tests", [])

        records = []
        with transaction.atomic():
            for _ in range(quantity):
                case = create_case(
                    location_id=location.pk,
                    user=self.request.user,
                    external_id="",
                    language=language,
                )
                visit = create_visit(case, questionnaire)
                if tag_names:
                    visit.tags = tag_names
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

                records.append(
                    {
                        "Case ID": case.human_id,
                        "Questionnaire URL": get_case_link(case),
                        "Location": location.name,
                        "Questionnaire": questionnaire.name,
                        "Language": language,
                        "Tags": ", ".join(tag_names),
                        "Created At": timezone.localtime(visit.created_at).strftime(
                            "%Y-%m-%d %H:%M:%S"
                        ),
                    }
                )

        filename = "_".join(
            slugify(part) for part in ["case_batch", location.name, *tag_names]
        )
        response = HttpResponse(
            case_batch_workbook(records),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}.xlsx"'
        return response


#: Rows are this tall so the QR code next to the links can be scanned from a
#: printout; QR_SCALE is the size of one QR module in pixels.
QR_ROW_HEIGHT = 120
QR_SCALE = 4


def case_batch_workbook(records: list[dict[str, str]]) -> bytes:
    """Writes the cases of a batch to Excel, a scannable QR code in every row.

    The QR code goes into the third column, right after case ID and URL, so
    the columns a label print needs are next to each other.
    """
    output = io.BytesIO()
    # Not in_memory: xlsxwriter 3.2.9 then names the rels file of embedded
    # images "/xl/richData/...", which LibreOffice refuses to open.
    workbook = xlsxwriter.Workbook(output)
    sheet = workbook.add_worksheet("Cases")
    header = workbook.add_format({"bold": True})
    cell = workbook.add_format({"valign": "vcenter"})
    # Links get their own format from xlsxwriter, which drops the alignment.
    link = workbook.add_format(
        {"valign": "vcenter", "font_color": "blue", "underline": 1}
    )

    columns = list(records[0]) if records else []
    columns.insert(2, "QR Code")
    for index, column in enumerate(columns):
        sheet.write(0, index, column, header)
    sheet.set_column(0, 0, 14)
    sheet.set_column(1, 1, 45)
    sheet.set_column(2, 2, 24)
    sheet.set_column(3, len(columns) - 1, 18)

    for row, record in enumerate(records, start=1):
        sheet.set_row(row, QR_ROW_HEIGHT, cell)
        values = list(record.values())
        values.insert(2, "")
        for index, value in enumerate(values):
            sheet.write(row, index, value, link if index == 1 else cell)

        qr_code = io.BytesIO()
        segno.make(record["Questionnaire URL"], error="m").save(
            qr_code, kind="png", scale=QR_SCALE, border=2
        )
        # Placed in the cell rather than floating over it, so it stays with its
        # row when the sheet is sorted or filtered.
        sheet.embed_image(row, 2, "qr.png", {"image_data": qr_code})

    # Print all columns on one landscape page width, header on every page.
    sheet.set_landscape()
    sheet.fit_to_pages(1, 0)
    sheet.repeat_rows(0)

    workbook.close()
    return output.getvalue()


class ReportFormFileActionView(UnfoldModelAdminViewMixin, FormView):
    """Base of the admin views that act on one report form file."""

    permission_required = ("sure.change_reportformfile",)
    template_name = "admin/sure/report_form_file_action.html"
    # Set by the subclasses, unfold refuses views without a title.
    title: str
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
        # Admin views are only reachable by logged in staff.
        pdf = fill_report(self.file, visit, cast(User, self.request.user))
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
