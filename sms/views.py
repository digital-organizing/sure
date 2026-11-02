import io

import xlsxwriter
from django.core.exceptions import PermissionDenied
from django.db.models import Count, IntegerField, Sum
from django.db.models.fields.json import KT
from django.db.models.functions import Cast, Coalesce
from django.http import HttpResponse
from django.views.generic.edit import FormView
from unfold.views import UnfoldModelAdminViewMixin

from sms.forms import SMSUsageExportForm
from sms.models import SMSCategory, SMSMessage

UNKNOWN = "Unknown"


def sms_usage(start, end) -> list[dict]:
    """SMS sent between both days, totalled per tenant, location and category.

    Credits come from the provider's answer: a long message is split into
    several SMS and costs as many credits.
    """
    labels = dict(SMSCategory.choices)
    rows = (
        SMSMessage.objects.filter(sent_at__date__gte=start, sent_at__date__lte=end)
        .values("tenant__name", "location__name", "category")
        .annotate(
            count=Count("id"),
            credits=Sum(Coalesce(Cast(KT("response__cost"), IntegerField()), 1)),
        )
    )
    usage = [
        {
            "Tenant": row["tenant__name"] or UNKNOWN,
            "Location": row["location__name"] or UNKNOWN,
            "Category": labels.get(row["category"], UNKNOWN),
            "SMS": row["count"],
            "Credits": row["credits"],
        }
        for row in rows
    ]
    return sorted(
        usage, key=lambda row: (row["Tenant"], row["Location"], row["Category"])
    )


def sms_usage_workbook(usage: list[dict]) -> bytes:
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output)
    sheet = workbook.add_worksheet("SMS usage")
    bold = workbook.add_format({"bold": True})

    columns = ["Tenant", "Location", "Category", "SMS", "Credits"]
    sheet.write_row(0, 0, columns, bold)
    for row, record in enumerate(usage, start=1):
        sheet.write_row(row, 0, [record[column] for column in columns])

    total = len(usage) + 1
    sheet.write(total, 0, "Total", bold)
    sheet.write(total, 3, sum(record["SMS"] for record in usage), bold)
    sheet.write(total, 4, sum(record["Credits"] for record in usage), bold)
    sheet.set_column(0, 2, 28)
    sheet.set_column(3, 4, 10)

    workbook.close()
    return output.getvalue()


class SMSUsageExportView(UnfoldModelAdminViewMixin, FormView):
    """Exports the SMS usage per tenant, for billing by AHS."""

    title = "Export SMS usage"
    permission_required = ("sms.view_smsmessage",)
    form_class = SMSUsageExportForm
    template_name = "admin/sms/usage_export.html"

    def dispatch(self, request, *args, **kwargs):
        # The usage of all tenants, so only for AHS, not for tenant admins.
        if not request.user.is_superuser:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form) -> HttpResponse:
        start, end = form.cleaned_data["start_date"], form.cleaned_data["end_date"]
        response = HttpResponse(
            sms_usage_workbook(sms_usage(start, end)),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = (
            f'attachment; filename="sms_usage_{start:%Y-%m-%d}_{end:%Y-%m-%d}.xlsx"'
        )
        return response
