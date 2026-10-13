import time
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from django_otp.oath import TOTP
from django_otp.plugins.otp_totp.models import TOTPDevice


class LoginLockoutTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("consultant@example.com", password="pw")

    def _login(self, password):
        return self.client.post(
            "/api/auth/login",
            {"username": self.user.username, "password": password},
        )

    def test_wrong_password_has_a_code(self):
        response = self._login("wrong")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["code"], "invalid_credentials")

    def test_lockout_is_reported_as_json(self):
        for _ in range(settings.AXES_FAILURE_LIMIT):
            response = self._login("wrong")

        self.assertEqual(response.status_code, 429)
        data = response.json()
        self.assertEqual(data["code"], "locked_out")
        self.assertEqual(data["retry_after"], settings.AXES_COOLOFF_TIME * 3600)
        self.assertTrue(data["error"])

        # The correct password is locked out as well, and says so.
        response = self._login("pw")
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.json()["code"], "locked_out")

    def test_attempts_during_lockout_do_not_extend_it(self):
        from axes.models import AccessAttempt

        for _ in range(settings.AXES_FAILURE_LIMIT):
            self._login("wrong")
        locked_at = AccessAttempt.objects.get().attempt_time

        self._login("wrong")
        self._login("pw")

        self.assertEqual(AccessAttempt.objects.get().attempt_time, locked_at)


class OtpChallengeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("consultant@example.com", password="pw")
        self.device = TOTPDevice.objects.create(
            user=self.user, name="default", confirmed=True
        )
        self.client.force_login(self.user)

    def _token(self):
        device = self.device
        totp = TOTP(device.bin_key, device.step, device.t0, device.digits, device.drift)
        totp.time = time.time()
        return f"{totp.token():06d}"

    def _challenge(self, token):
        return self.client.post(
            "/api/auth/otp/2fa-challenge",
            {"device_id": self.device.persistent_id, "token": token},
        )

    def test_token_with_whitespace_is_accepted(self):
        token = self._token()

        response = self._challenge(f" {token[:3]} {token[3:]} ")

        self.assertEqual(response.status_code, 200)

    def test_wrong_token_has_a_code(self):
        response = self._challenge("abc")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["code"], "invalid_token")

    def test_throttled_device_is_not_reported_as_invalid_token(self):
        self._challenge("abc")

        # django-otp rejects even the correct code while throttled.
        response = self._challenge(self._token())

        self.assertEqual(response.status_code, 429)
        data = response.json()
        self.assertEqual(data["code"], "throttled")
        self.assertGreaterEqual(data["retry_after"], 1)

        TOTPDevice.objects.filter(pk=self.device.pk).update(
            throttling_failure_timestamp=timezone.now() - timedelta(minutes=1)
        )
        self.assertEqual(self._challenge(self._token()).status_code, 200)

    def test_throttled_setup_verification_is_reported(self):
        device = TOTPDevice.objects.create(user=self.user, name="new", confirmed=False)
        session = self.client.session
        session["otp_device_id"] = self.device.persistent_id
        session.save()
        data = {"device_id": device.persistent_id, "token": "abc"}

        self.assertEqual(
            self.client.post("/api/auth/otp/verify-device", data).status_code, 401
        )
        response = self.client.post("/api/auth/otp/verify-device", data)

        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.json()["code"], "throttled")
