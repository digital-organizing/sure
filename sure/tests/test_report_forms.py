"""Tests for prefilling clinical report forms."""

import datetime as dt

import pymupdf
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from django_otp.plugins.otp_totp.models import TOTPDevice

from labor.models import Laboratory, LocationToLab
from sure.models import (
    Case,
    ClientAnswer,
    ClientQuestion,
    ConsultantAnswer,
    ConsultantQuestion,
    Questionnaire,
    ReportField,
    ReportFieldKind,
    ReportForm,
    ReportFormFile,
    ReportSource,
    Section,
    Test,
    TestCategory,
    TestKind,
    TestResult,
    TestResultOption,
    Visit,
    VisitLog,
)
from sure.report_forms import (
    available_report_forms,
    bag_gender,
    fill_report,
    fit_text,
    format_date,
)
from tenants.models import Consultant, Location, Tenant

IN_MEMORY_STORAGE = {
    "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

TEXT = pymupdf.PDF_WIDGET_TYPE_TEXT  # ty: ignore[unresolved-attribute]
CHECKBOX = pymupdf.PDF_WIDGET_TYPE_CHECKBOX  # ty: ignore[unresolved-attribute]

FORM_FIELDS = [
    (TEXT, "Birth", (300, 50, 400, 64), {"date_format": "dd/mm/yyyy"}),
    (CHECKBOX, "Gender_w", (50, 52, 60, 62)),
    (CHECKBOX, "Gender_m", (80, 52, 90, 62)),
    (TEXT, "Postcode", (50, 80, 150, 94)),
    (CHECKBOX, "HIV-1", (50, 110, 60, 120)),
    (TEXT, "ResultDate", (100, 110, 200, 124), {"date_format": "dd/mm/yyyy"}),
    (TEXT, "Lab", (50, 140, 250, 154)),
    (TEXT, "Doctor", (50, 170, 300, 210), {"multiline": True}),
    (TEXT, "Today", (320, 170, 420, 184), {"date_format": "mm/yyyy"}),
    (CHECKBOX, "Vaccinated", (50, 230, 60, 240)),
    (TEXT, "Fixed", (80, 230, 200, 244)),
]


def make_pdf(fields) -> bytes:
    """A one page PDF with form fields given as (type, name, rect[, options])."""
    document = pymupdf.open()
    page = document.new_page()
    for field_type, name, rect, *rest in fields:
        options = rest[0] if rest else {}
        widget = pymupdf.Widget()
        widget.field_type = field_type
        widget.field_name = name
        widget.rect = pymupdf.Rect(rect)
        if "date_format" in options:
            widget.script_format = f'AFDate_FormatEx("{options["date_format"]}");'
        if options.get("multiline"):
            widget.field_flags |= pymupdf.PDF_TX_FIELD_IS_MULTILINE  # ty: ignore[unresolved-attribute]
        page.add_widget(widget)
    return document.tobytes()


def read_values(pdf: bytes) -> dict[str, str]:
    document = pymupdf.open(stream=pdf, filetype="pdf")
    page = document[0]
    return {widget.field_name: widget.field_value for widget in page.widgets()}


def is_ticked(value) -> bool:
    return value not in ("Off", "", False, None)


class BagGenderTest(SimpleTestCase):
    def test_gender_and_sex_map_to_the_bag_categories(self):
        cases = [
            (("1", "1"), "m"),
            (("1", "2"), "ftm"),
            (("1", "99"), "m"),
            (("2", "2"), "w"),
            (("2", "1"), "mtf"),
            (("2", None), "w"),
            (("3", "1"), "mtf"),
            (("3", "2"), "ftm"),
            (("3", "97"), None),
            (("4", "1"), None),
            (("99", "1"), None),
            ((None, None), None),
        ]
        for (gender, sex), expected in cases:
            with self.subTest(gender=gender, sex=sex):
                self.assertEqual(bag_gender(gender, sex), expected)

    def test_acrobat_date_formats(self):
        date = dt.date(2026, 9, 4)
        self.assertEqual(format_date(date, "dd/mm/yyyy"), "04/09/2026")
        self.assertEqual(format_date(date, "mm/yyyy"), "09/2026")
        self.assertEqual(format_date(date, ""), "04.09.2026")

    def test_lines_are_joined_when_that_allows_a_larger_font(self):
        text, size = fit_text(
            "Checkpoint Zürich\nKonradstrasse 1\n8005 Zürich\n044 000 00 00\nDora Muster",
            pymupdf.Rect(0, 0, 207, 29),
        )

        self.assertEqual(text.count("\n"), 1)
        self.assertEqual(
            text.replace("\n", ", "),
            "Checkpoint Zürich, Konradstrasse 1, 8005 Zürich, 044 000 00 00, Dora Muster",
        )
        self.assertGreater(size, 8)

    def test_lines_that_fit_are_kept(self):
        self.assertEqual(fit_text("A\nB", pymupdf.Rect(0, 0, 200, 60)), ("A\nB", 10.0))


@override_settings(STORAGES=IN_MEMORY_STORAGE)
class ReportFormTestCase(TestCase):
    def setUp(self):
        owner = User.objects.create_user(username="owner", password="pw")
        self.tenant = Tenant.objects.create(name="Tenant", owner=owner)
        self.location = Location.objects.create(
            tenant=self.tenant,
            name="Checkpoint Test",
            address="Teststrasse 1\n8000 Zürich",
            phone_number="044 000 00 00",
        )
        self.user = User.objects.create_user(
            username="doctor", password="pw", first_name="Dora", last_name="Doktor"
        )
        consultant = Consultant.objects.create(tenant=self.tenant, user=self.user)
        consultant.locations.add(self.location)

        laboratory = Laboratory.objects.create(name="Labor Test AG")
        LocationToLab.objects.create(
            labor=laboratory, location=self.location, client_code="C1"
        )

        questionnaire = Questionnaire.objects.create(name="Q")
        section = Section.objects.create(questionnaire=questionnaire, title="S")
        for order, code in enumerate(
            ["SEDFACT-GENDER", "SEDFACT-SEX", "SEDFACT-POSTCODE"]
        ):
            ClientQuestion.objects.create(
                section=section, code=code, question_text=code, order=order
            )
        ConsultantQuestion.objects.create(
            questionnaire=questionnaire, code="VACCINATIONSTATUS", question_text="V"
        )

        self.case = Case.objects.create(id="1234567", location=self.location)
        self.visit = Visit.objects.create(case=self.case, questionnaire=questionnaire)

        category = TestCategory.objects.create(number=1, name="STI")
        test_kind = TestKind.objects.create(category=category, number=1, name="HIV")
        self.positive = TestResultOption.objects.create(
            test_kind=test_kind, label="HIV-1 positive"
        )
        self.negative = TestResultOption.objects.create(
            test_kind=test_kind, label="negative"
        )
        self.test = Test.objects.create(visit=self.visit, test_kind=test_kind)
        self.result = TestResult.objects.create(
            result_option=self.positive, test=self.test
        )

        self.form = ReportForm.objects.create(name="HIV-Infektion")
        self.form.result_options.add(self.positive)
        self.file = ReportFormFile.objects.create(
            form=self.form,
            language="de",
            pdf=ContentFile(make_pdf(FORM_FIELDS), name="hiv.pdf"),
        )

    def answer(self, code: str, choices: list[int], texts: list[str]):
        question = ClientQuestion.objects.get(code=code)
        ClientAnswer.objects.create(
            visit=self.visit, question=question, choices=choices, texts=texts
        )

    def map_field(self, name: str, source: str, question_code="", value=""):
        updated = ReportField.objects.filter(file=self.file, name=name).update(
            source=source, question_code=question_code, value=value
        )
        self.assertEqual(updated, 1)

    def login(self, user: User):
        device = TOTPDevice.objects.create(user=user, name="default", confirmed=True)
        self.client.force_login(user)
        session = self.client.session
        session["otp_device_id"] = device.persistent_id
        session.save()


class ReportFieldSyncTest(ReportFormTestCase):
    def test_fields_are_read_in_reading_order(self):
        report_fields = list(self.file.report_fields.all())

        self.assertEqual(
            [f.name for f in report_fields],
            [
                "Gender_w",
                "Gender_m",
                "Birth",
                "Postcode",
                "HIV-1",
                "ResultDate",
                "Lab",
                "Doctor",
                "Today",
                "Vaccinated",
                "Fixed",
            ],
        )
        self.assertEqual([f.number for f in report_fields], list(range(1, 12)))
        by_name = {f.name: f for f in report_fields}
        self.assertEqual(by_name["Gender_w"].kind, ReportFieldKind.CHECKBOX)
        self.assertEqual(by_name["Birth"].kind, ReportFieldKind.TEXT)
        self.assertEqual(by_name["Birth"].date_format, "dd/mm/yyyy")
        self.assertEqual(by_name["Postcode"].date_format, "")
        self.file.refresh_from_db()
        self.assertEqual(self.file.page_count, 1)

    def test_new_version_keeps_the_mapping_of_fields_that_keep_their_name(self):
        self.map_field("Postcode", ReportSource.CLIENT_ANSWER, "SEDFACT-POSTCODE")

        self.file.pdf = ContentFile(
            make_pdf(
                [
                    (TEXT, "Canton", (50, 50, 90, 64)),
                    (TEXT, "Postcode", (50, 80, 150, 94)),
                ]
            ),
            name="hiv-v2.pdf",
        )
        self.file.save()

        report_fields = {f.name: f for f in self.file.report_fields.all()}
        self.assertEqual(set(report_fields), {"Canton", "Postcode"})
        self.assertEqual(report_fields["Postcode"].source, ReportSource.CLIENT_ANSWER)
        self.assertEqual(report_fields["Postcode"].question_code, "SEDFACT-POSTCODE")
        self.assertEqual(report_fields["Canton"].source, "")
        self.assertEqual(report_fields["Canton"].number, 1)


class FillReportTest(ReportFormTestCase):
    def test_fields_are_filled_from_their_sources(self):
        self.answer("SEDFACT-GENDER", [1], ["Ein Mann"])
        self.answer("SEDFACT-SEX", [1], ["Männlich"])
        self.answer("SEDFACT-POSTCODE", [1], ["8004"])
        ConsultantAnswer.objects.create(
            visit=self.visit,
            question=ConsultantQuestion.objects.get(code="VACCINATIONSTATUS"),
            choices=[1, 2],
            texts=["Hepatitis A", "Hepatitis B"],
        )
        self.map_field("Gender_w", ReportSource.GENDER, value="w")
        self.map_field("Gender_m", ReportSource.GENDER, value="m")
        self.map_field("Postcode", ReportSource.CLIENT_ANSWER, "SEDFACT-POSTCODE")
        self.map_field("HIV-1", ReportSource.RESULT_OPTION, value=str(self.positive.pk))
        self.map_field("ResultDate", ReportSource.RESULT_DATE)
        self.map_field("Lab", ReportSource.LABORATORY)
        self.map_field("Doctor", ReportSource.DOCTOR)
        self.map_field("Today", ReportSource.TODAY)
        self.map_field(
            "Vaccinated", ReportSource.CONSULTANT_ANSWER, "VACCINATIONSTATUS", "2"
        )
        self.map_field("Fixed", ReportSource.FIXED, value="behandelnder Arzt")

        values = read_values(fill_report(self.file, self.visit, self.user))

        self.assertFalse(is_ticked(values["Gender_w"]))
        self.assertTrue(is_ticked(values["Gender_m"]))
        self.assertEqual(values["Postcode"], "8004")
        self.assertTrue(is_ticked(values["HIV-1"]))
        result_date = timezone.localtime(self.result.created_at).date()
        self.assertEqual(values["ResultDate"], result_date.strftime("%d/%m/%Y"))
        self.assertEqual(values["Lab"], "Labor Test AG")
        self.assertEqual(
            values["Doctor"].replace("\n", ", "),
            "Checkpoint Test, Teststrasse 1, 8000 Zürich, 044 000 00 00, Dora Doktor",
        )
        self.assertEqual(values["Today"], timezone.localdate().strftime("%m/%Y"))
        self.assertTrue(is_ticked(values["Vaccinated"]))
        self.assertEqual(values["Fixed"], "behandelnder Arzt")
        self.assertEqual(values["Birth"], "")

    def test_fields_without_data_stay_empty(self):
        self.answer("SEDFACT-GENDER", [99], ["Das möchte ich nicht sagen."])
        self.map_field("Gender_w", ReportSource.GENDER, value="w")
        self.map_field("Gender_m", ReportSource.GENDER, value="m")
        self.map_field("Postcode", ReportSource.CLIENT_ANSWER, "SEDFACT-POSTCODE")
        self.map_field("HIV-1", ReportSource.RESULT_OPTION, value=str(self.negative.pk))

        values = read_values(fill_report(self.file, self.visit, self.user))

        self.assertFalse(is_ticked(values["Gender_w"]))
        self.assertFalse(is_ticked(values["Gender_m"]))
        self.assertEqual(values["Postcode"], "")
        self.assertFalse(is_ticked(values["HIV-1"]))

    def test_checkbox_ticks_for_any_of_several_values(self):
        self.map_field(
            "HIV-1",
            ReportSource.RESULT_OPTION,
            value=f"{self.negative.pk}, {self.positive.pk}",
        )

        values = read_values(fill_report(self.file, self.visit, self.user))

        self.assertTrue(is_ticked(values["HIV-1"]))

    def test_answer_placeholders_are_not_filled_in(self):
        self.answer("SEDFACT-POSTCODE", [2], ["-"])
        self.map_field("Postcode", ReportSource.CLIENT_ANSWER, "SEDFACT-POSTCODE")

        values = read_values(fill_report(self.file, self.visit, self.user))

        self.assertEqual(values["Postcode"], "")

    def test_latest_answer_wins(self):
        self.answer("SEDFACT-POSTCODE", [1], ["8004"])
        self.answer("SEDFACT-POSTCODE", [1], ["3000"])
        self.map_field("Postcode", ReportSource.CLIENT_ANSWER, "SEDFACT-POSTCODE")

        values = read_values(fill_report(self.file, self.visit, self.user))

        self.assertEqual(values["Postcode"], "3000")


class AvailableReportFormsTest(ReportFormTestCase):
    def test_offered_when_the_latest_result_is_linked(self):
        self.assertEqual(list(available_report_forms(self.visit)), [self.form])

    def test_not_offered_when_a_newer_result_is_not_linked(self):
        TestResult.objects.filter(pk=self.result.pk).update(
            created_at=timezone.now() - dt.timedelta(hours=1)
        )
        TestResult.objects.create(result_option=self.negative, test=self.test)

        self.assertEqual(list(available_report_forms(self.visit)), [])

    def test_not_offered_for_deleted_tests(self):
        self.test.mark_deleted()

        self.assertEqual(list(available_report_forms(self.visit)), [])

    def test_not_offered_without_pdf(self):
        self.file.delete()

        self.assertEqual(list(available_report_forms(self.visit)), [])


class ReportFormApiTest(ReportFormTestCase):
    def url(self, suffix=""):
        return f"/api/sure/case/{self.case.human_id}/reports/{suffix}"

    def test_list_available_forms(self):
        self.login(self.user)

        response = self.client.get(self.url())

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(
            response.json(),
            [{"id": self.form.pk, "name": "HIV-Infektion", "languages": ["de"]}],
        )

    def test_download_filled_form(self):
        self.map_field("Lab", ReportSource.LABORATORY)
        self.login(self.user)

        response = self.client.get(self.url(f"{self.form.pk}/de/"))

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertEqual(read_values(response.content)["Lab"], "Labor Test AG")
        self.assertTrue(
            VisitLog.objects.filter(
                visit=self.visit,
                user=self.user,
                action__startswith="Report form downloaded",
            ).exists()
        )

    def test_unknown_language_is_not_found(self):
        self.login(self.user)

        response = self.client.get(self.url(f"{self.form.pk}/fr/"))

        self.assertEqual(response.status_code, 404)

    def test_form_that_is_not_available_is_not_found(self):
        self.form.result_options.clear()
        self.login(self.user)

        response = self.client.get(self.url(f"{self.form.pk}/de/"))

        self.assertEqual(response.status_code, 404)

    def test_consultant_without_access_to_the_location_is_denied(self):
        other = User.objects.create_user(username="other", password="pw")
        other_location = Location.objects.create(tenant=self.tenant, name="Other")
        consultant = Consultant.objects.create(tenant=self.tenant, user=other)
        consultant.locations.add(other_location)
        self.login(other)

        self.assertEqual(self.client.get(self.url()).status_code, 403)
        self.assertEqual(
            self.client.get(self.url(f"{self.form.pk}/de/")).status_code, 403
        )


class ReportFormAdminTest(ReportFormTestCase):
    def setUp(self):
        super().setUp()
        self.admin = User.objects.create_superuser(username="admin", password="pw")

    def test_change_page_shows_the_preview_and_the_fields(self):
        self.login(self.admin)

        response = self.client.get(
            reverse("admin:sure_reportformfile_change", args=[self.file.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            reverse("admin:sure_reportformfile_preview", args=[self.file.pk, 0]),
        )
        self.assertContains(response, "Gender_w")

    def test_preview_image(self):
        self.login(self.admin)

        response = self.client.get(
            reverse("admin:sure_reportformfile_preview", args=[self.file.pk, 0])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/png")
        missing_page = reverse(
            "admin:sure_reportformfile_preview", args=[self.file.pk, 1]
        )
        self.assertEqual(self.client.get(missing_page).status_code, 404)

    def test_test_fill_downloads_the_filled_pdf(self):
        self.map_field("Lab", ReportSource.LABORATORY)
        self.login(self.admin)

        response = self.client.post(
            reverse("admin:sure_reportformfile_test_fill_view", args=[self.file.pk]),
            {"case_id": self.case.human_id},
        )

        self.assertEqual(response.status_code, 200, response.content[:500])
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertEqual(read_values(response.content)["Lab"], "Labor Test AG")

    def test_copy_mapping_from_another_language(self):
        self.map_field("Postcode", ReportSource.CLIENT_ANSWER, "SEDFACT-POSTCODE")
        french = ReportFormFile.objects.create(
            form=self.form,
            language="fr",
            pdf=ContentFile(make_pdf(FORM_FIELDS), name="vih.pdf"),
        )
        self.login(self.admin)

        response = self.client.post(
            reverse("admin:sure_reportformfile_copy_mapping_view", args=[french.pk]),
            {"source": self.file.pk},
        )

        self.assertRedirects(
            response,
            reverse("admin:sure_reportformfile_change", args=[french.pk]),
            fetch_redirect_response=False,
        )
        postcode = french.report_fields.get(name="Postcode")
        self.assertEqual(postcode.source, ReportSource.CLIENT_ANSWER)
        self.assertEqual(postcode.question_code, "SEDFACT-POSTCODE")

    def test_mapping_is_saved_through_the_inline(self):
        self.login(self.admin)
        url = reverse("admin:sure_reportformfile_change", args=[self.file.pk])
        report_fields = list(self.file.report_fields.all())
        data = {
            "language": "de",
            "report_fields-TOTAL_FORMS": str(len(report_fields)),
            "report_fields-INITIAL_FORMS": str(len(report_fields)),
            "report_fields-MIN_NUM_FORMS": "0",
            "report_fields-MAX_NUM_FORMS": "1000",
        }
        for index, report_field in enumerate(report_fields):
            prefix = f"report_fields-{index}"
            data[f"{prefix}-id"] = str(report_field.pk)
            data[f"{prefix}-file"] = str(self.file.pk)
            data[f"{prefix}-source"] = ""
            data[f"{prefix}-question_code"] = ""
            data[f"{prefix}-value"] = ""
        postcode_index = [f.name for f in report_fields].index("Postcode")
        data[f"report_fields-{postcode_index}-source"] = ReportSource.CLIENT_ANSWER
        data[f"report_fields-{postcode_index}-question_code"] = "UNKNOWN"

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "There is no question with this code.")

        data[f"report_fields-{postcode_index}-question_code"] = "SEDFACT-POSTCODE"
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, 302, response.content[:2000])
        self.assertEqual(
            self.file.report_fields.get(name="Postcode").question_code,
            "SEDFACT-POSTCODE",
        )

    def test_only_superusers_manage_report_forms(self):
        staff = User.objects.create_user(username="staff", password="pw", is_staff=True)
        self.login(staff)

        response = self.client.get(
            reverse("admin:sure_reportformfile_change", args=[self.file.pk])
        )

        self.assertIn(response.status_code, (302, 403))
        preview = reverse("admin:sure_reportformfile_preview", args=[self.file.pk, 0])
        self.assertIn(self.client.get(preview).status_code, (302, 403, 404))
