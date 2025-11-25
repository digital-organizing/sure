import pandas as pd
from django.test import TestCase

from sure.api import _prefetch_questionnaire
from sure.models import ClientQuestion, Questionnaire
from sure.questionnaire import import_client_questions, import_consultant_questions


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

        questionnaire = _prefetch_questionnaire(
            excluded_question_ids=list(excluded_ids)
        ).get(pk=questionnaire.pk)

        for section in questionnaire.sections.all():
            for question in section.client_questions.all():
                self.assertNotEqual(question.id, excluded_ids[0])
                self.assertNotEqual(question.id, excluded_ids[1])
                self.assertNotEqual(question.id, excluded_ids[2])

        should_not_exclude = ClientQuestion.objects.filter(
            optional_for_centers=False
        ).values_list("id", flat=True)[:1]

        questionnaire = _prefetch_questionnaire(
            excluded_question_ids=list(should_not_exclude)
        ).get(pk=questionnaire.pk)

        found = False
        for section in questionnaire.sections.all():
            for question in section.client_questions.all():
                if question.id == should_not_exclude[0]:
                    found = True
        self.assertTrue(found)
