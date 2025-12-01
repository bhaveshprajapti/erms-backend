# notifications/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FCMTokenViewSet, NotificationViewSet

router = DefaultRouter()
router.register(r'fcm-tokens', FCMTokenViewSet, basename='fcm-token')
router.register(r'notifications', NotificationViewSet, basename='notification')

urlpatterns = [
    path('', include(router.urls)),
]
