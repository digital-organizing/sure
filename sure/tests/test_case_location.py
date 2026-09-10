"""Tests for moving a case to another location of its tenant."""

from django.contrib.auth.models import User
from django.test import TestCase
from django_otp.plugins.otp_totp.models import TOTPDevice

from sure.models import Case, Client, Connection, Contact, Questionnaire, Visit
from tenants.models import Consultant, Location, Tenant


class TestCaseLocation(TestCase):
    def setUp(self):
        owner = User.objects.create_user(username="owner", password="pw")
        self.tenant = Tenant.objects.create(name="Own", owner=owner)
        other_tenant = Tenant.objects.create(name="Other", owner=owner)
        self.location = Location.objects.create(tenant=self.tenant, name="Center")
        self.second_location = Location.objects.create(
            tenant=self.tenant, name="Second Center"
        )
        # Same tenant, but the consultant does not work there.
        self.unassigned_location = Location.objects.create(
            tenant=self.tenant, name="Unassigned Center"
        )
        self.other_location = Location.objects.create(
            tenant=other_tenant, name="Other Center"
        )

        self.questionnaire = Questionnaire.objects.create(name="Q")
        self.case = Case.objects.create(id="1111111", location=self.location)
        Visit.objects.create(case=self.case, questionnaire=self.questionnaire)

        self.user = User.objects.create_user(username="consultant", password="pw")
        self.consultant = Consultant.objects.create(tenant=self.tenant, user=self.user)
        self.consultant.locations.add(self.location, self.second_location)

    def _login(self, user):
        device = TOTPDevice.objects.create(user=user, name="default", confirmed=True)
        self.client.force_login(user)
        session = self.client.session
        session["otp_device_id"] = device.persistent_id
        session.save()

    def _move(self, case, location_id):
        return self.client.post(
            f"/api/sure/case/{case.human_id}/location/", {"location_id": location_id}
        )

    def test_move_to_location_with_access(self):
        self._login(self.user)
        response = self._move(self.case, self.second_location.pk)
        self.assertEqual(response.status_code, 200, response.content)

        self.case.refresh_from_db()
        self.assertEqual(self.case.location, self.second_location)
        log = self.case.visit.logs.get()
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.action, "Location changed from Center to Second Center")

    def test_move_to_same_location_is_not_logged(self):
        self._login(self.user)
        response = self._move(self.case, self.location.pk)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertFalse(self.case.visit.logs.exists())

    def test_move_to_location_without_access_is_denied(self):
        self._login(self.user)
        response = self._move(self.case, self.unassigned_location.pk)
        self.assertEqual(response.status_code, 403)

        self.case.refresh_from_db()
        self.assertEqual(self.case.location, self.location)
        self.assertFalse(self.case.visit.logs.exists())

    def test_move_to_other_tenant_is_denied_despite_access(self):
        self.consultant.locations.add(self.other_location)
        self._login(self.user)
        response = self._move(self.case, self.other_location.pk)
        self.assertEqual(response.status_code, 403)

        self.case.refresh_from_db()
        self.assertEqual(self.case.location, self.location)

    def test_case_of_other_tenant_cannot_be_moved_into_own_tenant(self):
        # The consultant sees the other tenant's case through the shared client.
        other_case = Case.objects.create(id="2222222", location=self.other_location)
        Visit.objects.create(case=other_case, questionnaire=self.questionnaire)
        client = Client.objects.create(
            contact=Contact.objects.create(phone_number="+41791234567")
        )
        Connection.objects.create(case=self.case, client=client)
        Connection.objects.create(case=other_case, client=client)

        self._login(self.user)
        response = self._move(other_case, self.second_location.pk)
        self.assertEqual(response.status_code, 403)

        other_case.refresh_from_db()
        self.assertEqual(other_case.location, self.other_location)

    def test_superuser_moves_within_tenant_only(self):
        admin = User.objects.create_user(
            username="admin", password="pw", is_superuser=True, is_staff=True
        )
        self._login(admin)

        response = self._move(self.case, self.other_location.pk)
        self.assertEqual(response.status_code, 403)

        response = self._move(self.case, self.unassigned_location.pk)
        self.assertEqual(response.status_code, 200, response.content)
        self.case.refresh_from_db()
        self.assertEqual(self.case.location, self.unassigned_location)

    def test_unknown_location(self):
        self._login(self.user)
        response = self._move(self.case, 999999)
        self.assertEqual(response.status_code, 404)

    def test_visit_reports_location_and_tenant(self):
        self._login(self.user)
        response = self.client.get(f"/api/sure/case/{self.case.human_id}/visit/")
        self.assertEqual(response.status_code, 200, response.content)
        visit = response.json()
        self.assertEqual(visit["location_id"], self.location.pk)
        self.assertEqual(visit["tenant_id"], self.tenant.pk)
