from collections.abc import Callable

from django.http import HttpRequest, HttpResponse


def head_without_body(get_response: Callable[[HttpRequest], HttpResponse]):
    """Views answer HEAD exactly like GET; this drops the body, as HTTP requires.

    gunicorn sends whatever body the app returns, even for HEAD. Listed last so the outer
    middleware sees the empty body and sets Content-Length to match.
    """

    def middleware(request: HttpRequest) -> HttpResponse:
        response = get_response(request)
        if request.method == "HEAD" and not response.streaming:
            response.content = b""
        return response

    return middleware
