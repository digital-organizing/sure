from django.shortcuts import redirect
from .models import Test, VisitExport, VisitExportDownload
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
from sure.forms import GenerateCaseBatchForm


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
