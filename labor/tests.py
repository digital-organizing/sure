from pathlib import Path

from django.contrib.auth.models import User
from django.test import TestCase

from labor.models import (
    LabOrder,
    LabOrderCounter,
    Laboratory,
    LocationToLab,
    OrderStatus,
    ResultMapping,
    TestProfile,
)
from labor.service import parse_hl7_to_db
from sure.models import (
    Case,
    Questionnaire,
    Test,
    TestCategory,
    TestKind,
    TestResult,
    TestResultOption,
    Visit,
    VisitNote,
)
from tenants.models import Location, Tenant


class ParseHl7ToDbTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="pw")
        self.tenant = Tenant.objects.create(name="Tenant", owner=self.owner)
        self.location = Location.objects.create(tenant=self.tenant, name="Center A")

        self.case = Case.objects.create(id="7273738", location=self.location)
        self.questionnaire = Questionnaire.objects.create(name="Q")
        self.visit = Visit.objects.create(
            case=self.case, questionnaire=self.questionnaire
        )

        self.laboratory = Laboratory.objects.create(name="Lab A")
        self.counter = LabOrderCounter.objects.create(
            nr_kreis="9610",
            base_number="0001297740",
            last_index=44,
        )
        LocationToLab.objects.create(
            labor=self.laboratory,
            location=self.location,
            client_code="TEAMW",
            nr_kreis="9610",
        )

        self.order = LabOrder.objects.create(
            visit=self.visit,
            lab_order_counter=self.counter,
            order_number="96100001297784",
        )

        category = TestCategory.objects.create(number=900, name="Lab")
        self.kind_hiv = TestKind.objects.create(
            category=category,
            number=901,
            name="HIV PCR",
        )
        self.kind_serology = TestKind.objects.create(
            category=category,
            number=902,
            name="Serology",
        )
        self.kind_pcr = TestKind.objects.create(
            category=category,
            number=903,
            name="CT/GO PCR",
        )

        self.opt_negative = TestResultOption.objects.create(
            test_kind=self.kind_hiv,
            label="Negative",
        )
        self.opt_positive = TestResultOption.objects.create(
            test_kind=self.kind_pcr,
            label="Positive",
        )
        self.opt_serology = TestResultOption.objects.create(
            test_kind=self.kind_serology,
            label="Low",
        )

        self.profile_hiv = TestProfile.objects.create(
            laboratory=self.laboratory,
            test_kind=self.kind_hiv,
            profile_name="Infektionserkrankungen (HIV)",
            profile_code="34",
        )
        self.profile_serology = TestProfile.objects.create(
            laboratory=self.laboratory,
            test_kind=self.kind_serology,
            profile_name="Infektserologie",
            profile_code="35",
            fallback_result_option=self.opt_serology,
        )
        self.profile_pcr = TestProfile.objects.create(
            laboratory=self.laboratory,
            test_kind=self.kind_pcr,
            profile_name="Molekularbiologie (PCR)",
            profile_code="53",
        )

        # Exact text mappings expected in the sample file.
        ResultMapping.objects.create(
            profile=self.profile_hiv,
            result_text="negativ",
            result_option=self.opt_negative,
        )
        ResultMapping.objects.create(
            profile=self.profile_pcr,
            result_text="positiv",
            result_option=self.opt_positive,
        )

        # Intentionally no mapping for value "0.8" to verify fallback behavior.
        ResultMapping.objects.create(
            profile=self.profile_serology,
            result_text="<1.0",
            result_option=self.opt_serology,
        )

    def _load_sample_hl7(self):
        sample_path = Path(__file__).resolve().parents[0] / "bsp_result.hl7"
        content = sample_path.read_text(encoding="iso-8859-1")
        normalized = content.replace("\r\n", "\n").replace("\r", "\n")
        return normalized.replace("\n", "\r")

    def test_parse_hl7_to_db_imports_mappings_and_profile_fallback(self):
        content = self._load_sample_hl7()

        lab_result = parse_hl7_to_db(content)

        self.order.refresh_from_db()

        self.assertEqual(lab_result.order, self.order)
        self.assertEqual(lab_result.visit, self.visit)
        self.assertEqual(lab_result.content, content)
        self.assertEqual(self.order.status, OrderStatus.COMPLETED)

        # One HIV result + one serology fallback + two PCR results.
        self.assertEqual(TestResult.objects.count(), 4)

        test_hiv = Test.objects.get(visit=self.visit, test_kind=self.kind_hiv)
        test_serology = Test.objects.get(visit=self.visit, test_kind=self.kind_serology)
        test_pcr = Test.objects.get(visit=self.visit, test_kind=self.kind_pcr)

        self.assertEqual(test_hiv.results.count(), 1)
        self.assertEqual(test_serology.results.count(), 1)
        self.assertEqual(test_pcr.results.count(), 2)

        hiv_result = test_hiv.results.first()
        self.assertIsNotNone(hiv_result)
        if hiv_result is None:
            self.fail("Expected HIV result to be created")
        self.assertEqual(hiv_result.result_option, self.opt_negative)
        self.assertEqual(hiv_result.note, "negativ")
        self.assertIn(
            "HIV1-RNA wurde nicht nachgewiesen",
            hiv_result.note_lab,
        )

        pcr_notes = list(test_pcr.results.values_list("note", flat=True).order_by("id"))
        self.assertEqual(pcr_notes, ["positiv", "positiv"])

        serology_result = test_serology.results.first()
        self.assertIsNotNone(serology_result)
        if serology_result is None:
            self.fail("Expected serology fallback result to exist")
        self.assertEqual(serology_result.result_option, self.opt_serology)
        self.assertEqual(serology_result.note, "0.8")

        last_pcr_result = test_pcr.results.order_by("id").last()
        self.assertIsNotNone(last_pcr_result)
        if last_pcr_result is None:
            self.fail("Expected last PCR result to exist")
        self.assertEqual(last_pcr_result.note_lab, "Zufallsbefund")

        notes = list(
            VisitNote.objects.filter(visit=self.visit).values_list("note", flat=True)
        )
        self.assertEqual(len(notes), 2)
        self.assertIn("Lab Note (HIV-1 quantitativ (RNA) - PCR)", notes[0])
        self.assertIn("Lab Note (Neisseria gonorrhoeae (DNA))", notes[1])


