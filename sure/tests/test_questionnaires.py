import pandas as pd
from django.contrib.auth.models import User
from django.test import TestCase

from sure.api import prefetch_questionnaire
from sure.models import ClientQuestion, Questionnaire
from sure.questionnaire import (import_client_questions,
                                import_consultant_questions)
from tenants.models import Location, Tenant


class TestQuestionnaireImport(TestCase):
    def test_client_import(self):
        df = pd.read_excel("sure/tests/data/SURE_Q.xlsx", sheet_name="CLIENT")

        questionnaire = Questionnaire.objects.create(name="Test Questionnaire")
        import_client_questions(df, questionnaire)

    def test_consultant_import(self):
        df = pd.read_excel("sure/tests/data/SURE_Q.xlsx", sheet_name="CONSULTANT")

        questionnaire = Questionnaire.objects.create(name="Test Questionnaire")
        import_consultant_questions(df, questionnaire)

    def test_excluded_questions(self):
        df = pd.read_excel("sure/tests/data/SURE_Q.xlsx", sheet_name="CLIENT")

        questionnaire = Questionnaire.objects.create(name="Test Questionnaire")
        import_client_questions(df, questionnaire)

        excluded_ids = ClientQuestion.objects.filter(
            optional_for_centers=True
        ).values_list("id", flat=True)[:3]
        user = User.objects.create_user(username="testuser", password="testpass")
        tenant = Tenant.objects.create(name="Test Tenant", owner=user)
        location = Location.objects.create(name="Test Location", tenant=tenant)
        location.excluded_questions.set(
            ClientQuestion.objects.filter(id__in=excluded_ids)
        )

        questionnaire = prefetch_questionnaire(location=location).get(
            pk=questionnaire.pk
        )

        for section in questionnaire.sections.all():
            for question in section.client_questions.all():
                self.assertNotEqual(question.id, excluded_ids[0])
                self.assertNotEqual(question.id, excluded_ids[1])
                self.assertNotEqual(question.id, excluded_ids[2])
