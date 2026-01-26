from django.shortcuts import redirect
from .models import VisitExport, VisitExportDownload
from django.core.exceptions import PermissionDenied
from core.auth import require_2fa_or_trusted


@require_2fa_or_trusted
def download_visit_export(request, pk):
    visit_export = VisitExport.objects.get(pk=pk)

    if not request.user.is_superuser:
        export_tenant = visit_export.user.consultant.tenant_id
        user_tenant = request.user.consultant.tenant_id

        if export_tenant != user_tenant:
            raise PermissionDenied(
                "You do not have permission to download this export."
            )

    redirect_url = visit_export.file.url
    VisitExportDownload.objects.create(
        visit_export=visit_export,
        user=request.user,
    )
    # Logic to handle the download process would go here
    return redirect(redirect_url)
