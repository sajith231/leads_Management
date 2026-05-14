# app2/api_urls.py
# Dedicated URLs for API endpoints only (for mobile app)
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# API Router 
router = DefaultRouter()
router.register(r'feeders', views.FeederViewSet, basename='feeder-api')

urlpatterns = [
    # Router URLs (provides CRUD operations)
    path('', include(router.urls)),
    
    # Additional API endpoints
    path('feeder-status-choices/', views.feeder_status_choices, name='api-feeder-status-choices'),
    path('feeder-business-nature-choices/', views.feeder_business_nature_choices, name='api-feeder-business-nature-choices'),
]
