from .models import User
import json

def user_info(request):
    """Make the user image, name, and menu access available on all templates."""
    context = {"user_image": None, "user_name": None, "allowed_menus": []}
    
    if request.user.is_authenticated:
        try:
            # Get the custom user
            custom_user = User.objects.get(userid=request.user.username)
            
            # Add user info to context
            context["user_image"] = custom_user.image.url if custom_user.image else None
            context["user_name"] = custom_user.name
            
            # Add menu access info to context
            if request.user.is_superuser or custom_user.user_level == 'admin_level':
                # Admin users have access to all menus
                context["allowed_menus"] = "all"  # Special value for admins
            else:
                # Regular users get their assigned menus
                try:
                    context["allowed_menus"] = json.loads(custom_user.allowed_menus) if custom_user.allowed_menus else []
                except json.JSONDecodeError:
                    context["allowed_menus"] = []
                    
        except User.DoesNotExist:
            pass
            
    return context