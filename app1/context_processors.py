from .models import User

def user_info(request):
    """Make the user image and name available on all templates."""
    if request.user.is_authenticated:
        try:
            custom_user = User.objects.get(userid=request.user.username)
            return {
                "user_image": custom_user.image.url if custom_user.image else None,
                "user_name": custom_user.name,  # Add the user name
            }
        except User.DoesNotExist:
            return {"user_image": None, "user_name": None}
    return {"user_image": None, "user_name": None}
