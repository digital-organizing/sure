from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from django_otp.plugins.otp_totp.models import TOTPDevice

from tenants.models import Consultant, Tenant

# The admin index is rendered, which needs static files without a manifest.
PLAIN_STATICFILES = {
    "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


@override_settings(STORAGES=PLAIN_STATICFILES)
class ConsultantViewLinkTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser("admin", password="pw")
        self.tenant = Tenant.objects.create(name="Tenant", owner=self.user)

        device = TOTPDevice.objects.create(
            user=self.user, name="default", confirmed=True
        )
        self.client.force_login(self.user)
        session = self.client.session
        session["otp_device_id"] = device.persistent_id
        session.save()

    def test_consultants_get_a_link_to_the_consultant_view(self):
        Consultant.objects.create(tenant=self.tenant, user=self.user)

        response = self.client.get(reverse("admin:index"))

        self.assertContains(response, 'href="/consultant"')

    def test_admins_without_consultant_profile_get_no_link(self):
        response = self.client.get(reverse("admin:index"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'href="/consultant"')
