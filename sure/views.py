from django.views.generic import TemplateView
from unfold.views import UnfoldModelAdminViewMixin


class CaseDashboardView(UnfoldModelAdminViewMixin, TemplateView):
    """Admin view for the case dashboard."""

    title = "Case Dashboard"
    template_name = "admin/sure/case_dashboard.html"
