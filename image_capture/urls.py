from django.urls import path
from . import views

urlpatterns = [
    
    path('generate/', views.image_capture_form, name='image_capture_form'),
    path('capture/<uuid:unique_id>/', views.capture_link_view, name='capture_link'),
    path('verify_otp/<uuid:unique_id>/', views.verify_otp, name='verify_otp'),
    path('submit_image/<uuid:unique_id>/', views.submit_image, name='submit_image'),
]
