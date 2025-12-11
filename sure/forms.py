from django import forms
from unfold import widgets


class ExportCaseForm(forms.Form):
    start_date = forms.DateField(
        label="Start Date",
        widget=widgets.UnfoldAdminDateWidget(),
    )

    end_date = forms.DateField(
        label="End Date",
        widget=widgets.UnfoldAdminDateWidget(),
    )
