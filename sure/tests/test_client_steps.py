"""Tests for the client steps while the consultant is ahead of the client."""

import json
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.utils import translation

from sure.models import Case, Questionnaire, Visit, VisitStatus
from tenants.models import Location, Tenant
from texts.translate import translate


class TestClientSteps(TestCase):
    def setUp(self):
        # The endpoints activate the requested language for the whole thread.
        self.addCleanup(translation.activate, translation.get_language())
        user = User.objects.create_user(username="consultant", password="pw")
        tenant = Tenant.objects.create(name="Tenant", owner=user)
        location = Location.objects.create(tenant=tenant, name="Center A")
        self.case = Case.objects.create(id="7273738", location=location)
        self.visit = Visit.objects.create(
            case=self.case, questionnaire=Questionnaire.objects.create(name="Q")
        )

    def _set_status(self, status):
        self.visit.status = status
        self.visit.save(update_fields=["status"])

    def _submit(self):
        return self.client.post(
            f"/api/sure/case/{self.case.human_id}/submit/?lang=de",
            data=json.dumps({"answers": []}),
            content_type="application/json",
        )

    def _set_key(self):
        return self.client.post(
            f"/api/sure/case/{self.case.human_id}/set-key/?lang=de",
            data={"key": "a-long-secret"},
        )

    def _get_questionnaire(self):
        return self.client.get(f"/api/sure/case/{self.case.human_id}/questionnaire/")

    def test_submit_moves_created_visit_to_client_submitted(self):
        self.assertEqual(self._submit().status_code, 200)

        self.visit.refresh_from_db()
        self.assertEqual(self.visit.status, VisitStatus.CLIENT_SUBMITTED)
        self.assertIsNotNone(self.visit.client_submitted_at)

    def test_client_can_finish_after_tests_were_recorded(self):
        self._set_status(VisitStatus.TESTS_RECORDED)

        self.assertEqual(self._get_questionnaire().status_code, 200)
        self.assertEqual(self._submit().status_code, 200)
        # Submitted but no key yet, so the client is sent on to the key step.
        self.assertEqual(self._get_questionnaire().status_code, 302)
        self.assertEqual(self._set_key().status_code, 200)

        self.visit.refresh_from_db()
        self.case.refresh_from_db()
        self.assertEqual(self.visit.status, VisitStatus.TESTS_RECORDED)
        self.assertTrue(self.case.has_key())

    def test_client_can_submit_only_once(self):
        self._set_status(VisitStatus.TESTS_RECORDED)
        self.assertEqual(self._submit().status_code, 200)

        response = self._submit()

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["detail"], translate("client-submit-not-allowed", "de")
        )
        self.assertNotEqual(response.json()["detail"], "client-submit-not-allowed")

    def test_client_steps_are_closed_after_tests_recorded(self):
        self._set_status(VisitStatus.RESULTS_RECORDED)

        self.assertEqual(self._get_questionnaire().status_code, 403)
        self.assertEqual(self._submit().status_code, 400)

        # Even a client who submitted in time cannot set the key anymore.
        Visit.objects.filter(pk=self.visit.pk).update(
            client_submitted_at=self.visit.created_at
        )
        response = self._set_key()

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["message"], translate("client-key-not-allowed", "de")
        )
        self.case.refresh_from_db()
        self.assertFalse(self.case.has_key())

    def test_key_requires_submitted_questionnaire(self):
        self._set_status(VisitStatus.TESTS_RECORDED)

        self.assertEqual(self._set_key().status_code, 400)

    @override_settings(TOKEN_RESEND_INTERVAL_MINUTES=3)
    @patch("sure.client_service.send_sms")
    def test_send_token_reports_resend_interval(self, send_sms):
        url = f"/api/sure/case/{self.case.human_id}/send-token/?lang=de"
        body = json.dumps({"phone_number": "079 123 45 67"})

        response = self.client.post(url, data=body, content_type="application/json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["resend_after_seconds"], 180)
        send_sms.assert_called_once()

        # Asking again within the interval is rejected with an explanation.
        response = self.client.post(url, data=body, content_type="application/json")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["message"], translate("recent-token-error", "de")
        )
        send_sms.assert_called_once()
