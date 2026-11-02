import io
from datetime import UTC, date, datetime, timedelta
from unittest.mock import patch

from django.contrib.auth.models import Permission, User
from django.test import TestCase, override_settings
from django.urls import reverse
from django_otp.plugins.otp_totp.models import TOTPDevice
from openpyxl import load_workbook

from sms.backfill import backfill
from sms.models import SMSCategory, SMSMessage
from sms.service import send_sms
from sms.views import sms_usage
from sure.models import (
    Case,
    Client,
    Connection,
    Contact,
    Questionnaire,
    Token,
    Visit,
    VisitLog,
)
from tenants.models import Location, Tenant

PHONE = "+41791234567"
SENT = datetime(2026, 10, 1, 10, 0, tzinfo=UTC)

# The export form is rendered, which needs static files without a manifest.
PLAIN_STATICFILES = {
    "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


class SMSTestCase(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user("owner", password="pw")
        self.tenant = Tenant.objects.create(name="Tenant", owner=self.owner)
        self.location = Location.objects.create(tenant=self.tenant, name="Center")
        self.other_tenant = Tenant.objects.create(name="Other", owner=self.owner)
        self.questionnaire = Questionnaire.objects.create(name="Q")

    def _visit(self, case_id="1111111", location=None, phone=PHONE):
        case = Case.objects.create(id=case_id, location=location or self.location)
        visit = Visit.objects.create(case=case, questionnaire=self.questionnaire)
        if phone:
            contact = Contact.objects.create(phone_number=phone)
            Connection.objects.create(
                case=case, client=Client.objects.create(contact=contact)
            )
        return visit

    def _sms(self, at, to=PHONE, tenant=None, cost=1):
        sms = SMSMessage.objects.create(
            to=to, response={"cost": cost}, tenant=tenant or self.tenant
        )
        SMSMessage.objects.filter(pk=sms.pk).update(sent_at=at)
        return sms

    def _log(self, visit, action, at):
        log = visit.logs.create(action=action)
        VisitLog.objects.filter(pk=log.pk).update(timestamp=at)


class SendSMSTests(SMSTestCase):
    @patch("sms.service._send_sms", return_value={"cost": 2})
    def test_category_location_and_tenant_are_recorded(self, _send):
        send_sms(PHONE, "Hello", self.location, SMSCategory.REMINDER)

        sms = SMSMessage.objects.get()
        self.assertEqual(sms.category, SMSCategory.REMINDER)
        self.assertEqual(sms.location, self.location)
        self.assertEqual(sms.tenant, self.tenant)
        self.assertEqual(sms.to, "XXXXXXXX4567")


class BackfillTests(SMSTestCase):
    def _attributed(self, sms):
        sms.refresh_from_db()
        return sms.category, sms.location

    def test_verification_code_is_matched_by_token(self):
        visit = self._visit()
        token = Token.objects.create(
            contact=visit.case.connection.client.contact, case=visit.case
        )
        Token.objects.filter(pk=token.pk).update(created_at=SENT)
        sms = self._sms(SENT + timedelta(seconds=2))

        backfill()

        self.assertEqual(
            self._attributed(sms), (SMSCategory.VERIFICATION_CODE, self.location)
        )

    def test_reminder_is_matched_by_reminder_time(self):
        visit = self._visit()
        Visit.objects.filter(pk=visit.pk).update(
            reminder_sent_at=SENT + timedelta(seconds=1)
        )
        sms = self._sms(SENT)

        backfill()

        self.assertEqual(self._attributed(sms), (SMSCategory.REMINDER, self.location))

    def test_results_link_needs_the_clients_number(self):
        visit = self._visit()
        self._log(visit, "Results published to client", SENT)
        other_number = self._sms(SENT + timedelta(seconds=1), to="+41790000000")
        own_number = self._sms(SENT + timedelta(seconds=3))

        backfill()

        self.assertEqual(self._attributed(other_number), ("", None))
        self.assertEqual(
            self._attributed(own_number), (SMSCategory.RESULTS_LINK, self.location)
        )

    def test_case_link_is_matched_shortly_after_creation_only(self):
        visit = self._visit(phone=None)
        self._log(visit, "Case created", SENT)
        later = self._visit(case_id="2222222", phone=None)
        self._log(later, "Case created", SENT + timedelta(hours=1))
        right_after = self._sms(SENT + timedelta(seconds=2))
        much_later = self._sms(SENT + timedelta(hours=1, minutes=5))

        backfill()

        self.assertEqual(
            self._attributed(right_after), (SMSCategory.CASE_LINK, self.location)
        )
        self.assertEqual(self._attributed(much_later), ("", None))

    def test_sms_of_another_tenant_is_not_matched(self):
        visit = self._visit()
        Visit.objects.filter(pk=visit.pk).update(reminder_sent_at=SENT)
        sms = self._sms(SENT, tenant=self.other_tenant)

        backfill()

        self.assertEqual(self._attributed(sms), ("", None))

    def test_sms_without_tenant_gets_it_from_the_match(self):
        visit = self._visit()
        Visit.objects.filter(pk=visit.pk).update(reminder_sent_at=SENT)
        sms = self._sms(SENT)
        SMSMessage.objects.filter(pk=sms.pk).update(tenant=None)

        backfill()

        sms.refresh_from_db()
        self.assertEqual(sms.tenant, self.tenant)
        self.assertEqual(sms.to, "XXXXXXXX4567")

    def test_dry_run_saves_nothing(self):
        visit = self._visit()
        Visit.objects.filter(pk=visit.pk).update(reminder_sent_at=SENT)
        sms = self._sms(SENT)

        counts = backfill(dry_run=True)

        self.assertEqual(counts["Reminder"], 1)
        self.assertEqual(self._attributed(sms), ("", None))


class UsageTests(SMSTestCase):
    def test_usage_is_totalled_per_location_and_category(self):
        for cost in (1, 2):
            sms = self._sms(SENT, cost=cost)
            SMSMessage.objects.filter(pk=sms.pk).update(
                location=self.location, category=SMSCategory.REMINDER
            )
        self._sms(SENT)
        self._sms(SENT + timedelta(days=40))

        usage = sms_usage(date(2026, 10, 1), date(2026, 10, 31))

        self.assertEqual(
            usage,
            [
                {
                    "Tenant": "Tenant",
                    "Location": "Center",
                    "Category": "Reminder",
                    "SMS": 2,
                    "Credits": 3,
                },
                {
                    "Tenant": "Tenant",
                    "Location": "Unknown",
                    "Category": "Unknown",
                    "SMS": 1,
                    "Credits": 1,
                },
            ],
        )


@override_settings(STORAGES=PLAIN_STATICFILES)
class UsageExportViewTests(SMSTestCase):
    url = reverse("admin:sms_smsmessage_export_usage_view")

    def _login(self, user):
        device = TOTPDevice.objects.create(user=user, name="default", confirmed=True)
        self.client.force_login(user)
        session = self.client.session
        session["otp_device_id"] = device.persistent_id
        session.save()

    def test_superuser_downloads_the_usage(self):
        self._sms(SENT, cost=2)
        self._login(User.objects.create_superuser("admin", password="pw"))

        response = self.client.post(
            self.url, {"start_date": "2026-10-01", "end_date": "2026-10-31"}
        )

        sheet = load_workbook(io.BytesIO(response.content)).active
        rows = list(sheet.iter_rows(values_only=True))
        self.assertEqual(rows[0], ("Tenant", "Location", "Category", "SMS", "Credits"))
        self.assertEqual(rows[-1], ("Total", None, None, 1, 2))

    def test_tenant_admin_is_denied(self):
        admin = User.objects.create_user("tenant_admin", password="pw", is_staff=True)
        admin.user_permissions.set(Permission.objects.all())
        self._login(admin)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)
