from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ClientViewSet, ClientRoleViewSet, QuotationViewSet

router = DefaultRouter()
router.register(r'clients', ClientViewSet)
router.register(r'client-roles', ClientRoleViewSet)
router.register(r'quotations', QuotationViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
