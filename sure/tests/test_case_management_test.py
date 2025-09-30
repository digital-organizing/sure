from django.contrib.auth.models import User
from django.test import TestCase

from sure.client_service import (canonicalize_phone_number, connect_case,
                                 create_case, generate_token, get_case_link,
                                 get_cases, get_client_by_id, verify_token)
from sure.models import Client, ConsentChoice, Contact, Token
from tenants.models import Tenant


class CaseManagementTest(TestCase):
    def setUp(self) -> None:
        owner = User.objects.create_user(username="owner")
        tenant = Tenant.objects.create(
            name="Test Tenant",
            owner=owner,
        )
        location = tenant.locations.create(name="Test Location")
        self.location = location

    def test_canonicalize_phone_number(self):
        self.assertEqual(canonicalize_phone_number("+41 79 736 05 16"), "+41797360516")
        self.assertEqual(canonicalize_phone_number("0797360516"), "+41797360516")

    def test_create_case(self):
        case = create_case(self.location)
        self.assertIsNotNone(case)
        self.assertEqual(case.location, self.location)

    def test_get_case_link(self):
        case = create_case(self.location)
        from django.conf import settings

        link = get_case_link(case)
        self.assertTrue(link.startswith(settings.SITE_URL))
        self.assertIn(case.human_id, link)

    def test_generate_token(self):
        phone_number = "+41797360516"
        token = generate_token(phone_number)
        contact = Contact.objects.filter(
            phone_number=canonicalize_phone_number(phone_number)
        ).first()
        self.assertIsNotNone(contact)

        token = Token.objects.filter(contact=contact).get()
        self.assertIsNone(token.used_at)

        contact = Contact.objects.get(phone_number=phone_number)
        self.assertTrue(contact.tokens.filter(token=token.token).exists())

    def test_verify_token(self):
        phone_number = "+41797360516"
        _, token = generate_token(phone_number)

        contact = verify_token(token, phone_number)

        self.assertIsNotNone(contact)
        assert contact is not None
        self.assertEqual(contact.phone_number, canonicalize_phone_number(phone_number))

        self.assertIsNone(contact.tokens.get(token=token).used_at)

    def test_connect_case(self):
        phone_number = "+41797360516"
        case = create_case(self.location)
        _, token = generate_token(phone_number)

        conection = connect_case(
            case, phone_number, token, consent=ConsentChoice.ALLOWED
        )
        client = conection.client

        self.assertIsNotNone(client)
        self.assertIsNotNone(client.contact)
        self.assertEqual(
            client.contact.phone_number, canonicalize_phone_number(phone_number)
        )

        self.assertIsNotNone(conection)
        self.assertEqual(conection.case, case)

        client2 = get_client_by_id(client.id, case.id)

        assert client2 is not None
        self.assertEqual(client2.id, client.id)

    def test_connect_case_no_consent(self):
        phone_number = "+41797360516"
        case = create_case(self.location)
        _, token = generate_token(phone_number)

        with self.assertRaises(ValueError):
            connect_case(case, phone_number, token, consent=ConsentChoice.DENIED)

    def test_connect_case_invalid_token(self):
        phone_number = "+41797360516"
        case = create_case(self.location)
        generate_token(phone_number)

        with self.assertRaises(ValueError):
            connect_case(
                case, phone_number, "invalidtoken", consent=ConsentChoice.ALLOWED
            )

    def test_get_cases(self):
        case1 = create_case(self.location)
        case2 = create_case(self.location)
        phone_number = "+41797360516"

        _, token = generate_token(phone_number)

        connect_case(case1, phone_number, token, consent=ConsentChoice.ALLOWED)

        _, token = generate_token(phone_number)
        connect_case(case2, phone_number, token, consent=ConsentChoice.ALLOWED)

        contact = Contact.objects.get(phone_number=phone_number)

        client = Client.objects.get(contact=contact)

        cases = get_cases(client)
        self.assertEqual(len(cases), 2)
        self.assertIn(case1, cases)
        self.assertIn(case2, cases)
