from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    UserViewSet, OrganizationViewSet, RoleViewSet, 
    PermissionViewSet, ModuleViewSet, ProfileUpdateRequestViewSet,
    custom_login
)

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'organizations', OrganizationViewSet)
router.register(r'roles', RoleViewSet)
router.register(r'permissions', PermissionViewSet)
router.register(r'modules', ModuleViewSet)
router.register(r'profile-update-requests', ProfileUpdateRequestViewSet, basename='profileupdaterequest')

urlpatterns = [
    path('login', custom_login, name='custom_login'),
    path('token/refresh', TokenRefreshView.as_view(), name='token_refresh'),
    path('', include(router.urls)),
]
