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
TOTAL_CREDITS = "Total credits"


def _category_labels() -> list[str]:
    # Unknown last: SMS sent before the category was recorded still have to be
    # billed, so they get columns of their own instead of being dropped.
    return [str(label) for _, label in SMSCategory.choices] + [UNKNOWN]


def usage_columns() -> list[str]:
    columns = ["Tenant", "Location"]
    for label in _category_labels():
        columns += [f"{label} SMS", f"{label} credits"]
    return columns + [TOTAL_CREDITS]


def sms_usage(start, end) -> list[dict]:
    """SMS sent between both days, one row per location for billing.

    Every category has a column for the number of SMS and one for the credits.
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

    usage: dict[tuple[str, str], dict] = {}
    for row in rows:
        tenant = row["tenant__name"] or UNKNOWN
        location = row["location__name"] or UNKNOWN
        record = usage.setdefault(
            (tenant, location),
            {"Tenant": tenant, "Location": location}
            | {column: 0 for column in usage_columns()[2:]},
        )
        label = str(labels.get(row["category"], UNKNOWN))
        record[f"{label} SMS"] += row["count"]
        record[f"{label} credits"] += row["credits"]
        record[TOTAL_CREDITS] += row["credits"]

    return [usage[key] for key in sorted(usage)]


def sms_usage_workbook(usage: list[dict]) -> bytes:
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output)
    sheet = workbook.add_worksheet("SMS usage")
    bold = workbook.add_format({"bold": True})
    # Category headers are long, wrap them instead of widening every column.
    header = workbook.add_format({"bold": True, "text_wrap": True, "valign": "top"})

    columns = usage_columns()
    sheet.write_row(0, 0, columns, header)
    sheet.set_row(0, 45)
    for row, record in enumerate(usage, start=1):
        sheet.write_row(row, 0, [record[column] for column in columns])

    total = len(usage) + 1
    sheet.write(total, 0, "Total", bold)
    for index, column in enumerate(columns[2:], start=2):
        sheet.write(total, index, sum(record[column] for record in usage), bold)

    sheet.set_column(0, 1, 28)
    sheet.set_column(2, len(columns) - 1, 14)
    sheet.freeze_panes(1, 2)
    sheet.set_landscape()
    sheet.fit_to_pages(1, 0)
    sheet.repeat_rows(0)

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
