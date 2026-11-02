import io
import zipfile

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from django_otp.plugins.otp_totp.models import TOTPDevice
from openpyxl import load_workbook

from sure.client_service import get_case_link
from sure.models import Case, Questionnaire, Visit
from tenants.models import Location, Tag, Tenant

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
        self.other_location = Location.objects.create(tenant=tenant, name="Other")
        self.questionnaire = Questionnaire.objects.create(name="Q")
        self.questionnaire.locations.add(self.location)

        self.outreach = Tag.objects.create(name="outreach", owner=self.user)
        self.party = Tag.objects.create(name="party", owner=self.user)
        self.outreach.available_in.add(self.location)
        self.party.available_in.add(self.location)

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
                "language": "en",
                "quantity": 3,
                "tags": [self.outreach.pk],
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

    def test_selected_tags_are_applied_to_all_cases(self):
        self._generate(tags=[self.outreach.pk, self.party.pk])

        self.assertEqual(
            [sorted(tags) for tags in Visit.objects.values_list("tags", flat=True)],
            [["outreach", "party"]] * 3,
        )

    def test_at_least_one_tag_is_required(self):
        response = self._generate(tags=[])

        self.assertIn("tags", response.context["form"].errors)
        self.assertFalse(Case.objects.exists())

    def test_tag_not_available_at_location_is_rejected(self):
        elsewhere = Tag.objects.create(name="elsewhere", owner=self.user)
        elsewhere.available_in.add(self.other_location)

        response = self._generate(tags=[self.outreach.pk, elsewhere.pk])

        self.assertIn("elsewhere", str(response.context["form"].errors["tags"]))
        self.assertFalse(Case.objects.exists())

    def test_excel_lists_case_url_and_qr_code(self):
        response = self._generate(tags=[self.outreach.pk])

        self.assertIn(
            "case_batch_center_outreach.xlsx", response["Content-Disposition"]
        )
        sheet = load_workbook(io.BytesIO(response.content)).active
        rows = list(sheet.iter_rows(values_only=True))
        self.assertEqual(rows[0][:3], ("Case ID", "Questionnaire URL", "QR Code"))

        cases = {case.human_id: case for case in Case.objects.all()}
        self.assertEqual({row[0] for row in rows[1:]}, set(cases))
        for row in rows[1:]:
            self.assertEqual(row[1], get_case_link(cases[row[0]]))
        # One QR code per case, placed in the cell. openpyxl cannot read
        # images in cells, so look at the package itself.
        with zipfile.ZipFile(io.BytesIO(response.content)) as package:
            names = package.namelist()
            sheet_xml = package.read("xl/worksheets/sheet1.xml").decode()
        self.assertEqual(len([n for n in names if n.startswith("xl/media/")]), 3)
        self.assertIn("xl/richData/rdrichvalue.xml", names)
        self.assertFalse([name for name in names if name.startswith("/")])
        for row in (2, 3, 4):
            self.assertRegex(sheet_xml, rf'<c r="C{row}"[^>]*vm="\d+"')
