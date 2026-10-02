from django.contrib.auth.models import User
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import RequestFactory, TestCase, TransactionTestCase
from django.urls import reverse
from django_otp.plugins.otp_totp.models import TOTPDevice

from tenants.auth import auth_tenant_api_token
from tenants.models import APIToken, Tenant, hash_api_token


class APITokenTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_superuser("root", password="pw")
        self.tenant = Tenant.objects.create(name="Tenant", owner=self.owner)
        self.api_token = APIToken.objects.create(tenant=self.tenant, owner=self.owner)
        self.raw_token = self.api_token.raw_token

    def _authenticate(self, key):
        request = RequestFactory().get("/")
        return auth_tenant_api_token.authenticate(request, key), request

    def test_only_the_hash_is_stored(self):
        stored = APIToken.objects.get(pk=self.api_token.pk)

        self.assertEqual(stored.token_hash, hash_api_token(self.raw_token))
        self.assertEqual(stored.token_hint, self.raw_token[-4:])
        self.assertIsNone(stored.raw_token)
        self.assertNotIn(self.raw_token, [str(v) for v in vars(stored).values()])

    def test_saving_again_keeps_the_token(self):
        stored = APIToken.objects.get(pk=self.api_token.pk)
        stored.revoked = False
        stored.save()

        tenant, _ = self._authenticate(f"{stored.name}:{self.raw_token}")
        self.assertEqual(tenant, self.tenant)

    def test_valid_token_authenticates_as_its_owner(self):
        tenant, request = self._authenticate(f"{self.api_token.name}:{self.raw_token}")

        self.assertEqual(tenant, self.tenant)
        self.assertEqual(request.user, self.owner)

    def test_wrong_hashed_or_revoked_token_is_rejected(self):
        name = self.api_token.name
        for key in (
            f"{name}:wrong",
            f"{name}:{self.api_token.token_hash}",
            f"other:{self.raw_token}",
            self.raw_token,
            None,
        ):
            with self.subTest(key=key):
                self.assertIsNone(self._authenticate(key)[0])

        self.api_token.revoked = True
        self.api_token.save()
        self.assertIsNone(self._authenticate(f"{name}:{self.raw_token}")[0])

    def test_admin_shows_the_token_once(self):
        device = TOTPDevice.objects.create(
            user=self.owner, name="default", confirmed=True
        )
        self.client.force_login(self.owner)
        session = self.client.session
        session["otp_device_id"] = device.persistent_id
        session.save()

        response = self.client.post(
            reverse("admin:tenants_apitoken_add"),
            {
                "name": "new",
                "tenant": self.tenant.pk,
                "owner": self.owner.pk,
                "_save": "Save",
            },
        )

        created = APIToken.objects.get(name="new")
        shown = [str(m) for m in response.wsgi_request._messages]
        header = next(m for m in shown if "X-Tenant-Token" in m)
        raw_token = header.split("new:")[1].split(" ")[0]
        self.assertTrue(created.matches(raw_token))


class HashExistingTokensMigrationTests(TransactionTestCase):
    before = [("tenants", "0029_invitation_mail_placeholders")]
    after = [("tenants", "0030_hash_api_tokens")]

    def test_existing_tokens_keep_working(self):
        executor = MigrationExecutor(connection)
        executor.migrate(self.before)
        apps = executor.loader.project_state(self.before).apps
        owner = apps.get_model("auth", "User").objects.create(username="root")
        tenant = apps.get_model("tenants", "Tenant").objects.create(
            name="Tenant", owner=owner
        )
        old = apps.get_model("tenants", "APIToken").objects.create(
            tenant=tenant, owner=owner, name="legacy", token="a" * 46 + "beef"
        )

        executor = MigrationExecutor(connection)
        executor.migrate(self.after)

        migrated = APIToken.objects.get(pk=old.pk)
        self.assertTrue(migrated.matches("a" * 46 + "beef"))
        self.assertEqual(migrated.token_hint, "beef")

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
