from django.contrib.auth.models import User
from django.test import TestCase

from sure.cases import get_export_dict
from sure.models import Case, ClientAnswer, ClientOption, ClientQuestion, Questionnaire, Section, Visit
from tenants.models import Location, Tenant


class TestExportWithShowForOptions(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="password")
        self.tenant = Tenant.objects.create(name="Test Tenant", owner=self.user)
        self.location = Location.objects.create(name="Test Location", tenant=self.tenant)
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
