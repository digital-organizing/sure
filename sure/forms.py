from crispy_forms.helper import FormHelper
from crispy_forms.layout import Column, Div, Layout, Row
from django import forms
from unfold import widgets
from unfold.layout import Submit

from sure.models import VisitStatus
from tenants.models import Tag


class ExportCaseForm(forms.Form):
    start_date = forms.DateField(
        label="Start Date",
        widget=widgets.UnfoldAdminDateWidget(),
    )

    end_date = forms.DateField(
        label="End Date",
        widget=widgets.UnfoldAdminDateWidget(),
    )


class CohortFilterForm(forms.Form):
    tag = forms.ModelChoiceField(
        queryset=Tag.objects.all(),
        required=False,
        label="Tag",
        help_text="Filter cases by tag.",
        widget=widgets.UnfoldAdminSelect2Widget(),
    )

    status = forms.ChoiceField(
        choices=[("", "---------")] + VisitStatus.choices,
        required=False,
        label="Status",
        help_text="Filter cases by status.",
        widget=widgets.UnfoldAdminSelect2Widget(),
    )

    start_date = forms.DateField(
        label="Start Date",
        required=False,
        widget=widgets.UnfoldAdminDateWidget(),
    )

    end_date = forms.DateField(
        label="End Date",
        required=False,
        widget=widgets.UnfoldAdminDateWidget(),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "get"
        self.helper.form_show_labels = True

        self.helper.layout = Layout(
            Row(
                Column(
                    "start_date",
                    "status",
                    css_class="w-1/3",
                ),
                Column(
                    "end_date",
                    "tag",
                    css_class="w-1/3",
                ),
            ),
            Row(
                Div(
                    Submit("submit", "Filter"),
                    css_class="mt-4",
                )
            ),
        )

    def get_filter_dict(self):
        filter_dict = {}
        if self.cleaned_data.get("tag"):
            filter_dict["tags__contains"] = [self.cleaned_data["tag"].name]
        if self.cleaned_data.get("status"):
            filter_dict["status"] = self.cleaned_data["status"]
        if self.cleaned_data.get("start_date"):
            filter_dict["created_at__gte"] = self.cleaned_data["start_date"]
        if self.cleaned_data.get("end_date"):
            filter_dict["created_at__lte"] = self.cleaned_data["end_date"]
        return filter_dict
