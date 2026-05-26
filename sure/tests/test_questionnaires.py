import pandas as pd
from django.contrib import admin
from django.contrib.auth.models import User
from django.test import TestCase

from sure.api import prefetch_questionnaire
from sure.models import (
    ClientOption,
    ClientQuestion,
    ConsultantOption,
    ConsultantQuestion,
    Questionnaire,
    Section,
)
from sure.questionnaire import import_client_questions, import_consultant_questions
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

    def test_exclusive_options(self):
        questionnaire = Questionnaire.objects.create(name="Exclusive Test")
        section = questionnaire.sections.create(title="Section 1", order=0)
        client_question = ClientQuestion.objects.create(
            section=section,
            question_text="Multi choice exclusive test",
            code="M1",
            format="multiple choice",
            order=0,
        )
        opt1 = ClientOption.objects.create(
            question=client_question,
            code="O1",
            text="Option 1 (Normal)",
            exclusive=False,
            order=0,
        )
        opt2 = ClientOption.objects.create(
            question=client_question,
            code="O2",
            text="Option 2 (Exclusive)",
            exclusive=True,
            order=1,
        )

        self.assertFalse(opt1.exclusive)
        self.assertTrue(opt2.exclusive)

        consultant_question = ConsultantQuestion.objects.create(
            questionnaire=questionnaire,
            question_text="Consultant exclusive test",
            code="C1",
            format="multiple choice",
            order=0,
        )
        copt1 = ConsultantOption.objects.create(
            question=consultant_question,
            code="CO1",
            text="C Option 1 (Normal)",
            exclusive=False,
            order=0,
        )
        copt2 = ConsultantOption.objects.create(
            question=consultant_question,
            code="CO2",
            text="C Option 2 (Exclusive)",
            exclusive=True,
            order=1,
        )
        self.assertFalse(copt1.exclusive)
        self.assertTrue(copt2.exclusive)

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


