from django.shortcuts import redirect
from django.urls import resolve

EXCLUDED_APPS = ['flutter', 'image_capture', 'my_drive']
EXCLUDED_PATHS = ['/login/', '/logout/', '/admin/login/','/']

class LoginRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        
        # Allow login & excluded paths
        if request.path in EXCLUDED_PATHS:
            return self.get_response(request)

        # Get app name safely
        try:
            app_name = resolve(request.path_info).app_name
        except:
            app_name = None

        # Allow excluded apps
        if app_name in EXCLUDED_APPS:
            return self.get_response(request)

        # Block all other pages
        if not request.user.is_authenticated:
            return redirect('login')

        return self.get_response(request)
