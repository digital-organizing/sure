import pandas as pd
from django.test import TestCase

from sure.models import Questionnaire
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
