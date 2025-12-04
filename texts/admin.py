import io

import polars as pl
from django.conf import settings
from django.contrib import admin
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import URLPattern, path, reverse
from modeltranslation.admin import TabbedTranslationAdmin
from unfold.admin import ModelAdmin
from unfold.decorators import action

from texts.models import Text
from texts.views import ImportTextView

# Register your models here.


@admin.register(Text)
class TextAdmin(ModelAdmin, TabbedTranslationAdmin):
    list_display = ("slug", "context", "internal")
    search_fields = ("slug", "context")
    list_filter = ("internal",)

    actions = ["export_as_excel"]
    actions_list = ["export_all_texts", "import_texts"]

    @action(description="Export as Excel")
    def export_as_excel(self, request: HttpRequest, queryset):
        records = queryset.values(
            "slug",
            "context",
            "internal",
            *[f"content_{lang_code}" for lang_code, _ in settings.LANGUAGES],
        )
        df = pl.from_records(list(records))

        output = io.BytesIO()
        df.write_excel(output)

        output.seek(0)
        response = HttpResponse(
            output.read(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = "attachment; filename=texts.xlsx"
        return response

    @action(description="Export all texts", icon="download")
    def export_all_texts(self, request: HttpRequest):
        return self.export_as_excel(request, self.get_queryset(request))

    @action(description="Import Texts", icon="upload")
    def import_texts(self, request: HttpRequest):
        return redirect(reverse("admin:texts_import"))

    def get_urls(self) -> list[URLPattern]:
        import_view = self.admin_site.admin_view(
            ImportTextView.as_view(model_admin=self)
        )
        return [
            path("import/", import_view, name="texts_import"),
        ] + super().get_urls()
