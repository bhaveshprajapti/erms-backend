from django.urls import path, include
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet, OrganizationViewSet, RoleViewSet, 
    PermissionViewSet, ModuleViewSet
)

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'organizations', OrganizationViewSet)
router.register(r'roles', RoleViewSet)
router.register(r'permissions', PermissionViewSet)
router.register(r'modules', ModuleViewSet)

urlpatterns = [
    path('login', obtain_auth_token, name='api_token_auth'),
    path('', include(router.urls)),
]
