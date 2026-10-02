from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from sure.client_service import can_connect_case, connect_case, generate_token
from sure.models import Case, ConsentChoice
from tenants.models import Location, Tenant

PHONE_NUMBER = "+41791234567"


@override_settings(TOKEN_MAX_ATTEMPTS=3, TOKEN_RESEND_INTERVAL_MINUTES=3)
class TokenAttemptLimitTests(TestCase):
    def setUp(self):
        owner = User.objects.create_user(username="token_owner", password="pw")
        tenant = Tenant.objects.create(name="Tenant Token", owner=owner)
        location = Location.objects.create(tenant=tenant, name="Center Token")
        self.case = Case.objects.create(id="9184722", location=location)
        self.contact, self.token = generate_token(PHONE_NUMBER, self.case)
        self.wrong = "000000" if self.token != "000000" else "111111"

    def _connect(self, token):
        return connect_case(self.case, PHONE_NUMBER, token, ConsentChoice.ALLOWED)

    def _fail(self, times):
        for _ in range(times):
            with self.assertRaises(ValueError):
                self._connect(self.wrong)

    def test_wrong_codes_below_the_limit_leave_the_token_usable(self):
        self._fail(2)

        self._connect(self.token)

        self.assertFalse(can_connect_case(self.case))

    def test_token_is_rejected_once_the_attempts_are_used_up(self):
        self._fail(3)

        with self.assertRaises(ValueError):
            self._connect(self.token)

        self.assertEqual(self.contact.tokens.get().failed_attempts, 4)
        self.assertTrue(can_connect_case(self.case))

    def test_locked_token_still_blocks_an_immediate_resend(self):
        self._fail(3)

        self.assertTrue(self.contact.has_recent_token())
