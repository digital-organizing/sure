def auth_2fa_or_trusted(request) -> bool:
    return request.user.is_authenticated and (
        request.user.is_verified() or request.agent.is_trusted
    )


def auth_2fa(request) -> bool:
    return request.user.is_authenticated and request.user.is_verified()
