"""Tests for flagging visits that belong to another tenant than the consultant's."""

from django.contrib.auth.models import User
from django.test import TestCase
from django_otp.plugins.otp_totp.models import TOTPDevice

from sure.models import Case, Client, Connection, Contact, Questionnaire, Visit
from tenants.models import Consultant, Location, Tenant


class TestVisitOtherTenant(TestCase):
    def setUp(self):
        owner = User.objects.create_user(username="owner", password="pw")
        own_tenant = Tenant.objects.create(name="Own", owner=owner)
        other_tenant = Tenant.objects.create(name="Other", owner=owner)
        own_location = Location.objects.create(tenant=own_tenant, name="Own Center")
        other_location = Location.objects.create(
            tenant=other_tenant, name="Other Center"
        )

        questionnaire = Questionnaire.objects.create(name="Q")
        self.own_case = Case.objects.create(id="1111111", location=own_location)
        self.other_case = Case.objects.create(id="2222222", location=other_location)
        Visit.objects.create(case=self.own_case, questionnaire=questionnaire)
        Visit.objects.create(case=self.other_case, questionnaire=questionnaire)

        # The consultant sees the other tenant's case through the shared client.
        client = Client.objects.create(
            contact=Contact.objects.create(phone_number="+41791234567")
        )
        Connection.objects.create(case=self.own_case, client=client)
        Connection.objects.create(case=self.other_case, client=client)

        self.user = User.objects.create_user(username="consultant", password="pw")
        consultant = Consultant.objects.create(tenant=own_tenant, user=self.user)
        consultant.locations.add(own_location)

    def _login(self, user):
        device = TOTPDevice.objects.create(user=user, name="default", confirmed=True)
        self.client.force_login(user)
        session = self.client.session
        session["otp_device_id"] = device.persistent_id
        session.save()

    def _get_visit(self, case):
        response = self.client.get(f"/api/sure/case/{case.human_id}/visit/")
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()

    def test_case_of_own_tenant_is_not_flagged(self):
        self._login(self.user)
        self.assertFalse(self._get_visit(self.own_case)["other_tenant"])

    def test_case_of_other_tenant_is_flagged(self):
        self._login(self.user)
        visit = self._get_visit(self.other_case)
        self.assertTrue(visit["other_tenant"])
        self.assertEqual(visit["location"], "Other Center")

    def test_superuser_without_tenant_is_never_flagged(self):
        admin = User.objects.create_user(
            username="admin", password="pw", is_superuser=True, is_staff=True
        )
        self._login(admin)
        self.assertFalse(self._get_visit(self.other_case)["other_tenant"])
