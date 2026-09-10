from typing import Any

from ninja.security.apikey import APIKeyHeader

from .models import APIToken


class TenantTokenAuth(APIKeyHeader):
    param_name = "X-Tenant-Token"

    def authenticate(self, request, key: str | None) -> Any | None:
        name, token = key.split(":", 1) if key and ":" in key else (None, None)
        if not name or not token:
            return None

        api_token = APIToken.objects.filter(name=name, token=token).first()

        if api_token and not api_token.revoked:
            request.user = api_token.owner
            return api_token.tenant


auth_tenant_api_token = TenantTokenAuth()
