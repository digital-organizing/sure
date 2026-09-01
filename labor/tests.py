import base64
from pathlib import Path

import hl7
from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from labor.models import (
    LabOrder,
    LabOrderCounter,
    Laboratory,
    LocationToLab,
    OrderStatus,
    ResultMapping,
    TestProfile,
)
from labor.service import (
    _normalize_segments,
    _unescape_hl7_text,
    extract_embedded_documents,
    parse_hl7_to_db,
)
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
    VisitStatus,
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
        """Returns the sample exactly as retrieve_results delivers it.

        Read as bytes and decoded, so the file's CRLF separators survive as-is
        instead of being folded by universal newlines. parse_hl7_to_db is
        responsible for normalizing them.
        """
        sample_path = Path(__file__).resolve().parents[0] / "bsp_result.hl7"
        return sample_path.read_bytes().decode("utf-8")

    def test_parse_hl7_to_db_imports_mappings_and_profile_fallback(self):
        content = self._load_sample_hl7()

        lab_result = parse_hl7_to_db(content)

        self.order.refresh_from_db()

        self.assertEqual(lab_result.order, self.order)
        self.assertEqual(lab_result.visit, self.visit)
        self.assertEqual(lab_result.content, _normalize_segments(content))
        self.assertNotIn("\n", lab_result.content)
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

    def test_parse_hl7_to_db_accepts_lf_and_crlf_separators(self):
        """The lab ships CRLF; other senders ship bare LF. Both must ingest."""
        crlf = self._load_sample_hl7()
        lf = crlf.replace("\r\n", "\n")

        for label, content in (("CRLF", crlf), ("LF", lf)):
            with self.subTest(separator=label):
                TestResult.objects.all().delete()
                Test.objects.filter(visit=self.visit).delete()
                VisitNote.objects.filter(visit=self.visit).delete()

                parse_hl7_to_db(content)

                self.assertEqual(TestResult.objects.count(), 4)

    def test_parse_hl7_to_db_keeps_deleted_tests_deleted(self):
        """A result arriving for a test the consultant deleted is stored on that
        test, but must not resurrect it -- a visit log flags the situation."""
        deleted_test = Test.objects.create(
            visit=self.visit,
            test_kind=self.kind_hiv,
        )
        deleted_test.mark_deleted(user=self.owner)

        parse_hl7_to_db(self._load_sample_hl7())

        deleted_test.refresh_from_db()
        self.assertIsNotNone(deleted_test.deleted_at)
        self.assertEqual(deleted_test.results.count(), 1)
        # No duplicate was created next to the deleted one.
        self.assertEqual(
            Test.all_objects.filter(visit=self.visit, test_kind=self.kind_hiv).count(),
            1,
        )

        log = self.visit.logs.filter(
            action__startswith="Received lab result for deleted test"
        ).get()
        self.assertIn("HIV PCR", log.action)

    def test_parse_hl7_to_db_sets_visit_status(self):
        parse_hl7_to_db(self._load_sample_hl7())

        self.visit.refresh_from_db()
        self.assertEqual(self.visit.status, VisitStatus.RESULTS_RECORDED)

    def test_parse_hl7_to_db_rejects_non_result_messages(self):
        """Our own OML orders land in the results directory; they must not
        be ingested as results and silently complete the order."""
        order_path = Path(__file__).resolve().parents[0] / "bsp_order.hl7"
        content = order_path.read_bytes().decode("utf-8")

        with self.assertRaises(ValueError) as ctx:
            parse_hl7_to_db(content)

        self.assertIn("expected ORU", str(ctx.exception))

        self.order.refresh_from_db()
        self.visit.refresh_from_db()
        self.assertNotEqual(self.order.status, OrderStatus.COMPLETED)
        self.assertNotEqual(self.visit.status, VisitStatus.RESULTS_RECORDED)
        self.assertEqual(TestResult.objects.count(), 0)

    def test_unescape_hl7_text_turns_br_escapes_into_newlines(self):
        """The lab puts \\.br\\ inside OBX-5 values, not only in NTE segments."""
        raw = (
            "Crescita abbondante di Actinotignum schaalii\\.br\\ "
            "Crescita moderata di Streptococcus anginosus\\.br\\\\.br\\"
            "S=Sensibel, R=Resistent\\.br\\"
        )

        unescaped = _unescape_hl7_text(raw)

        self.assertEqual(
            unescaped,
            "Crescita abbondante di Actinotignum schaalii\n "
            "Crescita moderata di Streptococcus anginosus\n\n"
            "S=Sensibel, R=Resistent\n",
        )
        # No stray backslashes or half-eaten escapes left behind.
        self.assertNotIn("\\", unescaped)
        self.assertNotIn(".br", unescaped)

    def test_unescape_hl7_text_handles_missing_closing_backslash(self):
        self.assertEqual(_unescape_hl7_text("erste\\.brzweite"), "erste\nzweite")

    def test_unescape_hl7_text_leaves_plain_values_untouched(self):
        for value in ("negativ", "0.8", ">1000000 germi/ml", "<1.0"):
            with self.subTest(value=value):
                self.assertEqual(_unescape_hl7_text(value), value)

    def test_normalize_segments_drops_blank_segments(self):
        normalized = _normalize_segments("MSH|^~\\&|A\n\nPID|1\r\n\r\nORC|NW|1\n")

        self.assertEqual(normalized, "MSH|^~\\&|A\rPID|1\rORC|NW|1")