from django.core.exceptions import ValidationError
from unittest.mock import MagicMock, patch
from labor.schema import PatientDataSchema
from labor.service import generate_hl7_order
from labor.team_w import upload_order
from labor.models import FTPConnection


class HL7OrderGenerationAndUploadTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner2", password="pw")
        self.tenant = Tenant.objects.create(name="Tenant2", owner=self.owner)
        self.location = Location.objects.create(tenant=self.tenant, name="Center B")
        self.case = Case.objects.create(id="1234567", location=self.location)
        self.questionnaire = Questionnaire.objects.create(name="Q2")
        self.visit = Visit.objects.create(
            case=self.case, questionnaire=self.questionnaire
        )
        self.laboratory = Laboratory.objects.create(name="Lab B")
        self.counter = LabOrderCounter.objects.create(
            nr_kreis="9610",
            base_number="0001297740",
            last_index=1,
        )
        LocationToLab.objects.create(
            labor=self.laboratory,
            location=self.location,
            client_code="TEAMW",
            nr_kreis="9610",
        )
        category = TestCategory.objects.create(number=800, name="Lab2")
        self.kind = TestKind.objects.create(
            category=category,
            number=801,
            name="Test Kind 1",
        )
        Test.objects.create(visit=self.visit, test_kind=self.kind)

        self.profile = TestProfile.objects.create(
            laboratory=self.laboratory,
            test_kind=self.kind,
            profile_name="Profile 1",
            profile_code="100",
            materials=["Serum", "EDTA"],
            material_codes=["S", "E"],
        )

        FTPConnection.objects.create(
            laboratory=self.laboratory,
            host="ftp.example.com",
            user="user",
            password="password",
            upload_directory="/upload",
            results_directory="/results",
        )

    def test_spm_segment_has_no_linebreaks(self):
        patient_data = PatientDataSchema(
            birth_year="1990",
            gender="m",
            note="",
        )
        order = generate_hl7_order(self.visit, patient_data)
        lines = order.content.split("\n")

        spm_lines = [line for line in lines if line.startswith("SPM|")]
        self.assertEqual(len(spm_lines), 2)
        # Verify SPM|2| segment specifically has no internal linebreaks
        spm_2 = spm_lines[1]
        self.assertTrue(spm_2.startswith("SPM|2|"))
        self.assertNotIn("\r", spm_2)
        self.assertNotIn("\n", spm_2)
        self.assertIn("E^EDTA", spm_2)

    def test_profile_clean_raises_validation_error_on_newlines(self):
        invalid_profile = TestProfile(
            laboratory=self.laboratory,
            profile_name="Invalid Profile",
            profile_code="101",
            materials=["Serum\nSerum"],
            material_codes=["E\nE"],
        )
        with self.assertRaises(ValidationError) as ctx:
            invalid_profile.clean()

        self.assertIn("material_codes", ctx.exception.message_dict)
        self.assertIn("materials", ctx.exception.message_dict)
        self.assertIn(
            "comma-separated without line breaks",
            ctx.exception.message_dict["material_codes"][0],
        )

    @patch("labor.team_w.WindowsFTP_TLS")
    def test_upload_order_uses_hl7_extension(self, mock_ftp_class):
        mock_ftp_instance = MagicMock()
        mock_ftp_class.return_value.__enter__.return_value = mock_ftp_instance

        upload_order("MSH|...", self.laboratory)

        mock_ftp_instance.storbinary.assert_called_once()
        stor_arg = mock_ftp_instance.storbinary.call_args[0][0]
        self.assertTrue(
            stor_arg.startswith("STOR order_"),
            f"Expected command to start with STOR order_, got {stor_arg}",
        )
        self.assertTrue(
            stor_arg.endswith(".hl7"),
            f"Expected command to end with .hl7, got {stor_arg}",
        )
        self.assertFalse(
            stor_arg.endswith(".txt"),
            f"Command should not end with .txt, got {stor_arg}",
        )

