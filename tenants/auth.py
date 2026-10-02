from typing import Any

from ninja.security.apikey import APIKeyHeader

from .models import APIToken


class TenantTokenAuth(APIKeyHeader):
    param_name = "X-Tenant-Token"

    def authenticate(self, request, key: str | None) -> Any | None:
        name, token = key.split(":", 1) if key and ":" in key else (None, None)
        if not name or not token:
            return None

        for api_token in APIToken.objects.filter(name=name, revoked=False):
            if api_token.matches(token):
                request.user = api_token.owner
                return api_token.tenant
        return None


auth_tenant_api_token = TenantTokenAuth()
