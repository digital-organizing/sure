from typing import Any, Optional
from ninja.security.apikey import APIKeyHeader

from .models import APIToken


class TenantTokenAuth(APIKeyHeader):
    param_name = "X-Tenant-Token"

    def authenticate(self, request, key: Optional[str]) -> Optional[Any]:
        name, token = key.split(":", 1) if key and ":" in key else (None, None)
        if not name or not token:
            return None

        token = token = APIToken.objects.filter(name=name, token=token).first()

        if token and not token.revoked:
            request.user = token.owner
            return token.tenant


auth_tenant_api_token = TenantTokenAuth()
