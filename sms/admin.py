from django.contrib import admin
from django.http import HttpRequest
from django.shortcuts import redirect
from django.urls import URLPattern, path, reverse
from unfold.admin import ModelAdmin
from unfold.decorators import action

from .models import SMSMessage
from .views import SMSUsageExportView


@admin.register(SMSMessage)
class SMSMessageAdmin(ModelAdmin):
    list_display = ("to", "sent_at", "tenant", "location", "category")
    list_filter = ("category", "tenant")
    readonly_fields = ("to", "sent_at", "response", "tenant", "location", "category")
    ordering = ("-sent_at",)

    actions_list = ["export_usage"]

    @action(
        description="Export SMS usage", icon="download", permissions=["export_usage"]
    )
    def export_usage(self, request: HttpRequest):
        return redirect(reverse("admin:sms_smsmessage_export_usage_view"))

    def has_export_usage_permission(self, request: HttpRequest) -> bool:
        return getattr(request.user, "is_superuser", False)

    def get_urls(self) -> list[URLPattern]:
        export_view = self.admin_site.admin_view(
            SMSUsageExportView.as_view(model_admin=self)
        )
        return [
            path("export-usage/", export_view, name="sms_smsmessage_export_usage_view"),
        ] + super().get_urls()
