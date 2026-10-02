from django.contrib.auth.models import Permission, User
from django.test import TestCase, override_settings
from django.urls import reverse
from django_otp.plugins.otp_totp.models import TOTPDevice

from tenants.models import APIToken, Consultant, Location, Tag, Tenant

# Rejected forms are rendered again, which needs static files without a manifest.
PLAIN_STATICFILES = {
    "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


@override_settings(STORAGES=PLAIN_STATICFILES)
class TenantAdminScopingTests(TestCase):
    """A tenant admin must not be able to submit ids of another tenant."""

    def setUp(self):
        self.admin_a = User.objects.create_user("admin_a", password="pw", is_staff=True)
        self.admin_a.user_permissions.set(Permission.objects.all())
        owner_b = User.objects.create_user("owner_b", password="pw")

        self.tenant_a = Tenant.objects.create(name="A", owner=self.admin_a)
        self.tenant_a.admins.add(self.admin_a)
        self.tenant_b = Tenant.objects.create(name="B", owner=owner_b)
        self.location_a = Location.objects.create(tenant=self.tenant_a, name="Loc A")
        self.location_b = Location.objects.create(tenant=self.tenant_b, name="Loc B")
        self.consultant = Consultant.objects.create(
            tenant=self.tenant_a, user=self.admin_a
        )
        self.consultant.locations.add(self.location_a)

        self._login(self.admin_a)

    def _login(self, user):
        device = TOTPDevice.objects.create(user=user, name="default", confirmed=True)
        self.client.force_login(user)
        session = self.client.session
        session["otp_device_id"] = device.persistent_id
        session.save()

    def _save_consultant(self, locations):
        url = reverse("admin:tenants_consultant_change", args=[self.consultant.pk])
        return self.client.post(
            url, {"locations": [loc.pk for loc in locations], "_save": "Save"}
        )

    def test_consultant_cannot_be_given_a_foreign_location(self):
        response = self._save_consultant([self.location_a, self.location_b])

        self.assertEqual(response.status_code, 200)
        self.assertIn("locations", response.context["adminform"].form.errors)
        self.assertEqual(list(self.consultant.locations.all()), [self.location_a])

    def test_own_location_is_still_accepted(self):
        other = Location.objects.create(tenant=self.tenant_a, name="Loc A2")

        response = self._save_consultant([self.location_a, other])

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.consultant.locations.count(), 2)

    def test_existing_foreign_value_survives_a_save(self):
        self.consultant.locations.add(self.location_b)

        response = self._save_consultant([self.location_a, self.location_b])

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.consultant.locations.count(), 2)

    def test_api_token_cannot_be_created_for_a_foreign_tenant(self):
        response = self.client.post(
            reverse("admin:tenants_apitoken_add"),
            {
                "name": "x",
                "tenant": self.tenant_b.pk,
                "owner": self.admin_a.pk,
                "_save": "Save",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(APIToken.objects.exists())

    def test_tag_cannot_be_made_available_in_a_foreign_location(self):
        response = self.client.post(
            reverse("admin:tenants_tag_add"),
            {
                "name": "t",
                "owner": self.admin_a.pk,
                "available_in": [self.location_b.pk],
                "_save": "Save",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Tag.objects.exists())

    def test_superuser_is_not_restricted(self):
        root = User.objects.create_superuser("root", password="pw")
        self._login(root)

        response = self._save_consultant([self.location_a, self.location_b])

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.consultant.locations.count(), 2)
