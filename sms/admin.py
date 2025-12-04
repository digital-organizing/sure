from django.contrib import admin
from unfold.admin import ModelAdmin

# Register your models here.
from .models import SMSMessage


@admin.register(SMSMessage)
class SMSMessageAdmin(ModelAdmin):
    list_display = ("to", "sent_at")
    readonly_fields = ("to", "sent_at", "response")
    ordering = ("-sent_at",)
