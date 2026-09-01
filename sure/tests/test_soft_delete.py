"""Tests for marking tests as deleted instead of removing them."""

import json

from django.contrib.auth.models import User
from django.test import TestCase
from django_otp.plugins.otp_totp.models import TOTPDevice

from sure.cases import get_case_tests_with_latest_results, get_test_results
from sure.models import (
    Case,
    Questionnaire,
    Test,
    TestCategory,
    TestKind,
    TestResult,
    TestResultOption,
    Visit,
)
from tenants.models import Location, Tenant


class TestSoftDeleteTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="consultant", password="pw", is_superuser=True, is_staff=True
        )
        self.tenant = Tenant.objects.create(name="Tenant", owner=self.user)
        self.location = Location.objects.create(tenant=self.tenant, name="Center A")

        self.case = Case.objects.create(id="7273738", location=self.location)
        self.questionnaire = Questionnaire.objects.create(name="Q")
        self.visit = Visit.objects.create(
            case=self.case, questionnaire=self.questionnaire
        )

        category = TestCategory.objects.create(number=900, name="Lab")
        self.kind_hiv = TestKind.objects.create(
            category=category, number=901, name="HIV PCR"
        )
        self.kind_syphilis = TestKind.objects.create(
            category=category, number=902, name="Syphilis"
        )
        self.option = TestResultOption.objects.create(
            test_kind=self.kind_hiv, label="Negative", information_by_sms=True
        )

        device = TOTPDevice.objects.create(
            user=self.user, name="default", confirmed=True
        )
        self.client.force_login(self.user)
        session = self.client.session
        session["otp_device_id"] = device.persistent_id
        session.save()

    def _submit_tests(self, test_kind_ids, free_form_tests=None):
        response = self.client.post(
            f"/api/sure/case/{self.case.human_id}/tests/",
            data=json.dumps(
                {
                    "test_kind_ids": test_kind_ids,
                    "free_form_tests": free_form_tests or [],
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        return response

    def test_deselecting_marks_deleted_without_removing_the_row(self):
        self._submit_tests([self.kind_hiv.pk, self.kind_syphilis.pk])
        self.assertEqual(Test.objects.filter(visit=self.visit).count(), 2)

        self._submit_tests([self.kind_hiv.pk])

        self.assertEqual(Test.all_objects.filter(visit=self.visit).count(), 2)
        self.assertEqual(Test.objects.filter(visit=self.visit).count(), 1)

        deleted = Test.all_objects.get(visit=self.visit, test_kind=self.kind_syphilis)
        self.assertIsNotNone(deleted.deleted_at)
        self.assertEqual(deleted.deleted_by, self.user)
        self.assertTrue(deleted.is_deleted)

    def test_deletion_is_logged(self):
        self._submit_tests([self.kind_hiv.pk, self.kind_syphilis.pk])
        self._submit_tests([self.kind_hiv.pk])

        log = self.visit.logs.filter(action__startswith="Marked tests as deleted").get()
        self.assertIn("Syphilis", log.action)
        self.assertEqual(log.user, self.user)

    def test_deleted_tests_are_excluded_from_the_visit_relation(self):
        self._submit_tests([self.kind_hiv.pk, self.kind_syphilis.pk])
        self._submit_tests([self.kind_hiv.pk])

        kinds = [test.test_kind_id for test in self.visit.tests.all()]
        self.assertEqual(kinds, [self.kind_hiv.pk])

    def test_reselecting_restores_instead_of_duplicating(self):
        self._submit_tests([self.kind_hiv.pk, self.kind_syphilis.pk])
        original = Test.objects.get(visit=self.visit, test_kind=self.kind_syphilis)

        self._submit_tests([self.kind_hiv.pk])
        self._submit_tests([self.kind_hiv.pk, self.kind_syphilis.pk])

        restored = Test.objects.get(visit=self.visit, test_kind=self.kind_syphilis)
        self.assertEqual(restored.pk, original.pk)
        self.assertIsNone(restored.deleted_at)
        self.assertIsNone(restored.deleted_by)
        self.assertEqual(Test.all_objects.filter(visit=self.visit).count(), 2)

        log = self.visit.logs.filter(action__startswith="Restored tests").get()
        self.assertIn("Syphilis", log.action)

    def test_a_test_with_results_can_be_deleted_and_its_results_are_hidden(self):
        self._submit_tests([self.kind_hiv.pk])
        test = Test.objects.get(visit=self.visit, test_kind=self.kind_hiv)
        TestResult.objects.create(test=test, result_option=self.option)

        self.assertEqual(get_test_results(self.visit).count(), 1)

        self._submit_tests([])

        test.refresh_from_db()
        self.assertIsNotNone(test.deleted_at)
        # The result itself is kept, it is just no longer surfaced.
        self.assertEqual(TestResult.objects.filter(test=test).count(), 1)
        self.assertEqual(get_test_results(self.visit).count(), 0)

    def test_deleted_tests_are_excluded_from_case_tests_with_results(self):
        self._submit_tests([self.kind_hiv.pk, self.kind_syphilis.pk])
        self._submit_tests([self.kind_hiv.pk])

        tests = get_case_tests_with_latest_results(self.visit)
        self.assertEqual(
            [test.test_kind_id for test in tests.all()], [self.kind_hiv.pk]
        )

    def test_get_case_tests_endpoint_hides_deleted_tests(self):
        self._submit_tests([self.kind_hiv.pk, self.kind_syphilis.pk])
        self._submit_tests([self.kind_hiv.pk])

        response = self.client.get(f"/api/sure/case/{self.case.human_id}/tests/")
        self.assertEqual(response.status_code, 200, response.content)
        payload = response.json()
        self.assertEqual(
            [test["test_kind"]["id"] for test in payload], [self.kind_hiv.pk]
        )

    def test_visit_history_still_shows_deleted_tests(self):
        self._submit_tests([self.kind_hiv.pk, self.kind_syphilis.pk])
        self._submit_tests([self.kind_hiv.pk])

        response = self.client.get(
            f"/api/sure/case/{self.case.human_id}/visit/history/"
        )
        self.assertEqual(response.status_code, 200, response.content)
        tests = response.json()["tests"]

        by_kind = {test["test_kind"]: test for test in tests}
        self.assertEqual(len(by_kind), 2)
        self.assertIsNone(by_kind[self.kind_hiv.pk]["deleted_at"])
        self.assertIsNotNone(by_kind[self.kind_syphilis.pk]["deleted_at"])
