from crispy_forms.helper import FormHelper
from crispy_forms.layout import Column, Div, Fieldset, Layout, Row
from django import forms
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from unfold import widgets
from unfold.layout import Submit
from unfold.widgets import UnfoldAdminEmailInputWidget


class ConsultantInviteForm(forms.Form):
    """Form for inviting a consultant to a tenant."""

    email = forms.EmailField(
        label="Consultant Email", max_length=254, widget=UnfoldAdminEmailInputWidget()
    )

    first_name = forms.CharField(
        label="First Name", max_length=60, widget=widgets.UnfoldAdminTextInputWidget()
    )
    last_name = forms.CharField(
        label="Last Name", max_length=150, widget=widgets.UnfoldAdminTextInputWidget
    )

    locations = forms.ModelMultipleChoiceField(
        label="Assign Locations",
        queryset=None,  # to be set in __init__
        required=True,
        widget=widgets.UnfoldAdminSelect2MultipleWidget(
            {
                "class": "w-full",
                "size": "10",
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        tenant = kwargs.pop("tenant", None)
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_input(Submit("submit", ("Submit Hallo")))

        if tenant:
            self.fields["locations"].queryset = tenant.locations.all() # type: ignore
        else:
            self.fields["locations"].queryset = [] # type: ignore
        self.helper.layout = Layout(
            Row(
                Column(
                    Fieldset(
                        _("Custom form"),
                        Column(
                            Row(
                                Div("email", css_class="w-1/2"),
                            ),
                            Row(
                                Div("first_name", css_class="w-1/2"),
                                Div("last_name", css_class="w-1/2"),
                            ),
                            "locations",
                            css_class="gap-5",
                        ),
                    ),
                    css_class="lg:w-1/2",
                ),
                css_class="mb-8",
            ),
        )

    def clean_email(self) -> str:
        email = self.cleaned_data["email"]
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email
