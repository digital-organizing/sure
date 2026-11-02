from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from django_otp.plugins.otp_totp.models import TOTPDevice

from sure.models import Case, Questionnaire
from tenants.models import Location, Tenant

# Rejected forms are rendered again, which needs static files without a manifest.
PLAIN_STATICFILES = {
    "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


@override_settings(STORAGES=PLAIN_STATICFILES)
class GenerateCaseBatchTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser("admin", password="pw")
        tenant = Tenant.objects.create(name="Tenant", owner=self.user)
        self.location = Location.objects.create(tenant=tenant, name="Center")
        self.questionnaire = Questionnaire.objects.create(name="Q")
        self.questionnaire.locations.add(self.location)

        device = TOTPDevice.objects.create(
            user=self.user, name="default", confirmed=True
        )
        self.client.force_login(self.user)
        session = self.client.session
        session["otp_device_id"] = device.persistent_id
        session.save()

    def _generate(self, **data):
        return self.client.post(
            reverse("admin:sure_visit_generate_batch_view"),
            {
                "location": self.location.pk,
                "questionnaire": self.questionnaire.pk,
                "tag": "event",
                "quantity": 3,
                **data,
            },
        )

    def test_language_is_applied_to_all_cases(self):
        response = self._generate(language="fr")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            list(Case.objects.values_list("language", flat=True)), ["fr"] * 3
        )

    def test_unknown_language_is_rejected(self):
        response = self._generate(language="xx")

        self.assertIn("language", response.context["form"].errors)
        self.assertFalse(Case.objects.exists())
