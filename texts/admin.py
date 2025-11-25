from django.contrib import admin
from modeltranslation.admin import TabbedTranslationAdmin
from unfold.admin import ModelAdmin

from texts.models import Text

# Register your models here.


@admin.register(Text)
class TextAdmin(ModelAdmin, TabbedTranslationAdmin):
    list_display = ("slug", "context", "internal")
    search_fields = ("slug", "context")
    list_filter = ("internal",)
