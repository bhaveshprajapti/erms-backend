from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    UserViewSet, OrganizationViewSet, RoleViewSet, 
    PermissionViewSet, ModuleViewSet, ProfileUpdateRequestViewSet,
    EmployeePaymentViewSet, custom_login, custom_logout
)

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'organizations', OrganizationViewSet)
router.register(r'roles', RoleViewSet)
router.register(r'permissions', PermissionViewSet)
router.register(r'modules', ModuleViewSet)
router.register(r'profile-update-requests', ProfileUpdateRequestViewSet, basename='profileupdaterequest')
router.register(r'employee-payments', EmployeePaymentViewSet, basename='employeepayment')

urlpatterns = [
    path('login/', custom_login, name='custom_login'),
    path('logout/', custom_logout, name='custom_logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('', include(router.urls)),
]
