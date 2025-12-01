"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
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
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/common/', include('common.urls')),
    path('api/v1/accounts/', include('accounts.urls')),
    path('api/v1/policies/', include('policies.urls')),
    path('api/v1/attendance/', include('attendance.urls')),
    path('api/v1/projects/', include('projects.urls')),
    path('api/v1/clients/', include('clients.urls')),
    path('api/v1/quotations/', include('clients.quotations_urls')),
    path('api/v1/assets/', include('assets.urls')),
    path('api/v1/resources/', include('resources.urls')),
    path('api/v1/audit/', include('audit.urls')),
    path('api/v1/leave/', include('leave.urls')),
    path('api/v1/files/', include('files.urls')),
    path('api/v1/announcement/', include('announcement.urls')),
    path('api/v1/', include('notifications.urls')),  # FCM notifications
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

