"""
URL configuration for leads project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings
from app2 import views 
from app2 import views as app2_views 

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('app1.urls')),
    path('app2/', include('app2.urls')),
    path('app3/', include('app3.urls')),
    path('app4/', include('app4.urls')),  # This includes api/clients/
    path('flutter/', include('flutter.urls')),
    path('app5/', include('app5.urls')),
    path('sim_card/', include('sim_card.urls')),
    path('fuel_management/', include('fuel_management.urls')),
    path('my_drive/', include('my_drive.urls')),
    path('edit-field/<int:field_id>/', views.edit_field, name='edit_field'),
    path('feeder/', include('app2.urls')), 
    path('feeder/<int:feeder_id>/status-update/', app2_views.feeder_status_update, name='feeder_status_update'),
    path('wfh_request/', include('wfh_Request.urls')),
    path('', include('punchout_reminder.urls')),



] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)