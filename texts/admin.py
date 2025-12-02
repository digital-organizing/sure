from django.conf import settings
import io
from django.contrib import admin
import polars as pl
from django.http import HttpRequest, HttpResponse
from modeltranslation.admin import TabbedTranslationAdmin
from unfold.admin import ModelAdmin

from texts.models import Text

# Register your models here.


@admin.register(Text)
class TextAdmin(ModelAdmin, TabbedTranslationAdmin):
    list_display = ("slug", "context", "internal")
    search_fields = ("slug", "context")
    list_filter = ("internal",)

    actions = ["export_as_excel"]

    @admin.action(description="Export as Excel")
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
