from urllib.parse import parse_qs, urlparse

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import translation
from storages.backends.s3 import S3Storage

from sure.export import generate_pdfs
from sure.models import (
    Case,
    Questionnaire,
    Visit,
    VisitDocument,
    signed_download_url,
)
from tenants.models import Location, Tenant

IN_MEMORY_STORAGE = {
    "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


@override_settings(STORAGES=IN_MEMORY_STORAGE)
class VisitDocumentStorageTests(TestCase):
    def setUp(self):
        owner = User.objects.create_user(username="doc_owner", password="pw")
        tenant = Tenant.objects.create(name="Tenant Doc", owner=owner)
        location = Location.objects.create(tenant=tenant, name="Center Doc")
        questionnaire = Questionnaire.objects.create(name="Q Doc")
        self.visits = [
            Visit.objects.create(
                case=Case.objects.create(id=case_id, location=location),
                questionnaire=questionnaire,
            )
            for case_id in ("9184722", "9184723")
        ]

    def _upload(self, visit):
        return VisitDocument.objects.create(
            visit=visit,
            name="Lab report",
            document=SimpleUploadedFile("Befund Mai.PDF", b"%PDF-1.5"),
        )

    def test_same_file_name_gets_separate_keys(self):
        first, second = (self._upload(visit) for visit in self.visits)

        for document, visit in zip((first, second), self.visits):
            self.assertRegex(
                document.document.name,
                rf"^visit_documents/{visit.pk}/[0-9a-f]{{32}}\.pdf$",
            )
        self.assertNotEqual(first.document.name, second.document.name)

    def test_uploaded_file_name_is_kept(self):
        document = self._upload(self.visits[0])

        document.refresh_from_db()
        self.assertEqual(document.name, "Lab report")
        self.assertEqual(document.filename, "Befund Mai.PDF")

    def test_s3_link_downloads_under_the_original_name(self):
        document = self._upload(self.visits[0])
        document.document.storage = S3Storage(
            access_key="key",
            secret_key="secret",
            bucket_name="bucket",
            region_name="us-east-1",
            querystring_auth=True,
        )

        query = parse_qs(urlparse(document.download_link()).query)

        self.assertEqual(
            query["response-content-disposition"],
            ['attachment; filename="Befund Mai.PDF"'],
        )

    def test_other_storages_fall_back_to_the_plain_url(self):
        document = VisitDocument(visit=self.visits[0], name="x")
        document.document.save("a.pdf", ContentFile(b"%PDF-1.5"), save=False)

        self.assertEqual(
            signed_download_url(document.document, ""), document.document.url
        )


@override_settings(STORAGES=IN_MEMORY_STORAGE)
class QuestionnairePdfTests(TestCase):
    def test_regenerating_replaces_the_old_pdfs(self):
        questionnaire = Questionnaire.objects.create(name="Q Pdf")

        # generate_pdfs leaves its last language active
        with translation.override("en"):
            generate_pdfs(questionnaire)
            questionnaire.refresh_from_db()
            first = questionnaire.client_pdf_en.name
            generate_pdfs(questionnaire)
            questionnaire.refresh_from_db()

        self.assertEqual(questionnaire.client_pdf_en.name, first)
        _, files = default_storage.listdir("questionnaire_pdfs")
        self.assertEqual(len(files), 2 * len(settings.LANGUAGES))
