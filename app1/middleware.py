import json
from .models import User
from django.utils.deprecation import MiddlewareMixin




class UserMenuMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # Don't do anything for anonymous users
        if not request.user.is_authenticated:
            return None
            
        # Always refresh the allowed_menus in each request
        # This ensures if permissions change, they're immediately reflected
        if hasattr(request, 'session'):
            # For superusers, no need to check permissions
            if request.user.is_superuser:
                request.session['allowed_menus'] = "all"
                return None
                
            # For others, get custom_user_id from session
            custom_user_id = request.session.get('custom_user_id')
            if custom_user_id:
                try:
                    custom_user = User.objects.get(id=custom_user_id)
                    # Try to parse allowed_menus
                    try:
                        allowed_menus = json.loads(custom_user.allowed_menus) if custom_user.allowed_menus else []
                    except json.JSONDecodeError:
                        allowed_menus = []
                    request.session['allowed_menus'] = allowed_menus
                except User.DoesNotExist:
                    # If user doesn't exist anymore, don't update allowed_menus
                    pass
                    
        return None
    


class NoCacheMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        if request.user.is_authenticated:
            # Add headers to prevent caching for authenticated users
            response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
        return response