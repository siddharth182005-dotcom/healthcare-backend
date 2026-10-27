"""JSON versions of Django's 404 / 500 pages (so API clients never get HTML)."""
from django.http import JsonResponse


def not_found(request, exception=None):
    return JsonResponse({"detail": "Not found."}, status=404)


def server_error(request):
    return JsonResponse({"detail": "Internal server error."}, status=500)
