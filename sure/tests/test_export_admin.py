from datetime import date
from unittest.mock import patch

from django.contrib.auth.models import Permission, User
from django.test import TestCase
from django.urls import reverse
from django_otp.plugins.otp_totp.models import TOTPDevice

from sure.models import ExportStatus, VisitExport
from tenants.models import Consultant, Tenant


class StartExportTests(TestCase):
    """Only the owner may start an export, and only once."""

    def setUp(self):
        self.user = self._admin("admin_one")
        self.colleague = self._admin("admin_two")
        tenant = Tenant.objects.create(name="Tenant", owner=self.user)
        for user in (self.user, self.colleague):
            tenant.admins.add(user)
            Consultant.objects.create(tenant=tenant, user=user)

        device = TOTPDevice.objects.create(
            user=self.user, name="default", confirmed=True
        )
        self.client.force_login(self.user)
        session = self.client.session
        session["otp_device_id"] = device.persistent_id
        session.save()

    def _admin(self, username):
        user = User.objects.create_user(username, password="pw", is_staff=True)
        user.user_permissions.set(Permission.objects.all())
        return user

    def _start(self, user, status=ExportStatus.PENDING):
        export = VisitExport.objects.create(
            user=user,
            status=status,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
        )
        url = reverse("admin:sure_visitexport_start_export_obj", args=[export.pk])
        with patch("sure.admin.create_export.delay") as delay:
            self.client.get(url)
        return export, delay

    def test_own_pending_export_is_started(self):
        export, delay = self._start(self.user)

        delay.assert_called_once_with(str(export.pk))

    def test_export_of_a_colleague_is_not_started(self):
        _, delay = self._start(self.colleague)

        delay.assert_not_called()

    def test_export_that_already_ran_is_not_started_again(self):
        for status in (
            ExportStatus.IN_PROGRESS,
            ExportStatus.COMPLETED,
            ExportStatus.FAILED,
        ):
            with self.subTest(status=status):
                _, delay = self._start(self.user, status)

                delay.assert_not_called()
