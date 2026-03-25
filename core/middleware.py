class CaddyUserLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Add the user to the header if authenticated
        if request.user.is_authenticated:
            response["X-Caddy-User"] = request.user.get_username()

        return response
