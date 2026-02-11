from django.urls import path

# from .views import download_visit_export
import sure.views

app_name = "sure"


urlpatterns = [
    path(
        "download-visit-export/<int:pk>/",
        sure.views.download_visit_export,
        name="download_visit_export",
    ),
]