IN_MEMORY_STORAGE = {
    "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


@override_settings(STORAGES=IN_MEMORY_STORAGE)
class EmbeddedDocumentTests(TestCase):
    """MDM^T02 messages carry the report as a base64 PDF instead of results."""

    def setUp(self):
        self.owner = User.objects.create_user(username="doc_owner", password="pw")
        self.tenant = Tenant.objects.create(name="Tenant Doc", owner=self.owner)
        self.location = Location.objects.create(tenant=self.tenant, name="Center Doc")
        self.case = Case.objects.create(id="9184722", location=self.location)
        self.questionnaire = Questionnaire.objects.create(name="Q Doc")
        self.visit = Visit.objects.create(
            case=self.case, questionnaire=self.questionnaire
        )

        self.laboratory = Laboratory.objects.create(name="Lab Doc")
        self.counter = LabOrderCounter.objects.create(
            nr_kreis="9611",
            base_number="0001297740",
            last_index=59,
        )
        LocationToLab.objects.create(
            labor=self.laboratory,
            location=self.location,
            client_code="TEAMW",
            nr_kreis="9611",
        )
        # The sample only names our order number inside the document file name;
        # its ORC-2 carries the laboratory's own number.
        self.order = LabOrder.objects.create(
            visit=self.visit,
            lab_order_counter=self.counter,
            order_number="96100001297799",
        )

    def _load_sample_hl7(self):
        sample_path = Path(__file__).resolve().parents[0] / "bsp_document.hl7"
        return sample_path.read_bytes().decode("utf-8")

    def test_extract_embedded_documents_returns_named_pdf(self):
        h = hl7.parse(_normalize_segments(self._load_sample_hl7()))

        documents = extract_embedded_documents(h)

        self.assertEqual(len(documents), 1)
        self.assertEqual(
            documents[0].filename,
            "XXWPET.ANONYM_SUF-91FK6GJ__96100001297799__Y260668679.pdf",
        )
        self.assertTrue(documents[0].content.startswith(b"%PDF-"))

    def test_parse_hl7_to_db_attaches_document_to_visit(self):
        lab_result = parse_hl7_to_db(self._load_sample_hl7())

        self.assertEqual(lab_result.order, self.order)

        document = self.visit.documents.get()
        self.assertTrue(document.hidden)
        self.assertIsNone(document.user)
        self.assertEqual(document.document.read()[:5], b"%PDF-")

    def test_parse_hl7_to_db_leaves_status_untouched_for_documents(self):
        """A report PDF accompanies the results, it does not replace them."""
        parse_hl7_to_db(self._load_sample_hl7())

        self.visit.refresh_from_db()
        self.order.refresh_from_db()
        self.assertNotEqual(self.visit.status, VisitStatus.RESULTS_RECORDED)
        self.assertNotEqual(self.order.status, OrderStatus.COMPLETED)
        self.assertEqual(TestResult.objects.count(), 0)

    def test_parse_hl7_to_db_does_not_duplicate_redelivered_documents(self):
        content = self._load_sample_hl7()

        parse_hl7_to_db(content)
        parse_hl7_to_db(content)

        self.assertEqual(self.visit.documents.count(), 1)

    def test_parse_hl7_to_db_rejects_document_without_matching_order(self):
        self.order.delete()

        with self.assertRaises(ValueError) as ctx:
            parse_hl7_to_db(self._load_sample_hl7())

        self.assertIn("Lab order not found", str(ctx.exception))

    def test_result_message_attaches_embedded_report(self):
        """An ORU may carry the report inline; it must not become a result."""
        pdf = b"%PDF-1.5\n" + b"0" * 200
        encoded = base64.b64encode(pdf).decode("ascii")
        content = "\r".join(
            [
                "MSH|^~\\&|LX|TEAMW|LTW||20260303112942||ORU^R01|1|P|2.4||||||8859/1",
                "PID|1|SUF-iar9ar7|9184722^^^^^TEAMW||ANONYM^SUF-IAR9AR7||19970101|M",
                "ORC|NW|96100001297799|Y26019305734^LX|Y260193057^LX|CM",
                f"OBX|1|ED|REPORT^Befund^LX||^application^PDF^Base64^{encoded}|||||||F",
            ]
        )

        parse_hl7_to_db(content)

        self.assertEqual(TestResult.objects.count(), 0)
        document = self.visit.documents.get()
        self.assertEqual(document.name, "lab_report_1.pdf")
        self.assertEqual(document.document.read(), pdf)


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

