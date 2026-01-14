from django.contrib.auth.models import User
from django.test import TestCase

from sure.client_service import (canonicalize_phone_number, connect_case,
                                 create_case, create_visit, generate_token,
                                 get_case_link, get_cases, get_client_by_id,
                                 location_can_view_case, record_client_answers,
                                 verify_access_to_location)
from sure.models import (Client, ClientQuestion, ConsentChoice, Contact,
                         Questionnaire, Section, Token, VisitStatus)
from sure.schema import AnswerSchema, ChoiceSchema
from tenants.models import Consultant, Tenant


class CaseManagementTest(TestCase):
    def setUp(self) -> None:
        owner = User.objects.create_user(username="owner")
        self.user = owner
        tenant = Tenant.objects.create(
            name="Test Tenant",
            owner=owner,
        )
        tenant.admins.add(owner)
        consultant = Consultant.objects.create(
            tenant=tenant,
            user=owner,
        )
        location = tenant.locations.create(name="Test Location")
        consultant.locations.set([location])
        self.case = create_case(location.pk, owner)

        self.location = location

    def test_canonicalize_phone_number(self):
        self.assertEqual(canonicalize_phone_number("+41 79 736 05 16"), "+41797360516")
        self.assertEqual(canonicalize_phone_number("0797360516"), "+41797360516")

    def test_create_case(self):
        case = create_case(self.location.pk, self.user)
        self.assertIsNotNone(case)
        self.assertEqual(case.location, self.location)

    def test_get_case_link(self):
        case = create_case(self.location.pk, self.user)
        from django.conf import settings

        link = get_case_link(case)
        self.assertTrue(link.startswith(settings.SITE_URL))
        self.assertIn(case.human_id, link)

    def test_generate_token(self):
        phone_number = "+41797360516"
        token = generate_token(phone_number, self.case)
        contact = Contact.objects.filter(
            phone_number=canonicalize_phone_number(phone_number)
        ).first()
        self.assertIsNotNone(contact)

        token = Token.objects.filter(contact=contact).get()
        self.assertIsNone(token.used_at)

        contact = Contact.objects.get(phone_number=phone_number)
        self.assertTrue(contact.tokens.filter(token=token.token).exists())

    def test_connect_case(self):
        phone_number = "+41797360516"
        case = create_case(self.location.pk, self.user)
        _, token = generate_token(phone_number, case)

        connection = connect_case(
            case, phone_number, token, consent=ConsentChoice.ALLOWED
        )
        client = connection.client

        self.assertIsNotNone(client)
        self.assertIsNotNone(client.contact)
        self.assertEqual(
            client.contact.phone_number, canonicalize_phone_number(phone_number)
        )

        self.assertIsNotNone(connection)
        self.assertEqual(connection.case, case)

        client2 = get_client_by_id(client.id, case.id)

        assert client2 is not None
        self.assertEqual(client2.id, client.id)

    def test_connect_case_no_consent(self):
        phone_number = "+41797360516"
        case = create_case(self.location.pk, self.user)
        _, token = generate_token(phone_number, case)

        with self.assertRaises(ValueError):
            connect_case(case, phone_number, token, consent=ConsentChoice.DENIED)

    def test_connect_case_invalid_token(self):
        phone_number = "+41797360516"
        case = create_case(self.location.pk, self.user)
        generate_token(phone_number, case)

        with self.assertRaises(ValueError):
            connect_case(
                case, phone_number, "invalidtoken", consent=ConsentChoice.ALLOWED
            )

    def test_verify_access_to_location(self):
        # owner (self.user) should have access via tenant.admins
        self.assertTrue(verify_access_to_location(self.location, self.user))

        # a different normal user should not have access
        other = User.objects.create_user(username="other")
        self.assertFalse(verify_access_to_location(self.location, other))

        # superuser should always have access
        superu = User.objects.create_user(username="super")
        superu.is_superuser = True
        superu.save()
        self.assertTrue(verify_access_to_location(self.location, superu))

    def test_create_visit(self):
        questionnaire = Questionnaire.objects.create(name="Test Questionnaire")
        case = create_case(self.location.pk, self.user)
        visit = create_visit(case, questionnaire)

        self.assertIsNotNone(visit)
        self.assertEqual(visit.case, case)
        self.assertEqual(visit.questionnaire, questionnaire)
        self.assertEqual(visit.status, VisitStatus.CREATED)

    def test_record_client_answers(self):
        # Build a minimal questionnaire with one client question
        questionnaire = Questionnaire.objects.create(name="Q with client question")
        section = Section.objects.create(
            questionnaire=questionnaire, order=0, title="S"
        )
        client_question = ClientQuestion.objects.create(
            section=section, question_text="How are you?", code="Q1", order=0
        )

        case = create_case(self.location.pk, self.user)
        visit = create_visit(case, questionnaire)

        # create an answer object with the shape expected by record_client_answers
        choice = ChoiceSchema(code="1", text="fine")
        answer = AnswerSchema(questionId=client_question.pk, choices=[choice])

        # record answers (user None allowed for CREATED visits)
        record_client_answers(visit, [answer], user=None)

        visit.refresh_from_db()
        self.assertEqual(visit.status, VisitStatus.CLIENT_SUBMITTED)

        # ensure the client answer was created and stored correctly
        self.assertEqual(visit.client_answers.count(), 1)
        ca = visit.client_answers.first()
        assert ca is not None
        self.assertEqual(ca.choices, [1])
        self.assertEqual(ca.texts, ["fine"])

    def test_get_cases(self):
        case1 = create_case(self.location.pk, self.user)
        case2 = create_case(self.location.pk, self.user)
        phone_number = "+41797360516"

        _, token = generate_token(phone_number, case1)

        connect_case(case1, phone_number, token, consent=ConsentChoice.ALLOWED)

        _, token = generate_token(phone_number, case2)
        connect_case(case2, phone_number, token, consent=ConsentChoice.ALLOWED)

        contact = Contact.objects.get(phone_number=phone_number)

        client = Client.objects.get(contact=contact)

        cases = get_cases(client)
        self.assertEqual(len(cases), 2)
        self.assertIn(case1, cases)
        self.assertIn(case2, cases)

    def test_case_access(self):
        case1 = create_case(self.location.pk, self.user)

        phone_number = "+41797360516"

        new_location = self.location.tenant.locations.create(name="Other Location")

        other_user = User.objects.create_user(username="other")
        other_consultant = Consultant.objects.create(
            tenant=self.location.tenant,
            user=other_user,
        )
        other_consultant.locations.set([new_location])

        case2 = create_case(new_location.pk, other_user)

        self.assertFalse(location_can_view_case([new_location.pk], case1))
        self.assertFalse(location_can_view_case([self.location.pk], case2))

        _, token = generate_token(phone_number, case1)
        connect_case(case1, phone_number, token, consent=ConsentChoice.ALLOWED)
        _, token = generate_token(phone_number, case2)
        connect_case(case2, phone_number, token, consent=ConsentChoice.ALLOWED)

        self.assertTrue(location_can_view_case([new_location.pk], case1))
        self.assertTrue(location_can_view_case([self.location.pk], case2))
