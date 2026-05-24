from crispy_forms.helper import FormHelper
from crispy_forms.layout import Column, Div, Layout, Row
from django import forms
from unfold import widgets
from unfold.layout import Submit

from sure.models import Questionnaire, VisitStatus
from tenants.models import Location, Tag


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
        self.request = kwargs.pop("request")
        super().__init__(*args, **kwargs)
        if self.request.user.is_superuser:
            self.fields["tag"].queryset = Tag.objects.all()  # type: ignore
        else:
            tenant = getattr(self.request.user, "consultant").tenant
            self.fields["tag"].queryset = Tag.objects.filter(  # type: ignore
                available_in__tenant=tenant
            )

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


class GenerateCaseBatchForm(forms.Form):
    location = forms.ModelChoiceField(
        queryset=Location.objects.none(),
        label="Location",
        widget=widgets.UnfoldAdminSelect2Widget(),
    )
    questionnaire = forms.ModelChoiceField(
        queryset=Questionnaire.objects.none(),
        label="Questionnaire",
        widget=widgets.UnfoldAdminSelect2Widget(),
    )
    tag = forms.CharField(
        max_length=50,
        required=True,
        label="Tag",
        help_text="Tag to apply to all generated cases in this batch.",
        widget=widgets.UnfoldAdminTextInputWidget(),
    )
    quantity = forms.IntegerField(
        min_value=1,
        max_value=1000,
        initial=10,
        label="Quantity",
        help_text="Number of cases to generate (max 1000).",
        widget=widgets.UnfoldAdminTextInputWidget(),
    )

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request")
        super().__init__(*args, **kwargs)

        if self.request.user.is_superuser:
            self.fields["location"].queryset = Location.objects.all()  # ty:ignore[unresolved-attribute]
            self.fields["questionnaire"].queryset = Questionnaire.objects.all()  # ty:ignore[unresolved-attribute]
        else:
            tenants = self.request.user.tenants.all()
            self.fields["location"].queryset = Location.objects.filter(  # ty:ignore[unresolved-attribute]
                tenant__in=tenants
            )
            self.fields["questionnaire"].queryset = Questionnaire.objects.filter(  # ty:ignore[unresolved-attribute]
                locations__tenant__in=tenants
            ).distinct()

        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.form_show_labels = True

        self.helper.layout = Layout(
            Row(
                Column(
                    "location",
                    "questionnaire",
                    css_class="w-1/2",
                ),
                Column(
                    "tag",
                    "quantity",
                    css_class="w-1/2",
                ),
            ),
            Row(
                Div(
                    Submit("submit", "Generate Batch"),
                    css_class="mt-4",
                )
            ),
        )

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data is not None:
            location = cleaned_data.get("location")
            questionnaire = cleaned_data.get("questionnaire")
            if location and questionnaire:
                if not questionnaire.locations.filter(pk=location.pk).exists():
                    raise forms.ValidationError(
                        "The selected questionnaire is not available at the selected location."
                    )
        return cleaned_data
