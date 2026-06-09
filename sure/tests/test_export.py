from django.contrib.auth.models import User
from django.test import TestCase

from sure.cases import get_export_dict
from sure.models import (
    Case,
    ClientAnswer,
    ClientOption,
    ClientQuestion,
    ConsultantAnswer,
    ConsultantOption,
    ConsultantQuestion,
    Questionnaire,
    Section,
    Visit,
)
from tenants.models import Location, Tenant


class TestExportWithShowForOptions(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="password")
        self.tenant = Tenant.objects.create(name="Test Tenant", owner=self.user)
        self.location = Location.objects.create(
            name="Test Location", tenant=self.tenant
        )
        self.q = Questionnaire.objects.create(name="Test Questionnaire")
        self.section = Section.objects.create(
            questionnaire=self.q, title="Section 1", order=0
        )

        # Question A (the dependency question)
        self.question_a = ClientQuestion.objects.create(
            section=self.section,
            code="QA",
            question_text="Do you have symptom X?",
            format="single choice",
            order=0,
        )
        # Options for Question A
        self.option_yes = ClientOption.objects.create(
            question=self.question_a,
            code="1",
            text="Yes",
            order=0,
        )
        self.option_no = ClientOption.objects.create(
            question=self.question_a,
            code="2",
            text="No",
            order=1,
        )

        # Question B (the dependent question)
        self.question_b = ClientQuestion.objects.create(
            section=self.section,
            code="QB",
            question_text="Please describe symptom X.",
            format="open text field",
            order=1,
        )
        # Question B depends on option "Yes" (code "1") of Question A
        self.question_b.show_for_options.add(self.option_yes)

    def test_export_when_dependency_is_met(self):
        # Case & Visit
        case = Case.objects.create(location=self.location)
        visit = Visit.objects.create(case=case, questionnaire=self.q)

        # Client answers QA with "Yes" (code "1") and QB with description
        ClientAnswer.objects.create(
            visit=visit,
            question=self.question_a,
            choices=[1],
            texts=["Yes"],
        )
        ClientAnswer.objects.create(
            visit=visit,
            question=self.question_b,
            choices=[1],
            texts=["Some description of symptom X"],
        )

        # Retrieve visit with prefetch matching tasks.py
        visit_prefetched = (
            Visit.objects.filter(pk=visit.pk)
            .select_related("case__location__tenant", "questionnaire")
            .prefetch_related(
                "questionnaire__sections__client_questions__options",
                "questionnaire__sections__client_questions__show_for_options__question",
                "client_answers",
            )
            .get()
        )

        export_dict = get_export_dict(visit_prefetched)

        # QB should be included because the dependency (QA=1) was met
        self.assertIn("QB_codes", export_dict)
        self.assertIn("QB_texts", export_dict)
        self.assertEqual(export_dict["QB_texts"], "Some description of symptom X")

    def test_export_when_dependency_is_not_met(self):
        # Case & Visit
        case = Case.objects.create(location=self.location)
        visit = Visit.objects.create(case=case, questionnaire=self.q)

        # Client answers QA with "No" (code "2") and does not answer QB
        ClientAnswer.objects.create(
            visit=visit,
            question=self.question_a,
            choices=[2],
            texts=["No"],
        )

        # Retrieve visit with prefetch matching tasks.py
        visit_prefetched = (
            Visit.objects.filter(pk=visit.pk)
            .select_related("case__location__tenant", "questionnaire")
            .prefetch_related(
                "questionnaire__sections__client_questions__options",
                "questionnaire__sections__client_questions__show_for_options__question",
                "client_answers",
            )
            .get()
        )

        export_dict = get_export_dict(visit_prefetched)

        # QB should NOT be included because the dependency was not met
        self.assertNotIn("QB_codes", export_dict)
        self.assertNotIn("QB_texts", export_dict)


class TestExportConsultantAnswers(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="password")
        self.tenant = Tenant.objects.create(name="Test Tenant", owner=self.user)
        self.location = Location.objects.create(
            name="Test Location", tenant=self.tenant
        )
        self.q = Questionnaire.objects.create(name="Test Questionnaire")

        # Question 1: single choice option with translated list choices
        self.question_1 = ConsultantQuestion.objects.create(
            questionnaire=self.q,
            code="QC1",
            question_text="Consultant Question 1",
            format="single choice",
            order=0,
        )
        self.option_1 = ConsultantOption.objects.create(
            question=self.question_1,
            code="1",
            text_en="Simple Option",
            text_de="Einfache Option",
            choices_en=["English Option A", "English Option B"],
            choices_de=["German Option A", "German Option B"],
            order=0,
        )

        # Question 2: allow text option
        self.question_2 = ConsultantQuestion.objects.create(
            questionnaire=self.q,
            code="QC2",
            question_text="Consultant Question 2",
            format="open text field",
            order=1,
        )
        self.option_2 = ConsultantOption.objects.create(
            question=self.question_2,
            code="2",
            text_en="Other",
            text_de="Sonstige",
            allow_text=True,
            order=0,
        )

        # Question 3: simple translation option (just text_en / text_de)
        self.question_3 = ConsultantQuestion.objects.create(
            questionnaire=self.q,
            code="QC3",
            question_text="Consultant Question 3",
            format="single choice",
            order=2,
        )
        self.option_3 = ConsultantOption.objects.create(
            question=self.question_3,
            code="3",
            text_en="Yes",
            text_de="Ja",
            order=0,
        )

    def test_consultant_answers_export_translation(self):
        # Create a Case with language="de" (German)
        case = Case.objects.create(location=self.location, language="de")
        visit = Visit.objects.create(case=case, questionnaire=self.q)

        # Create consultant answers
        # For question 1, choices matches choice code 1, text is the German text "German Option B"
        ConsultantAnswer.objects.create(
            visit=visit,
            question=self.question_1,
            choices=[1],
            texts=["German Option B"],
        )
        # For question 2, choice code 2 (allow text), text is custom input
        ConsultantAnswer.objects.create(
            visit=visit,
            question=self.question_2,
            choices=[2],
            texts=["custom text"],
        )
        # For question 3, choice code 3, text is German "Ja"
        ConsultantAnswer.objects.create(
            visit=visit,
            question=self.question_3,
            choices=[3],
            texts=["Ja"],
        )

        # Retrieve visit with prefetch matching tasks.py
        visit_prefetched = (
            Visit.objects.filter(pk=visit.pk)
            .select_related("case__location__tenant", "questionnaire")
            .prefetch_related(
                "questionnaire__sections__client_questions__options",
                "questionnaire__sections__client_questions__show_for_options__question",
                "questionnaire__consultant_questions__options",
                "client_answers",
                "consultant_answers",
            )
            .get()
        )

        export_dict = get_export_dict(visit_prefetched)

        # QC1: option code "1" should be mapped to english choices: index of "German Option B" is 1, choices_en[1] is "English Option B"
        self.assertEqual(export_dict["QC1_codes"], 1)
        self.assertEqual(export_dict["QC1_texts"], "English Option B")

        # QC2: allow text option, code "2", text should be "Other: custom text"
        self.assertEqual(export_dict["QC2_codes"], 2)
        self.assertEqual(export_dict["QC2_texts"], "Other: custom text")

        # QC3: simple translation option, code "3", text should be "Yes"
        self.assertEqual(export_dict["QC3_codes"], 3)
        self.assertEqual(export_dict["QC3_texts"], "Yes")
