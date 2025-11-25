from django.shortcuts import redirect

# Apps and paths that should not require login
EXCLUDED_APPS = ['flutter', 'image_capture', 'my_drive','app4']
EXCLUDED_PATHS = ['/login/', '/logout/', '/admin/login/', '/']

class LoginRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Allow login and explicitly excluded paths
        if request.path in EXCLUDED_PATHS:
            return self.get_response(request)

        # Allow requests starting with excluded app paths
        for app in EXCLUDED_APPS:
            if request.path.startswith(f'/{app}/'):
                return self.get_response(request)

        # If user is not logged in, redirect to login page
        if not request.user.is_authenticated:
            return redirect('login')

        # Otherwise, allow normal processing
        return self.get_response(request)
