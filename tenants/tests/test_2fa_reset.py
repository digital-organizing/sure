import time

from django.contrib.auth.models import User
from django.test import TestCase
from django_otp import devices_for_user
from django_otp.oath import TOTP
from django_otp.plugins.otp_totp.models import TOTPDevice

from tenants.account import reset_2fa


class Reset2FaTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("consultant@example.com", password="pw")
        self.device = TOTPDevice.objects.create(
            user=self.user, name="default", confirmed=True
        )

    def _login(self):
        return self.client.post(
            "/api/auth/login", {"username": self.user.username, "password": "pw"}
        )

    def _account(self):
        return self.client.post("/api/auth/account").json()

    def _trust_this_browser(self):
        device = self.device
        totp = TOTP(device.bin_key, device.step, device.t0, device.digits, device.drift)
        totp.time = time.time()
        response = self.client.post(
            "/api/auth/otp/2fa-challenge",
            {
                "device_id": device.persistent_id,
                "token": f"{totp.token():06d}",
                "remember": "true",
            },
        )
        self.assertEqual(response.status_code, 200)

    def test_reset_removes_devices(self):
        TOTPDevice.objects.create(user=self.user, name="pending", confirmed=False)

        reset_2fa(self.user)

        self.assertEqual(list(devices_for_user(self.user, confirmed=None)), [])

    def test_reset_revokes_trusted_browsers(self):
        self._login()
        self._trust_this_browser()
        self.client.post("/api/auth/logout")

        # A trusted browser gets in with the password alone.
        self._login()
        self.assertTrue(self._account()["verified"])
        self.client.post("/api/auth/logout")

        reset_2fa(User.objects.get(pk=self.user.pk))

        self._login()
        account = self._account()
        self.assertFalse(account["is_trusted"])
        self.assertFalse(account["verified"])

    def test_reset_ends_a_verified_session(self):
        self._login()
        self._trust_this_browser()
        self.assertTrue(self._account()["verified"])

        reset_2fa(User.objects.get(pk=self.user.pk))

        self.assertFalse(self._account()["verified"])
