# rrc_clients_new/views.py

import requests
from django.shortcuts import render
from django.http import JsonResponse

EXTERNAL_API = 'https://accmaster.imcbs.com/api/sync/rrc-clients/'

def rrc_clients2_list(request):
    return render(request, "rrc_client2_list.html")

def rrc_clients2_api(request):
    """Proxy endpoint — browser calls this, Django fetches the external API."""
    try:
        resp = requests.get(EXTERNAL_API, timeout=15)
        resp.raise_for_status()
        return JsonResponse(resp.json(), safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=502)