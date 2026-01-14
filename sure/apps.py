from django.apps import AppConfig
from django.contrib.admin.apps import AdminConfig


class SureConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "sure"
    verbose_name = "Sure"

    def ready(self) -> None:
        from django.contrib import \
            admin  # pylint: disable=import-outside-toplevel
        from django.contrib.admin import \
            sites  # pylint: disable=import-outside-toplevel

        from core.admin import \
            admin_site  # pylint: disable=import-outside-toplevel

        admin.site = admin_site
        sites.site = admin_site
        return super().ready()


class SureAdminConfig(AdminConfig):
    default_site = "core.admin.MyAdminSite"
