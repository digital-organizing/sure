from crispy_forms.helper import FormHelper
from crispy_forms.layout import Column, Div, Fieldset, Layout, Row
from django import forms
from django.conf import settings
from django.contrib.auth.models import User
from django.template import Context, Template
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from unfold import widgets
from unfold.layout import Submit
from unfold.widgets import UnfoldAdminEmailInputWidget

from tenants.models import Location, Tenant
from tenants.tasks import send_background_mail


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

    as_admin = forms.BooleanField(
        label="Grant Admin Privileges",
        required=False,
        help_text="If checked, the consultant will have admin privileges for this tenant.",
    )

    tenant = forms.ModelChoiceField(
        label="Tenant",
        queryset=Tenant.objects.all(),
        widget=widgets.UnfoldAdminSelect2Widget(
            {
                "class": "w-full",
                "size": "10",
            }
        ),
    )

    locations = forms.ModelMultipleChoiceField(
        label="Assign Locations",
        queryset=None,  # to be set in __init__
        required=False,
        widget=widgets.UnfoldAdminSelect2MultipleWidget(
            {
                "class": "w-full",
                "size": "10",
            }
        ),
    )

    def send_invitation_email(self, request, activation_link: str) -> None:
        """Send the invitation email to the consultant."""

        template = Template(self.cleaned_data["tenant"].invitation_mail_template)
        context = Context(
            {
                "first_name": self.cleaned_data["first_name"],
                "tenant": self.cleaned_data["tenant"],
                "user": request.user,
                "activation_link": mark_safe(activation_link),  # nosec
            }
        )
        message = template.render(context)
        subject = self.cleaned_data["tenant"].invitation_mail_subject

        send_background_mail.delay(
            {
                "subject": subject,
                "message": message,
                "from_email": settings.DEFAULT_FROM_EMAIL,
                "recipient_list": [self.cleaned_data["email"]],
            }
        )

    def __init__(self, *args, **kwargs):
        request = kwargs.pop("request")
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_input(Submit("submit", ("Submit Hallo")))

        self.fields["locations"].queryset = Location.objects.filter(
            tenant__admins=request.user
        )
        self.fields["tenant"].queryset = Tenant.objects.filter(admins=request.user)
        self.fields["tenant"].initial = Tenant.objects.filter(
            admins=request.user
        ).first()

        self.helper.layout = Layout(
            Row(
                Column(
                    Fieldset(
                        _("Custom form"),
                        Column(
                            "tenant",
                            Row(
                                Div("email", css_class="w-1/2"),
                            ),
                            Row(
                                Div("first_name", css_class="w-1/2"),
                                Div("last_name", css_class="w-1/2"),
                            ),
                            "locations",
                            "as_admin",
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

    def clean(self) -> dict:
        cleaned_data = super().clean()
        tenant = cleaned_data.get("tenant")
        locations = cleaned_data.get("locations")

        for location in locations:
            if location.tenant != tenant:
                raise forms.ValidationError(
                    f"Location {location.name} does not belong to tenant {tenant.name}."
                )
        return cleaned_data
