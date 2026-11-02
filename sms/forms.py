from datetime import date, timedelta

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Column, Div, Layout, Row
from django import forms
from django.utils import timezone
from unfold import widgets
from unfold.layout import Submit


def _last_month() -> tuple[date, date]:
    end = timezone.localdate().replace(day=1) - timedelta(days=1)
    return end.replace(day=1), end


class SMSUsageExportForm(forms.Form):
    start_date = forms.DateField(
        label="Start Date", widget=widgets.UnfoldAdminDateWidget()
    )
    end_date = forms.DateField(
        label="End Date",
        help_text="Both days are included.",
        widget=widgets.UnfoldAdminDateWidget(),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Usually billed per month, so default to the last complete one.
        self.fields["start_date"].initial, self.fields["end_date"].initial = (
            _last_month()
        )

        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.form_show_labels = True
        self.helper.layout = Layout(
            Row(
                Column("start_date", css_class="w-1/2"),
                Column("end_date", css_class="w-1/2"),
            ),
            Row(Div(Submit("submit", "Export"), css_class="mt-4")),
        )

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data is not None:
            start = cleaned_data.get("start_date")
            end = cleaned_data.get("end_date")
            if start and end and start > end:
                raise forms.ValidationError(
                    "The start date must be before the end date."
                )
        return cleaned_data
