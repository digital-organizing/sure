# Create your views here.

from typing import Any
from urllib.parse import urlencode

from django.contrib.auth.models import Group, User
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic.edit import FormView
from sesame.utils import get_parameters
from unfold.views import UnfoldModelAdminViewMixin

from tenants.forms import ConsultantInviteForm
from tenants.models import Consultant, Tenant


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

    @transaction.atomic
    def form_valid(self, form: Any) -> HttpResponse:
        data = form.cleaned_data

        user = User.objects.create_user(
            username=data["email"],
            email=data["email"],
            first_name=data["first_name"],
            last_name=data["last_name"],
        )
        consultant = Consultant.objects.create(
            tenant=form.tenant,
            user=user,
        )
        consultant.locations.set(data["locations"])

        if data.get("as_admin"):
            form.tenant.admins.add(user)
            form.tenant.save()
            user.is_staff = True
            user.groups.add(Group.objects.get_or_create(name="Tenant Admins")[0])

        user.set_unusable_password()

        user.save()

        param = get_parameters(user=user, scope=f"setup_account:{user.email}")
        param["email"] = user.email

        print(f"Generated params for sesame: {param}")
        link = self.request.build_absolute_uri("/setup") + f"?{urlencode(param)}"

        form.send_invitation_email(self.request, activation_link=link)

        return redirect(reverse("admin:tenants_consultant_changelist"))
