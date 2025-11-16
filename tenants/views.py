# Create your views here.

from typing import Any

from django.contrib.auth.models import User
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic.edit import FormView
from sesame.utils import get_query_string
from unfold.views import UnfoldModelAdminViewMixin

from tenants.forms import ConsultantInviteForm
from tenants.models import Tenant


class ConsultantInviteView(UnfoldModelAdminViewMixin, FormView):
    """Admin view for inviting consultants to a tenant."""

    title = "Invite Consultant"
    form_class = ConsultantInviteForm
    permission_required = ("tenants.add_consultant",)
    template_name = "admin/tenants/consultant_invite.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        user = self.request.user
        tenant = Tenant.objects.filter(admins=user).first()
        kwargs["tenant"] = tenant
        print(f"Form kwargs: {kwargs}")
        return kwargs

    def form_valid(self, form: Any) -> HttpResponse:
        data = form.cleaned_data

        user = User.objects.create_user(
            username=data["email"],
            email=data["email"],
            first_name=data["first_name"],
            last_name=data["last_name"],
        )
        user.set_unusable_password()

        user.save()

        link = get_query_string(user=user, scope=f"setup_account:{user.email}")
        print(f"Generated sesame link: {link}")

        return redirect(reverse("admin:tenants_consultant_changelist"))
