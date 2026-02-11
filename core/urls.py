"""URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import include, path
from django.views.generic.base import TemplateView

import core.api

urlpatterns = [
    path("admin/", admin.site.urls),
    # path("admin-old/", admin.site.urls),
    path("i18n/", include("django.conf.urls.i18n")),
    path("api/", core.api.api.urls),
    path("ht/", include("health_check.urls")),
    path("sure/", include("sure.urls")),
    path("", TemplateView.as_view(template_name="index.html")),
    path("<path:path>", TemplateView.as_view(template_name="index.html")),
]