class TestQuestionnaireDuplication(TestCase):
    def test_duplicate_questionnaire_logic(self):
        # 1. Setup Questionnaire and translation fields
        q = Questionnaire.objects.create(name="Original Questionnaire", order=5)
        if hasattr(q, "name_en"):
            q.name_en = "Original Questionnaire EN"
        if hasattr(q, "name_fr"):
            q.name_fr = "Original Questionnaire FR"
        q.save()

        # 2. Setup locations (ManyToMany)
        user = User.objects.create_user(username="testuser", password="testpass")
        tenant = Tenant.objects.create(name="Test Tenant", owner=user)
        loc = Location.objects.create(name="Test Location", tenant=tenant)
        q.locations.add(loc)

        # 3. Setup Sections, questions, options, conditional options
        sec = Section.objects.create(
            questionnaire=q,
            title="Section 1",
            order=1,
            label="S1",
            description="Desc 1",
        )
        if hasattr(sec, "title_en"):
            sec.title_en = "Section 1 EN"
        sec.save()

        # Client questions
        q1 = ClientQuestion.objects.create(
            section=sec,
            question_text="Q1 Text",
            code="code_q1",
            format="multiple choice",
            order=1,
            label="q1_lbl",
        )
        if hasattr(q1, "question_text_en"):
            q1.question_text_en = "Q1 Text EN"
        q1.save()

        # Client options
        opt1 = ClientOption.objects.create(
            question=q1,
            text="Opt 1 text",
            code="code_opt1",
            order=1,
            text_for_consultant="Opt 1 consultant text",
        )
        if hasattr(opt1, "text_en"):
            opt1.text_en = "Opt 1 text EN"
        opt1.save()

        opt2 = ClientOption.objects.create(
            question=q1, text="Opt 2 text", code="code_opt2", order=2
        )
        opt2.save()

        # Q2 with conditional showing for Opt1
        q2 = ClientQuestion.objects.create(
            section=sec,
            question_text="Q2 Text",
            code="code_q2",
            format="single choice",
            order=2,
        )
        q2.show_for_options.add(opt1)

        # Consultant Question and Option
        cq = ConsultantQuestion.objects.create(
            questionnaire=q,
            question_text="CQ Text",
            code="code_cq",
            format="single choice",
            order=1,
        )
        copt = ConsultantOption.objects.create(
            question=cq, text="COpt text", code="code_copt", order=1
        )

        # 4. Perform the duplication using the admin action methods
        admin_site = admin.AdminSite()
        from sure.admin import QuestionaireAdmin

        q_admin = QuestionaireAdmin(Questionnaire, admin_site)

        new_q = q_admin._duplicate_single_questionnaire(q)

        # 5. Assertions on the new cloned Questionnaire
        self.assertNotEqual(new_q.pk, q.pk)
        self.assertEqual(new_q.order, q.order)

        # Check translated names
        if hasattr(new_q, "name_en"):
            self.assertEqual(new_q.name_en, "Original Questionnaire EN (Copy)")
            self.assertEqual(new_q.name, "Original Questionnaire EN (Copy)")
        else:
            self.assertEqual(new_q.name, "Original Questionnaire (Copy)")

        if hasattr(new_q, "name_fr"):
            self.assertEqual(new_q.name_fr, "Original Questionnaire FR (Copy)")

        # Verify ManyToMany 'locations' relationship is completely cleared/empty
        self.assertEqual(new_q.locations.count(), 0)

        # Verify Section duplication
        self.assertEqual(new_q.sections.count(), 1)
        new_sec = new_q.sections.first()
        self.assertNotEqual(new_sec.pk, sec.pk)
        self.assertEqual(new_sec.title, sec.title)
        if hasattr(new_sec, "title_en"):
            self.assertEqual(new_sec.title_en, "Section 1 EN")
        self.assertEqual(new_sec.order, sec.order)
        self.assertEqual(new_sec.label, sec.label)
        self.assertEqual(new_sec.description, sec.description)

        # Verify ClientQuestions duplication
        self.assertEqual(new_sec.client_questions.count(), 2)
        new_q1 = new_sec.client_questions.get(code="code_q1")
        new_q2 = new_sec.client_questions.get(code="code_q2")

        self.assertNotEqual(new_q1.pk, q1.pk)
        self.assertEqual(new_q1.question_text, q1.question_text)
        if hasattr(new_q1, "question_text_en"):
            self.assertEqual(new_q1.question_text_en, "Q1 Text EN")
        self.assertEqual(new_q1.format, q1.format)
        self.assertEqual(new_q1.order, q1.order)
        self.assertEqual(new_q1.label, q1.label)

        # Verify ClientOptions duplication
        self.assertEqual(new_q1.options.count(), 2)
        new_opt1 = new_q1.options.get(code="code_opt1")
        new_q1.options.get(code="code_opt2")

        self.assertNotEqual(new_opt1.pk, opt1.pk)
        self.assertEqual(new_opt1.text, opt1.text)
        if hasattr(new_opt1, "text_en"):
            self.assertEqual(new_opt1.text_en, "Opt 1 text EN")
        self.assertEqual(new_opt1.text_for_consultant, opt1.text_for_consultant)
        self.assertEqual(new_opt1.order, opt1.order)

        # Verify conditional mapping (show_for_options)
        new_q2_show_options = list(new_q2.show_for_options.all())
        self.assertEqual(len(new_q2_show_options), 1)
        self.assertEqual(new_q2_show_options[0].pk, new_opt1.pk)
        self.assertNotEqual(new_q2_show_options[0].pk, opt1.pk)

        # Verify ConsultantQuestion duplication
        self.assertEqual(new_q.consultant_questions.count(), 1)
        new_cq = new_q.consultant_questions.first()
        self.assertNotEqual(new_cq.pk, cq.pk)
        self.assertEqual(new_cq.question_text, cq.question_text)
        self.assertEqual(new_cq.format, cq.format)

        # Verify ConsultantOption duplication
        self.assertEqual(new_cq.options.count(), 1)
        new_copt = new_cq.options.first()
        self.assertNotEqual(new_copt.pk, copt.pk)
        self.assertEqual(new_copt.text, copt.text)
        self.assertEqual(new_copt.code, copt.code)

    def test_duplicate_questionnaire_action_method(self):
        # Setup questionnaire
        q1 = Questionnaire.objects.create(name="Q1")

        admin_site = admin.AdminSite()
        from sure.admin import QuestionaireAdmin

        q_admin = QuestionaireAdmin(Questionnaire, admin_site)

        # Mock request and message_user
        from unittest.mock import MagicMock

        request = MagicMock()
        q_admin.message_user = MagicMock()

        # Call action
        response = q_admin.duplicate_questionnaire_action(request, q1.pk)

        # Assert duplicate questionnaire was created
        self.assertTrue(Questionnaire.objects.filter(name="Q1 (Copy)").exists())
        new_q = Questionnaire.objects.get(name="Q1 (Copy)")

        # Assert message_user was called
        q_admin.message_user.assert_called_once()

        # Assert redirection to the new questionnaire's change page
        from django.urls import reverse

        expected_url = reverse("admin:sure_questionnaire_change", args=[new_q.pk])
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, expected_url)
