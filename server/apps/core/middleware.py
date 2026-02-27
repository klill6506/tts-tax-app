"""Custom middleware for the TTS Tax App."""

from django.middleware.csrf import get_token


class EnsureCsrfCookieMiddleware:
    """Ensure the CSRF cookie is set on every response.

    The React SPA needs the csrftoken cookie available before its first POST
    (e.g. login). Since the SPA is served as a static file (not a Django
    template), Django won't set the cookie by default. This middleware forces it.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        get_token(request)  # marks the cookie for inclusion in the response
        return self.get_response(request)
